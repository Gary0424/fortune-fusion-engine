# 多命理融合预测引擎 v2.0

基于10大传统命理体系的智能融合预测服务 · 云原生架构

## 系统架构

```
                     ┌──────────────┐
                     │   Ingress    │
                     │  (Nginx+TLS) │
                     └──────┬───────┘
                            │
                ┌───────────┼───────────┐
                ▼           ▼           ▼
          ┌──────────┐┌──────────┐┌──────────┐
          │ API Pod 1││ API Pod 2││ API Pod 3│  ← HPA 3~10
          └────┬─────┘└────┬─────┘└────┬─────┘
               │           │           │
       ┌───────┴───────────┴───────────┘
       │
  ┌────┴─────┐    ┌───────────┐    ┌───────────┐
  │ 命理引擎  │    │ 融合引擎   │    │ 反馈校准   │
  │ (10体系)  │───▶│ (动态权重)  │───▶│ (滚动准确率)│
  └──────────┘    └───────────┘    └───────────┘
       │               │                │
  ┌────┴───────────────┴────────────────┴────┐
  │              缓存 + 持久化层              │
  │  ┌─────────┐  ┌──────────┐  ┌─────────┐ │
  │  │  Redis  │  │PostgreSQL│  │  MinIO  │ │
  │  │ (L1+L2) │  │ (查询+校准)│  │ (快照)  │ │
  │  └─────────┘  └──────────┘  └─────────┘ │
  └──────────────────────────────────────────┘
       │
  ┌────┴─────────────────────────────────────┐
  │           可观测性 + 告警                  │
  │  ┌───────────┐ ┌─────────┐ ┌──────────┐ │
  │  │Prometheus │ │ Grafana │ │AlertMgr  │ │
  │  │ (指标采集) │ │(仪表盘) │ │ (告警)   │ │
  │  └───────────┘ └─────────┘ └──────────┘ │
  └──────────────────────────────────────────┘
```

## SLO 目标

| 指标 | 目标 | 当前 |
|------|------|------|
| 可用性 | 99.99% | - |
| P99 延迟 | < 1s | - |
| 错误率 | < 0.1% | - |
| 缓存命中率 | > 90% | - |

## 快速开始

### 一键安装（推荐）

```bash
cd fortune-fusion-engine
chmod +x setup.sh
./setup.sh
```

### 本地开发

```bash
cd fortune-fusion-engine

# 安装核心依赖（最小化）
pip install -r requirements-minimal.txt

# 启动服务
python -m uvicorn src.api.main:app --port 8000 --reload

# 测试
curl http://localhost:8000/health
```

### 完整安装（含监控）

```bash
# 安装所有依赖
pip install -r requirements.txt

# 启动服务
python -m uvicorn src.api.main:app --port 8000 --reload
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

### Docker Compose

```bash
docker-compose up -d
python tests/test_api.py
```

### Kubernetes

```bash
# 修改 k8s/infra.yml 中的密码
kubectl apply -f k8s/
```

## API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/health` | GET | 健康检查 (含缓存/熔断状态) |
| `/metrics` | GET | Prometheus 指标 |
| `/query` | POST | 命理查询 (支持缓存/熔断) |
| `/feedback` | POST | 用户反馈 (校准体系准确率) |
| `/systems` | GET | 体系列表 (含熔断状态) |
| `/scenes` | GET | 场景列表 (含缓存TTL) |
| `/stats` | GET | 服务统计 + SLO |
| `/cache/stats` | GET | 缓存统计 |
| `/cache/clear` | POST | 清除缓存 |

## 核心特性

### 🔥 熔断降级
- 每个命理体系独立熔断
- 连续 5 次失败触发熔断
- 30s 后进入半开状态探测
- 熔断期间自动跳过，不影响其他体系

### 📦 多级缓存
- L1: 内存 LRU (1000 条目)
- L2: Redis (可选)
- 场景感知 TTL (终身格局 24h, 具体事件 1h)
- Cache-Aside 模式，Redis 不可用自动降级

### 📊 可观测性
- Prometheus 指标采集
- Grafana SRE 仪表盘
- 告警规则 (错误率/P99延迟/错误预算)
- 请求级追踪

### 🎯 用户校准
- 反馈驱动的体系准确率更新
- 指数加权滚动准确率
- 个性化权重校准

## 项目结构

```
fortune-fusion-engine/
├── src/
│   ├── api/main.py           # FastAPI 服务 v2
│   ├── calc_engine/          # 10大命理计算引擎
│   ├── fusion_engine/        # 融合决策引擎
│   ├── models/database.py    # SQLAlchemy 数据模型
│   └── utils/
│       ├── cache.py          # 多级缓存管理
│       └── metrics.py        # Prometheus 指标
├── config/
│   ├── prometheus.yml        # Prometheus 配置
│   ├── alerts.yml            # 告警规则
│   └── grafana-dashboard.yml # 仪表盘
├── k8s/
│   ├── infra.yml             # 命名空间/Secret/Ingress
│   ├── api-deployment.yml    # API + HPA
│   ├── redis-statefulset.yml # Redis
│   ├── postgres-statefulset.yml # PostgreSQL
│   └── deploy.sh             # 一键部署
├── docker/
│   └── Dockerfile
├── tests/test_api.py         # API 测试 v2
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## 免责声明

本系统仅基于传统命理学民俗文化进行学术性、娱乐性的算法建模，属于民俗文化研究范畴，不具备科学预测效力，不构成任何人生、商业决策建议。

## License

MIT
