#!/bin/bash
set -e

# 初始化数据库脚本
# 此脚本在容器首次启动时自动执行

echo "开始初始化数据库..."

# 创建 textloom_core schema（为 TextLoom 项目准备）
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- 创建 textloom_core schema
    CREATE SCHEMA IF NOT EXISTS textloom_core;

    -- 授权给当前用户
    GRANT ALL PRIVILEGES ON SCHEMA textloom_core TO $POSTGRES_USER;

    -- 设置默认权限
    ALTER DEFAULT PRIVILEGES IN SCHEMA textloom_core
    GRANT ALL ON TABLES TO $POSTGRES_USER;

    ALTER DEFAULT PRIVILEGES IN SCHEMA textloom_core
    GRANT ALL ON SEQUENCES TO $POSTGRES_USER;

    -- 创建扩展（如果需要）
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE EXTENSION IF NOT EXISTS "pg_trgm";

    -- 显示当前数据库信息
    SELECT current_database(), current_user, version();
EOSQL

echo "数据库初始化完成！"
echo "数据库: $POSTGRES_DB"
echo "用户: $POSTGRES_USER"
echo "Schema: textloom_core"
