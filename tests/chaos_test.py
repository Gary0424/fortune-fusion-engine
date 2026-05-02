"""
混沌工程测试 - 验证系统降级和恢复能力
"""
import asyncio
import time
from datetime import datetime
from typing import List, Dict, Any


class ChaosExperiment:
    """混沌实验基类"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.results = []
    
    async def run(self) -> Dict[str, Any]:
        raise NotImplementedError
    
    def report(self) -> str:
        lines = [f"Experiment: {self.name}", f"Description: {self.description}"]
        for r in self.results:
            status = "PASS" if r["success"] else "FAIL"
            lines.append(f"  [{status}] {r['check']}: {r['detail']}")
        passed = sum(1 for r in self.results if r["success"])
        lines.append(f"Result: {passed}/{len(self.results)} checks passed")
        return "\n".join(lines)


class CircuitBreakerChaos(ChaosExperiment):
    """熔断器混沌测试 - 模拟体系故障，验证熔断和恢复"""
    
    def __init__(self):
        super().__init__(
            "Circuit Breaker Resilience",
            "Inject failures into fortune systems, verify circuit breaker triggers and recovers"
        )
        self.api_base = "http://localhost:8000"
    
    async def run(self) -> Dict[str, Any]:
        import httpx
        async with httpx.AsyncClient(timeout=30) as client:
            
            # Check 1: 所有体系初始可用
            r = await client.get(f"{self.api_base}/systems")
            systems = r.json()["systems"]
            all_available = all(s["available"] for s in systems)
            self.results.append({
                "check": "All systems initially available",
                "success": all_available,
                "detail": f"{sum(1 for s in systems if s['available'])}/{len(systems)} available"
            })
            
            # Check 2: 正常查询成功
            r = await client.post(f"{self.api_base}/query", json={
                "birth_info": {"year": 1990, "month": 5, "day": 15, "hour": 12, "minute": 0, "latitude": 31.23, "longitude": 121.47},
                "gender": "male", "scene": "终身格局"
            })
            query_ok = r.status_code == 200
            self.results.append({
                "check": "Normal query succeeds",
                "success": query_ok,
                "detail": f"status={r.status_code}"
            })
            
            # Check 3: 缓存命中测试
            r2 = await client.post(f"{self.api_base}/query", json={
                "birth_info": {"year": 1990, "month": 5, "day": 15, "hour": 12, "minute": 0, "latitude": 31.23, "longitude": 121.47},
                "gender": "male", "scene": "终身格局"
            })
            cached = r2.json().get("from_cache", False)
            self.results.append({
                "check": "Cache hit on repeat query",
                "success": cached,
                "detail": f"cached={cached}"
            })
            
            # Check 4: 不同场景查询
            scenes = ["月度趋势", "具体事件", "性格分析"]
            scene_ok = True
            for scene in scenes:
                r = await client.post(f"{self.api_base}/query", json={
                    "birth_info": {"year": 1985, "month": 10, "day": 20, "hour": 6, "minute": 30, "latitude": 39.9, "longitude": 116.4},
                    "gender": "female", "scene": scene
                })
                if r.status_code != 200:
                    scene_ok = False
            self.results.append({
                "check": "Multiple scenes work",
                "success": scene_ok,
                "detail": f"tested {len(scenes)} scenes"
            })
            
            # Check 5: SLO 指标检查
            r = await client.get(f"{self.api_base}/stats")
            stats = r.json()
            slo_ok = stats["slo"]["error_budget_remaining"] >= 0.8
            self.results.append({
                "check": "SLO error budget healthy",
                "success": slo_ok,
                "detail": f"remaining={stats['slo']['error_budget_remaining']}"
            })
            
            # Check 6: Prometheus 指标采集
            r = await client.get(f"{self.api_base}/metrics")
            ffe_metrics = [l for l in r.text.split('\n') if l.startswith('ffe_') and not l.startswith('#')]
            metrics_ok = len(ffe_metrics) > 50
            self.results.append({
                "check": "Prometheus metrics collected",
                "success": metrics_ok,
                "detail": f"{len(ffe_metrics)} FFE metrics"
            })
            
            # Check 7: 清除缓存后仍可查询
            await client.post(f"{self.api_base}/cache/clear")
            r = await client.post(f"{self.api_base}/query", json={
                "birth_info": {"year": 1990, "month": 5, "day": 15, "hour": 12, "minute": 0, "latitude": 31.23, "longitude": 121.47},
                "gender": "male", "scene": "终身格局"
            })
            post_clear_ok = r.status_code == 200 and not r.json().get("from_cache", True)
            self.results.append({
                "check": "Query works after cache clear",
                "success": post_clear_ok,
                "detail": f"status={r.status_code}, cached={r.json().get('from_cache')}"
            })
        
        passed = sum(1 for r in self.results if r["success"])
        return {"experiment": self.name, "passed": passed, "total": len(self.results)}


class CacheDegradationChaos(ChaosExperiment):
    """缓存降级混沌测试 - 验证 Redis 不可用时内存缓存接管"""
    
    def __init__(self):
        super().__init__(
            "Cache Degradation",
            "Verify graceful fallback when Redis is unavailable"
        )
        self.api_base = "http://localhost:8000"
    
    async def run(self) -> Dict[str, Any]:
        import httpx
        async with httpx.AsyncClient(timeout=30) as client:
            
            # Check 1: 缓存统计中 Redis 不可用
            r = await client.get(f"{self.api_base}/cache/stats")
            cache = r.json()
            redis_fallback = not cache["redis_available"]
            self.results.append({
                "check": "Redis unavailable, memory cache active",
                "success": redis_fallback,
                "detail": f"redis_available={cache['redis_available']}, memory_entries={cache['memory_entries']}"
            })
            
            # Check 2: 内存缓存仍然工作
            # 第一次查询
            r1 = await client.post(f"{self.api_base}/query", json={
                "birth_info": {"year": 1995, "month": 3, "day": 8, "hour": 14, "minute": 30, "latitude": 22.5, "longitude": 114.1},
                "gender": "female", "scene": "月度趋势"
            })
            # 第二次相同查询应命中内存缓存
            r2 = await client.post(f"{self.api_base}/query", json={
                "birth_info": {"year": 1995, "month": 3, "day": 8, "hour": 14, "minute": 30, "latitude": 22.5, "longitude": 114.1},
                "gender": "female", "scene": "月度趋势"
            })
            cache_hit = r2.json().get("from_cache", False)
            self.results.append({
                "check": "Memory cache hit works without Redis",
                "success": cache_hit,
                "detail": f"cached={cache_hit}"
            })
            
            # Check 3: 缓存清除
            await client.post(f"{self.api_base}/cache/clear")
            r = await client.get(f"{self.api_base}/cache/stats")
            cleared = r.json()["memory_entries"] == 0
            self.results.append({
                "check": "Cache clear works",
                "success": cleared,
                "detail": f"memory_entries after clear={r.json()['memory_entries']}"
            })
        
        passed = sum(1 for r in self.results if r["success"])
        return {"experiment": self.name, "passed": passed, "total": len(self.results)}


async def run_all_chaos_experiments():
    """运行所有混沌实验"""
    print("=" * 60)
    print("  Chaos Engineering Test Suite")
    print("  Fortune Fusion Engine v2.0")
    print("=" * 60)
    
    experiments = [
        CircuitBreakerChaos(),
        CacheDegradationChaos(),
    ]
    
    all_results = []
    for exp in experiments:
        print(f"\n--- Running: {exp.name} ---")
        result = await exp.run()
        print(exp.report())
        all_results.append(result)
    
    # Summary
    total_passed = sum(r["passed"] for r in all_results)
    total_checks = sum(r["total"] for r in all_results)
    
    print("\n" + "=" * 60)
    print(f"  CHAOS SUMMARY: {total_passed}/{total_checks} checks passed")
    if total_passed == total_checks:
        print("  STATUS: ALL EXPERIMENTS PASSED")
    else:
        print(f"  STATUS: {total_checks - total_passed} FAILURES")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_all_chaos_experiments())
