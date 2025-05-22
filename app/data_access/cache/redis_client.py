"""
Redis客户端封装模块

该模块封装了对Redis的各种操作，包括基本的键值操作、哈希表操作和Streams功能。
支持同步和异步操作模式，主要用于缓存、消息队列和分布式锁等场景。
"""

import logging
import pickle
import json
import uuid
import asyncio
from typing import Any, Dict, List, Optional, Tuple, Union, Callable, Awaitable

import redis
from redis.exceptions import ResponseError, LockNotOwnedError, LockError
from redis.asyncio import Redis as AsyncRedis
from redis.asyncio import ConnectionPool

from app.core.config import get_settings

logger = logging.getLogger(__name__)

class RedisClient:
    """封装Redis操作的客户端类"""
    
    def __init__(
        self,
        redis_url: str = None,
        decode_responses: bool = False,
        encoding: str = "utf-8"
    ):
        """
        初始化Redis客户端
        
        参数:
            redis_url: str - Redis连接URL，格式为"redis://[[username]:[password]]@host:port/db"
            decode_responses: bool - 是否自动解码响应（True为字符串，False为字节）
            encoding: str - 编码格式
        """
        if redis_url is None:
            # 获取配置
            settings = get_settings()
            redis_url = getattr(settings, "redis_url", None)
            
        self.redis_url = redis_url
        self.decode_responses = decode_responses
        self.encoding = encoding
        self._pool = None
        self._client = None
        
    async def connect(self) -> None:
        """连接到Redis服务器"""
        if self._client is None:
            try:
                self._pool = ConnectionPool.from_url(
                    self.redis_url,
                    decode_responses=self.decode_responses,
                    encoding=self.encoding
                )
                self._client = AsyncRedis(connection_pool=self._pool)
                # 测试连接
                await self._client.ping()
                logger.info(f"成功连接到Redis服务器: {self.redis_url}")
            except Exception as e:
                logger.error(f"连接Redis服务器失败: {str(e)}")
                raise
    
    async def get(self, key: str) -> Any:
        """获取键值"""
        if self._client is None:
            await self.connect()
        
        value = await self._client.get(key)
        if value is not None and not self.decode_responses:
            try:
                return pickle.loads(value)
            except:
                return value
        return value
    
    async def set(self, key: str, value: Any, expire: int = None) -> None:
        """
        设置键值
        
        参数:
            key: str - 键名
            value: Any - 值（会自动序列化）
            expire: int - 过期时间（秒）
        """
        if self._client is None:
            await self.connect()
            
        if not isinstance(value, (str, bytes, int, float)) and not self.decode_responses:
            value = pickle.dumps(value)
            
        if expire:
            await self._client.setex(key, expire, value)
        else:
            await self._client.set(key, value)
    
    async def delete(self, key: str) -> None:
        """删除键"""
        if self._client is None:
            await self.connect()
            
        await self._client.delete(key)
    
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        if self._client is None:
            await self.connect()
            
        return await self._client.exists(key) > 0
    
    # 哈希表操作
    async def hset(self, name: str, key: str, value: Any) -> None:
        """设置哈希字段"""
        if self._client is None:
            await self.connect()
            
        if not isinstance(value, (str, bytes, int, float)) and not self.decode_responses:
            value = pickle.dumps(value)
            
        await self._client.hset(name, key, value)
    
    async def hget(self, name: str, key: str) -> Any:
        """获取哈希字段"""
        if self._client is None:
            await self.connect()
            
        value = await self._client.hget(name, key)
        if value is not None and not self.decode_responses:
            try:
                return pickle.loads(value)
            except:
                return value
        return value
    
    async def hmget(self, name: str, keys: List[str]) -> List[Any]:
        """获取多个哈希字段"""
        if self._client is None:
            await self.connect()
            
        values = await self._client.hmget(name, keys)
        if not self.decode_responses:
            result = []
            for value in values:
                if value is not None:
                    try:
                        result.append(pickle.loads(value))
                    except:
                        result.append(value)
                else:
                    result.append(None)
            return result
        return values
    
    async def hgetall(self, name: str) -> Dict[str, Any]:
        """获取所有哈希字段"""
        if self._client is None:
            await self.connect()
            
        result = await self._client.hgetall(name)
        if not self.decode_responses:
            deserialized_result = {}
            for key, value in result.items():
                try:
                    deserialized_result[key] = pickle.loads(value)
                except:
                    deserialized_result[key] = value
            return deserialized_result
        return result
    
    # Streams操作
    async def xadd(self, stream: str, fields: Dict[str, Any], id: str = "*", maxlen: int = None) -> str:
        """
        添加Stream条目
        
        参数:
            stream: str - 流名称
            fields: Dict[str, Any] - 字段和值的字典
            id: str - 条目ID，默认"*"让Redis自动生成
            maxlen: int - 流的最大长度，超过会裁剪旧条目
        
        返回:
            str: 添加的条目ID
        """
        if self._client is None:
            await self.connect()
            
        # 序列化复杂对象
        serialized_fields = {}
        for key, value in fields.items():
            if not isinstance(value, (str, bytes, int, float)) and not self.decode_responses:
                serialized_fields[key] = json.dumps(value)
            else:
                serialized_fields[key] = value
        
        kwargs = {}
        if maxlen is not None:
            kwargs['maxlen'] = maxlen
            
        return await self._client.xadd(stream, serialized_fields, id=id, **kwargs)
    
    async def xread(self, streams: Dict[str, str], block: int = None, count: int = None) -> List:
        """
        读取Stream条目
        
        参数:
            streams: Dict[str, str] - 流名称和起始ID的字典，如{'stream1': '0', 'stream2': '$'}
            block: int - 阻塞毫秒数，None为不阻塞
            count: int - 返回的最大条目数
        
        返回:
            List: 读取的条目列表
        """
        if self._client is None:
            await self.connect()
            
        kwargs = {}
        if block is not None:
            kwargs['block'] = block
        if count is not None:
            kwargs['count'] = count
            
        result = await self._client.xread(streams=streams, **kwargs)
        return result
    
    async def xgroup_create(self, stream: str, group: str, id: str = "$", mkstream: bool = False) -> bool:
        """
        创建消费者组
        
        参数:
            stream: str - 流名称
            group: str - 消费者组名称
            id: str - 起始ID，默认"$"表示只消费新消息
            mkstream: bool - 如果流不存在是否创建
        
        返回:
            bool: 成功返回True
        """
        if self._client is None:
            await self.connect()
            
        try:
            await self._client.xgroup_create(stream, group, id=id, mkstream=mkstream)
            return True
        except ResponseError as e:
            if "BUSYGROUP" in str(e):  # 消费者组已存在
                logger.info(f"消费者组 {group} 已存在于流 {stream}")
                return True
            logger.error(f"创建消费者组失败: {str(e)}")
            raise
    
    async def xreadgroup(self, group: str, consumer: str, streams: Dict[str, str], 
                        block: int = None, count: int = None) -> List:
        """
        消费者组读取
        
        参数:
            group: str - 消费者组名称
            consumer: str - 消费者名称
            streams: Dict[str, str] - 流名称和ID的字典，如{'stream1': '>', 'stream2': '>'}
                                     '>'表示未分配给其他消费者的消息
            block: int - 阻塞毫秒数，None为不阻塞
            count: int - 返回的最大条目数
        
        返回:
            List: 读取的条目列表
        """
        if self._client is None:
            await self.connect()
            
        kwargs = {}
        if block is not None:
            kwargs['block'] = block
        if count is not None:
            kwargs['count'] = count
            
        return await self._client.xreadgroup(group, consumer, streams, **kwargs)
    
    async def xack(self, stream: str, group: str, *ids) -> int:
        """
        确认消息处理
        
        参数:
            stream: str - 流名称
            group: str - 消费者组名称
            *ids - 要确认的消息ID列表
        
        返回:
            int: 确认的消息数量
        """
        if self._client is None:
            await self.connect()
            
        return await self._client.xack(stream, group, *ids)
    
    async def xpending(self, stream: str, group: str) -> Dict:
        """
        获取待处理消息信息
        
        参数:
            stream: str - 流名称
            group: str - 消费者组名称
        
        返回:
            Dict: 待处理消息信息
        """
        if self._client is None:
            await self.connect()
            
        return await self._client.xpending(stream, group)
    
    async def xclaim(self, stream: str, group: str, consumer: str, 
                    min_idle_time: int, *ids, **kwargs) -> List:
        """
        认领待处理消息
        
        参数:
            stream: str - 流名称
            group: str - 消费者组名称
            consumer: str - 消费者名称
            min_idle_time: int - 最小空闲时间(毫秒)
            *ids - 要认领的消息ID列表
            **kwargs - 其他参数
        
        返回:
            List: 认领的消息列表
        """
        if self._client is None:
            await self.connect()
            
        return await self._client.xclaim(stream, group, consumer, min_idle_time, *ids, **kwargs)
    
    async def xdel(self, stream: str, *ids) -> int:
        """
        删除消息
        
        参数:
            stream: str - 流名称
            *ids - 要删除的消息ID列表
        
        返回:
            int: 删除的消息数量
        """
        if self._client is None:
            await self.connect()
            
        return await self._client.xdel(stream, *ids)
    
    async def xtrim(self, stream: str, maxlen: int, approximate: bool = True) -> int:
        """
        裁剪流
        
        参数:
            stream: str - 流名称
            maxlen: int - 最大长度
            approximate: bool - 是否近似裁剪(效率更高)
        
        返回:
            int: 裁剪的消息数量
        """
        if self._client is None:
            await self.connect()
            
        return await self._client.xtrim(stream, maxlen=maxlen, approximate=approximate)
    
    # 分布式锁相关操作
    async def acquire_lock(self, lock_name: str, timeout: int = 10, wait_timeout: int = None, 
                          retry_interval: float = 0.2) -> str:
        """
        获取分布式锁
        
        参数:
            lock_name: str - 锁名称
            timeout: int - 锁超时时间(秒)，防止死锁
            wait_timeout: int - 等待锁的超时时间(秒)，None表示一直等待
            retry_interval: float - 重试间隔(秒)
            
        返回:
            str: 锁标识，用于释放锁
        """
        if self._client is None:
            await self.connect()
        
        # 生成唯一锁标识
        lock_id = str(uuid.uuid4())
        lock_key = f"lock:{lock_name}"
        
        # 获取当前时间
        start_time = asyncio.get_event_loop().time()
        
        while True:
            # 尝试获取锁 (NX = 只有不存在时才设置, EX = 设置过期时间)
            acquired = await self._client.set(lock_key, lock_id, nx=True, ex=timeout)
            
            if acquired:
                logger.debug(f"获取锁成功: {lock_name}, ID: {lock_id}")
                return lock_id
            
            # 检查是否超过等待时间
            if wait_timeout is not None:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > wait_timeout:
                    logger.warning(f"获取锁超时: {lock_name}")
                    return None
            
            # 等待重试
            await asyncio.sleep(retry_interval)
    
    async def release_lock(self, lock_name: str, lock_id: str) -> bool:
        """
        释放分布式锁
        
        参数:
            lock_name: str - 锁名称
            lock_id: str - 锁标识，必须与获取锁时返回的标识一致
            
        返回:
            bool: 是否成功释放锁
        """
        if self._client is None:
            await self.connect()
            
        lock_key = f"lock:{lock_name}"
        
        # 使用Lua脚本原子性释放锁，确保只释放自己的锁
        script = """
        if redis.call('get', KEYS[1]) == ARGV[1] then
            return redis.call('del', KEYS[1])
        else
            return 0
        end
        """
        
        try:
            result = await self._client.eval(script, 1, lock_key, lock_id)
            success = bool(result)
            if success:
                logger.debug(f"释放锁成功: {lock_name}, ID: {lock_id}")
            else:
                logger.warning(f"释放锁失败(可能已过期或不属于此客户端): {lock_name}, ID: {lock_id}")
            return success
        except Exception as e:
            logger.error(f"释放锁出错: {lock_name}, ID: {lock_id}, 错误: {str(e)}")
            return False
    
    # 分布式锁上下文管理器
    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        if self._client:
            await self.close()
            
    # 上下文管理器形式的锁
    async def lock(self, lock_name: str, timeout: int = 10, wait_timeout: int = None, 
                  retry_interval: float = 0.2):
        """
        分布式锁上下文管理器
        
        用法:
        async with redis_client.lock("my_lock"):
            # 临界区代码
            
        参数同acquire_lock
        """
        class AsyncLock:
            def __init__(self, client, name, timeout, wait_timeout, retry_interval):
                self.client = client
                self.name = name
                self.timeout = timeout
                self.wait_timeout = wait_timeout
                self.retry_interval = retry_interval
                self.lock_id = None
                
            async def __aenter__(self):
                self.lock_id = await self.client.acquire_lock(
                    self.name, self.timeout, self.wait_timeout, self.retry_interval
                )
                if not self.lock_id:
                    raise TimeoutError(f"无法获取锁: {self.name}")
                return self
                
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                if self.lock_id:
                    await self.client.release_lock(self.name, self.lock_id)
                    
        return AsyncLock(self, lock_name, timeout, wait_timeout, retry_interval)
    
    # 有序集合操作
    async def zadd(self, name: str, mapping: Dict[Any, float]) -> int:
        """
        添加到有序集合
        
        参数:
            name: str - 集合名称
            mapping: Dict[Any, float] - 成员到分数的映射
            
        返回:
            int: 添加的成员数量
        """
        if self._client is None:
            await self.connect()
            
        # 如果值不是简单类型且不自动解码，则序列化
        serialized_mapping = {}
        for member, score in mapping.items():
            if not isinstance(member, (str, bytes, int, float)) and not self.decode_responses:
                serialized_mapping[pickle.dumps(member)] = score
            else:
                serialized_mapping[member] = score
                
        return await self._client.zadd(name, serialized_mapping)
    
    async def zrange(self, name: str, start: int, end: int, withscores: bool = False) -> List:
        """
        获取有序集合范围内的成员
        
        参数:
            name: str - 集合名称
            start: int - 起始索引(从0开始)
            end: int - 结束索引(-1表示最后一个元素)
            withscores: bool - 是否返回分数
            
        返回:
            List: 成员列表，或成员和分数的元组列表
        """
        if self._client is None:
            await self.connect()
            
        result = await self._client.zrange(name, start, end, withscores=withscores)
        
        # 如果不自动解码，尝试反序列化
        if not self.decode_responses:
            if withscores:
                deserialized_result = []
                for member, score in result:
                    try:
                        deserialized_result.append((pickle.loads(member), score))
                    except:
                        deserialized_result.append((member, score))
                return deserialized_result
            else:
                deserialized_result = []
                for member in result:
                    try:
                        deserialized_result.append(pickle.loads(member))
                    except:
                        deserialized_result.append(member)
                return deserialized_result
                
        return result
    
    async def zrangebyscore(self, name: str, min: float, max: float, 
                          withscores: bool = False) -> List:
        """
        获取有序集合中指定分数范围的成员
        
        参数:
            name: str - 集合名称
            min: float - 最小分数
            max: float - 最大分数
            withscores: bool - 是否返回分数
            
        返回:
            List: 成员列表，或成员和分数的元组列表
        """
        if self._client is None:
            await self.connect()
            
        result = await self._client.zrangebyscore(name, min, max, withscores=withscores)
        
        # 如果不自动解码，尝试反序列化
        if not self.decode_responses:
            if withscores:
                deserialized_result = []
                for member, score in result:
                    try:
                        deserialized_result.append((pickle.loads(member), score))
                    except:
                        deserialized_result.append((member, score))
                return deserialized_result
            else:
                deserialized_result = []
                for member in result:
                    try:
                        deserialized_result.append(pickle.loads(member))
                    except:
                        deserialized_result.append(member)
                return deserialized_result
                
        return result
    
    async def zrem(self, name: str, *values) -> int:
        """
        从有序集合中删除成员
        
        参数:
            name: str - 集合名称
            *values - 要删除的成员列表
            
        返回:
            int: 删除的成员数量
        """
        if self._client is None:
            await self.connect()
            
        # 如果值不是简单类型且不自动解码，则序列化
        serialized_values = []
        for value in values:
            if not isinstance(value, (str, bytes, int, float)) and not self.decode_responses:
                serialized_values.append(pickle.dumps(value))
            else:
                serialized_values.append(value)
                
        return await self._client.zrem(name, *serialized_values)
    
    # 发布/订阅操作
    async def publish(self, channel: str, message: Any) -> int:
        """
        发布消息
        
        参数:
            channel: str - 频道名称
            message: Any - 消息内容，非简单类型会被JSON序列化
            
        返回:
            int: 接收消息的客户端数量
        """
        if self._client is None:
            await self.connect()
        
        # 序列化消息
        if not isinstance(message, (str, bytes, int, float)):
            message = json.dumps(message)
            
        return await self._client.publish(channel, message)
    
    async def subscribe(self, *channels: str) -> None:
        """
        订阅频道
        
        参数:
            *channels: str - 要订阅的频道名称列表
            
        返回:
            (channel, message) 的生成器
        """
        if self._client is None:
            await self.connect()
            
        pubsub = self._client.pubsub()
        await pubsub.subscribe(*channels)
        return pubsub
        
    async def psubscribe(self, *patterns: str) -> None:
        """
        订阅模式频道
        
        参数:
            *patterns: str - 要订阅的模式列表，支持通配符
            
        返回:
            pubsub对象
        """
        if self._client is None:
            await self.connect()
            
        pubsub = self._client.pubsub()
        await pubsub.psubscribe(*patterns)
        return pubsub
        
    async def listen_channel(self, pubsub, callback: Callable[[str, Any], Awaitable[None]]) -> None:
        """
        监听频道并处理消息
        
        参数:
            pubsub - pubsub对象，从subscribe或psubscribe获取
            callback: Callable - 消息处理回调函数，接收频道名和消息内容
        """
        try:
            async for message in pubsub.listen():
                # 跳过订阅确认消息
                if message['type'] in ('subscribe', 'psubscribe'):
                    continue
                    
                channel = message['channel']
                data = message['data']
                
                # 尝试解析JSON
                if isinstance(data, str):
                    try:
                        data = json.loads(data)
                    except:
                        pass  # 如果不是JSON，保留原始字符串
                        
                await callback(channel, data)
        except Exception as e:
            logger.error(f"监听频道出错: {str(e)}")
            
    async def close(self) -> None:
        """关闭连接"""
        if self._client is not None:
            await self._client.close()
            self._client = None
        if self._pool is not None:
            await self._pool.disconnect()
            self._pool = None
        logger.info("Redis连接已关闭")