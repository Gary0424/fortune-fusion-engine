---
name: fortune-fusion-engine
description: 10大传统命理体系智能融合预测引擎 — 八字/紫微/七政四余/占星/奇门/大六壬/六爻/梅花/数字/姓名，API驱动，支持熔断降级、多级缓存、Prometheus监控
author: Gary0424
version: 2.0.0
tags: [命理, 八字, 紫微斗数, 占星, 奇门遁甲, 六爻, 梅花易数, 姓名学, 预测引擎, 融合计算]
category: 命理/预测
license: MIT
github: https://github.com/Gary0424/fortune-fusion-engine
---

# 多命理融合预测引擎 v2.0

> 基于10大传统命理体系的智能融合预测服务 · 云原生架构 · API驱动

## 这是什么

Fortune Fusion Engine 是一个**多命理体系融合预测引擎**，将中国传统命理学（八字、紫微斗数、七政四余、奇门遁甲、大六壬、六爻纳甲、梅花易数）与西方占星术、数字命理学、姓名学共10大体系进行**智能融合计算**，输出综合吉凶评分、趋势判断和风险评估。

**核心价值：** 单一命理体系存在盲区，多体系融合可交叉验证、降低偏差、提升预测可靠性。

## 10大命理体系

| 体系 | 基础权重 | 擅长场景 | 说明 |
|------|---------|----------|------|
| 八字命理 | 0.12 | 终身格局、健康风险 | 四柱八字，天干地支五行生克 |
| 紫微斗数 | 0.10 | 终身格局、事业财运 | 十二宫位星曜组合 |
| 七政四余 | 0.08 | 年度趋势 | 日月五星四余星推算 |
| 奇门遁甲 | 0.08 | 具体事件决策 | 天地人三盘九星八门 |
| 大六壬 | 0.06 | 具体事件决策 | 四课三传天地盘 |
| 西方占星术 | 0.06 | 性格分析、关系匹配 | 行星相位宫位 |
| 六爻纳甲 | 0.04 | 具体事件短期预测 | 摇卦纳甲六亲 |
| 梅花易数 | 0.02 | 即时事件判断 | 象数理占 |
| 数字命理学 | 0.03 | 性格分析 | 生命数字密码 |
| 姓名学 | 0.01 | 姓名吉凶 | 五格三才笔画数理 |

> 权重总和为0.60，引擎自动归一化处理。实际动态权重 = 基础权重 × 场景适配 × 置信度 × 历史准确率 × 用户校准，详见 [WEIGHT_ALGORITHM.md](WEIGHT_ALGORITHM.md)

## 快速部署

### 方式零：一键安装（30秒体验）

```bash
git clone https://github.com/Gary0424/fortune-fusion-engine.git
cd fortune-fusion-engine
chmod +x setup.sh
./setup.sh
```

> 💡 一键安装脚本会自动安装核心依赖并启动服务，无需Redis/PostgreSQL即可运行。

### 方式一：本地直接运行

```bash
# 克隆项目
git clone https://github.com/Gary0424/fortune-fusion-engine.git
cd fortune-fusion-engine

# 安装核心依赖（最小化，开箱即用）
pip install -r requirements-minimal.txt

# 启动服务（无Redis/PostgreSQL也能运行，自动降级）
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000

# 访问 API 文档
# http://localhost:8000/docs
```

### 方式二：完整安装（含监控）

```bash
# 安装所有依赖
pip install -r requirements.txt

# 启动服务
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

### 可选依赖说明

| 依赖 | 用途 | 是否必须 |
|------|------|----------|
| fastapi | Web框架 | ✅ 必须 |
| uvicorn | ASGI服务器 | ✅ 必须 |
| numpy | 数值计算 | ✅ 必须 |
| pydantic | 数据验证 | ✅ 必须 |
| prometheus-client | 监控指标 | ⚪ 可选 |
| redis | 缓存加速 | ⚪ 可选 |
| sqlalchemy + asyncpg | 数据持久化 | ⚪ 可选 |

> 💡 **开箱即用**：核心功能不需要安装可选依赖，服务会自动降级运行。

### 方式二：Docker Compose（推荐生产环境）

```bash
docker-compose up -d
# 包含: API服务 + Redis + PostgreSQL + Prometheus + Grafana
```

### 方式三：Kubernetes

```bash
# 修改 k8s/infra.yml 中的密码和域名
kubectl apply -f k8s/
# 包含: HPA自动伸缩(3~10 Pod) + Ingress TLS
```

## API 使用指南

### 核心查询接口

```python
import requests

