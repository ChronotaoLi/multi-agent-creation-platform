"""
Alembic环境配置

此模块配置Alembic迁移环境，设置数据库连接和迁移选项
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# 导入配置和所有模型，确保迁移脚本识别所有表
from app.core.config import get_settings
from app.data_access.db_session import Base
from app.models.domain import *  # 导入所有实体模型

# 获取Alembic配置
config = context.config

# 读取logging配置
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 获取应用配置
settings = get_settings()

# 构建异步数据库URL，使用 asyncpg 驱动
sync_db_url = str(settings.database_url)
async_db_url = sync_db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
config.set_main_option("sqlalchemy.url", async_db_url)

# 添加模型的元数据
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    在"离线"模式下运行迁移

    在此模式下，不需要实际连接数据库，将生成SQL脚本
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """
    执行迁移操作
    
    Args:
        connection: 数据库连接对象
    """
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    以异步方式运行迁移
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """
    在"在线"模式下运行迁移
    
    在此模式下，需要实际连接数据库执行迁移
    """
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
