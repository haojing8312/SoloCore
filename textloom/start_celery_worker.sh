#!/bin/bash
# Celery服务启动脚本 - 包含Worker和Flower监控

echo "🚀 启动TextLoom Celery服务..."
echo "Redis地址: ${REDIS_HOST:-localhost}:${REDIS_PORT:-6379}"

# 检查Redis连接
echo "检查Redis连接..."
if command -v redis-cli &> /dev/null; then
    if redis-cli -h ${REDIS_HOST:-localhost} -p ${REDIS_PORT:-6379} ${REDIS_PASSWORD:+-a $REDIS_PASSWORD} ping &> /dev/null; then
        echo "✅ Redis连接正常"
    else
        echo "❌ Redis连接失败，请检查Redis服务和认证信息"
        exit 1
    fi
else
    echo "警告: redis-cli未安装，跳过Redis连接检查"
fi

# 检查必要的目录
echo "检查工作目录..."
mkdir -p workspace/materials/images
mkdir -p workspace/materials/videos  
mkdir -p workspace/materials/audio
mkdir -p workspace/processed
mkdir -p workspace/keyframes
mkdir -p workspace/logs
mkdir -p logs
echo "✅ 工作目录已创建"

# 设置环境变量
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# 选择启动模式
if [ "$1" = "worker" ]; then
    echo "启动Celery Worker..."
    exec uv run celery -A celery_config worker \
        --loglevel=info \
        --concurrency=1 \
        --pool=solo \
        --queues=video_processing,video_generation,maintenance,monitoring \
        --logfile=logs/celery_worker.log
        
elif [ "$1" = "flower" ]; then
    echo "启动Celery Flower监控..."
    echo "访问地址(仅本机): http://localhost:5555"
    # 仅监听本地回环地址，禁止未认证API（默认即禁用）
    # 可选：如需启用基础认证，设置环境变量 FLOWER_BASIC_AUTH=username:password
    FLOWER_ARGS="--address=127.0.0.1 --port=5555 --logging=info --enable_events"
    if [ -n "${FLOWER_BASIC_AUTH}" ]; then
        FLOWER_ARGS="$FLOWER_ARGS --basic_auth=${FLOWER_BASIC_AUTH}"
    fi
    exec uv run celery -A celery_config flower ${FLOWER_ARGS}
        
elif [ "$1" = "beat" ]; then
    echo "启动Celery Beat调度器..."
    exec uv run celery -A celery_config beat \
        --loglevel=info \
        --logfile=logs/celery_beat.log \
        --schedule=logs/celerybeat-schedule
        
else
    echo "用法："
    echo "  ./start_celery_worker.sh worker   # 启动Worker"
    echo "  ./start_celery_worker.sh flower   # 启动Flower监控"
    echo "  ./start_celery_worker.sh beat     # 启动Beat调度器"
    echo ""
    echo "或者后台启动所有服务："
    echo "  ./start_celery_worker.sh worker &"
    echo "  ./start_celery_worker.sh flower &"
    exit 1
fi