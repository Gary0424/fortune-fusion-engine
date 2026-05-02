"""
多命理融合预测引擎 - API 服务 v2
集成: Redis 缓存 + PostgreSQL + Prometheus 监控 + 熔断降级
"""
import asyncio
import time
import uuid
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Prometheus 可选依赖
try:
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from calc_engine import (
    BaZiSystem, ZiWeiSystem, QiZhengSystem, AstrologySystem,
    QiMenSystem, LiuRenSystem, LiuYaoSystem, MeiHuaSystem,
    NumerologySystem, NameologySystem,
    BaseFortuneSystem, CalculationResult
)
from fusion_engine import FusionEngine, FusionResult
from utils.cache import CacheManager, cache_manager
from utils.metrics import (
    REQUEST_COUNT, REQUEST_LATENCY, REQUEST_IN_PROGRESS,
    CALCULATION_COUNT, CALCULATION_LATENCY, CALCULATION_ERRORS,
    FUSION_SCORE, FUSION_UNCERTAINTY, FUSION_LATENCY, FUSION_CONFLICTS,
    ACTIVE_SYSTEMS, SYSTEM_WEIGHT, ERROR_BUDGET_REMAINING, APP_INFO,
)

logger = logging.getLogger("ffe.api")

# ============== 配置 ==============

class ServiceConfig:
    """服务配置"""
    VERSION = "2.0.0"
    
    # SLO 定义
    SLO_AVAILABILITY = 0.9999       # 99.99%
    SLO_P99_LATENCY_MS = 1000       # 1s
    SLO_ERROR_RATE = 0.001          # 0.1%
    
    # 熔断配置
    CIRCUIT_BREAKER_THRESHOLD = 5   # 连续失败次数
    CIRCUIT_BREAKER_TIMEOUT = 30    # 熔断恢复超时(秒)
    
    # 缓存 TTL
    CACHE_TTL_LIFETIME = 86400     # 终身格局: 24h
    CACHE_TTL_YEARLY = 43200       # 年度趋势: 12h
    CACHE_TTL_MONTHLY = 21600      # 月度趋势: 6h
    CACHE_TTL_EVENT = 3600         # 具体事件: 1h
    
    SCENE_CACHE_TTL = {
        "终身格局": CACHE_TTL_LIFETIME,
        "年度趋势": CACHE_TTL_YEARLY,
        "月度趋势": CACHE_TTL_MONTHLY,
        "具体事件": CACHE_TTL_EVENT,
        "性格分析": CACHE_TTL_LIFETIME,
        "健康风险": CACHE_TTL_YEARLY,
    }
    
    # 限流
    RATE_LIMIT_PER_MINUTE = 6000   # 生产环境建议60, 压测可调高
    RATE_LIMIT_BURST = 100


config = ServiceConfig()


# ============== 数据模型 (API 层) ==============

class BirthInfo(BaseModel):
    year: int = Field(..., ge=1900, le=2100)
    month: int = Field(..., ge=1, le=12)
    day: int = Field(..., ge=1, le=31)
    hour: int = Field(..., ge=0, le=23)
    minute: int = Field(0, ge=0, le=59)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class QueryRequest(BaseModel):
    user_id: Optional[str] = Field(None)
    birth_info: BirthInfo
    gender: str = Field(..., pattern="^(male|female)$")
    name: Optional[str] = Field(None)
    scene: str = Field(
        "终身格局",
        pattern="^(终身格局|年度趋势|月度趋势|具体事件|性格分析|健康风险)$"
    )
    query_time: Optional[datetime] = Field(None)
    specific_question: Optional[str] = Field(None)


class SystemResultOut(BaseModel):
    system: str; score: float; confidence: float; trend: str
    risk_level: str; calculation_time_ms: int; cached: bool


class FusionResultOut(BaseModel):
    score: float; uncertainty: float; trend: str; risk_level: str
    reliability: str; consensus: Dict[str, Any]
    conflicts: Optional[List[Dict]]; contributing_systems: List[Dict]
    calculation_time_ms: int


class QueryResponse(BaseModel):
    request_id: str; timestamp: datetime; scene: str
    individual_results: List[SystemResultOut]; fusion_result: FusionResultOut
    total_calculation_time_ms: int; from_cache: bool


class HealthResponse(BaseModel):
    status: str; version: str; uptime_seconds: float
    systems_available: List[str]; cache_stats: Dict[str, Any]
    circuit_breaker_status: Dict[str, str]


class FeedbackRequest(BaseModel):
    request_id: str
    accuracy_feedback: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


