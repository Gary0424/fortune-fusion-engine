"""
API 测试脚本 v2 - 覆盖缓存/熔断/监控/反馈
"""
import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"


def print_section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def test_health():
    """测试健康检查 (含缓存/熔断状态)"""
    r = requests.get(f"{BASE_URL}/health")
    print(f"Status: {r.status_code}")
    data = r.json()
    print(f"  版本: {data['version']}")
    print(f"  运行时间: {data['uptime_seconds']:.1f}s")
    print(f"  可用体系: {len(data['systems_available'])} 个")
    print(f"  缓存: {json.dumps(data['cache_stats'], ensure_ascii=False)}")
    print(f"  熔断: {json.dumps(data['circuit_breaker_status'], ensure_ascii=False)}")
    return r.status_code == 200


def test_systems():
    """测试体系列表 (含熔断状态)"""
    r = requests.get(f"{BASE_URL}/systems")
    print(f"Status: {r.status_code}")
    for s in r.json()["systems"]:
        state = "🟢" if s["available"] else "🔴"
        print(f"  {state} {s['name']} (权重: {s['weight']}, 状态: {s['state']})")
    return r.status_code == 200


def test_scenes():
    """测试场景列表 (含缓存 TTL)"""
    r = requests.get(f"{BASE_URL}/scenes")
    data = r.json()
    print(f"场景: {list(data['scenes'].keys())}")
    print(f"缓存 TTL: {json.dumps(data['cache_ttl'], ensure_ascii=False)}")
    return r.status_code == 200


def test_query(scene: str = "终身格局"):
    """测试命理查询"""
    payload = {
        "user_id": "test_user_001",
        "birth_info": {
            "year": 1990, "month": 5, "day": 15,
            "hour": 12, "minute": 0,
            "latitude": 31.2304, "longitude": 121.4737
        },
        "gender": "male",
        "name": "张三",
        "scene": scene
    }
    
    print(f"  场景: {scene}")
    r = requests.post(f"{BASE_URL}/query", json=payload)
    
    if r.status_code == 200:
        data = r.json()
        print(f"  请求ID: {data['request_id']}")
        print(f"  缓存: {'✅' if data['from_cache'] else '❌'}")
        print(f"  总耗时: {data['total_calculation_time_ms']}ms")
        
        print(f"\n  📊 各体系结果:")
        for result in data['individual_results']:
            print(f"    {result['system']}: {result['score']}分 "
                  f"(置信度: {result['confidence']}, "
                  f"趋势: {result['trend']}, "
                  f"风险: {result['risk_level']})")
        
        fusion = data['fusion_result']
        print(f"\n  🔮 融合结果:")
        print(f"    综合评分: {fusion['score']}分")
        print(f"    不确定性: {fusion['uncertainty']}")
        print(f"    趋势: {fusion['trend']}")
        print(f"    风险: {fusion['risk_level']}")
        print(f"    可靠性: {fusion['reliability']}")
        print(f"    融合耗时: {fusion['calculation_time_ms']}ms")
        
        if fusion['conflicts']:
            print(f"    ⚠️ 冲突: {len(fusion['conflicts'])} 个")
            for c in fusion['conflicts']:
                print(f"      {c['systems']} 差异: {c['diff']} ({c['severity']})")
        
        return data['request_id']
    else:
        print(f"  ❌ Error: {r.text}")
        return None


def test_cache_hit():
    """测试缓存命中 (重复查询)"""
    payload = {
        "birth_info": {
            "year": 1990, "month": 5, "day": 15,
            "hour": 12, "minute": 0,
            "latitude": 31.2304, "longitude": 121.4737
        },
        "gender": "male",
        "scene": "终身格局"
    }
    
    # 第一次查询
    r1 = requests.post(f"{BASE_URL}/query", json=payload)
    t1 = r1.json()['total_calculation_time_ms']
    
    # 第二次查询 (应该命中缓存)
    r2 = requests.post(f"{BASE_URL}/query", json=payload)
    data2 = r2.json()
    t2 = data2['total_calculation_time_ms']
    cached = data2['from_cache']
    
    print(f"  首次查询: {t1}ms")
    print(f"  缓存查询: {t2}ms (命中: {'✅' if cached else '❌'})")
    print(f"  加速比: {t1/max(t2,1):.1f}x")
    return cached


