"""
增强的LangGraph存储管理器实现。

该模块提供了对LangGraph存储接口的封装，增加了分布式锁管理、
改进的错误处理和跟踪等功能。
"""

from typing import Any, Dict, List, Optional, Tuple, Union, Protocol

# 修改导入，使用pydantic模型替代不存在的Document类
from pydantic import BaseModel

class Document(BaseModel):
    """文档类，用于存储和检索数据。"""
    
    page_content: str
    metadata: Dict[str, Any] = {}

# 创建Lock和BaseStore接口，替代不存在的导入
class Lock(Protocol):
    """锁接口。"""
    
    def acquire(self, blocking: bool = True, blocking_timeout: Optional[float] = None) -> bool:
        """获取锁。"""
        ...
    
    def release(self) -> None:
        """释放锁。"""
        ...

class BaseStore(Protocol):
    """存储接口基类。"""
    
    def get(self, namespace: Tuple, key: str) -> Any:
        """获取存储的值。"""
        ...
    
    async def aget(self, namespace: Tuple, key: str) -> Any:
        """异步获取存储的值。"""
        ...
    
    def put(self, namespace: Tuple, key: str, value: Any) -> None:
        """存储值。"""
        ...
    
    async def aput(self, namespace: Tuple, key: str, value: Any) -> None:
        """异步存储值。"""
        ...
    
    def delete(self, namespace: Tuple, key: str) -> None:
        """删除存储的值。"""
        ...
    
    async def adelete(self, namespace: Tuple, key: str) -> None:
        """异步删除存储的值。"""
        ...
    
    def search(self, namespace: Tuple, query: str, **kwargs) -> List[Document]:
        """搜索文档。"""
        ...
    
    async def asearch(self, namespace: Tuple, query: str, **kwargs) -> List[Document]:
        """异步搜索文档。"""
        ...

from app.data_access.cache.redis_client import RedisClient


class LockManager:
    """分布式锁管理器，基于Redis实现。"""

    def __init__(self, redis_client: RedisClient) -> None:
        """
        初始化锁管理器。

        参数:
            redis_client: Redis客户端实例
        """
        self.redis_client = redis_client

    def acquire_lock(self, name: str, timeout: int = 30, wait_timeout: int = 10) -> Lock:
        """
        获取分布式锁。

        参数:
            name: 锁的名称
            timeout: 锁的超时时间（秒）
            wait_timeout: 等待获取锁的超时时间（秒）

        返回:
            Lock: 锁对象
        """
        # Redis锁实现使用Redis客户端的lock方法
        lock = self.redis_client.get_lock(name, timeout=timeout)
        
        # 尝试获取锁，可以设置等待时间
        acquired = lock.acquire(blocking=True, blocking_timeout=wait_timeout)
        if not acquired:
            raise TimeoutError(f"无法在 {wait_timeout} 秒内获取锁 '{name}'")
        
        return lock


class StoreConfig(BaseModel):
    """存储配置模型。"""
    
    namespace_prefix: str = "multi_agent_platform:"
    default_ttl: int = 3600  # 默认TTL，单位为秒


