#!/bin/bash
# 一键启动所有TextLoom服务到后台

echo "🚀 启动TextLoom服务集群..."

# 从.env文件读取并设置Prometheus环境变量
if [ -f .env ]; then
    export $(grep "^PROMETHEUS_MULTIPROC_DIR=" .env | xargs)
fi
# 确保目录存在
mkdir -p ${PROMETHEUS_MULTIPROC_DIR:-./prometheus}

# 创建logs目录并清空历史日志
mkdir -p logs
echo "清空logs目录下历史日志..."
find logs -type f -name "*.log" -print -delete 2>/dev/null || true

# 启动FastAPI服务（后台）
echo "启动FastAPI API服务..."
nohup uv run uvicorn main:app --host 0.0.0.0 --port 48095 > logs/api.log 2>&1 &
API_PID=$!
echo "  ├─ PID: $API_PID"
echo "  └─ 日志: logs/api.log"

# 等待API服务启动
echo "等待API服务启动..."
sleep 3

# 启动Celery Worker（后台）
echo "启动Celery Worker..."
# （已在全局清理日志，此处无需再次清理单文件）
nohup ./start_celery_worker.sh worker > logs/celery_worker_start.log 2>&1 &
WORKER_PID=$!
echo "  ├─ PID: $WORKER_PID"  
echo "  └─ 日志: logs/celery_worker.log"

# 启动Celery Flower监控（后台）
echo "启动Celery Flower监控..."
# （已在全局清理日志，此处无需再次清理单文件）
nohup ./start_celery_worker.sh flower > logs/celery_flower.log 2>&1 &
FLOWER_PID=$!
echo "  ├─ PID: $FLOWER_PID"
echo "  └─ 日志: logs/celery_flower.log"

# 启动Celery Beat（后台）
echo "启动Celery Beat调度器..."
# （已在全局清理日志，此处无需再次清理单文件）
# 清理旧的Beat调度文件，避免过期调度缓存
rm -f logs/celerybeat-schedule 2>/dev/null || true
nohup ./start_celery_worker.sh beat > logs/celery_beat_start.log 2>&1 &
BEAT_PID=$!
echo "  ├─ PID: $BEAT_PID"
echo "  └─ 日志: logs/celery_beat.log"

# 等待服务启动
echo "等待Celery服务启动..."
sleep 5

# 验证服务状态
echo "验证服务状态..."

# 检查API服务
if curl -s http://localhost:48095/health > /dev/null 2>&1; then
    echo "  ✅ API服务: 运行正常"
else
    echo "  ⚠️  API服务: 可能还在启动中"
fi

# 检查Celery Worker
if grep -q "celery@.*ready" logs/celery_worker.log 2>/dev/null; then
    echo "  ✅ Celery Worker: 运行正常"
else
    echo "  ⚠️  Celery Worker: 可能还在启动中"
fi

# 检查Flower（本机回环地址）
if curl -s http://127.0.0.1:5555 > /dev/null 2>&1; then
    echo "  ✅ Flower监控: 运行正常（127.0.0.1:5555）"
else
    echo "  ⚠️  Flower监控: 可能还在启动中"
fi

# 检查Celery Beat
if grep -q "beat: Starting" logs/celery_beat.log 2>/dev/null; then
    echo "  ✅ Celery Beat: 运行正常"
else
    echo "  ⚠️  Celery Beat: 可能还在启动中"
fi

# 保存PID到文件
echo $API_PID > logs/api.pid
echo $WORKER_PID > logs/worker.pid  
echo $FLOWER_PID > logs/flower.pid
echo $BEAT_PID > logs/beat.pid

echo ""
echo "🎉 所有服务已启动到后台！"
echo ""
echo "📊 服务访问地址："
echo "  ├─ API文档: http://localhost:48095/docs"
echo "  ├─ API健康检查: http://localhost:48095/health"
echo "  └─ Celery监控: http://localhost:5555"
echo ""
echo "📋 服务管理："
echo "  ├─ 查看状态: ./status.sh"
echo "  ├─ 停止所有服务: ./stop_all.sh"
echo "  └─ 查看日志: tail -f logs/*.log"
echo ""
echo "📁 进程ID已保存到 logs/*.pid 文件"