"""
事件总线模块

提供基于发布/订阅模式的事件总线实现，用于组件间的消息通信。
"""
import asyncio
import logging
from typing import Any, Dict, List, Callable, Awaitable, Set, Optional
from functools import lru_cache

from app.data_access.cache.redis_client import RedisClient
from app.core.config import get_settings

logger = logging.getLogger(__name__)

# 事件处理器类型：接收事件类型和数据的异步回调
EventHandler = Callable[[str, Dict[str, Any]], Awaitable[None]]


class EventBus:
    """事件总线实现
    
    基于内存和Redis的混合事件总线，支持进程内和跨进程通信。
    """
    
    def __init__(self, redis_url: str = None):
        """初始化事件总线
        
        Args:
            redis_url: Redis连接URL，用于跨进程通信
        """
        self.redis_url = redis_url
        self.redis_client = RedisClient(redis_url) if redis_url else None
        # 事件处理器映射: {事件类型: 处理器集合}
        self.handlers: Dict[str, Set[EventHandler]] = {}
        # 是否正在监听
        self.is_listening = False
        # 监听任务
        self.listener_task: Optional[asyncio.Task] = None
    
    async def publish(self, event_type: str, data: Dict[str, Any]) -> None:
        """发布事件
        
        Args:
            event_type: 事件类型
            data: 事件数据
        """
        # 记录事件
        logger.debug(f"发布事件: {event_type}, 数据: {data}")
        
        # 本地处理
        await self._process_event(event_type, data)
        
        # Redis处理（跨进程）
        if self.redis_client:
            try:
                # 使用Redis Stream存储事件
                event_data = {"type": event_type, **data}
                await self.redis_client.xadd("events", event_data, maxlen=10000)
            except Exception as e:
                logger.error(f"发布事件到Redis失败: {str(e)}")
    
    async def _process_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """处理单个事件
        
        Args:
            event_type: 事件类型
            data: 事件数据
        """
        if event_type in self.handlers:
            # 获取该事件类型的所有处理器
            handlers = list(self.handlers[event_type])
            
            # 异步调用所有处理器
            for handler in handlers:
                try:
                    await handler(event_type, data)
                except Exception as e:
                    logger.error(f"事件处理器异常: {str(e)}")
    
    async def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """订阅事件
        
        Args:
            event_type: 事件类型
            handler: 事件处理器
        """
        if event_type not in self.handlers:
            self.handlers[event_type] = set()
        
        self.handlers[event_type].add(handler)
        logger.debug(f"订阅事件: {event_type}")
        
        # 如果是第一个订阅者且有Redis，则开始监听
        if self.redis_client and not self.is_listening:
            await self._start_listening()
    
    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """取消订阅事件
        
        Args:
            event_type: 事件类型
            handler: 事件处理器
        """
        if event_type in self.handlers and handler in self.handlers[event_type]:
            self.handlers[event_type].remove(handler)
            
            if not self.handlers[event_type]:
                del self.handlers[event_type]
                
            logger.debug(f"取消订阅事件: {event_type}")
    
    async def _start_listening(self) -> None:
        """开始监听Redis事件流"""
        if not self.redis_client or self.is_listening:
            return
            
        self.is_listening = True
        
        # 创建消费者组
        try:
            # 创建消费者组，如果已存在则忽略错误
            await self.redis_client.xgroup_create("events", "event_bus", id="0", mkstream=True)
        except Exception as e:
            logger.debug(f"创建消费者组失败（可能已存在）: {str(e)}")
        
        # 创建监听任务
        self.listener_task = asyncio.create_task(self._listen_events())
        
    async def _listen_events(self) -> None:
        """监听Redis事件流"""
        consumer_name = "c1"  # 每个实例一个唯一的消费者名称，这里简化处理
        last_id = "0"  # 从头开始消费
        
        while self.is_listening:
            try:
                # 读取消息
                messages = await self.redis_client.xreadgroup(
                    "event_bus", consumer_name, {"events": ">"}, block=1000
                )
                
                if not messages:
                    await asyncio.sleep(0.1)
                    continue
                
                # 处理消息
                for stream, entries in messages:
                    for entry_id, fields in entries:
                        try:
                            event_type = fields.get("type")
                            if event_type:
                                # 移除type字段，其余为数据
                                data = {k: v for k, v in fields.items() if k != "type"}
                                # 处理事件
                                await self._process_event(event_type, data)
                            
                            # 确认消息已处理
                            await self.redis_client.xack("events", "event_bus", entry_id)
                            last_id = entry_id
                        except Exception as e:
                            logger.error(f"处理事件消息失败: {str(e)}")
                
            except Exception as e:
                logger.error(f"监听事件流失败: {str(e)}")
                await asyncio.sleep(1)  # 出错后短暂暂停
    
    async def close(self) -> None:
        """关闭事件总线"""
        self.is_listening = False
        
        # 取消监听任务
        if self.listener_task:
            self.listener_task.cancel()
            try:
                await self.listener_task
            except asyncio.CancelledError:
                pass
            self.listener_task = None
        
        # 关闭Redis连接
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("事件总线已关闭")


_event_bus_instance = None

def get_event_bus() -> EventBus:
    """获取事件总线单例实例
    
    Returns:
        EventBus: 事件总线实例
    """
    global _event_bus_instance
    
    if _event_bus_instance is None:
        settings = get_settings()
        redis_url = getattr(settings, "redis_url", None)
        _event_bus_instance = EventBus(redis_url)
        logger.info("创建事件总线实例")
        
    return _event_bus_instance 