# ============== 熔断器 ==============

class CircuitBreaker:
    """命理体系熔断器"""
    
    def __init__(self, threshold: int = 5, timeout: int = 30):
        self.threshold = threshold
        self.timeout = timeout
        self.failure_counts: Dict[str, int] = {}
        self.last_failure: Dict[str, float] = {}
        self.states: Dict[str, str] = {}  # closed, open, half_open
    
    def is_available(self, system: str) -> bool:
        state = self.states.get(system, "closed")
        if state == "closed":
            return True
        if state == "open":
            # 检查是否超时进入 half_open
            if time.time() - self.last_failure.get(system, 0) > self.timeout:
                self.states[system] = "half_open"
                return True
            return False
        if state == "half_open":
            return True
        return False
    
    def record_success(self, system: str):
        self.failure_counts[system] = 0
        self.states[system] = "closed"
    
    def record_failure(self, system: str):
        self.failure_counts[system] = self.failure_counts.get(system, 0) + 1
        self.last_failure[system] = time.time()
        if self.failure_counts[system] >= self.threshold:
            self.states[system] = "open"
            logger.warning(f"[CB] Circuit breaker OPEN: {system}")
    
    def get_status(self) -> Dict[str, str]:
        return {k: self.states.get(k, "closed") for k in self.failure_counts}


# ============== 限流器 ==============

class RateLimiter:
    """滑动窗口限流"""
    
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, list] = {}
    
    def is_allowed(self, client_id: str) -> bool:
        now = time.time()
        if client_id not in self.requests:
            self.requests[client_id] = []
        
        # 清理过期请求
        self.requests[client_id] = [
            t for t in self.requests[client_id]
            if now - t < self.window_seconds
        ]
        
        if len(self.requests[client_id]) >= self.max_requests:
            return False
        
        self.requests[client_id].append(now)
        return True


# ============== 全局状态 ==============

class AppState:
    def __init__(self):
        self.start_time = time.time()
        self.systems: Dict[str, BaseFortuneSystem] = {}
        self.fusion_engine = FusionEngine()
        self.cache: CacheManager = cache_manager
        self.circuit_breaker = CircuitBreaker(
            threshold=config.CIRCUIT_BREAKER_THRESHOLD,
            timeout=config.CIRCUIT_BREAKER_TIMEOUT,
        )
        self.rate_limiter = RateLimiter(
            max_requests=config.RATE_LIMIT_PER_MINUTE
        )
        self.request_count = 0
        self.error_count = 0
        self.db_session_factory = None
    
    def get_uptime(self) -> float:
        return time.time() - self.start_time


app_state = AppState()


# ============== 中间件 ==============

async def metrics_middleware(request: Request, call_next):
    """Prometheus 指标采集中间件（可选）"""
    if not PROMETHEUS_AVAILABLE:
        return await call_next(request)
    
    method = request.method
    path = request.url.path
    
    # 排除 metrics 端点自身
    if path == "/metrics":
        return await call_next(request)
    
    REQUEST_IN_PROGRESS.labels(method=method, endpoint=path).inc()
    start = time.time()
    
    try:
        response = await call_next(request)
        duration = time.time() - start
        
        REQUEST_COUNT.labels(
            method=method, endpoint=path, status_code=response.status_code
        ).inc()
        REQUEST_LATENCY.labels(method=method, endpoint=path).observe(duration)
        
        return response
    except Exception as e:
        duration = time.time() - start
        REQUEST_COUNT.labels(method=method, endpoint=path, status_code=500).inc()
        REQUEST_LATENCY.labels(method=method, endpoint=path).observe(duration)
        raise
    finally:
        REQUEST_IN_PROGRESS.labels(method=method, endpoint=path).dec()


async def rate_limit_middleware(request: Request, call_next):
    """限流中间件"""
    if request.url.path in ("/health", "/metrics", "/docs", "/openapi.json"):
        return await call_next(request)
    
    client_id = request.client.host if request.client else "unknown"
    
    if not app_state.rate_limiter.is_allowed(client_id):
        return JSONResponse(
            status_code=429,
            content={"detail": "请求过于频繁，请稍后再试", "retry_after": 60}
        )
    
    return await call_next(request)


