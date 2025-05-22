"""
Redis缓存实现模块

提供基于Redis的缓存实现，支持多种数据类型的存储和读取。
"""
import logging
from typing import Any, Dict, List, Optional, Union
from functools import lru_cache

from app.data_access.cache.redis_client import RedisClient
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class RedisCache:
    """
    基于Redis的缓存实现
    """
    
    def __init__(self, redis_url: str = None):
        """
        初始化Redis缓存
        
        参数:
            redis_url: str - Redis连接URL
        """
        self.client = RedisClient(redis_url=redis_url)
        
    async def get(self, key: str) -> Any:
        """
        获取缓存值
        
        参数:
            key: str - 键名
            
        返回:
            Any: 缓存值，不存在则为None
        """
        try:
            return await self.client.get(key)
        except Exception as e:
            logger.error(f"从缓存获取键{key}失败: {str(e)}")
            return None
    
    async def set(self, key: str, value: Any, expiry: int = None) -> bool:
        """
        设置缓存值
        
        参数:
            key: str - 键名
            value: Any - 值
            expiry: int - 过期时间（秒）
            
        返回:
            bool: 操作是否成功
        """
        try:
            await self.client.set(key, value, expire=expiry)
            return True
        except Exception as e:
            logger.error(f"设置缓存键{key}失败: {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        删除缓存键
        
        参数:
            key: str - 键名
            
        返回:
            bool: 操作是否成功
        """
        try:
            await self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"删除缓存键{key}失败: {str(e)}")
            return False
    
    async def exists(self, key: str) -> bool:
        """
        检查键是否存在
        
        参数:
            key: str - 键名
            
        返回:
            bool: 键是否存在
        """
        try:
            return await self.client.exists(key)
        except Exception as e:
            logger.error(f"检查缓存键{key}是否存在失败: {str(e)}")
            return False
    
    # 哈希表操作
    async def hset(self, name: str, key: str, value: Any) -> bool:
        """
        设置哈希表字段
        
        参数:
            name: str - 哈希表名
            key: str - 字段名
            value: Any - 值
            
        返回:
            bool: 操作是否成功
        """
        try:
            await self.client.hset(name, key, value)
            return True
        except Exception as e:
            logger.error(f"设置哈希表{name}字段{key}失败: {str(e)}")
            return False
    
    async def hget(self, name: str, key: str) -> Any:
        """
        获取哈希表字段
        
        参数:
            name: str - 哈希表名
            key: str - 字段名
            
        返回:
            Any: 字段值，不存在则为None
        """
        try:
            return await self.client.hget(name, key)
        except Exception as e:
            logger.error(f"获取哈希表{name}字段{key}失败: {str(e)}")
            return None
    
    async def hgetall(self, name: str) -> Dict[str, Any]:
        """
        获取哈希表所有字段
        
        参数:
            name: str - 哈希表名
            
        返回:
            Dict[str, Any]: 字段和值的字典
        """
        try:
            return await self.client.hgetall(name)
        except Exception as e:
            logger.error(f"获取哈希表{name}所有字段失败: {str(e)}")
            return {}
    
    async def close(self) -> None:
        """
        关闭缓存连接
        """
        try:
            await self.client.close()
        except Exception as e:
            logger.error(f"关闭缓存连接失败: {str(e)}")


@lru_cache()
def get_cache() -> RedisCache:
    """
    获取Redis缓存单例实例
    
    返回:
        RedisCache: Redis缓存实例
    """
    settings = get_settings()
    return RedisCache(redis_url=settings.redis_url) 