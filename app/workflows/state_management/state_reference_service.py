"""
状态引用服务实现。

该模块提供了状态引用管理的能力，使用Redis作为引用存储后端。
"""

import json
import uuid
from typing import Any, Dict, Optional, Union

from app.data_access.cache.redis_client import RedisClient


class StateReferenceService:
    """
    状态引用服务，管理工作流状态引用。
    
    使用Redis作为存储后端，提供状态引用的创建、获取、更新和删除功能。
    """
    
    def __init__(
        self, 
        redis_client: RedisClient, 
        ttl: int = 3600,
        key_prefix: str = "multi_agent_platform:state_ref:"
    ) -> None:
        """
        初始化状态引用服务。

        参数:
            redis_client: Redis客户端实例
            ttl: 引用过期时间（秒），默认为1小时
            key_prefix: 键前缀
        """
        self.redis_client = redis_client
        self.ttl = ttl
        self.key_prefix = key_prefix

    def _get_key(self, reference_id: str) -> str:
        """
        获取完整的Redis键名。

        参数:
            reference_id: 引用ID

        返回:
            str: 完整的Redis键名
        """
        return f"{self.key_prefix}{reference_id}"

    def create(self, state_data: Dict[str, Any]) -> str:
        """
        创建状态引用并返回引用ID。

        参数:
            state_data: 要存储的状态数据

        返回:
            str: 引用ID
        """
        # 生成唯一引用ID
        reference_id = str(uuid.uuid4())
        key = self._get_key(reference_id)
        
        # 序列化状态数据
        serialized_data = json.dumps(state_data)
        
        # 存储数据并设置过期时间
        self.redis_client.set(key, serialized_data, ex=self.ttl)
        
        return reference_id

    async def acreate(self, state_data: Dict[str, Any]) -> str:
        """
        异步创建状态引用并返回引用ID。

        参数:
            state_data: 要存储的状态数据

        返回:
            str: 引用ID
        """
        # 生成唯一引用ID
        reference_id = str(uuid.uuid4())
        key = self._get_key(reference_id)
        
        # 序列化状态数据
        serialized_data = json.dumps(state_data)
        
        # 异步存储数据并设置过期时间
        await self.redis_client.aset(key, serialized_data, ex=self.ttl)
        
        return reference_id

    def get(self, reference_id: str) -> Optional[Dict[str, Any]]:
        """
        获取状态引用。

        参数:
            reference_id: 引用ID

        返回:
            Optional[Dict[str, Any]]: 状态数据，若不存在则返回None
        """
        key = self._get_key(reference_id)
        
        # 获取数据
        serialized_data = self.redis_client.get(key)
        
        if serialized_data is None:
            return None
        
        # 反序列化数据
        try:
            return json.loads(serialized_data)
        except json.JSONDecodeError:
            raise ValueError(f"无法反序列化引用数据 (reference_id={reference_id})")

    async def aget(self, reference_id: str) -> Optional[Dict[str, Any]]:
        """
        异步获取状态引用。

        参数:
            reference_id: 引用ID

        返回:
            Optional[Dict[str, Any]]: 状态数据，若不存在则返回None
        """
        key = self._get_key(reference_id)
        
        # 异步获取数据
        serialized_data = await self.redis_client.aget(key)
        
        if serialized_data is None:
            return None
        
        # 反序列化数据
        try:
            return json.loads(serialized_data)
        except json.JSONDecodeError:
            raise ValueError(f"无法反序列化引用数据 (reference_id={reference_id})")

    def update(self, reference_id: str, state_data: Dict[str, Any]) -> None:
        """
        更新状态引用。

        参数:
            reference_id: 引用ID
            state_data: 新的状态数据
        """
        key = self._get_key(reference_id)
        
        # 检查引用是否存在
        if not self.redis_client.exists(key):
            raise ValueError(f"引用不存在 (reference_id={reference_id})")
        
        # 序列化状态数据
        serialized_data = json.dumps(state_data)
        
        # 更新数据，保留原有的TTL
        ttl = self.redis_client.ttl(key)
        if ttl > 0:
            self.redis_client.set(key, serialized_data, ex=ttl)
        else:
            self.redis_client.set(key, serialized_data, ex=self.ttl)

    async def aupdate(self, reference_id: str, state_data: Dict[str, Any]) -> None:
        """
        异步更新状态引用。

        参数:
            reference_id: 引用ID
            state_data: 新的状态数据
        """
        key = self._get_key(reference_id)
        
        # 检查引用是否存在
        if not await self.redis_client.aexists(key):
            raise ValueError(f"引用不存在 (reference_id={reference_id})")
        
        # 序列化状态数据
        serialized_data = json.dumps(state_data)
        
        # 更新数据，保留原有的TTL
        ttl = await self.redis_client.attl(key)
        if ttl > 0:
            await self.redis_client.aset(key, serialized_data, ex=ttl)
        else:
            await self.redis_client.aset(key, serialized_data, ex=self.ttl)

    def delete(self, reference_id: str) -> None:
        """
        删除状态引用。

        参数:
            reference_id: 引用ID
        """
        key = self._get_key(reference_id)
        self.redis_client.delete(key)

    async def adelete(self, reference_id: str) -> None:
        """
        异步删除状态引用。

        参数:
            reference_id: 引用ID
        """
        key = self._get_key(reference_id)
        await self.redis_client.adelete(key)

    def extend_ttl(self, reference_id: str, ttl: Optional[int] = None) -> None:
        """
        延长引用过期时间。

        参数:
            reference_id: 引用ID
            ttl: 新的过期时间（秒），若为None则使用默认过期时间
        """
        key = self._get_key(reference_id)
        
        # 检查引用是否存在
        if not self.redis_client.exists(key):
            raise ValueError(f"引用不存在 (reference_id={reference_id})")
        
        # 延长过期时间
        self.redis_client.expire(key, ttl or self.ttl)

    async def aextend_ttl(self, reference_id: str, ttl: Optional[int] = None) -> None:
        """
        异步延长引用过期时间。

        参数:
            reference_id: 引用ID
            ttl: 新的过期时间（秒），若为None则使用默认过期时间
        """
        key = self._get_key(reference_id)
        
        # 检查引用是否存在
        if not await self.redis_client.aexists(key):
            raise ValueError(f"引用不存在 (reference_id={reference_id})")
        
        # 延长过期时间
        await self.redis_client.aexpire(key, ttl or self.ttl)