# ============== 生命周期 ==============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    logger.info("[BOOT] Initializing Fortune Fusion Engine v2.0...")
    
    # 初始化缓存
    import os
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    app_state.cache = CacheManager(redis_url=redis_url)
    await app_state.cache.initialize()
    
    # 注册命理体系
    app_state.systems = {
        "八字命理": BaZiSystem(),
        "紫微斗数": ZiWeiSystem(),
        "七政四余": QiZhengSystem(),
        "西方占星术": AstrologySystem(),
        "奇门遁甲": QiMenSystem(),
        "大六壬": LiuRenSystem(),
        "六爻纳甲": LiuYaoSystem(),
        "梅花易数": MeiHuaSystem(),
        "数字命理学": NumerologySystem(),
        "姓名学": NameologySystem(),
    }
    
    # 设置 Prometheus 指标
    ACTIVE_SYSTEMS.set(len(app_state.systems))
    for name, system in app_state.systems.items():
        SYSTEM_WEIGHT.labels(system=name).set(system.weight)
    APP_INFO.info({"version": config.VERSION, "systems": str(len(app_state.systems))})
    
    # 初始化数据库 (可选)
    try:
        from models import create_engine_pool, get_session_factory, Base
        engine = create_engine_pool()
        app_state.db_session_factory = get_session_factory(engine)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("[OK] Database connected")
    except Exception as e:
        logger.warning(f"[WARN] Database unavailable, fallback to no-persistence mode: {e}")
        app_state.db_session_factory = None
    
    logger.info(f"[OK] Loaded {len(app_state.systems)} fortune systems, service ready")
    
    yield
    
    # 清理
    await app_state.cache.close()
    logger.info("[STOP] Service shutdown")


# ============== FastAPI 应用 ==============

app = FastAPI(
    title="多命理融合预测引擎 API",
    description="基于10大传统命理体系的智能融合预测服务 - v2.0 云原生版",
    version=config.VERSION,
    lifespan=lifespan,
)

