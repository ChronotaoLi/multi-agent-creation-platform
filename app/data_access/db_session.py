"""
数据库会话管理模块

提供SQLAlchemy异步引擎设置、会话工厂和上下文管理功能。
"""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker, AsyncEngine
from sqlalchemy.orm import declarative_base

from app.core.config import get_settings

# 获取应用配置
settings = get_settings()
# 构建异步数据库URL，使用 asyncpg 驱动
sync_db_url = str(settings.database_url)
async_db_url = sync_db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# 创建数据库引擎
engine = create_async_engine(
    async_db_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
)

# 创建会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# 创建声明性基类
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话的依赖函数

    作为FastAPI依赖项使用，提供自动关闭的数据库会话。

    Yields:
        AsyncSession: 异步数据库会话对象
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db(engine: AsyncEngine) -> None:
    """初始化数据库模式

    创建所有表和必要的数据库结构。

    Args:
        engine: 异步SQLAlchemy引擎
    """
    async with engine.begin() as conn:
        # 导入所有模型以确保Base.metadata包含所有表
        # 避免循环导入
        from app.models.domain import user, project, agent, role, content, knowledge
        from app.models.domain import workflow_models
        
        # 创建所有表
        await conn.run_sync(Base.metadata.create_all)
