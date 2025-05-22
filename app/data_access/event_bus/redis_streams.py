"""
基于Redis Streams的事件总线实现模块

本模块提供基于Redis Streams的事件总线实现，支持可靠的消息传递和消费者组。
"""

import asyncio
import json
import logging
from asyncio import Task
from contextlib import suppress
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from app.core.config import get_settings
from app.data_access.cache.redis_client import RedisClient
from app.data_access.event_bus.event_models import Event
from app.utils.common_utils import InMemoryLockManager, generate_ulid

settings = get_settings()
logger = logging.getLogger(__name__)


class RedisStreamsEventBus:
    """使用Redis Streams实现事件总线，支持可靠的消息传递和消费者组"""
    
    def __init__(
        self,
        redis_client: Optional[RedisClient] = None,
        stream_prefix: str = "events",
        max_stream_length: int = 10000
    ):
        """
        初始化Redis Streams事件总线
        
        参数:
            redis_client: Redis客户端
            stream_prefix: Stream名称前缀
            max_stream_length: Stream最大长度(默认10000)
        """
        self.redis_client = redis_client or RedisClient(decode_responses=True)
        self.stream_prefix = stream_prefix
        self.consumer_groups: Dict[str, Set[str]] = {}
        self.max_stream_length = max_stream_length
        self.lock_manager = InMemoryLockManager()
        self.logger = logging.getLogger("RedisStreamsEventBus")
    
    def get_stream_name(self, event_type: str) -> str:
        """
        获取事件类型对应的Stream名称
        
        参数:
            event_type: 事件类型
        
        返回:
            Stream名称
        """
        # 将事件类型转换为Stream名称，例如：
        # "workflow.started" -> "events:workflow"
        parts = event_type.split(".")
        return f"{self.stream_prefix}:{parts[0]}"
    
    async def publish_event(self, event: Event) -> str:
        """
        发布事件到对应Stream
        
        参数:
            event: 事件对象
        
        返回:
            消息ID
        """
        if not hasattr(self.redis_client, "_client") or self.redis_client._client is None:
            await self.redis_client.connect()
        
        stream_name = self.get_stream_name(event.event_type)
        
        # 将事件转换为字典
        event_dict = event.to_dict()
        
        # 发布事件到Stream
        message_id = await self.redis_client.xadd(
            stream_name, 
            event_dict, 
            maxlen=self.max_stream_length
        )
        
        self.logger.debug(f"已发布事件到Stream {stream_name}，消息ID: {message_id}")
        
        return message_id
    
    async def create_consumer_group(
        self, 
        stream_name: str, 
        group_name: str, 
        from_id: str = "$"
    ) -> bool:
        """
        创建消费者组
        
        参数:
            stream_name: 流名称
            group_name: 消费者组名称
            from_id: 起始ID，默认"$"表示只消费新消息
        
        返回:
            成功返回True
        """
        if not hasattr(self.redis_client, "_client") or self.redis_client._client is None:
            await self.redis_client.connect()
        
        # 使用分布式锁确保消费者组创建的原子性
        lock_name = f"create_group:{stream_name}:{group_name}"
        async with self.lock_manager.acquire(lock_name):
            # 记录消费者组
            if stream_name not in self.consumer_groups:
                self.consumer_groups[stream_name] = set()
            self.consumer_groups[stream_name].add(group_name)
            
            # 创建消费者组
            return await self.redis_client.xgroup_create(
                stream_name, group_name, id=from_id, mkstream=True
            )
    
    async def read_events(
        self, 
        stream_name: str, 
        last_id: str = "0", 
        count: int = 10, 
        block: int = 0
    ) -> List[Tuple[str, Dict]]:
        """
        从Stream读取事件
        
        参数:
            stream_name: 流名称
            last_id: 上次读取的ID，"0"表示从头开始读取，"$"表示只读取新消息
            count: 最大读取数量
            block: 阻塞毫秒数，0表示永久阻塞
        
        返回:
            事件列表，每项为(消息ID, 消息内容)的元组
        """
        if not hasattr(self.redis_client, "_client") or self.redis_client._client is None:
            await self.redis_client.connect()
        
        # 读取Stream
        result = await self.redis_client.xread(
            {stream_name: last_id}, 
            count=count,
            block=block
        )
        
        # 处理结果格式
        events = []
        if result:
            for stream_data in result:
                stream_name, messages = stream_data
                for message_id, message in messages:
                    events.append((message_id, message))
        
        return events
    
    async def read_events_from_group(
        self, 
        group_name: str, 
        consumer_name: str, 
        stream_name: str, 
        count: int = 10, 
        block: int = 0
    ) -> List[Tuple[str, Dict]]:
        """
        从消费者组读取事件
        
        参数:
            group_name: 消费者组名称
            consumer_name: 消费者名称
            stream_name: 流名称
            count: 最大读取数量
            block: 阻塞毫秒数，0表示永久阻塞
        
        返回:
            事件列表，每项为(消息ID, 消息内容)的元组
        """
        if not hasattr(self.redis_client, "_client") or self.redis_client._client is None:
            await self.redis_client.connect()
        
        # 确保消费者组存在
        if stream_name not in self.consumer_groups or group_name not in self.consumer_groups.get(stream_name, set()):
            await self.create_consumer_group(stream_name, group_name)
        
        # 从消费者组读取未处理的消息
        result = await self.redis_client.xreadgroup(
            group_name,
            consumer_name,
            {stream_name: ">"},  # ">" 表示未分配给该消费者组内其他消费者的消息
            count=count,
            block=block
        )
        
        # 处理结果格式
        events = []
        if result:
            for stream_data in result:
                stream_name, messages = stream_data
                for message_id, message in messages:
                    events.append((message_id, message))
        
        return events
    
    async def acknowledge_event(
        self, 
        group_name: str, 
        stream_name: str, 
        message_id: str
    ) -> int:
        """
        确认事件已处理
        
        参数:
            group_name: 消费者组名称
            stream_name: 流名称
            message_id: 消息ID
        
        返回:
            确认的消息数量
        """
        if not hasattr(self.redis_client, "_client") or self.redis_client._client is None:
            await self.redis_client.connect()
        
        # 确认消息
        return await self.redis_client.xack(stream_name, group_name, message_id)
    
    async def claim_pending_events(
        self, 
        group_name: str, 
        consumer_name: str, 
        stream_name: str, 
        min_idle_time: int, 
        count: int = 10
    ) -> List[Tuple[str, Dict]]:
        """
        认领长时间未处理的事件
        
        参数:
            group_name: 消费者组名称
            consumer_name: 消费者名称
            stream_name: 流名称
            min_idle_time: 最小空闲时间(毫秒)
            count: 最大认领数量
        
        返回:
            认领的事件列表，每项为(消息ID, 消息内容)的元组
        """
        if not hasattr(self.redis_client, "_client") or self.redis_client._client is None:
            await self.redis_client.connect()
        
        # 获取待处理消息信息
        pending_info = await self.redis_client.xpending(stream_name, group_name)
        
        if pending_info and pending_info["pending"] > 0:
            # 有待处理消息，获取详细信息
            # 获取前count个待处理消息
            pending_messages = await self.redis_client._client.execute_command(
                "XPENDING", stream_name, group_name, "-", "+", count
            )
            
            if not pending_messages:
                return []
            
            # 提取消息ID
            message_ids = [msg[0] for msg in pending_messages if msg[2] >= min_idle_time]
            
            if not message_ids:
                return []
            
            # 认领消息
            claimed_messages = await self.redis_client.xclaim(
                stream_name, 
                group_name, 
                consumer_name, 
                min_idle_time,
                *message_ids
            )
            
            # 处理结果格式
            events = []
            for message_id, message in claimed_messages:
                events.append((message_id, message))
            
            return events
        
        return []
    
    async def get_pending_events_info(
        self, 
        group_name: str, 
        stream_name: str
    ) -> Dict[str, Any]:
        """
        获取待处理事件信息
        
        参数:
            group_name: 消费者组名称
            stream_name: 流名称
        
        返回:
            待处理事件信息
        """
        if not hasattr(self.redis_client, "_client") or self.redis_client._client is None:
            await self.redis_client.connect()
        
        # 获取待处理消息信息
        return await self.redis_client.xpending(stream_name, group_name)
    
    async def trim_stream(
        self, 
        stream_name: str, 
        max_len: int = None
    ) -> int:
        """
        修剪Stream长度
        
        参数:
            stream_name: 流名称
            max_len: 最大长度，默认使用初始化时的max_stream_length
        
        返回:
            修剪的消息数量
        """
        if not hasattr(self.redis_client, "_client") or self.redis_client._client is None:
            await self.redis_client.connect()
        
        max_len = max_len or self.max_stream_length
        return await self.redis_client.xtrim(stream_name, max_len)
    
    async def delete_message(
        self, 
        stream_name: str, 
        message_id: str
    ) -> int:
        """
        删除特定消息
        
        参数:
            stream_name: 流名称
            message_id: 消息ID
        
        返回:
            删除的消息数量
        """
        if not hasattr(self.redis_client, "_client") or self.redis_client._client is None:
            await self.redis_client.connect()
        
        return await self.redis_client.xdel(stream_name, message_id)
    
    async def create_dead_letter_queue(
        self, 
        source_stream: str, 
        dlq_name: str = None
    ) -> str:
        """
        创建死信队列
        
        参数:
            source_stream: 源流名称
            dlq_name: 死信队列名称，默认为源流名称+":dlq"
        
        返回:
            死信队列名称
        """
        if not hasattr(self.redis_client, "_client") or self.redis_client._client is None:
            await self.redis_client.connect()
        
        dlq_name = dlq_name or f"{source_stream}:dlq"
        
        # 确保死信队列存在（创建一个空消息）
        await self.redis_client.xadd(
            dlq_name,
            {"_init": "true"},
            maxlen=self.max_stream_length
        )
        
        return dlq_name


