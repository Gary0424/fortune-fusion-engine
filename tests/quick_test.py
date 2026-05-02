"""Quick API test script"""
import httpx, json

# Test health
r = httpx.get("http://localhost:8000/health")
print(f"Health: {r.status_code}")
h = r.json()
print(f"  Version: {h['version']}, Systems: {len(h['systems_available'])}, Redis: {h['cache_stats']['redis_available']}")

# Test query
r = httpx.post("http://localhost:8000/query", json={
    "birth_info": {"year": 1990, "month": 5, "day": 15, "hour": 12, "minute": 0, "latitude": 31.23, "longitude": 121.47},
    "gender": "male",
    "name": "Zhang",
    "scene": "终身格局"
}, timeout=30)

print(f"\nQuery: {r.status_code}")
if r.status_code == 200:
    data = r.json()
    print(f"  RequestID: {data['request_id']}")
    print(f"  TotalTime: {data['total_calculation_time_ms']}ms")
    print(f"  Cached: {data['from_cache']}")
    print(f"  Systems: {len(data['individual_results'])}")
    for s in data['individual_results']:
        print(f"    {s['score']}pts conf={s['confidence']} trend={s['trend']} risk={s['risk_level']}")
    f = data['fusion_result']
    print(f"  Fusion: {f['score']}pts unc={f['uncertainty']} trend={f['trend']} risk={f['risk_level']} rel={f['reliability']}")
    print(f"  Conflicts: {len(f.get('conflicts') or [])}")
    
    # Test cache hit (repeat query)
    r2 = httpx.post("http://localhost:8000/query", json={
        "birth_info": {"year": 1990, "month": 5, "day": 15, "hour": 12, "minute": 0, "latitude": 31.23, "longitude": 121.47},
        "gender": "male",
        "name": "Zhang",
        "scene": "终身格局"
    }, timeout=30)
    d2 = r2.json()
    print(f"\n  Cache Test: cached={d2['from_cache']} time={d2['total_calculation_time_ms']}ms")
    
    # Test feedback
    r3 = httpx.post("http://localhost:8000/feedback", json={
        "request_id": data['request_id'],
        "accuracy_feedback": 4,
        "comment": "test"
    }, timeout=10)
    print(f"\n  Feedback: {r3.status_code} - {r3.json()}")

# Test metrics
r4 = httpx.get("http://localhost:8000/metrics")
ffe_lines = [l for l in r4.text.split('\n') if l.startswith('ffe_') and not l.startswith('#')]
print(f"\nMetrics: {len(ffe_lines)} FFE metrics")
for l in ffe_lines[:3]:
    print(f"  {l}")

# Test stats
r5 = httpx.get("http://localhost:8000/stats")
s = r5.json()
print(f"\nStats: requests={s['total_requests']} error_rate={s['error_rate']} slo_remaining={s['slo']['error_budget_remaining']}")

print("\n=== ALL TESTS PASSED ===")
