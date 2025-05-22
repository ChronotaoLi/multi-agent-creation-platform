"""
智能体命令处理器

处理和路由智能体间的命令，管理命令执行和响应
"""

import asyncio
import logging
from queue import PriorityQueue
from typing import Dict, List, Optional, Protocol, Callable, Any, Tuple, TYPE_CHECKING

from app.data_access.cache.redis_client import RedisClient
from app.agents.communication.command import EnhancedCommand

# 使用TYPE_CHECKING条件导入来避免循环导入
if TYPE_CHECKING:
    from app.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class ProcessingStrategy(Protocol):
    """
    命令处理策略接口
    
    定义如何处理特定类型的命令
    """
    
    async def __call__(
        self, 
        command: EnhancedCommand, 
        processor: 'CommandProcessor'
    ) -> Optional[EnhancedCommand]:
        """
        执行处理策略
        
        参数:
            command: 要处理的命令
            processor: 命令处理器实例
            
        返回:
            Optional[EnhancedCommand]: 处理结果命令，如果没有响应则返回None
        """
        ...


class DefaultProcessingStrategy:
    """默认命令处理策略"""
    
    async def __call__(
        self, 
        command: EnhancedCommand, 
        processor: 'CommandProcessor'
    ) -> Optional[EnhancedCommand]:
        """
        执行默认处理逻辑
        
        参数:
            command: 要处理的命令
            processor: 命令处理器实例
            
        返回:
            Optional[EnhancedCommand]: 处理结果命令，如果没有响应则返回None
        """
        # 获取目标智能体列表
        target_ids = processor.route_command(command)
        
        results = []
        for agent_id in target_ids:
            # 获取目标智能体
            agent = processor.agent_registry.get(agent_id)
            if not agent:
                logger.warning(f"智能体 {agent_id} 未注册")
                continue
                
            # 调用智能体处理命令
            try:
                result = await agent.process_message(command.to_dict())
                if result:
                    results.append(result)
            except Exception as e:
                logger.error(f"智能体 {agent_id} 处理命令 {command.id} 失败: {str(e)}")
        
        # 如果有多个结果，应合并或选择一个
        if results:
            if len(results) == 1:
                return EnhancedCommand.from_dict(results[0])
            else:
                # 简单合并所有结果
                merged_content = {
                    "responses": results,
                    "response_to": command.id
                }
                return EnhancedCommand(
                    command_type="response",
                    content=merged_content,
                    source_id="command_processor",
                    target_ids=[command.source_id]
                )
        
        return None


class CommandQueueItem:
    """
    命令队列项
    
    用于PriorityQueue中的排序
    """
    
    def __init__(self, priority: int, timestamp: float, command: EnhancedCommand):
        self.priority = priority
        self.timestamp = timestamp
        self.command = command
    
    def __lt__(self, other):
        # 先比较优先级，再比较时间戳（先进先出）
        if self.priority != other.priority:
            return self.priority > other.priority  # 大的优先级值优先
        return self.timestamp < other.timestamp


