import os
from logging.config import fileConfig
from typing import Optional

from sqlalchemy import engine_from_config, pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from config import settings

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
from models.db_models import Base

target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def _resolve_db_url() -> Optional[str]:
    """从环境变量、alembic.ini、config.settings 解析数据库URL，并做必要转换。"""
    section = config.get_section(config.config_ini_section, {})
    db_url = (
        os.getenv("DATABASE_URL")
        or section.get("sqlalchemy.url")
        or settings.database_url
    )
    if db_url:
        db_url = db_url.strip()
        if db_url.startswith("postgresql+asyncpg://"):
            db_url = db_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    return db_url if db_url else None


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # 优先从环境 / alembic.ini / config.py 读取数据库 URL
    url = _resolve_db_url()
    if not url:
        raise RuntimeError(
            "DATABASE_URL 未设置，且 alembic.ini/sqlalchemy.url 为空。请导出环境变量或在 .env 中设置，并确保可被 config.Settings 读取。"
        )
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # 允许从环境/alembic.ini/config.settings 读取 URL
    section = config.get_section(config.config_ini_section, {})
    db_url = _resolve_db_url()
    if not db_url:
        raise RuntimeError(
            "DATABASE_URL 未设置，且 alembic.ini/sqlalchemy.url 为空。请导出环境变量或在 .env 中设置，并确保可被 config.Settings 读取。"
        )
    section["sqlalchemy.url"] = db_url

    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    # 仅包含 textloom_core schema 的对象，避免误删其他业务/系统表
    def include_object(object, name, type_, reflected, compare_to):
        if type_ == "schema":
            return name == "textloom_core"
        if type_ == "table":
            obj_schema = getattr(object, "schema", None)
            return obj_schema == "textloom_core"
        if type_ in (
            "index",
            "column",
            "unique_constraint",
            "foreign_key_constraint",
            "primary_key",
        ):
            table = getattr(object, "table", None)
            table_schema = getattr(table, "schema", None) if table is not None else None
            return table_schema == "textloom_core"
        return True

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema="textloom_core",
            include_schemas=True,
            include_object=include_object,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
