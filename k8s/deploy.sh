# 一键部署脚本
# kubectl apply -f k8s/ 按顺序部署

# 0. 命名空间 + Secrets
kubectl apply -f k8s/infra.yml

# 1. 数据库
kubectl apply -f k8s/postgres-statefulset.yml
echo "⏳ 等待 PostgreSQL 就绪..."
kubectl wait --for=condition=ready pod -l app=ffe-postgres -n fortune-fusion --timeout=120s

# 2. 缓存
kubectl apply -f k8s/redis-statefulset.yml
echo "⏳ 等待 Redis 就绪..."
kubectl wait --for=condition=ready pod -l app=ffe-redis -n fortune-fusion --timeout=60s

# 3. API 服务
kubectl apply -f k8s/api-deployment.yml
echo "⏳ 等待 API 就绪..."
kubectl wait --for=condition=ready pod -l app=ffe-api -n fortune-fusion --timeout=120s

# 4. 验证
echo ""
echo "✅ 部署完成！"
echo ""
kubectl get pods -n fortune-fusion
echo ""
echo "📊 服务状态:"
kubectl get svc -n fortune-fusion
echo ""
echo "🔧 查看日志:"
echo "  kubectl logs -f deployment/ffe-api -n fortune-fusion"
