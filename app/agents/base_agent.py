"""
智能体基础类

定义所有智能体共有的基本接口和行为
"""

import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from app.agents.tools import BaseTool
from app.services.interfaces.llm_service import LLMService
from app.agents.communication.command import EnhancedCommand, CommandFactory
from app.agents.communication.message_bus import MessageBus

logger = logging.getLogger(__name__)


class AgentContext:
    """
    智能体上下文
    
    提供智能体上下文管理
    """
    
    def __init__(self):
        """初始化上下文"""
        self.memory: Dict[str, Any] = {}
        self.current_task: Optional[Dict[str, Any]] = None
        self.environment: Dict[str, Any] = {}
        self.conversation_history: List[Dict[str, Any]] = []
    
    def add_memory(self, key: str, value: Any) -> None:
        """
        添加记忆
        
        参数:
            key: 记忆键
            value: 记忆值
        """
        self.memory[key] = value
    
    def get_memory(self, key: str) -> Optional[Any]:
        """
        获取记忆
        
        参数:
            key: 记忆键
            
        返回:
            Optional[Any]: 记忆值，不存在则返回None
        """
        return self.memory.get(key)
    
    def update_task(self, task_info: Dict[str, Any]) -> None:
        """
        更新任务信息
        
        参数:
            task_info: 任务信息
        """
        self.current_task = task_info
    
    def add_conversation_entry(self, entry: Dict[str, Any]) -> None:
        """
        添加对话记录
        
        参数:
            entry: 对话条目
        """
        self.conversation_history.append(entry)
        
        # 保留最近的对话历史，防止过长
        max_history = 50  # 可配置
        if len(self.conversation_history) > max_history:
            self.conversation_history = self.conversation_history[-max_history:]
    
    def get_conversation_summary(self) -> str:
        """
        获取对话摘要
        
        返回:
            str: 对话摘要
        """
        # 这里可以使用更复杂的摘要算法，目前简单返回最近几条对话
        recent_history = self.conversation_history[-5:] if self.conversation_history else []
        
        summary = []
        for entry in recent_history:
            role = entry.get("role", "unknown")
            content = entry.get("content", "")
            summary.append(f"{role}: {content}")
            
        return "\n".join(summary)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        
        返回:
            Dict[str, Any]: 上下文字典表示
        """
        return {
            "memory": self.memory,
            "current_task": self.current_task,
            "environment": self.environment,
            # 只包含最近的对话历史以减少大小
            "conversation_history": self.conversation_history[-10:] if self.conversation_history else []
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentContext':
        """
        从字典创建上下文
        
        参数:
            data: 上下文字典表示
            
        返回:
            AgentContext: 上下文对象
        """
        context = cls()
        context.memory = data.get("memory", {})
        context.current_task = data.get("current_task")
        context.environment = data.get("environment", {})
        context.conversation_history = data.get("conversation_history", [])
        return context


class BaseAgent(ABC):
    """
    基础智能体类
    
    所有智能体的基类，定义通用接口和行为
    """
    
    def __init__(
        self,
        id: str,
        name: str,
        agent_type: str,
        llm_service: LLMService,
        config: Dict[str, Any] = None
    ):
        """
        初始化智能体
        
        参数:
            id: 智能体唯一标识符
            name: 智能体名称
            agent_type: 智能体类型
            llm_service: LLM服务实例
            config: 智能体配置信息
        """
        self.id = id if id else str(uuid.uuid4())
        self.name = name
        self.description = ""
        self.agent_type = agent_type
        self.llm_service = llm_service
        self.context = AgentContext()
        self.tools: List[BaseTool] = []
        self.config = config or {}
        self.message_bus: Optional[MessageBus] = None
        
        # 初始化任务处理锁，防止并发问题
        self._processing_lock = asyncio.Lock()
    
    async def process_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        处理接收到的消息
        
        参数:
            message: 消息内容
            
        返回:
            Optional[Dict[str, Any]]: 响应消息，无响应则返回None
        """
        # 获取处理锁，确保同一时间只处理一条消息
        async with self._processing_lock:
            try:
                # 记录对话历史
                if isinstance(message, dict):
                    self.context.add_conversation_entry({
                        "role": "external",
                        "sender": message.get("source_id", "unknown"),
                        "content": message.get("content", {}),
                        "timestamp": message.get("created_at", "")
                    })
                
                # 根据消息类型处理
                command_type = message.get("command_type", "unknown")
                
                if command_type == "action":
                    return await self._handle_action(message)
                elif command_type == "query":
                    return await self._handle_query(message)
                elif command_type == "control":
                    return await self._handle_control(message)
                elif command_type == "response":
                    return await self._handle_response(message)
                else:
                    logger.warning(f"智能体 {self.id} 收到未知类型消息: {command_type}")
                    # 默认处理方法
                    return await self._handle_default(message)
            
            except Exception as e:
                logger.error(f"智能体 {self.id} 处理消息时出错: {str(e)}")
                # 返回错误响应
                return {
                    "command_type": "response",
                    "content": {
                        "status": "error",
                        "message": f"处理失败: {str(e)}",
                        "response_to": message.get("id", "")
                    },
                    "source_id": self.id,
                    "target_ids": [message.get("source_id", "")]
                }
    
    async def send_message(self, target_id: str, content: Dict[str, Any]) -> None:
        """
        发送消息到指定目标
        
        参数:
            target_id: 目标智能体ID
            content: 消息内容
        """
        if not self.message_bus:
            logger.error(f"智能体 {self.id} 未连接到消息总线")
            return
        
        # 创建消息命令
        command = EnhancedCommand(
            command_type="message", 
            content=content,
            source_id=self.id,
            target_ids=[target_id]
        )
        
        # 发送消息
        await self.message_bus.publish_message("agent_messages", command)
        
        # 记录对话历史
        self.context.add_conversation_entry({
            "role": "self",
            "target": target_id,
            "content": content,
            "timestamp": command.created_at.isoformat()
        })
    
    async def broadcast_message(self, content: Dict[str, Any]) -> None:
        """
        广播消息给所有智能体
        
        参数:
            content: 消息内容
        """
        if not self.message_bus:
            logger.error(f"智能体 {self.id} 未连接到消息总线")
            return
        
        # 创建广播命令
        command = CommandFactory.create_broadcast_command(
            source_id=self.id,
            message_type="broadcast",
            content=content
        )
        
        # 发送消息
        await self.message_bus.publish_message("agent_broadcasts", command)
        
        # 记录对话历史
        self.context.add_conversation_entry({
            "role": "self",
            "target": "broadcast",
            "content": content,
            "timestamp": command.created_at.isoformat()
        })
    
    def register_tool(self, tool: BaseTool) -> None:
        """
        注册工具
        
        参数:
            tool: 要注册的工具
        """
        # 检查是否已注册
        for existing_tool in self.tools:
            if existing_tool.name == tool.name:
                logger.warning(f"智能体 {self.id} 已注册工具 {tool.name}，将被覆盖")
                # 移除旧工具
                self.tools = [t for t in self.tools if t.name != tool.name]
                break
        
        # 添加新工具
        self.tools.append(tool)
        logger.info(f"智能体 {self.id} 注册工具 {tool.name}")
    
    async def use_tool(self, tool_name: str, **kwargs) -> Any:
        """
        使用指定工具
        
        参数:
            tool_name: 工具名称
            **kwargs: 工具参数
            
        返回:
            Any: 工具执行结果
            
        异常:
            ValueError: 工具不存在
        """
        # 查找工具
        for tool in self.tools:
            if tool.name == tool_name:
                try:
                    # 调用工具
                    result = tool(**kwargs)
                    
                    # 如果结果是协程，等待它完成
                    if asyncio.iscoroutine(result):
                        result = await result
                        
                    return result
                except Exception as e:
                    logger.error(f"使用工具 {tool_name} 时出错: {str(e)}")
                    raise
        
        # 工具不存在
        raise ValueError(f"工具 {tool_name} 不存在")
    
    def get_state(self) -> Dict[str, Any]:
        """
        获取智能体当前状态
        
        返回:
            Dict[str, Any]: 智能体状态
        """
        return {
            "id": self.id,
            "name": self.name,
            "type": self.agent_type,
            "context": self.context.to_dict(),
            "tools": [tool.to_dict() for tool in self.tools]
        }
    
    def update_state(self, state_updates: Dict[str, Any]) -> None:
        """
        更新智能体状态
        
        参数:
            state_updates: 状态更新
        """
        # 更新基本信息
        if "name" in state_updates:
            self.name = state_updates["name"]
        
        if "description" in state_updates:
            self.description = state_updates["description"]
        
        # 更新上下文
        if "context" in state_updates:
            context_updates = state_updates["context"]
            
            if "memory" in context_updates:
                for key, value in context_updates["memory"].items():
                    self.context.add_memory(key, value)
            
            if "current_task" in context_updates:
                self.context.update_task(context_updates["current_task"])
            
            if "environment" in context_updates:
                self.context.environment.update(context_updates["environment"])
    
    def set_message_bus(self, message_bus: MessageBus) -> None:
        """
        设置消息总线
        
        参数:
            message_bus: 消息总线实例
        """
        self.message_bus = message_bus
    
    # 以下为默认消息处理方法，子类可重写
    
    async def _handle_action(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """处理动作消息"""
        # 基类中提供默认实现
        content = message.get("content", {})
        action = content.get("action", "")
        parameters = content.get("parameters", {})
        
        logger.info(f"智能体 {self.id} 收到动作请求: {action}")
        
        # 默认行为是返回未实现响应
        return {
            "command_type": "response",
            "content": {
                "status": "not_implemented",
                "message": f"动作 {action} 未实现",
                "response_to": message.get("id", "")
            },
            "source_id": self.id,
            "target_ids": [message.get("source_id", "")]
        }
    
    async def _handle_query(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """处理查询消息"""
        # 基类中提供默认实现
        content = message.get("content", {})
        query = content.get("query", "")
        parameters = content.get("parameters", {})
        
        logger.info(f"智能体 {self.id} 收到查询请求: {query}")
        
        # 默认行为是返回未实现响应
        return {
            "command_type": "response",
            "content": {
                "status": "not_implemented",
                "message": f"查询 {query} 未实现",
                "response_to": message.get("id", "")
            },
            "source_id": self.id,
            "target_ids": [message.get("source_id", "")]
        }
    
    async def _handle_control(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """处理控制消息"""
        # 基类中提供默认实现
        content = message.get("content", {})
        control_type = content.get("control_type", "")
        parameters = content.get("parameters", {})
        
        logger.info(f"智能体 {self.id} 收到控制命令: {control_type}")
        
        # 默认行为是返回未实现响应
        return {
            "command_type": "response",
            "content": {
                "status": "not_implemented",
                "message": f"控制命令 {control_type} 未实现",
                "response_to": message.get("id", "")
            },
            "source_id": self.id,
            "target_ids": [message.get("source_id", "")]
        }
    
    async def _handle_response(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """处理响应消息"""
        # 基类中不对响应做进一步处理
        content = message.get("content", {})
        response_to = content.get("response_to", "")
        
        logger.info(f"智能体 {self.id} 收到对消息 {response_to} 的响应")
        
        # 默认不产生新响应
        return None
    
    async def _handle_default(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """处理默认消息"""
        # 基类中提供默认实现
        logger.info(f"智能体 {self.id} 收到未知类型消息")
        
        # 默认不产生响应
        return None
