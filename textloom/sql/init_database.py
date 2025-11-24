#!/usr/bin/env python3
"""
TextLoom 数据库管理脚本
包含数据库初始化、表创建、状态检查和验证功能
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime

import asyncpg
import requests

from config import settings

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def parse_database_url(url):
    """解析数据库URL"""
    import re

    pattern = r"postgresql\+asyncpg://([^:]+):([^@]+)@([^:]+):(\d+)/([^?]+)"
    match = re.match(pattern, url)
    if match:
        return {
            "user": match.group(1),
            "password": match.group(2),
            "host": match.group(3),
            "port": int(match.group(4)),
            "database": match.group(5),
        }
    raise ValueError(f"无法解析数据库URL: {url}")


async def create_connection():
    """创建数据库连接"""
    db_config = parse_database_url(settings.database_url)
    return await asyncpg.connect(
        user=db_config["user"],
        password=db_config["password"],
        host=db_config["host"],
        port=db_config["port"],
        database=db_config["database"],
        server_settings={"search_path": "textloom_core, public"},
        statement_cache_size=0,  # 禁用 prepared statements，兼容pgbouncer
    )


async def create_schema():
    """创建schema"""
    try:
        logger.info("创建 textloom_core schema...")
        conn = await create_connection()
        try:
            await conn.execute("CREATE SCHEMA IF NOT EXISTS textloom_core")
            logger.info("Schema 创建成功")
        finally:
            await conn.close()
        return True
    except Exception as e:
        logger.error(f"创建 schema 失败: {e}")
        return False


async def create_tables():
    """创建所有数据库表"""
    try:
        logger.info("创建数据库表...")
        conn = await create_connection()
        try:
            # 创建表的SQL语句
            sql_statements = [
                # 视频项目表
                """
                CREATE TABLE IF NOT EXISTS textloom_core.video_projects (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    project_name VARCHAR(255) NOT NULL,
                    description TEXT,
                    project_type VARCHAR(50) NOT NULL DEFAULT 'video_generation',
                    status VARCHAR(50) NOT NULL DEFAULT 'created',
                    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    config JSONB
                )
                """,
                # 任务表
                """
                CREATE TABLE IF NOT EXISTS textloom_core.tasks (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    task_name VARCHAR(255) NOT NULL,
                    task_type VARCHAR(50) NOT NULL,
                    status VARCHAR(50) NOT NULL DEFAULT 'pending',
                    priority INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    config JSONB,
                    result JSONB,
                    error_message TEXT
                )
                """,
                # 媒体项目表
                """
                CREATE TABLE IF NOT EXISTS textloom_core.media_items (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    task_id UUID NOT NULL REFERENCES textloom_core.tasks(id),
                    file_path VARCHAR(500) NOT NULL,
                    file_type VARCHAR(50) NOT NULL,
                    file_size BIGINT,
                    duration REAL,
                    metadata JSONB,
                    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """,
                # 素材分析表
                """
                CREATE TABLE IF NOT EXISTS textloom_core.material_analyses (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    task_id UUID NOT NULL REFERENCES textloom_core.tasks(id),
                    analysis_type VARCHAR(50) NOT NULL,
                    status VARCHAR(50) NOT NULL DEFAULT 'pending',
                    result JSONB,
                    confidence_score REAL,
                    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    error_message TEXT
                )
                """,
                # 人设表
                """
                CREATE TABLE IF NOT EXISTS textloom_core.personas (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name VARCHAR(100) NOT NULL,
                    persona_type VARCHAR(50) NOT NULL,
                    style VARCHAR(100),
                    target_audience VARCHAR(100),
                    characteristics TEXT,
                    tone VARCHAR(50),
                    keywords TEXT,
                    custom_prompts JSONB DEFAULT '{}',
                    is_preset BOOLEAN NOT NULL DEFAULT false,
                    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """,
                # 提示词模板表
                """
                CREATE TABLE IF NOT EXISTS textloom_core.prompt_templates (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    template_key VARCHAR(255) NOT NULL UNIQUE,
                    template_content TEXT NOT NULL,
                    description TEXT,
                    category VARCHAR(50),
                    template_type VARCHAR(50),
                    template_style VARCHAR(50),
                    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """,
                # 脚本内容表
                """
                CREATE TABLE IF NOT EXISTS textloom_core.script_contents (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    task_id UUID NOT NULL REFERENCES textloom_core.tasks(id),
                    persona_id UUID REFERENCES textloom_core.personas(id),
                    script_style VARCHAR(100),
                    generation_status VARCHAR(50) NOT NULL DEFAULT 'pending',
                    titles JSONB,
                    narration JSONB,
                    material_mapping JSONB,
                    description TEXT,
                    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """,
                # 子视频任务表
                """
                CREATE TABLE IF NOT EXISTS textloom_core.sub_video_tasks (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    parent_task_id UUID NOT NULL REFERENCES textloom_core.tasks(id),
                    sub_task_name VARCHAR(255) NOT NULL,
                    sub_task_type VARCHAR(50) NOT NULL,
                    status VARCHAR(50) NOT NULL DEFAULT 'pending',
                    config JSONB,
                    result JSONB,
                    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """,
            ]

            for sql in sql_statements:
                await conn.execute(sql)

            logger.info("所有表创建完成")
            return True

        finally:
            await conn.close()

    except Exception as e:
        logger.error(f"创建表失败: {e}")
        return False


async def check_tables():
    """检查表状态"""
    try:
        logger.info("检查数据库表...")
        conn = await create_connection()
        try:
            rows = await conn.fetch(
                """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'textloom_core' 
                ORDER BY table_name
            """
            )

            tables = [row["table_name"] for row in rows]

            if tables:
                logger.info(f"找到 {len(tables)} 个表:")
                for table in tables:
                    logger.info(f"  - {table}")
            else:
                logger.warning("textloom_core schema 中没有找到表")

            return tables
        finally:
            await conn.close()

    except Exception as e:
        logger.error(f"检查表失败: {e}")
        return []


async def drop_tables():
    """删除所有表"""
    try:
        logger.warning("删除所有表...")
        conn = await create_connection()
        try:
            # 按依赖关系倒序删除
            tables = [
                "sub_video_tasks",
                "script_contents",
                "material_analyses",
                "media_items",
                "tasks",
                "video_projects",
                "prompt_templates",
                "personas",
            ]

            for table in tables:
                await conn.execute(
                    f"DROP TABLE IF EXISTS textloom_core.{table} CASCADE"
                )

            logger.warning("所有表已删除")
            return True

        finally:
            await conn.close()

    except Exception as e:
        logger.error(f"删除表失败: {e}")
        return False


async def verify_service():
    """验证服务运行状态"""
    try:
        logger.info("验证服务状态...")
        response = requests.get("http://localhost:48095/health", timeout=5)
        if response.status_code == 200:
            logger.info("✅ 服务运行正常")
            return True
        else:
            logger.warning(f"⚠️ 服务响应异常，状态码: {response.status_code}")
            return False
    except Exception as e:
        logger.warning(f"⚠️ 无法连接到服务: {e}")
        return False


async def verify_database():
    """验证数据库连接和配置"""
    try:
        logger.info("验证数据库连接...")
        conn = await create_connection()
        try:
            version = await conn.fetchval("SELECT version()")
            logger.info(f"✅ PostgreSQL版本: {version[:60]}...")

            # 检查schema
            schema_exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name = 'textloom_core')"
            )
            if schema_exists:
                logger.info("✅ textloom_core schema 存在")
            else:
                logger.warning("⚠️ textloom_core schema 不存在")

            return True
        finally:
            await conn.close()

    except Exception as e:
        logger.error(f"❌ 数据库验证失败: {e}")
        return False


def get_expected_schema():
    """从模型定义动态获取预期schema"""
    try:
        # 导入模型
        import os
        import sys

        sys.path.append(os.path.dirname(os.path.dirname(__file__)))

        from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
        from sqlalchemy.dialects.postgresql import UUID

        from models.db_models import Base

        schema = {}

        # 遍历所有表模型
        for table_name, table in Base.metadata.tables.items():
            # 移除schema前缀，只保留表名
            clean_table_name = (
                table_name.split(".")[-1] if "." in table_name else table_name
            )
            schema[clean_table_name] = {}

            for column in table.columns:
                col_name = column.name
                col_type = column.type

                # 映射SQLAlchemy类型到数据库类型
                if isinstance(col_type, UUID):
                    db_type = "uuid"
                elif isinstance(col_type, String):
                    if col_type.length:
                        db_type = f"varchar({col_type.length})"
                    else:
                        db_type = "varchar"
                elif isinstance(col_type, Text):
                    db_type = "text"
                elif isinstance(col_type, Integer):
                    db_type = "integer"
                elif isinstance(col_type, Float):
                    db_type = "real"
                elif isinstance(col_type, Boolean):
                    db_type = "boolean"
                elif isinstance(col_type, DateTime):
                    db_type = "timestamp"
                elif isinstance(col_type, JSON):
                    db_type = "json"
                else:
                    db_type = str(col_type).lower()

                # 获取默认值
                default_value = None
                if column.default is not None:
                    if hasattr(column.default, "arg"):
                        if callable(column.default.arg):
                            default_value = (
                                "gen_random_uuid()"
                                if "uuid" in str(column.default.arg)
                                else str(column.default.arg)
                            )
                        else:
                            default_value = str(column.default.arg)
                    elif hasattr(column.default, "name"):
                        default_value = (
                            "CURRENT_TIMESTAMP"
                            if "now" in column.default.name
                            else column.default.name
                        )
                    else:
                        default_value = str(column.default)

                schema[clean_table_name][col_name] = {
                    "type": db_type,
                    "nullable": column.nullable,
                    "default": default_value,
                }

        return schema

    except Exception as e:
        logger.error(f"无法从模型获取schema定义: {e}")
        logger.info("使用备用硬编码schema...")
        # 如果动态获取失败，使用简化的备用定义
        return get_fallback_schema()


def get_fallback_schema():
    """备用的简化schema定义"""
    return {
        "video_projects": {
            "id": {"type": "uuid", "nullable": False, "default": "gen_random_uuid()"},
            "title": {"type": "varchar(255)", "nullable": False, "default": None},
            "status": {"type": "varchar(50)", "nullable": False, "default": None},
            "video_url": {"type": "text", "nullable": True, "default": None},
            "created_at": {"type": "timestamp", "nullable": False, "default": None},
            "updated_at": {"type": "timestamp", "nullable": False, "default": None},
        },
        "tasks": {
            "id": {"type": "uuid", "nullable": False, "default": "gen_random_uuid()"},
            "title": {"type": "varchar(255)", "nullable": False, "default": None},
            "description": {"type": "text", "nullable": True, "default": None},
            "creator_id": {"type": "varchar(100)", "nullable": True, "default": None},
            "task_type": {"type": "varchar(50)", "nullable": False, "default": None},
            "status": {"type": "varchar(50)", "nullable": False, "default": None},
            "progress": {"type": "integer", "nullable": False, "default": None},
            "created_at": {"type": "timestamp", "nullable": False, "default": None},
            "updated_at": {"type": "timestamp", "nullable": True, "default": None},
            "started_at": {"type": "timestamp", "nullable": True, "default": None},
            "completed_at": {"type": "timestamp", "nullable": True, "default": None},
            "error_message": {"type": "text", "nullable": True, "default": None},
            "celery_task_id": {
                "type": "varchar(255)",
                "nullable": True,
                "default": None,
            },
            "worker_name": {"type": "varchar(100)", "nullable": True, "default": None},
            "retry_count": {"type": "integer", "nullable": True, "default": None},
            "max_retries": {"type": "integer", "nullable": True, "default": None},
            "error_traceback": {"type": "text", "nullable": True, "default": None},
        },
    }


def generate_fix_sql(current_schema, expected_schema):
    """生成修复SQL脚本"""
    sql_statements = []
    sql_statements.append("-- TextLoom 数据库架构自动修复脚本")
    sql_statements.append("-- 根据 models/db_models.py 中的模型定义生成")
    sql_statements.append("")

    for table_name, expected_columns in expected_schema.items():
        current_columns = current_schema.get(table_name, {})

        sql_statements.append(f"-- =====================================")
        sql_statements.append(f"-- 修复 {table_name} 表")
        sql_statements.append(f"-- =====================================")
        sql_statements.append("")

        # 检查需要添加的字段
        missing_columns = []
        for col_name, col_def in expected_columns.items():
            if col_name not in current_columns:
                missing_columns.append((col_name, col_def))

        if missing_columns:
            sql_statements.append(f"-- 添加缺失的字段到 {table_name}")
            for col_name, col_def in missing_columns:
                col_type = col_def["type"].upper()
                nullable = "NULL" if col_def["nullable"] else "NOT NULL"
                default = f"DEFAULT {col_def['default']}" if col_def["default"] else ""

                sql_statements.append(
                    f"ALTER TABLE textloom_core.{table_name} ADD COLUMN IF NOT EXISTS {col_name} {col_type} {nullable} {default};"
                )
            sql_statements.append("")

        # 检查需要删除的字段（数据库有但模型没有）
        extra_columns = []
        for col_name in current_columns:
            if col_name not in expected_columns:
                extra_columns.append(col_name)

        if extra_columns:
            sql_statements.append(f"-- 删除多余的字段从 {table_name}")
            for col_name in extra_columns:
                sql_statements.append(
                    f"-- ALTER TABLE textloom_core.{table_name} DROP COLUMN IF EXISTS {col_name}; -- 取消注释以删除"
                )
            sql_statements.append("")

    sql_statements.append("-- 脚本结束")
    return "\n".join(sql_statements)


async def check_schema_diff():
    """检查数据库schema与模型定义的差异"""
    try:
        logger.info("检查数据库与模型的差异...")
        conn = await create_connection()
        try:
            # 获取当前数据库中的表结构
            current_tables = {}

            # 查询所有表的列信息
            expected_schema = get_expected_schema()
            for table_name in expected_schema.keys():
                columns = await conn.fetch(
                    """
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns 
                    WHERE table_schema = 'textloom_core' AND table_name = $1
                    ORDER BY ordinal_position
                """,
                    table_name,
                )

                if columns:
                    current_tables[table_name] = {
                        row["column_name"]: {
                            "type": row["data_type"],
                            "nullable": row["is_nullable"] == "YES",
                            "default": row["column_default"],
                        }
                        for row in columns
                    }

            # 对比并生成报告
            logger.info("=" * 60)
            logger.info("数据库架构对比报告")
            logger.info("=" * 60)

            total_issues = 0
            for table_name, expected_columns in expected_schema.items():
                current_columns = current_tables.get(table_name, {})

                logger.info(f"\n📋 {table_name} 表:")
                logger.info(f"  预期字段: {len(expected_columns)} 个")
                logger.info(f"  当前字段: {len(current_columns)} 个")

                # 检查缺失字段
                missing = [
                    col for col in expected_columns if col not in current_columns
                ]
                if missing:
                    logger.error(
                        f"  ❌ 缺失字段 ({len(missing)}): {', '.join(missing)}"
                    )
                    total_issues += len(missing)

                # 检查多余字段
                extra = [col for col in current_columns if col not in expected_columns]
                if extra:
                    logger.warning(f"  ⚠️  多余字段 ({len(extra)}): {', '.join(extra)}")
                    total_issues += len(extra)

                if not missing and not extra:
                    logger.info(f"  ✅ 字段完全匹配")

            logger.info("=" * 60)
            if total_issues > 0:
                logger.error(f"发现 {total_issues} 个字段不一致问题")

                # 生成修复SQL
                fix_sql = generate_fix_sql(current_tables, expected_schema)

                # 写入文件
                with open("database_fix.sql", "w", encoding="utf-8") as f:
                    f.write(fix_sql)

                logger.info("✅ 已生成修复SQL脚本: database_fix.sql")
                logger.info("请手动执行该脚本修复数据库架构")
            else:
                logger.info("✅ 数据库架构与模型定义完全一致")

            return current_tables

        finally:
            await conn.close()

    except Exception as e:
        logger.error(f"检查schema差异失败: {e}")
        return {}


async def migrate_database():
    """执行数据库迁移 - 已简化，请使用 diff 命令生成SQL脚本后手动执行"""
    try:
        logger.info("迁移功能已简化...")
        logger.info("请使用以下步骤:")
        logger.info("1. 运行: python init_database.py diff")
        logger.info("2. 检查生成的 database_fix.sql 文件")
        logger.info("3. 手动执行 SQL 脚本修复数据库")

        # 只保留迁移跟踪表的创建
        await add_migration_tracking()

        return True

    except Exception as e:
        logger.error(f"迁移准备失败: {e}")
        return False


async def add_migration_tracking():
    """添加迁移跟踪表"""
    try:
        logger.info("创建迁移跟踪表...")
        conn = await create_connection()
        try:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS textloom_core.schema_migrations (
                    id SERIAL PRIMARY KEY,
                    migration_name VARCHAR(255) NOT NULL UNIQUE,
                    applied_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    description TEXT
                )
            """
            )
            logger.info("迁移跟踪表创建完成")
            return True
        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"创建迁移跟踪表失败: {e}")
        return False


async def init_preset_data():
    """初始化预设数据（人设和提示词模板）"""
    try:
        logger.info("开始初始化预设数据...")
        conn = await create_connection()
        try:
            # 检查是否已有预设人设
            existing_personas = await conn.fetch(
                """
                SELECT id FROM textloom_core.personas WHERE is_preset = true LIMIT 1
            """
            )

            if existing_personas:
                logger.info("预设数据已存在，跳过初始化")
                return True

            # 创建预设人设
            preset_personas = [
                {
                    "name": "知识科普博主",
                    "persona_type": "educator",
                    "style": "专业严谨",
                    "target_audience": "求知者",
                    "characteristics": "逻辑清晰，表达准确，善于将复杂概念简化",
                    "tone": "专业而亲和",
                    "keywords": "知识,科普,学习,教育",
                    "custom_prompts": {
                        "intro": "作为一名知识科普博主，我致力于将复杂的知识用简单易懂的方式传达给大家...",
                        "style": "请用专业但通俗易懂的语言，确保内容准确性...",
                    },
                },
                {
                    "name": "生活方式达人",
                    "persona_type": "lifestyle",
                    "style": "轻松愉快",
                    "target_audience": "生活爱好者",
                    "characteristics": "热爱生活，善于分享实用技巧和美好体验",
                    "tone": "亲切友好",
                    "keywords": "生活,技巧,分享,体验",
                    "custom_prompts": {
                        "intro": "大家好！我是你们的生活方式达人，今天要和大家分享...",
                        "style": "用轻松愉快的语调，分享实用的生活技巧...",
                    },
                },
                {
                    "name": "商业分析师",
                    "persona_type": "business",
                    "style": "数据驱动",
                    "target_audience": "商业人士",
                    "characteristics": "善于数据分析，洞察商业趋势，提供专业见解",
                    "tone": "专业权威",
                    "keywords": "商业,分析,数据,趋势",
                    "custom_prompts": {
                        "intro": "从商业分析的角度来看...",
                        "style": "请用数据和事实支撑观点，提供专业的商业分析...",
                    },
                },
            ]

            # 插入人设数据
            for persona in preset_personas:
                await conn.execute(
                    """
                    INSERT INTO textloom_core.personas 
                    (id, name, persona_type, style, target_audience, characteristics, tone, keywords, custom_prompts, is_preset, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """,
                    uuid.uuid4(),
                    persona["name"],
                    persona["persona_type"],
                    persona["style"],
                    persona["target_audience"],
                    persona["characteristics"],
                    persona["tone"],
                    persona["keywords"],
                    json.dumps(persona["custom_prompts"]),
                    True,
                    datetime.utcnow(),
                    datetime.utcnow(),
                )

            # 创建预设提示词模板
            preset_templates = [
                {
                    "template_key": "script_generation_base",
                    "template_content": """基于提供的素材，创建一个引人入胜的视频脚本。

素材信息：
{material_info}

要求：
1. 创建吸引人的标题（3-5个选择）
2. 编写流畅的旁白内容
3. 合理安排素材使用顺序
4. 估算视频时长
5. 添加相关标签

请确保内容：
- 符合目标受众需求
- 逻辑清晰，结构完整
- 语言生动，富有吸引力
- 适合视频媒体特点""",
                    "description": "基础脚本生成模板",
                    "category": "script",
                },
                {
                    "template_key": "material_analysis_base",
                    "template_content": """请分析这个素材文件：

文件类型：{file_type}
文件信息：{file_info}

请提供：
1. 详细的内容描述
2. 识别的关键对象/元素
3. 情感基调分析
4. 视觉风格评估
5. 质量评分（1-10分）
6. 使用建议

分析要准确、客观，为后续脚本生成提供有价值的信息。""",
                    "description": "基础素材分析模板",
                    "category": "analysis",
                },
            ]

            # 插入模板数据
            for template in preset_templates:
                await conn.execute(
                    """
                    INSERT INTO textloom_core.prompt_templates
                    (id, template_key, template_content, description, category, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """,
                    uuid.uuid4(),
                    template["template_key"],
                    template["template_content"],
                    template["description"],
                    template["category"],
                    datetime.utcnow(),
                )

            logger.info(
                f"预设数据初始化完成 - 创建了 {len(preset_personas)} 个人设和 {len(preset_templates)} 个模板"
            )
            return True

        finally:
            await conn.close()

    except Exception as e:
        logger.error(f"初始化预设数据失败: {e}")
        return False


async def full_verify():
    """完整验证"""
    logger.info("=" * 50)
    logger.info("TextLoom 系统验证")
    logger.info("=" * 50)

    # 验证数据库
    db_ok = await verify_database()

    # 检查表
    tables = await check_tables()
    tables_ok = len(tables) > 0

    # 验证服务
    service_ok = await verify_service()

    logger.info("=" * 50)
    if db_ok and tables_ok and service_ok:
        logger.info("✅ 所有验证通过，系统运行正常！")
    else:
        logger.warning("⚠️ 发现问题，请检查上述输出")
    logger.info("=" * 50)


async def main():
    """主函数"""
    import sys

    if len(sys.argv) < 2:
        print("TextLoom 数据库管理工具")
        print("用法:")
        print("  python init_database.py create     # 创建schema和表")
        print("  python init_database.py check      # 检查表状态")
        print("  python init_database.py drop       # 删除所有表")
        print("  python init_database.py schema     # 只创建schema")
        print("  python init_database.py reset      # 重置（删除后重建）")
        print("  python init_database.py verify     # 完整系统验证")
        print("  python init_database.py migrate    # 执行数据库迁移")
        print("  python init_database.py diff       # 检查模型与数据库差异")
        print("  python init_database.py init-data  # 初始化预设数据（人设和模板）")
        return

    command = sys.argv[1].lower()

    logger.info(f"连接数据库: {settings.database_url.split('@')[1]}")

    try:
        if command == "create":
            await create_schema()
            success = await create_tables()
            if success:
                await check_tables()

        elif command == "check":
            await check_tables()

        elif command == "drop":
            confirm = input("确认删除所有表? (yes/no): ")
            if confirm.lower() == "yes":
                await drop_tables()
            else:
                logger.info("操作已取消")

        elif command == "schema":
            await create_schema()

        elif command == "reset":
            confirm = input("确认重置数据库? (yes/no): ")
            if confirm.lower() == "yes":
                await drop_tables()
                await create_schema()
                await create_tables()
                await check_tables()
            else:
                logger.info("操作已取消")

        elif command == "verify":
            await full_verify()

        elif command == "diff":
            await check_schema_diff()

        elif command == "migrate":
            await add_migration_tracking()
            await migrate_database()

        elif command == "init-data":
            success = await init_preset_data()
            if success:
                logger.info("✅ 预设数据初始化完成")
            else:
                logger.error("❌ 预设数据初始化失败")

        else:
            logger.error(f"未知命令: {command}")

    except Exception as e:
        logger.error(f"操作失败: {e}")


if __name__ == "__main__":
    asyncio.run(main())
