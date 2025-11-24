#!/bin/bash
# 停止所有TextLoom服务

echo "🛑 停止TextLoom服务..."

# 从PID文件读取进程ID并停止（含 beat）
for service in api worker flower beat; do
    pid_file="logs/${service}.pid"
    if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo "停止 $service 服务 (PID: $pid)..."
            kill "$pid"
            rm "$pid_file"
        else
            echo "⚠️  $service 服务已停止"
            rm -f "$pid_file"
        fi
    else
        echo "⚠️  未找到 $service 的PID文件"
    fi
done

# 额外检查并清理可能残留的进程
echo "清理残留进程..."
pkill -f "uvicorn main:app"
pkill -f "celery.*worker"
pkill -f "celery.*flower"
pkill -f "celery.*beat"

echo "✅ 所有服务已停止"