def test_feedback(request_id: str):
    """测试用户反馈"""
    payload = {
        "request_id": request_id,
        "accuracy_feedback": 4,
        "comment": "测试反馈 - 整体准确"
    }
    r = requests.post(f"{BASE_URL}/feedback", json=payload)
    print(f"  Status: {r.status_code}")
    print(f"  Response: {r.json()}")
    return r.status_code in (200, 404)


def test_stats():
    """测试统计信息 (含 SLO)"""
    r = requests.get(f"{BASE_URL}/stats")
    data = r.json()
    print(f"  请求总数: {data['total_requests']}")
    print(f"  错误数: {data['error_count']}")
    print(f"  错误率: {data['error_rate']}")
    print(f"  缓存命中率: {data['cache_stats']['hit_rate']}")
    print(f"  SLO 目标: {data['slo']['target_availability']}")
    print(f"  当前可用性: {data['slo']['current_availability']}")
    print(f"  错误预算剩余: {data['slo']['error_budget_remaining']}")
    return r.status_code == 200


def test_cache_stats():
    """测试缓存统计"""
    r = requests.get(f"{BASE_URL}/cache/stats")
    data = r.json()
    print(f"  命中率: {data['hit_rate']}")
    print(f"  内存条目: {data['memory_entries']}/{data['max_memory_entries']}")
    print(f"  Redis: {'✅' if data['redis_available'] else '❌'}")
    return r.status_code == 200


def test_metrics():
    """测试 Prometheus 指标"""
    r = requests.get(f"{BASE_URL}/metrics")
    lines = r.text.strip().split('\n')
    ffe_metrics = [l for l in lines if l.startswith('ffe_') and not l.startswith('#')]
    print(f"  FFE 指标数: {len(ffe_metrics)}")
    for m in ffe_metrics[:5]:
        print(f"    {m}")
    if len(ffe_metrics) > 5:
        print(f"    ... 还有 {len(ffe_metrics) - 5} 个指标")
    return r.status_code == 200


if __name__ == "__main__":
    print("=" * 60)
    print("  多命理融合预测引擎 v2.0 - API 测试")
    print("=" * 60)
    
    try:
        results = []
        
        # 基础功能
        print_section("1. 健康检查")
        results.append(("健康检查", test_health()))
        
        print_section("2. 体系列表")
        results.append(("体系列表", test_systems()))
        
        print_section("3. 场景列表")
        results.append(("场景列表", test_scenes()))
        
        # 核心查询
        print_section("4. 命理查询 (终身格局)")
        rid = test_query("终身格局")
        results.append(("命理查询", rid is not None))
        
        print_section("5. 命理查询 (具体事件)")
        rid2 = test_query("具体事件")
        results.append(("事件查询", rid2 is not None))
        
        # 缓存
        print_section("6. 缓存命中测试")
        results.append(("缓存命中", test_cache_hit()))
        
        # 反馈
        print_section("7. 用户反馈")
        if rid:
            results.append(("用户反馈", test_feedback(rid)))
        else:
            results.append(("用户反馈", False))
        
        # 监控
        print_section("8. Prometheus 指标")
        results.append(("Prometheus", test_metrics()))
        
        print_section("9. 服务统计 + SLO")
        results.append(("服务统计", test_stats()))
        
        print_section("10. 缓存统计")
        results.append(("缓存统计", test_cache_stats()))
        
        # 汇总
        print_section("测试汇总")
        for name, success in results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"  {status}: {name}")
        
        passed = sum(1 for _, s in results if s)
        print(f"\n  总计: {passed}/{len(results)} 通过")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ 无法连接到服务")
        print(f"   请确保 API 已启动: {BASE_URL}")
        print("   启动命令: cd fortune-fusion-engine && python -m uvicorn src.api.main:app --port 8000")
