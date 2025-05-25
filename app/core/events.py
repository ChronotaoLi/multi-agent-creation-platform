"""
事件处理模块

处理应用启动和关闭事件，初始化和释放资源。
"""
import logging
from typing import Callable

from fastapi import FastAPI

from .logging_config import configure_logging, get_logger
from .config import get_settings

# 获取应用配置和日志器
settings = get_settings()
logger = get_logger(__name__)


def startup_event_handler(app: FastAPI) -> Callable:
    """注册应用启动事件处理函数

    Args:
        app: FastAPI应用实例

    Returns:
        Callable: 启动事件处理函数
    """
    async def startup() -> None:
        """应用启动事件处理函数"""
        # 配置日志系统
        configure_logging()
        
        logger.info(f"应用正在启动，环境: {settings.app_env}，调试模式: {settings.debug}")
        
        # 初始化各种资源
        await _startup_db(app)
        await _startup_redis(app)
        await _startup_vector_store(app)
        await _startup_graph_store(app)
        
        logger.info("应用启动完成")
    
    return startup


async def _startup_db(app: FastAPI) -> None:
    """初始化数据库连接

    Args:
        app: FastAPI应用实例
    """
    logger.info("正在初始化数据库连接...")
    from app.data_access.db_session import engine, init_db
    await init_db(engine)
    app.state.db_engine = engine
    app.state.db_initialized = True
    logger.info("数据库连接初始化完成")


async def _startup_redis(app: FastAPI) -> None:
    """初始化Redis连接

    Args:
        app: FastAPI应用实例
    """
    logger.info("正在初始化Redis连接...")
    from app.data_access.cache.redis_client import RedisClient
    client = RedisClient()
    await client.connect()
    app.state.redis_client = client
    app.state.redis_initialized = True
    logger.info("Redis连接初始化完成")


async def _startup_vector_store(app: FastAPI) -> None:
    """初始化向量存储

    Args:
        app: FastAPI应用实例
    """
    logger.info("正在初始化向量存储...")
    from app.data_access.vector_store.milvus_client import MilvusClient
    client = MilvusClient()
    await client.connect()
    app.state.milvus_client = client
    app.state.vector_store_initialized = True
    logger.info("向量存储初始化完成")


async def _startup_graph_store(app: FastAPI) -> None:
    """初始化图存储

    Args:
        app: FastAPI应用实例
    """
    logger.info("正在初始化图存储...")
    from app.data_access.graph_store.neo4j_client import Neo4jClient
    # settings is already imported at the top of the file
    client = Neo4jClient(
        uri=settings.neo4j_uri,
        user=settings.neo4j_username,
        password=settings.neo4j_password,
        database=settings.neo4j_database  # Assuming settings.neo4j_database exists
    )
    await client.connect()
    app.state.neo4j_client = client
    app.state.graph_store_initialized = True
    logger.info("图存储初始化完成")


def shutdown_event_handler(app: FastAPI) -> Callable:
    """注册应用关闭事件处理函数

    Args:
        app: FastAPI应用实例

    Returns:
        Callable: 关闭事件处理函数
    """
    async def shutdown() -> None:
        """应用关闭事件处理函数"""
        logger.info("应用正在关闭...")
        
        # 释放各种资源
        await _shutdown_db(app)
        await _shutdown_redis(app)
        await _shutdown_vector_store(app)
        await _shutdown_graph_store(app)
        
        logger.info("应用已关闭")
    
    return shutdown


async def _shutdown_db(app: FastAPI) -> None:
    """关闭数据库连接

    Args:
        app: FastAPI应用实例
    """
    logger.info("正在关闭数据库连接...")
    from app.data_access.db_session import engine # Import engine, though it might be better to get it from app.state
    if hasattr(app.state, 'db_engine') and app.state.db_engine:
        await app.state.db_engine.dispose()
    app.state.db_initialized = False
    logger.info("数据库连接已关闭")


async def _shutdown_redis(app: FastAPI) -> None:
    """关闭Redis连接

    Args:
        app: FastAPI应用实例
    """
    logger.info("正在关闭Redis连接...")
    if hasattr(app.state, 'redis_client') and app.state.redis_client:
        await app.state.redis_client.close()
    app.state.redis_initialized = False
    logger.info("Redis连接已关闭")


async def _shutdown_vector_store(app: FastAPI) -> None:
    """关闭向量存储

    Args:
        app: FastAPI应用实例
    """
    logger.info("正在关闭向量存储...")
    if hasattr(app.state, 'milvus_client') and app.state.milvus_client:
        await app.state.milvus_client.close()
    app.state.vector_store_initialized = False
    logger.info("向量存储已关闭")


async def _shutdown_graph_store(app: FastAPI) -> None:
    """关闭图存储

    Args:
        app: FastAPI应用实例
    """
    logger.info("正在关闭图存储...")
    if hasattr(app.state, 'neo4j_client') and app.state.neo4j_client:
        await app.state.neo4j_client.close()
    app.state.graph_store_initialized = False
    logger.info("图存储已关闭")