class StreamEventProcessor:
    """处理事件流的基类，用于实现特定的事件处理逻辑"""
    
    def __init__(
        self,
        event_bus: RedisStreamsEventBus,
        stream_name: str,
        group_name: str,
        consumer_name: str = None,
        handler_map: Dict[str, Callable] = None,
        max_retry_count: int = 3,
        dlq_suffix: str = "dlq"
    ):
        """
        初始化流事件处理器
        
        参数:
            event_bus: 事件总线
            stream_name: 处理的Stream名称
            group_name: 消费者组名称
            consumer_name: 消费者名称，默认自动生成
            handler_map: 事件类型到处理函数的映射
            max_retry_count: 最大重试次数
            dlq_suffix: 死信队列后缀
        """
        self.event_bus = event_bus
        self.stream_name = stream_name
        self.group_name = group_name
        self.consumer_name = consumer_name or f"consumer-{generate_ulid()}"
        self.handler_map = handler_map or {}
        self.max_retry_count = max_retry_count
        self.dlq_suffix = dlq_suffix
        self.running = False
        self.process_task: Optional[Task] = None
        self.logger = logging.getLogger(f"StreamEventProcessor-{self.consumer_name}")
    
    def register_handler(self, event_type: str, handler: Callable) -> None:
        """
        注册事件处理函数
        
        参数:
            event_type: 事件类型
            handler: 处理函数
        """
        self.handler_map[event_type] = handler
    
    async def start(self) -> None:
        """启动处理器"""
        if self.running:
            return
        
        self.running = True
        
        # 确保消费者组存在
        await self.event_bus.create_consumer_group(self.stream_name, self.group_name)
        
        # 启动事件循环
        self.process_task = asyncio.create_task(self._event_loop())
        self.logger.info(f"事件处理器启动: stream={self.stream_name}, group={self.group_name}, consumer={self.consumer_name}")
    
    async def stop(self) -> None:
        """停止处理器"""
        if not self.running:
            return
        
        self.running = False
        
        # 取消事件循环任务
        if self.process_task:
            self.process_task.cancel()
            with suppress(asyncio.CancelledError):
                await self.process_task
            self.process_task = None
        
        self.logger.info(f"事件处理器停止: stream={self.stream_name}, group={self.group_name}, consumer={self.consumer_name}")
    
    async def _event_loop(self) -> None:
        """事件处理循环"""
        
        # 先处理待处理的消息
        await self._process_pending_events()
        
        # 处理新消息
        while self.running:
            try:
                # 从消费者组读取事件
                events = await self.event_bus.read_events_from_group(
                    self.group_name,
                    self.consumer_name,
                    self.stream_name,
                    count=10,
                    block=1000  # 阻塞1秒
                )
                
                # 处理事件
                for event_id, event_data in events:
                    try:
                        await self.process_event(event_id, event_data)
                    except Exception as e:
                        self.logger.error(f"处理事件 {event_id} 失败: {str(e)}")
                        await self._handle_error(event_id, event_data, e)
                
                # 如果没有新消息，等待一段时间
                if not events:
                    await asyncio.sleep(0.1)
            
            except asyncio.CancelledError:
                self.logger.info("事件处理循环被取消")
                break
            
            except Exception as e:
                self.logger.error(f"事件处理循环发生错误: {str(e)}")
                await asyncio.sleep(1)  # 出错后等待一段时间再继续
    
    async def _process_pending_events(self) -> None:
        """处理待处理的事件"""
        try:
            # 认领空闲超过30秒的消息
            pending_events = await self.event_bus.claim_pending_events(
                self.group_name,
                self.consumer_name,
                self.stream_name,
                min_idle_time=30000,  # 30秒
                count=50
            )
            
            # 处理这些消息
            for event_id, event_data in pending_events:
                try:
                    await self.process_event(event_id, event_data)
                except Exception as e:
                    self.logger.error(f"处理待处理事件 {event_id} 失败: {str(e)}")
                    await self._handle_error(event_id, event_data, e)
        
        except Exception as e:
            self.logger.error(f"处理待处理事件发生错误: {str(e)}")
    
    async def process_event(self, event_id: str, event_data: Dict) -> None:
        """
        处理单个事件
        
        参数:
            event_id: 事件ID
            event_data: 事件数据
        """
        if "event_type" not in event_data:
            self.logger.warning(f"事件 {event_id} 缺少event_type字段")
            await self.event_bus.acknowledge_event(self.group_name, self.stream_name, event_id)
            return
        
        event_type = event_data["event_type"]
        
        # 查找处理函数
        handler = self.handler_map.get(event_type)
        
        if not handler:
            self.logger.warning(f"事件类型 {event_type} 没有对应的处理函数")
            await self.event_bus.acknowledge_event(self.group_name, self.stream_name, event_id)
            return
        
        # 调用处理函数
        await handler(event_data)
        
        # 确认消息已处理
        await self.event_bus.acknowledge_event(self.group_name, self.stream_name, event_id)
        
        self.logger.debug(f"处理事件 {event_id} 成功，类型: {event_type}")
    
    async def _handle_error(self, event_id: str, event_data: Dict, error: Exception) -> None:
        """
        处理错误逻辑
        
        参数:
            event_id: 事件ID
            event_data: 事件数据
            error: 错误信息
        """
        # 获取重试次数
        retry_count = event_data.get("_retry_count", 0)
        
        if retry_count < self.max_retry_count:
            # 未达到最大重试次数，增加重试计数并重新发布
            event_data["_retry_count"] = retry_count + 1
            event_data["_last_error"] = str(error)
            
            # 确认原消息
            await self.event_bus.acknowledge_event(self.group_name, self.stream_name, event_id)
            
            # 重新发布
            await self.event_bus.redis_client.xadd(self.stream_name, event_data)
            
            self.logger.warning(f"事件 {event_id} 处理失败，将重试 (尝试 {retry_count + 1}/{self.max_retry_count}): {str(error)}")
        
        else:
            # 达到最大重试次数，发送到死信队列
            await self._send_to_dlq(event_id, event_data, str(error))
            
            # 确认原消息
            await self.event_bus.acknowledge_event(self.group_name, self.stream_name, event_id)
            
            self.logger.error(f"事件 {event_id} 处理失败达到最大重试次数 {self.max_retry_count}，已发送到死信队列: {str(error)}")
    
    async def _send_to_dlq(self, event_id: str, event_data: Dict, error: str) -> None:
        """
        将事件发送到死信队列
        
        参数:
            event_id: 事件ID
            event_data: 事件数据
            error: 错误信息
        """
        # 创建死信队列
        dlq_name = f"{self.stream_name}:{self.dlq_suffix}"
        
        # 添加错误信息
        event_data["_original_id"] = event_id
        event_data["_error"] = error
        event_data["_failed_at"] = get_utc_now().isoformat()
        
        # 发送到死信队列
        await self.event_bus.redis_client.xadd(dlq_name, event_data)
