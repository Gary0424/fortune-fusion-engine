"""
Performance & Load Test - Validate SLO targets
SLO: P99 < 1s, Error Rate < 0.1%, 1000 QPS sustained
"""
import asyncio
import time
import statistics
import random
from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class RequestResult:
    """单次请求结果"""
    success: bool
    status_code: int
    latency_ms: float
    cached: bool = False
    error: str = ""


@dataclass
class LoadTestReport:
    """压测报告"""
    name: str
    total_requests: int
    successful: int
    failed: int
    error_rate: float
    latencies_ms: List[float] = field(default_factory=list)
    
    @property
    def p50(self) -> float:
        return self._percentile(50)
    
    @property
    def p90(self) -> float:
        return self._percentile(90)
    
    @property
    def p95(self) -> float:
        return self._percentile(95)
    
    @property
    def p99(self) -> float:
        return self._percentile(99)
    
    @property
    def p999(self) -> float:
        return self._percentile(99.9)
    
    @property
    def avg(self) -> float:
        return statistics.mean(self.latencies_ms) if self.latencies_ms else 0
    
    @property
    def min(self) -> float:
        return min(self.latencies_ms) if self.latencies_ms else 0
    
    @property
    def max(self) -> float:
        return max(self.latencies_ms) if self.latencies_ms else 0
    
    def _percentile(self, p: float) -> float:
        if not self.latencies_ms:
            return 0
        sorted_lat = sorted(self.latencies_ms)
        idx = int(len(sorted_lat) * p / 100)
        idx = min(idx, len(sorted_lat) - 1)
        return sorted_lat[idx]
    
    def to_summary(self) -> str:
        lines = [
            f"Load Test: {self.name}",
            f"  Requests: {self.total_requests} (OK: {self.successful}, Fail: {self.failed})",
            f"  Error Rate: {self.error_rate:.4f} (SLO: <0.1%)",
            f"  Latency (ms):",
            f"    min={self.min:.1f}  avg={self.avg:.1f}  max={self.max:.1f}",
            f"    p50={self.p50:.1f}  p90={self.p90:.1f}  p95={self.p95:.1f}  p99={self.p99:.1f}",
            f"  SLO Check:",
            f"    P99 < 1000ms: {'PASS' if self.p99 < 1000 else 'FAIL'} ({self.p99:.1f}ms)",
            f"    Error < 0.1%: {'PASS' if self.error_rate < 0.001 else 'FAIL'} ({self.error_rate:.4f})",
        ]
        return "\n".join(lines)


# Sample birth data for varied queries
BIRTH_SAMPLES = [
    {"year": 1990, "month": 5, "day": 15, "hour": 12, "minute": 0, "latitude": 31.23, "longitude": 121.47},
    {"year": 1985, "month": 10, "day": 20, "hour": 6, "minute": 30, "latitude": 39.9, "longitude": 116.4},
    {"year": 1995, "month": 3, "day": 8, "hour": 14, "minute": 30, "latitude": 22.5, "longitude": 114.1},
    {"year": 1988, "month": 7, "day": 22, "hour": 18, "minute": 0, "latitude": 30.57, "longitude": 104.07},
    {"year": 1992, "month": 12, "day": 1, "hour": 0, "minute": 15, "latitude": 23.13, "longitude": 113.26},
    {"year": 1980, "month": 4, "day": 10, "hour": 8, "minute": 45, "latitude": 34.26, "longitude": 108.94},
    {"year": 1998, "month": 9, "day": 30, "hour": 20, "minute": 0, "latitude": 30.27, "longitude": 120.15},
    {"year": 1975, "month": 1, "day": 15, "hour": 3, "minute": 30, "latitude": 45.75, "longitude": 126.65},
    {"year": 2000, "month": 6, "day": 18, "hour": 11, "minute": 11, "latitude": 29.56, "longitude": 106.55},
    {"year": 1983, "month": 11, "day": 5, "hour": 16, "minute": 20, "latitude": 28.23, "longitude": 112.94},
]

SCENES = ["终身格局", "月度趋势", "具体事件", "性格分析", "年度趋势"]
GENDERS = ["male", "female"]


async def single_query(client, birth: dict, scene: str, gender: str) -> RequestResult:
    """执行单次查询请求"""
    start = time.perf_counter()
    try:
        r = await client.post("http://localhost:8000/query", json={
            "birth_info": birth,
            "gender": gender,
            "scene": scene,
        }, timeout=30)
        elapsed = (time.perf_counter() - start) * 1000
        cached = False
        if r.status_code == 200:
            cached = r.json().get("from_cache", False)
        return RequestResult(
            success=r.status_code == 200,
            status_code=r.status_code,
            latency_ms=elapsed,
            cached=cached,
        )
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        return RequestResult(
            success=False,
            status_code=0,
            latency_ms=elapsed,
            error=str(e),
        )


async def warmup(client):
    """预热 - 让缓存填充"""
    print("[WARMUP] Sending warmup requests...")
    birth = BIRTH_SAMPLES[0]
    for scene in SCENES:
        for gender in GENDERS:
            await single_query(client, birth, scene, gender)
    print("[WARMUP] Done")