# 命理查询
response = requests.post("http://localhost:8000/query", json={
    "birth_info": {
        "year": 1990,
        "month": 6,
        "day": 15,
        "hour": 14,
        "minute": 30,
        "latitude": 32.06,   # 南京纬度
        "longitude": 118.78  # 南京经度
    },
    "gender": "male",
    "name": "张三",
    "scene": "终身格局",      # 可选: 终身格局/年度趋势/月度趋势/具体事件/性格分析/健康风险
    "specific_question": "今年事业运势如何？"
})

result = response.json()
print(f"综合评分: {result['fusion_result']['score']}/100")
print(f"趋势: {result['fusion_result']['trend']}")
print(f"风险等级: {result['fusion_result']['risk_level']}")
print(f"可靠性: {result['fusion_result']['reliability']}")

# 查看各体系得分
for sys in result['individual_results']:
    print(f"  {sys['system']}: {sys['score']}分 (置信度:{sys['confidence']})")
```

### 查询场景说明

| 场景 | 缓存TTL | 说明 |
|------|---------|------|
| 终身格局 | 24h | 八字/紫微权重提升 |
| 年度趋势 | 12h | 七政四余权重提升 |
| 月度趋势 | 6h | 六爻/梅花权重提升 |
| 具体事件 | 1h | 奇门/大六壬/六爻权重提升 |
| 性格分析 | 24h | 占星/数字命理权重提升 |
| 健康风险 | 12h | 八字五行平衡分析 |

### 用户反馈校准

```python
# 提交反馈，引擎会自动校准体系准确率
requests.post("http://localhost:8000/feedback", json={
    "request_id": "a1b2c3d4",
    "accuracy_feedback": 5,  # 1-5，4-5视为准确
    "comment": "预测非常准确！"
})
```

### 其他接口

```python
# 健康检查（含熔断/缓存状态）
GET /health

# 体系列表（含熔断状态）
GET /systems

# 服务统计 + SLO
GET /stats

# Prometheus 指标
GET /metrics

# 缓存管理
GET /cache/stats
POST /cache/clear
```

## 实战案例

### 案例1：择日 — 5月19日表白吉凶

**场景**：我想在5月19日向喜欢的人表白，这天合适吗？

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "birth_info": {
      "year": 2003, "month": 6, "day": 4,
      "hour": 16, "minute": 5,
      "latitude": 32.06, "longitude": 118.78
    },
    "gender": "male",
    "scene": "具体事件",
    "query_time": "2026-05-19T10:00:00"
  }'
```

**返回结果解读**：

```json
{
  "fusion_result": {
    "score": 62.22,           // 综合评分：中等偏吉
    "trend": "neutral",       // 趋势：平稳，非大吉但也不凶
    "uncertainty": 11.96,     // 不确定性：中等，体系间有分歧
    "reliability": "medium",  // 可靠性：中等
    "risk_level": "medium"    // 风险：中等
  }
}
```

**各体系分析**：
| 体系 | 评分 | 动态权重 | 解读 |
|------|------|---------|------|
| 奇门遁甲 | 71.5 | 9.1% ⬆️ | 具体事件场景权重提升3倍，显示吉 |
| 梅花易数 | 78.75 | 2.0% | 最高分，象数层面吉利 |
| 八字命理 | 74.82 | 4.2% | 日主格局支持 |
| 六爻纳甲 | 38.85 | 3.8% ⚠️ | 最低分，卦象层面有阻力 |

**结论**：62分属于"可以做但不是最佳时机"。奇门遁甲和梅花易数都显示吉（>70），但六爻有阻力。建议：
- 5/19可以行动，但不要期望太高
- 如果有更好的日期，可以再测算对比
- 六爻的低分提示"准备可能不够充分"，注意方式方法

---

### 案例2：合婚 — 两个人八字合不合

**场景**：我和她八字合不合？分别测算两人终身格局，对比分析。

```bash
# 男方测算
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "birth_info": {
      "year": 2003, "month": 6, "day": 4,
      "hour": 16, "minute": 5,
      "latitude": 32.06, "longitude": 118.78
    },
    "gender": "male",
    "scene": "终身格局"
  }'

# 女方测算
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "birth_info": {
      "year": 2001, "month": 11, "day": 15,
      "hour": 6, "minute": 0,
      "latitude": 29.59, "longitude": 120.83
    },
    "gender": "female",
    "scene": "终身格局",
    "name": "陈雯璐"
  }'
```