# 中间件注册
app.middleware("http")(metrics_middleware)
app.middleware("http")(rate_limit_middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ============== 前端页面 ==============
from fastapi.responses import HTMLResponse
from pathlib import Path as FilePath

WEB_DIR = FilePath(__file__).parent.parent.parent / "web"

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """前端页面"""
    index_path = WEB_DIR / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Frontend not found</h1>", status_code=404)

# ============== API 端点 ==============

# ============== API 端点 ==============

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查 (含缓存、熔断状态)"""
    return HealthResponse(
        status="healthy",
        version=config.VERSION,
        uptime_seconds=app_state.get_uptime(),
        systems_available=list(app_state.systems.keys()),
        cache_stats=app_state.cache.get_stats(),
        circuit_breaker_status=app_state.circuit_breaker.get_status(),
    )


@app.get("/metrics")
async def metrics_endpoint():
    """Prometheus 指标端点"""
    if not PROMETHEUS_AVAILABLE:
        return JSONResponse(
            status_code=503,
            content={"detail": "prometheus-client 未安装，监控指标不可用。请运行: pip install prometheus-client"}
        )
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.post("/query", response_model=QueryResponse)
async def query_fortune(request: QueryRequest):
    """
    执行命理查询
    
    支持: 缓存命中 / 熔断降级 / 并行计算 / 结果融合
    """
    request_id = str(uuid.uuid4())[:8]
    start_time = time.time()
    
    # 1. 缓存查询
    cache_key = app_state.cache._generate_key(
        prefix="query",
        year=request.birth_info.year,
        month=request.birth_info.month,
        day=request.birth_info.day,
        hour=request.birth_info.hour,
        minute=request.birth_info.minute,
        lat=round(request.birth_info.latitude, 2),
        lon=round(request.birth_info.longitude, 2),
        gender=request.gender,
        scene=request.scene,
        name=request.name or "",
    )
    
    cached_result = await app_state.cache.get(cache_key)
    if cached_result:
        cached_result["from_cache"] = True
        return QueryResponse(**cached_result)
    
    # 2. 构建参数
    birth_datetime = datetime(
        request.birth_info.year, request.birth_info.month,
        request.birth_info.day, request.birth_info.hour,
        request.birth_info.minute,
    )
    birth_location = {
        "latitude": request.birth_info.latitude,
        "longitude": request.birth_info.longitude,
    }
    
    # 3. 并行计算 (带熔断保护)
    calc_tasks = []
    available_systems = []
    
    for name, system in app_state.systems.items():
        if not app_state.circuit_breaker.is_available(name):
            logger.info(f"[CB] Circuit breaker skip: {name}")
            continue
        available_systems.append(name)
        calc_tasks.append(
            system.calculate(
                birth_datetime=birth_datetime,
                birth_location=birth_location,
                gender=request.gender,
                query_scene=request.scene,
                query_time=request.query_time,
                name=request.name,
            )
        )
    
    if not available_systems:
        raise HTTPException(status_code=503, detail="所有命理体系暂时不可用，请稍后重试")
    
    # 4. 等待结果
    individual_results = await asyncio.gather(*calc_tasks, return_exceptions=True)
    
    valid_results = []
    for i, result in enumerate(individual_results):
        system_name = available_systems[i]
        if isinstance(result, Exception):
            logger.error(f"[ERR] {system_name} calculation failed: {result}")
            CALCULATION_ERRORS.labels(system=system_name, error_type=type(result).__name__).inc()
            app_state.circuit_breaker.record_failure(system_name)
        else:
            app_state.circuit_breaker.record_success(system_name)
            valid_results.append(result)
            CALCULATION_COUNT.labels(system=system_name).inc()
            CALCULATION_LATENCY.labels(system=system_name).observe(
                result.calculation_time_ms / 1000.0
            )
    
    if not valid_results:
        raise HTTPException(status_code=500, detail="所有命理体系计算失败")
    
    # 5. 融合
    fusion_start = time.time()
    fusion_result = app_state.fusion_engine.fuse(
        scene=request.scene,
        results=valid_results,
        user_id=request.user_id,
    )
    fusion_duration = time.time() - fusion_start
    
    FUSION_SCORE.labels(scene=request.scene).observe(fusion_result.score)
    FUSION_UNCERTAINTY.labels(scene=request.scene).observe(fusion_result.uncertainty)
    FUSION_LATENCY.observe(fusion_duration)
    
    if fusion_result.conflicts:
        for conflict in fusion_result.conflicts:
            severity = conflict.get("severity", "medium")
            FUSION_CONFLICTS.labels(severity=severity).inc()
    
    total_time = int((time.time() - start_time) * 1000)
    app_state.request_count += 1
    
    # 6. 构建响应
    response_data = {
        "request_id": request_id,
        "timestamp": datetime.now(),
        "scene": request.scene,
        "individual_results": [
            SystemResultOut(
                system=r.system, score=r.score, confidence=r.confidence,
                trend=r.trend, risk_level=r.risk_level,
                calculation_time_ms=r.calculation_time_ms, cached=r.cached,
            )
            for r in valid_results
        ],
        "fusion_result": FusionResultOut(
            score=fusion_result.score, uncertainty=fusion_result.uncertainty,
            trend=fusion_result.trend, risk_level=fusion_result.risk_level,
            reliability=fusion_result.reliability, consensus=fusion_result.consensus,
            conflicts=fusion_result.conflicts,
            contributing_systems=fusion_result.contributing_systems,
            calculation_time_ms=fusion_result.calculation_time_ms,
        ),
        "total_calculation_time_ms": total_time,
        "from_cache": False,
    }
    
    # 7. 写入缓存
    cache_ttl = config.SCENE_CACHE_TTL.get(request.scene, 3600)
    await app_state.cache.set(cache_key, response_data, ttl=cache_ttl)
    
    # 8. 异步持久化到数据库
    if app_state.db_session_factory:
        asyncio.create_task(
            _persist_query(request_id, request, fusion_result, valid_results, total_time)
        )
    
    return QueryResponse(**response_data)


@app.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """
    提交用户反馈 (用于体系准确率校准)
    """
    if not app_state.db_session_factory:
        return {"status": "accepted", "note": "数据库不可用，反馈已记录到日志"}
    
    try:
        async with app_state.db_session_factory() as session:
            from models import QueryModel
            from sqlalchemy import select
            
            stmt = select(QueryModel).where(QueryModel.request_id == request.request_id)
            result = await session.execute(stmt)
            query = result.scalar_one_or_none()
            
            if query:
                query.accuracy_feedback = request.accuracy_feedback
                query.feedback_comment = request.comment
                await session.commit()
                
                # 更新体系准确率
                if query.system_results:
                    await _update_system_accuracy(session, query, request.accuracy_feedback)
                
                return {"status": "ok", "message": "反馈已记录"}
            else:
                raise HTTPException(status_code=404, detail="查询记录不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"反馈保存失败: {e}")
        return {"status": "accepted", "note": "反馈已记录到日志"}


@app.get("/systems")
async def list_systems():
    """列出命理体系 (含熔断状态)"""
    return {
        "systems": [
            {
                "name": name,
                "weight": system.weight,
                "available": app_state.circuit_breaker.is_available(name),
                "state": app_state.circuit_breaker.states.get(name, "closed"),
            }
            for name, system in app_state.systems.items()
        ]
    }


@app.get("/scenes")
async def list_scenes():
    from fusion_engine import SCENE_ADJUSTMENTS
    return {
        "scenes": list(SCENE_ADJUSTMENTS.keys()),
        "cache_ttl": config.SCENE_CACHE_TTL,
    }


@app.get("/stats")
async def get_stats():
    """服务统计 + SLO 指标"""
    uptime = app_state.get_uptime()
    error_rate = app_state.error_count / max(app_state.request_count, 1)
    
    # 错误预算计算 (30天窗口)
    total_budget = 1 - config.SLO_AVAILABILITY
    consumed = error_rate
    remaining = max(0, total_budget - consumed) / total_budget if total_budget > 0 else 1.0
    
    ERROR_BUDGET_REMAINING.labels(slo_name="availability").set(remaining)
    
    return {
        "uptime_seconds": round(uptime, 1),
        "total_requests": app_state.request_count,
        "error_count": app_state.error_count,
        "error_rate": round(error_rate, 6),
        "systems_loaded": len(app_state.systems),
        "cache_stats": app_state.cache.get_stats(),
        "circuit_breaker": app_state.circuit_breaker.get_status(),
        "slo": {
            "target_availability": config.SLO_AVAILABILITY,
            "current_availability": round(1 - error_rate, 6),
            "error_budget_remaining": round(remaining, 4),
        },
        "version": config.VERSION,
    }


@app.get("/cache/stats")
async def cache_stats():
    """缓存详细统计"""
    return app_state.cache.get_stats()


@app.post("/cache/clear")
async def cache_clear():
    """清除缓存 (运维用)"""
    # 仅清除内存缓存，Redis 缓存自然过期
    app_state.cache._memory_cache.clear()
    app_state.cache._access_order.clear()
    return {"status": "ok", "message": "内存缓存已清除"}


# ============== 内部函数 ==============

async def _persist_query(
    request_id: str,
    request: QueryRequest,
    fusion_result: FusionResult,
    individual_results: list,
    total_time_ms: int,
):
    """异步持久化查询结果"""
    try:
        async with app_state.db_session_factory() as session:
            from models import QueryModel
            
            query = QueryModel(
                request_id=request_id,
                user_id=request.user_id,
                scene=request.scene,
                birth_info=request.birth_info.model_dump(),
                gender=request.gender,
                name=request.name,
                fusion_score=fusion_result.score,
                fusion_trend=fusion_result.trend,
                fusion_risk_level=fusion_result.risk_level,
                fusion_reliability=fusion_result.reliability,
                fusion_uncertainty=fusion_result.uncertainty,
                fusion_details=fusion_result.to_dict(),
                system_results=[r.to_dict() for r in individual_results],
                calculation_time_ms=total_time_ms,
            )
            session.add(query)
            await session.commit()
    except Exception as e:
        logger.error(f"持久化失败: {e}")


async def _update_system_accuracy(session, query, feedback_score: int):
    """更新体系准确率 (基于用户反馈)"""
    try:
        from models import SystemAccuracyModel
        from sqlalchemy import select
        
        # feedback 4-5 视为准确，1-2 视为不准确，3 为中性
        is_accurate = feedback_score >= 4
        
        for system_result in query.system_results:
            system_name = system_result.get("system")
            if not system_name:
                continue
            
            stmt = select(SystemAccuracyModel).where(
                SystemAccuracyModel.system == system_name
            )
            result = await session.execute(stmt)
            accuracy = result.scalar_one_or_none()
            
            if accuracy:
                accuracy.total_predictions += 1
                if is_accurate:
                    accuracy.accurate_predictions += 1
                # 滚动准确率 (指数加权)
                alpha = 0.1
                accuracy.rolling_accuracy = (
                    alpha * (1.0 if is_accurate else 0.0) +
                    (1 - alpha) * accuracy.rolling_accuracy
                )
            else:
                session.add(SystemAccuracyModel(
                    system=system_name,
                    total_predictions=1,
                    accurate_predictions=1 if is_accurate else 0,
                    rolling_accuracy=1.0 if is_accurate else 0.0,
                ))
        
        await session.commit()
    except Exception as e:
        logger.error(f"更新准确率失败: {e}")


# ============== 异常处理 ==============

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    app_state.error_count += 1
    logger.error(f"未处理异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "服务内部错误，请稍后重试", "error_type": type(exc).__name__}
    )


# ============== 主入口 ==============

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
    )
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