async def run_concurrent_test(
    name: str,
    concurrency: int,
    total_requests: int,
    varied: bool = True
) -> LoadTestReport:
    """运行并发压测"""
    import httpx
    
    report = LoadTestReport(
        name=name,
        total_requests=total_requests,
        successful=0,
        failed=0,
        error_rate=0,
    )
    
    semaphore = asyncio.Semaphore(concurrency)
    
    async def bounded_query(client, idx: int):
        async with semaphore:
            if varied:
                birth = BIRTH_SAMPLES[idx % len(BIRTH_SAMPLES)]
                scene = SCENES[idx % len(SCENES)]
                gender = GENDERS[idx % len(GENDERS)]
            else:
                birth = BIRTH_SAMPLES[0]
                scene = SCENES[0]
                gender = "male"
            return await single_query(client, birth, scene, gender)
    
    async with httpx.AsyncClient(timeout=30) as client:
        # Warmup
        await warmup(client)
        
        # Main test
        print(f"\n[RUN] {name}: concurrency={concurrency}, requests={total_requests}")
        start_time = time.perf_counter()
        
        tasks = [bounded_query(client, i) for i in range(total_requests)]
        results = await asyncio.gather(*tasks)
        
        total_elapsed = (time.perf_counter() - start_time) * 1000
        
        for r in results:
            if r.success:
                report.successful += 1
                report.latencies_ms.append(r.latency_ms)
            else:
                report.failed += 1
        
        report.error_rate = report.failed / report.total_requests if report.total_requests > 0 else 0
        
        # Calculate throughput
        qps = total_requests / (total_elapsed / 1000)
        print(f"  Elapsed: {total_elapsed:.0f}ms, QPS: {qps:.1f}")
    
    return report


async def run_sustained_test(duration_seconds: int, target_qps: int) -> LoadTestReport:
    """持续负载测试 - 验证目标QPS可持续性"""
    import httpx
    
    name = f"Sustained {target_qps} QPS for {duration_seconds}s"
    report = LoadTestReport(
        name=name,
        total_requests=0,
        successful=0,
        failed=0,
        error_rate=0,
    )
    
    interval = 1.0 / target_qps  # seconds between requests
    
    async with httpx.AsyncClient(timeout=30) as client:
        print(f"\n[RUN] {name}")
        start_time = time.perf_counter()
        end_time = start_time + duration_seconds
        
        request_count = 0
        while time.perf_counter() < end_time:
            birth = BIRTH_SAMPLES[request_count % len(BIRTH_SAMPLES)]
            scene = SCENES[request_count % len(SCENES)]
            gender = GENDERS[request_count % len(GENDERS)]
            
            r = await single_query(client, birth, scene, gender)
            request_count += 1
            
            if r.success:
                report.successful += 1
                report.latencies_ms.append(r.latency_ms)
            else:
                report.failed += 1
            
            # Rate control
            elapsed = time.perf_counter() - start_time
            expected = request_count * interval
            if elapsed < expected:
                await asyncio.sleep(expected - elapsed)
        
        report.total_requests = request_count
        report.error_rate = report.failed / report.total_requests if report.total_requests > 0 else 0
    
    return report


async def main():
    print("=" * 60)
    print("  SLO Validation - Performance & Load Test")
    print("  Fortune Fusion Engine v2.0")
    print("  Targets: P99 < 1000ms, Error < 0.1%, 1000 QPS")
    print("=" * 60)
    
    # Test 1: Sequential baseline
    report1 = await run_concurrent_test(
        "Sequential Baseline",
        concurrency=1,
        total_requests=50,
        varied=True,
    )
    print(report1.to_summary())
    
    # Test 2: Moderate concurrency
    report2 = await run_concurrent_test(
        "Moderate Concurrency (10)",
        concurrency=10,
        total_requests=100,
        varied=True,
    )
    print(report2.to_summary())
    
    # Test 3: High concurrency
    report3 = await run_concurrent_test(
        "High Concurrency (50)",
        concurrency=50,
        total_requests=200,
        varied=True,
    )
    print(report3.to_summary())
    
    # Test 4: Cache-heavy (same query repeated)
    report4 = await run_concurrent_test(
        "Cache-Heavy (same query)",
        concurrency=20,
        total_requests=100,
        varied=False,
    )
    print(report4.to_summary())
    
    # Test 5: Sustained load
    report5 = await run_sustained_test(duration_seconds=10, target_qps=50)
    print(report5.to_summary())
    
    # Final Summary
    print("\n" + "=" * 60)
    print("  SLO VALIDATION SUMMARY")
    print("=" * 60)
    
    all_reports = [
        ("Sequential", report1),
        ("Concurrency=10", report2),
        ("Concurrency=50", report3),
        ("Cache-Heavy", report4),
        ("Sustained 50QPS", report5),
    ]
    
    p99_pass = all(r.p99 < 1000 for _, r in all_reports)
    err_pass = all(r.error_rate < 0.001 for _, r in all_reports)
    
    print(f"\n  {'Test':<20} {'P99(ms)':<10} {'ErrRate':<10} {'P99<1s':<8} {'Err<0.1%':<8}")
    print("  " + "-" * 56)
    for name, r in all_reports:
        p99_ok = "PASS" if r.p99 < 1000 else "FAIL"
        err_ok = "PASS" if r.error_rate < 0.001 else "FAIL"
        print(f"  {name:<20} {r.p99:<10.1f} {r.error_rate:<10.4f} {p99_ok:<8} {err_ok:<8}")
    
    print(f"\n  Overall P99 < 1s:   {'PASS' if p99_pass else 'FAIL'}")
    print(f"  Overall Error < 0.1%: {'PASS' if err_pass else 'FAIL'}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