**返回结果对比**：

| 维度 | 男方 | 女方 | 合婚分析 |
|------|------|------|---------|
| 综合评分 | ~55 | 67.52 | 女方格局更高，互补型 |
| 趋势 | neutral | neutral | 两人运势节奏同步 |
| 八字命理 | ~43 | 80.35 | 女方八字强，男方需要女方带动 |
| 姓名学 | ~50 | 86.0 | 女方姓名格局极佳 |
| 高权重体系 | 八字 | 八字 | 两人都以八字为核心，共鸣度高 |

**合婚要点**：
1. **互补格局**：男方评分偏低但不代表差，而是"需要助力"，女方恰好能补
2. **趋势同步**：两人都是neutral趋势，运势节奏一致，不会出现一方大起一方大落
3. **八字为核心**：两人的高权重体系都是八字命理，说明人生观、价值观层面有共鸣基础
4. **女方带动**：女方八字80分+姓名86分，整体格局强，是关系中的"稳定器"

---

### 案例3：创业 — 这个月创业能成功吗

**场景**：我想这个月开始创业，时机如何？

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "birth_info": {
      "year": 1990, "month": 3, "day": 15,
      "hour": 9, "minute": 30,
      "latitude": 31.23, "longitude": 121.47
    },
    "gender": "male",
    "name": "李明",
    "scene": "月度趋势",
    "specific_question": "这个月创业能成功吗？"
  }'
```

**场景选择说明**：
- ❌ 不用"具体事件"：创业不是单一事件，是一个过程
- ❌ 不用"终身格局"：看的是本月时机，不是一生格局
- ✅ 用"月度趋势"：最适合看当月运势走向

**结果解读思路**：
1. **看综合评分**：≥70果断行动，50-69谨慎准备，<50再等等
2. **看趋势**：positive适合启动，neutral适合筹备，negative暂缓
3. **看冲突**：如果奇门遁甲（决策）和八字（格局）冲突大，说明"时机到了但自身没准备好"
4. **看风险等级**：high以上建议推迟，做好风控再动

**不同场景下的权重变化**：

| 体系 | 终身格局 | 月度趋势 | 具体事件 | 说明 |
|------|---------|---------|---------|------|
| 八字命理 | ⬆️ 1.2x | ⬆️ 1.1x | ⬇️ 0.5x | 看大势用八字，看小事不用 |
| 奇门遁甲 | ⬇️ 0.5x | ⬇️ 0.7x | ⬆️ **1.5x** | 做决策用奇门，看终身不用 |
| 六爻纳甲 | ⬇️ 0.5x | ⬇️ 0.7x | ⬆️ **1.3x** | 占卜短期事件最强 |
| 西方占星 | ⬆️ 1.2x | 1.0x | ⬇️ 0.5x | 本命盘看终身，不看短期 |

**关键结论**：选对场景非常重要！同一个问题，用不同场景会得到完全不同的权重分配和评分结果。

---

### 场景选择速查表

| 你要问的问题 | 用什么场景 | 为什么 |
|-------------|-----------|--------|
| 我这一生命运如何？ | 终身格局 | 八字/紫微/占星权重最高 |
| 今年运势怎么样？ | 年度趋势 | 七政四余（天文命理）权重提升 |
| 这个月适合做什么？ | 月度趋势 | 平衡各体系，看月度节奏 |
| 明天去面试能过吗？ | 具体事件 | 奇门/大六壬/六爻权重翻3倍 |
| 我是什么性格？ | 性格分析 | 占星/数字命理权重提升 |
| 身体健康要注意什么？ | 健康风险 | 八字五行分析为主 |

---

## 融合算法原理

### 动态权重计算

```
最终权重 = 基础权重 × 场景适配系数 × 历史准确率 × 置信度 × 用户校准系数
```

- **基础权重**：每个体系的默认权重（见上表）
- **场景适配**：不同场景下各体系的权重调整系数
- **历史准确率**：基于用户反馈滚动更新（指数加权，α=0.1）
- **置信度**：每个体系根据数据完整度、计算确定性、场景适配度自评
- **用户校准**：个性化权重调整

### 冲突检测

当两个体系的评分差 ≥ 50分时，标记为冲突：
- 分差 50-70：中等冲突，以高权重体系为主
- 分差 ≥ 70：严重冲突，需人工审核

### 不确定性量化

使用标准差衡量各体系评分的离散程度，配合高置信度体系占比评估可靠性：
- σ < 10 且高置信占比 ≥ 60%：可靠性 high
- σ < 20 且高置信占比 ≥ 40%：可靠性 medium
- 其他：可靠性 low

## 生产级特性

### 熔断降级
- 每个命理体系独立熔断器
- 连续5次失败触发熔断
- 30秒后进入半开状态探测
- 熔断期间自动跳过，不影响其他体系

### 多级缓存
- L1：内存LRU（1000条目，零延迟）
- L2：Redis（可选，跨进程共享）
- 场景感知TTL（终身24h → 事件1h）
- Redis不可用时自动降级到内存缓存

### 可观测性
- Prometheus指标：请求量、延迟、错误率、体系得分、融合不确定性
- Grafana仪表盘：SRE监控面板
- 告警规则：错误率>0.1%、P99>1s、错误预算耗尽

### 限流保护
- 滑动窗口限流（默认60请求/分钟）
- 健康检查和指标端点免限流

## Agent 集成示例

```python
# 在你的 Agent 中调用命理引擎
async def analyze_fortune(birth_info: dict, question: str) -> str:
    """Agent 调用命理引擎分析"""
    import httpx
    
    async with httpx.AsyncClient() as client:
        resp = await client.post("http://localhost:8000/query", json={
            "birth_info": birth_info,
            "gender": "male",
            "scene": "具体事件",
            "specific_question": question
        }, timeout=30)
        
        data = resp.json()
        fusion = data["fusion_result"]
        
        # 构建 Agent 可理解的摘要
        summary = f"""
命理综合分析结果：
- 综合评分：{fusion['score']}/100
- 趋势判断：{fusion['trend']}
- 风险等级：{fusion['risk_level']}
- 结果可靠性：{fusion['reliability']}
- 不确定性：±{fusion['uncertainty']}

各体系详情：
"""
        for sys in data["individual_results"]:
            summary += f"- {sys['system']}: {sys['score']}分 (置信度{sys['confidence']})\n"
        
        if fusion.get("conflicts"):
            summary += "\n⚠️ 体系间存在分歧：\n"
            for c in fusion["conflicts"]:
                summary += f"  {c['systems'][0]} vs {c['systems'][1]}，分差{c['diff']}\n"
        
        return summary
