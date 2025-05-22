"""
智能体间消息总线

基于Redis Streams实现的可靠消息队列，用于智能体间通信
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Union, Set

from app.data_access.cache.redis_client import RedisClient
from app.agents.communication.command import EnhancedCommand

logger = logging.getLogger(__name__)

class Subscription:
    """
    消息总线订阅
    
    表示对特定主题的订阅
    """
    
    def __init__(
        self,
        topics: List[str],
        handler: Callable,
        group_name: Optional[str] = None,
        consumer_name: Optional[str] = None
    ):
        """
        初始化订阅
        
        参数:
            topics: 订阅主题列表
            handler: 消息处理函数
            group_name: 消费者组名称
            consumer_name: 消费者名称
        """
        self.id = str(uuid.uuid4())
        self.topics = topics
        self.handler = handler
        self.group_name = group_name
        self.consumer_name = consumer_name or f"consumer-{self.id[:8]}"
        self.active = False
    
    def activate(self) -> None:
        """激活订阅"""
        self.active = True
    
    def deactivate(self) -> None:
        """停用订阅"""
        self.active = False
    
    def matches_topic(self, topic: str) -> bool:
        """
        检查是否匹配主题
        
        参数:
            topic: 要检查的主题
            
        返回:
            bool: 是否匹配
        """
        return topic in self.topics


class MessageBus:
    """
    消息总线
    
    提供智能体间的消息传递机制，基于Redis Streams实现可靠的消息队列
    """
    
    def __init__(
        self,
        redis_client: RedisClient,
        stream_prefix: str = "agent_stream:",
        max_stream_length: int = 1000
    ):
        """
        初始化消息总线
        
        参数:
            redis_client: Redis客户端实例
            stream_prefix: 流名称前缀
            max_stream_length: 流最大长度
        """
        self.redis_client = redis_client
        self.stream_prefix = stream_prefix
        self.max_stream_length = max_stream_length
        self.consumer_groups: Dict[str, Dict[str, str]] = {}  # {topic: {group_name: last_id}}
        self.handler_registry: Dict[str, Dict[str, Callable]] = {}  # {topic: {subscription_id: handler}}
        self.subscriptions: Dict[str, Subscription] = {}  # {subscription_id: subscription}
        self._consumer_tasks: Dict[str, asyncio.Task] = {}  # {subscription_id: task}
    
    def _get_stream_name(self, topic: str) -> str:
        """
        获取流名称
        
        参数:
            topic: 主题名称
            
        返回:
            str: 完整的流名称
        """
        return f"{self.stream_prefix}{topic}"
    
    async def publish_message(self, topic: str, message: EnhancedCommand) -> str:
        """
        发布消息到指定主题
        
        参数:
            topic: 主题名称
            message: 消息内容
            
        返回:
            str: 消息ID
        """
        stream_name = self._get_stream_name(topic)
        message_dict = message.to_dict()
        
        # 添加时间戳
        message_dict["publish_timestamp"] = datetime.now().isoformat()
        
        # 发布到Redis Stream
        message_id = await self.redis_client.xadd(
            stream_name,
            message_dict,
            maxlen=self.max_stream_length
        )
        
        logger.debug(f"发布消息到 {topic}: {message_id}")
        return message_id
    
    async def subscribe(
        self,
        topics: List[str],
        handler: Callable,
        group_name: str = None,
        consumer_name: str = None
    ) -> str:
        """
        订阅主题
        
        参数:
            topics: 主题列表
            handler: 消息处理函数
            group_name: 消费者组名称，如果提供则使用消费者组模式
            consumer_name: 消费者名称
            
        返回:
            str: 订阅ID
        """
        # 创建订阅
        subscription = Subscription(topics, handler, group_name, consumer_name)
        self.subscriptions[subscription.id] = subscription
        
        # 注册处理函数
        for topic in topics:
            if topic not in self.handler_registry:
                self.handler_registry[topic] = {}
            
            self.handler_registry[topic][subscription.id] = handler
            
            # 如果使用消费者组模式，创建消费者组
            if group_name:
                stream_name = self._get_stream_name(topic)
                await self.create_consumer_group(topic, group_name)
                
                # 记录消费者组信息
                if topic not in self.consumer_groups:
                    self.consumer_groups[topic] = {}
                self.consumer_groups[topic][group_name] = "0"  # 从头开始消费
        
        logger.info(f"创建订阅 {subscription.id} 到主题 {topics}")
        return subscription.id
    
    async def unsubscribe(self, subscription_id: str) -> None:
        """
        取消订阅
        
        参数:
            subscription_id: 订阅ID
        """
        if subscription_id not in self.subscriptions:
            logger.warning(f"订阅 {subscription_id} 不存在")
            return
        
        # 停止消费任务
        await self.stop_consuming(subscription_id)
        
        # 删除处理函数注册
        subscription = self.subscriptions[subscription_id]
        for topic in subscription.topics:
            if topic in self.handler_registry and subscription_id in self.handler_registry[topic]:
                del self.handler_registry[topic][subscription_id]
                
                # 如果主题没有订阅者了，清理
                if not self.handler_registry[topic]:
                    del self.handler_registry[topic]
        
        # 删除订阅
        del self.subscriptions[subscription_id]
        logger.info(f"取消订阅 {subscription_id}")
    
    async def create_consumer_group(self, topic: str, group_name: str) -> None:
        """
        创建消费者组
        
        参数:
            topic: 主题名称
            group_name: 消费者组名称
        """
        stream_name = self._get_stream_name(topic)
        await self.redis_client.xgroup_create(
            stream_name,
            group_name,
            id="$",  # 只消费新消息
            mkstream=True  # 如果流不存在则创建
        )
        logger.debug(f"为主题 {topic} 创建消费者组 {group_name}")
    
    async def start_consuming(self, subscription_id: str) -> None:
        """
        开始消费消息
        
        参数:
            subscription_id: 订阅ID
        """
        if subscription_id not in self.subscriptions:
            logger.error(f"订阅 {subscription_id} 不存在")
            return
        
        subscription = self.subscriptions[subscription_id]
        subscription.activate()
        
        # 如果已经有消费任务在运行，先停止
        if subscription_id in self._consumer_tasks:
            await self.stop_consuming(subscription_id)
        
        # 创建新的消费任务
        if subscription.group_name:
            # 消费者组模式
            task = asyncio.create_task(self._consume_group_messages(subscription))
        else:
            # 普通模式
            task = asyncio.create_task(self._consume_messages(subscription))
        
        self._consumer_tasks[subscription_id] = task
        logger.info(f"开始消费订阅 {subscription_id}")
    
    async def stop_consuming(self, subscription_id: str) -> None:
        """
        停止消费消息
        
        参数:
            subscription_id: 订阅ID
        """
        if subscription_id in self.subscriptions:
            self.subscriptions[subscription_id].deactivate()
        
        if subscription_id in self._consumer_tasks:
            task = self._consumer_tasks[subscription_id]
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            del self._consumer_tasks[subscription_id]
            logger.info(f"停止消费订阅 {subscription_id}")
    
    async def _consume_messages(self, subscription: Subscription) -> None:
        """
        消费消息（普通模式）
        
        参数:
            subscription: 订阅对象
        """
        streams = {self._get_stream_name(topic): "$" for topic in subscription.topics}
        
        while subscription.active:
            try:
                # 阻塞读取最新消息
                result = await self.redis_client.xread(
                    streams=streams,
                    block=5000,  # 阻塞5秒
                    count=10  # 每次最多获取10条
                )
                
                if not result:
                    continue
                    
                # 处理消息
                for stream_name, messages in result:
                    # 提取主题名称
                    topic = stream_name[len(self.stream_prefix):]
                    
                    for message_id, message_data in messages:
                        # 更新下次读取的起始ID
                        streams[stream_name] = message_id
                        
                        try:
                            # 还原消息对象
                            command = EnhancedCommand.from_dict(message_data)
                            
                            # 调用处理函数
                            await subscription.handler(topic, command)
                        except Exception as e:
                            logger.error(f"处理消息 {message_id} 失败: {str(e)}")
            
            except asyncio.CancelledError:
                logger.info(f"取消消费订阅 {subscription.id}")
                break
            except Exception as e:
                logger.error(f"消费消息失败: {str(e)}")
                # 短暂休眠后重试
                await asyncio.sleep(1)
    
    async def _consume_group_messages(self, subscription: Subscription) -> None:
        """
        消费消息（消费者组模式）
        
        参数:
            subscription: 订阅对象
        """
        if not subscription.group_name:
            logger.error("订阅未设置消费者组")
            return
            
        streams = {
            self._get_stream_name(topic): ">" for topic in subscription.topics
        }
        
        while subscription.active:
            try:
                # 读取分配给当前消费者的消息
                result = await self.redis_client.xreadgroup(
                    group=subscription.group_name,
                    consumer=subscription.consumer_name,
                    streams=streams,
                    block=5000,  # 阻塞5秒
                    count=10  # 每次最多获取10条
                )
                
                if not result:
                    # 如果没有新消息，尝试处理待确认的消息
                    await self._process_pending_messages(subscription)
                    continue
                    
                # 处理消息
                for stream_name, messages in result:
                    # 提取主题名称
                    topic = stream_name[len(self.stream_prefix):]
                    
                    for message_id, message_data in messages:
                        try:
                            # 还原消息对象
                            command = EnhancedCommand.from_dict(message_data)
                            
                            # 调用处理函数
                            await subscription.handler(topic, command)
                            
                            # 确认消息已处理
                            await self.acknowledge_message(
                                topic,
                                subscription.group_name,
                                message_id
                            )
                        except Exception as e:
                            logger.error(f"处理消息 {message_id} 失败: {str(e)}")
            
            except asyncio.CancelledError:
                logger.info(f"取消消费订阅 {subscription.id}")
                break
            except Exception as e:
                logger.error(f"消费消息失败: {str(e)}")
                # 短暂休眠后重试
                await asyncio.sleep(1)
    
    async def _process_pending_messages(self, subscription: Subscription) -> None:
        """
        处理待确认的消息
        
        参数:
            subscription: 订阅对象
        """
        # 每隔一段时间才处理一次待确认消息，避免过于频繁
        for topic in subscription.topics:
            try:
                # 获取待确认的消息
                pending_messages = await self.get_pending_messages(
                    topic,
                    subscription.group_name
                )
                
                if not pending_messages:
                    continue
                    
                # 认领超过30秒未被确认的消息
                messages = await self.claim_pending_messages(
                    topic,
                    subscription.group_name,
                    subscription.consumer_name,
                    30000  # 30秒
                )
                
                # 处理认领的消息
                for message_id, message_data in messages:
                    try:
                        # 还原消息对象
                        command = EnhancedCommand.from_dict(message_data)
                        
                        # 调用处理函数
                        await subscription.handler(topic, command)
                        
                        # 确认消息已处理
                        await self.acknowledge_message(
                            topic,
                            subscription.group_name,
                            message_id
                        )
                    except Exception as e:
                        logger.error(f"处理待确认消息 {message_id} 失败: {str(e)}")
            
            except Exception as e:
                logger.error(f"处理待确认消息失败: {str(e)}")
    
    async def acknowledge_message(self, topic: str, group_name: str, message_id: str) -> None:
        """
        确认消息处理完成
        
        参数:
            topic: 主题名称
            group_name: 消费者组名称
            message_id: 消息ID
        """
        stream_name = self._get_stream_name(topic)
        await self.redis_client.xack(stream_name, group_name, message_id)
    
    async def get_pending_messages(self, topic: str, group_name: str) -> List[Dict[str, Any]]:
        """
        获取待处理消息
        
        参数:
            topic: 主题名称
            group_name: 消费者组名称
            
        返回:
            List[Dict[str, Any]]: 待处理消息列表
        """
        stream_name = self._get_stream_name(topic)
        return await self.redis_client.xpending(stream_name, group_name)
    
    async def claim_pending_messages(
        self,
        topic: str,
        group_name: str,
        consumer_name: str,
        min_idle_time: int
    ) -> List[Dict[str, Any]]:
        """
        认领待处理消息
        
        参数:
            topic: 主题名称
            group_name: 消费者组名称
            consumer_name: 消费者名称
            min_idle_time: 最小空闲时间（毫秒）
            
        返回:
            List[Dict[str, Any]]: 认领的消息列表
        """
        stream_name = self._get_stream_name(topic)
        pending = await self.redis_client.xpending(stream_name, group_name)
        
        if not pending:
            return []
            
        # 获取待处理消息的ID
        message_ids = []
        for item in pending:
            # 检查消息是否超过最小空闲时间
            if item.get("idle") > min_idle_time:
                message_ids.append(item.get("message_id"))
        
        if not message_ids:
            return []
            
        # 认领消息
        return await self.redis_client.xclaim(
            stream_name,
            group_name,
            consumer_name,
            min_idle_time,
            *message_ids
        )
