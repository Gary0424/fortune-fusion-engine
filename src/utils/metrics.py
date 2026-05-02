"""
Prometheus 监控指标（可选依赖）
"""
try:
    from prometheus_client import Counter, Histogram, Gauge, Info
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # 提供空的占位类
    class _Stub:
        def __getattr__(self, name):
            return self
        def __call__(self, *args, **kwargs):
            return self
    Counter = Histogram = Gauge = Info = _Stub()


# ============== 请求指标 ==============

REQUEST_COUNT = Counter(
    "ffe_http_requests_total",
    "HTTP 请求总数",
    ["method", "endpoint", "status_code"]
) if PROMETHEUS_AVAILABLE else None

REQUEST_LATENCY = Histogram(
    "ffe_http_request_duration_seconds",
    "HTTP 请求延迟",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
) if PROMETHEUS_AVAILABLE else None

REQUEST_IN_PROGRESS = Gauge(
    "ffe_http_requests_in_progress",
    "当前进行中的请求数",
    ["method", "endpoint"]
) if PROMETHEUS_AVAILABLE else None


# ============== 计算引擎指标 ==============

CALCULATION_COUNT = Counter(
    "ffe_calculation_total",
    "命理计算次数",
    ["system"]
) if PROMETHEUS_AVAILABLE else None

CALCULATION_LATENCY = Histogram(
    "ffe_calculation_duration_seconds",
    "命理计算耗时",
    ["system"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
) if PROMETHEUS_AVAILABLE else None

CALCULATION_ERRORS = Counter(
    "ffe_calculation_errors_total",
    "命理计算错误数",
    ["system", "error_type"]
) if PROMETHEUS_AVAILABLE else None


# ============== 融合引擎指标 ==============

FUSION_SCORE = Histogram(
    "ffe_fusion_score",
    "融合评分分布",
    ["scene"],
    buckets=list(range(0, 110, 10))
) if PROMETHEUS_AVAILABLE else None

FUSION_UNCERTAINTY = Histogram(
    "ffe_fusion_uncertainty",
    "融合不确定性分布",
    ["scene"],
    buckets=[0, 5, 10, 15, 20, 25, 30, 40, 50]
) if PROMETHEUS_AVAILABLE else None

FUSION_LATENCY = Histogram(
    "ffe_fusion_duration_seconds",
    "融合计算耗时",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1]
) if PROMETHEUS_AVAILABLE else None

FUSION_CONFLICTS = Counter(
    "ffe_fusion_conflicts_total",
    "融合冲突次数",
    ["severity"]
) if PROMETHEUS_AVAILABLE else None


# ============== 缓存指标 ==============

CACHE_HITS = Counter(
    "ffe_cache_hits_total",
    "缓存命中次数",
    ["level"]  # memory, redis
) if PROMETHEUS_AVAILABLE else None

CACHE_MISSES = Counter(
    "ffe_cache_misses_total",
    "缓存未命中次数",
    ["level"]
) if PROMETHEUS_AVAILABLE else None

CACHE_LATENCY = Histogram(
    "ffe_cache_operation_duration_seconds",
    "缓存操作耗时",
    ["operation", "level"],
    buckets=[0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05]
) if PROMETHEUS_AVAILABLE else None


# ============== 系统指标 ==============

ACTIVE_SYSTEMS = Gauge(
    "ffe_systems_active",
    "活跃的命理体系数量"
) if PROMETHEUS_AVAILABLE else None

SYSTEM_WEIGHT = Gauge(
    "ffe_system_weight",
    "体系权重",
    ["system"]
) if PROMETHEUS_AVAILABLE else None

ERROR_BUDGET_REMAINING = Gauge(
    "ffe_error_budget_remaining_ratio",
    "SLO 错误预算剩余比例",
    ["slo_name"]
) if PROMETHEUS_AVAILABLE else None


# ============== 应用信息 ==============

APP_INFO = Info(
    "ffe_app",
    "应用信息"
) if PROMETHEUS_AVAILABLE else None


def is_available() -> bool:
    """检查 prometheus-client 是否可用"""
    return PROMETHEUS_AVAILABLE