```

## 项目结构

```
fortune-fusion-engine/
├── src/
│   ├── api/main.py           # FastAPI 服务（熔断+限流+监控）
│   ├── calc_engine/          # 10大命理计算引擎
│   │   ├── base.py           # 基类 + 标准化结果格式
│   │   ├── bazi.py           # 八字命理
│   │   ├── ziwei.py          # 紫微斗数
│   │   ├── qizheng.py        # 七政四余
│   │   ├── astrology.py      # 西方占星术
│   │   ├── qimen.py          # 奇门遁甲
│   │   ├── liuren.py         # 大六壬
│   │   ├── liuyao.py         # 六爻纳甲
│   │   ├── meihua.py         # 梅花易数
│   │   ├── numerology.py     # 数字命理学
│   │   └── nameology.py      # 姓名学
│   ├── fusion_engine/        # 融合决策引擎
│   │   ├── engine.py         # 动态权重+冲突消解+不确定性量化
│   │   └── weights.py        # 体系权重+场景适配矩阵
│   ├── models/database.py    # SQLAlchemy 数据模型
│   └── utils/
│       ├── cache.py          # 多级缓存（内存LRU + Redis）
│       └── metrics.py        # Prometheus 指标定义
├── k8s/                      # Kubernetes 部署配置
├── docker/                   # Dockerfile
├── config/                   # Prometheus/Grafana/告警配置
├── tests/test_api.py         # 测试套件
├── docker-compose.yml
└── requirements.txt
```

## 依赖

- Python 3.10+
- FastAPI + Uvicorn
- NumPy
- SQLAlchemy（可选，用于持久化）
- Redis（可选，用于L2缓存）
- Prometheus Client（可选，用于监控）

## 免责声明

本系统仅基于传统命理学民俗文化进行学术性、娱乐性的算法建模，属于民俗文化研究范畴，不具备科学预测效力，不构成任何人生、商业决策建议。

## License

MIT