class CommandProcessor:
    """
    命令处理器
    
    处理和路由智能体间的命令，管理命令执行和响应
    """
    
    def __init__(
        self,
        message_bus,
        redis_client: Optional[RedisClient] = None,
        max_concurrent_commands: int = 10,
        default_command_timeout: int = 60
    ):
        """
        初始化处理器
        
        参数:
            message_bus: 消息总线实例
            redis_client: Redis客户端（可选，用于分布式处理）
            max_concurrent_commands: 最大并发命令数
            default_command_timeout: 默认命令超时时间（秒）
        """
        self.agent_registry: Dict[str, 'BaseAgent'] = {}
        self.message_bus = message_bus
        self.processing_strategies: Dict[str, ProcessingStrategy] = {}
        self.command_queue = PriorityQueue()
        self.max_concurrent_commands = max_concurrent_commands
        self.redis_client = redis_client
        self.default_command_timeout = default_command_timeout
        
        # 正在处理的命令数
        self._processing_count = 0
        # 处理循环任务
        self._processing_task = None
        # 默认处理策略
        self._default_strategy = DefaultProcessingStrategy()
        
        # 用于命令处理的并发控制
        self._semaphore = asyncio.Semaphore(max_concurrent_commands)
    
    def register_agent(self, agent: 'BaseAgent') -> None:
        """
        注册智能体
        
        参数:
            agent: 要注册的智能体
        """
        self.agent_registry[agent.id] = agent
        logger.info(f"注册智能体 {agent.id}")
    
    def unregister_agent(self, agent_id: str) -> None:
        """
        注销智能体
        
        参数:
            agent_id: 智能体ID
        """
        if agent_id in self.agent_registry:
            del self.agent_registry[agent_id]
            logger.info(f"注销智能体 {agent_id}")
    
    def register_processing_strategy(self, command_type: str, strategy: ProcessingStrategy) -> None:
        """
        注册处理策略
        
        参数:
            command_type: 命令类型
            strategy: 处理策略
        """
        self.processing_strategies[command_type] = strategy
        logger.info(f"注册命令类型 {command_type} 的处理策略")
    
    async def process_command(self, command: EnhancedCommand) -> Optional[EnhancedCommand]:
        """
        处理单个命令
        
        参数:
            command: 要处理的命令
            
        返回:
            Optional[EnhancedCommand]: 处理结果命令，如果没有响应则返回None
        """
        # 检查命令是否过期
        if self._check_command_expiration(command):
            logger.info(f"命令 {command.id} 已过期，跳过处理")
            return None
        
        # 选择处理策略
        strategy = self._select_strategy(command)
        
        # 使用策略处理命令
        try:
            async with self._semaphore:
                self._processing_count += 1
                result = await strategy(command, self)
                self._processing_count -= 1
                
            self._log_command_processing(command, result)
            return result
        except Exception as e:
            logger.error(f"处理命令 {command.id} 失败: {str(e)}")
            self._processing_count = max(0, self._processing_count - 1)
            return None
    
    def route_command(self, command: EnhancedCommand) -> List[str]:
        """
        路由命令到目标智能体
        
        参数:
            command: 要路由的命令
            
        返回:
            List[str]: 目标智能体ID列表
        """
        if command.is_broadcast():
            # 广播命令，发送给所有智能体
            return list(self.agent_registry.keys())
        else:
            # 定向命令，只发送给指定智能体
            return [
                agent_id for agent_id in command.target_ids 
                if agent_id in self.agent_registry
            ]
    
    async def start_processing(self) -> None:
        """启动命令处理循环"""
        if self._processing_task is not None:
            logger.warning("命令处理循环已经在运行")
            return
        
        self._processing_task = asyncio.create_task(self._processing_loop())
        logger.info("启动命令处理循环")
    
    async def stop_processing(self) -> None:
        """停止命令处理循环"""
        if self._processing_task is None:
            logger.warning("命令处理循环未运行")
            return
        
        self._processing_task.cancel()
        try:
            await self._processing_task
        except asyncio.CancelledError:
            pass
        
        self._processing_task = None
        logger.info("停止命令处理循环")
    
    def enqueue_command(self, command: EnhancedCommand) -> None:
        """
        将命令加入队列
        
        参数:
            command: 要加入队列的命令
        """
        # 创建队列项
        import time
        item = CommandQueueItem(
            priority=command.priority,
            timestamp=time.time(),
            command=command
        )
        
        # 加入队列
        self.command_queue.put(item)
        logger.debug(f"将命令 {command.id} 加入队列")
    
    async def batch_process_commands(self, batch_size: int = 10) -> List[Optional[EnhancedCommand]]:
        """
        批量处理命令
        
        参数:
            batch_size: 每批处理的命令数
            
        返回:
            List[Optional[EnhancedCommand]]: 处理结果
        """
        # 获取最多batch_size个命令
        commands = []
        for _ in range(min(batch_size, self.command_queue.qsize())):
            if not self.command_queue.empty():
                item = self.command_queue.get()
                commands.append(item.command)
        
        if not commands:
            return []
        
        # 并发处理命令
        tasks = [self.process_command(cmd) for cmd in commands]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 过滤掉异常
        filtered_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"批量处理命令时发生异常: {str(result)}")
                filtered_results.append(None)
            else:
                filtered_results.append(result)
        
        return filtered_results
    
    async def _processing_loop(self) -> None:
        """命令处理循环"""
        while True:
            try:
                # 如果队列为空，等待一段时间
                if self.command_queue.empty():
                    await asyncio.sleep(0.1)
                    continue
                
                # 批量处理命令
                await self.batch_process_commands()
                
            except asyncio.CancelledError:
                logger.info("命令处理循环被取消")
                break
            except Exception as e:
                logger.error(f"命令处理循环出错: {str(e)}")
                # 短暂休眠后继续
                await asyncio.sleep(1)
    
    def _select_strategy(self, command: EnhancedCommand) -> ProcessingStrategy:
        """
        选择处理策略
        
        参数:
            command: 命令
            
        返回:
            ProcessingStrategy: 处理策略
        """
        return self.processing_strategies.get(
            command.command_type,
            self._default_strategy
        )
    
    def _check_command_expiration(self, command: EnhancedCommand) -> bool:
        """
        检查命令是否过期
        
        参数:
            command: 命令
            
        返回:
            bool: 是否过期
        """
        return command.is_expired()
    
    def _log_command_processing(self, command: EnhancedCommand, result: Optional[EnhancedCommand]) -> None:
        """
        记录命令处理日志
        
        参数:
            command: 处理的命令
            result: 处理结果
        """
        if result:
            logger.debug(f"命令 {command.id} 处理完成，生成响应 {result.id}")
        else:
            logger.debug(f"命令 {command.id} 处理完成，无响应")