class EnhancedStoreManager:
    """
    增强的存储管理器，封装LangGraph存储接口并添加额外功能。
    """
    
    def __init__(
        self, 
        store: BaseStore, 
        redis_client: RedisClient,
        config: Optional[StoreConfig] = None
    ) -> None:
        """
        初始化存储管理器。

        参数:
            store: LangGraph基础存储接口
            redis_client: Redis客户端实例
            config: 存储配置
        """
        self.store = store
        self.lock_manager = LockManager(redis_client)
        self.config = config or StoreConfig()
        self.redis_client = redis_client

    def get(self, namespace: Tuple, key: str) -> Any:
        """
        获取存储的值。

        参数:
            namespace: 命名空间元组
            key: 存储的键

        返回:
            Any: 存储的值
        """
        try:
            return self.store.get(namespace, key)
        except Exception as e:
            # 增强错误处理，提供更详细的上下文信息
            raise ValueError(
                f"获取存储值出错 (namespace={namespace}, key={key}): {str(e)}"
            ) from e

    async def aget(self, namespace: Tuple, key: str) -> Any:
        """
        异步获取存储的值。

        参数:
            namespace: 命名空间元组
            key: 存储的键

        返回:
            Any: 存储的值
        """
        try:
            return await self.store.aget(namespace, key)
        except Exception as e:
            # 增强错误处理，提供更详细的上下文信息
            raise ValueError(
                f"异步获取存储值出错 (namespace={namespace}, key={key}): {str(e)}"
            ) from e

    def put(self, namespace: Tuple, key: str, value: Any) -> None:
        """
        存储值。

        参数:
            namespace: 命名空间元组
            key: 存储的键
            value: 要存储的值
        """
        try:
            self.store.put(namespace, key, value)
        except Exception as e:
            # 增强错误处理，提供更详细的上下文信息
            raise ValueError(
                f"存储值出错 (namespace={namespace}, key={key}): {str(e)}"
            ) from e

    async def aput(self, namespace: Tuple, key: str, value: Any) -> None:
        """
        异步存储值。

        参数:
            namespace: 命名空间元组
            key: 存储的键
            value: 要存储的值
        """
        try:
            await self.store.aput(namespace, key, value)
        except Exception as e:
            # 增强错误处理，提供更详细的上下文信息
            raise ValueError(
                f"异步存储值出错 (namespace={namespace}, key={key}): {str(e)}"
            ) from e

    def delete(self, namespace: Tuple, key: str) -> None:
        """
        删除存储的值。

        参数:
            namespace: 命名空间元组
            key: 存储的键
        """
        try:
            self.store.delete(namespace, key)
        except Exception as e:
            # 增强错误处理，提供更详细的上下文信息
            raise ValueError(
                f"删除值出错 (namespace={namespace}, key={key}): {str(e)}"
            ) from e

    async def adelete(self, namespace: Tuple, key: str) -> None:
        """
        异步删除存储的值。

        参数:
            namespace: 命名空间元组
            key: 存储的键
        """
        try:
            await self.store.adelete(namespace, key)
        except Exception as e:
            # 增强错误处理，提供更详细的上下文信息
            raise ValueError(
                f"异步删除值出错 (namespace={namespace}, key={key}): {str(e)}"
            ) from e

    def search(self, namespace: Tuple, query: str, **kwargs) -> List[Document]:
        """
        搜索文档。

        参数:
            namespace: 命名空间元组
            query: 搜索查询字符串
            **kwargs: 额外的搜索参数

        返回:
            List[Document]: 文档列表
        """
        try:
            return self.store.search(namespace, query, **kwargs)
        except Exception as e:
            # 增强错误处理，提供更详细的上下文信息
            raise ValueError(
                f"搜索文档出错 (namespace={namespace}, query={query}): {str(e)}"
            ) from e

    async def asearch(self, namespace: Tuple, query: str, **kwargs) -> List[Document]:
        """
        异步搜索文档。

        参数:
            namespace: 命名空间元组
            query: 搜索查询字符串
            **kwargs: 额外的搜索参数

        返回:
            List[Document]: 文档列表
        """
        try:
            return await self.store.asearch(namespace, query, **kwargs)
        except Exception as e:
            # 增强错误处理，提供更详细的上下文信息
            raise ValueError(
                f"异步搜索文档出错 (namespace={namespace}, query={query}): {str(e)}"
            ) from e

    def get_lock(self, name: str, **kwargs) -> Lock:
        """
        获取分布式锁。

        参数:
            name: 锁的名称
            **kwargs: 锁的额外参数

        返回:
            Lock: 锁对象
        """
        # 使用锁管理器获取分布式锁
        return self.lock_manager.acquire_lock(
            f"{self.config.namespace_prefix}lock:{name}",
            **kwargs
        )

    def close(self) -> None:
        """关闭存储连接。"""
        try:
            # 调用底层存储的close方法（如果存在）
            if hasattr(self.store, "close"):
                self.store.close()
        except Exception as e:
            # 增强错误处理
            raise ValueError(f"关闭存储连接出错: {str(e)}") from e
