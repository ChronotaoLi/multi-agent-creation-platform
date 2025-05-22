"""
智能体通信命令模块

定义智能体间通信的命令对象和工厂类
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

# 移除Command的导入，因为最新版本LangGraph中不再存在
# from langgraph.graph import Command as LangGraphCommand

class EnhancedCommand:
    """
    增强版命令对象
    
    用于智能体间通信的命令，支持单目标和多目标
    """
    
    def __init__(
        self,
        command_type: str,
        content: Dict[str, Any],
        source_id: str,
        target_ids: List[str] = None,
        priority: int = 0,
        expires_at: Optional[datetime] = None,
        metadata: Dict[str, Any] = None
    ):
        """
        初始化命令
        
        参数:
            command_type: 命令类型，如"action", "query", "response", "control"等
            content: 命令内容
            source_id: 命令源智能体ID
            target_ids: 命令目标智能体ID列表，为None则为广播
            priority: 命令优先级，数字越大优先级越高
            expires_at: 命令过期时间
            metadata: 命令元数据
        """
        self.command_type = command_type
        self.content = content
        self.source_id = source_id
        self.target_ids = target_ids or []
        self.priority = priority
        self.id = str(uuid.uuid4())
        self.created_at = datetime.now()
        self.expires_at = expires_at
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        
        返回:
            Dict[str, Any]: 命令字典表示
        """
        result = {
            "id": self.id,
            "command_type": self.command_type,
            "content": self.content,
            "source_id": self.source_id,
            "target_ids": self.target_ids,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata
        }
        
        if self.expires_at:
            result["expires_at"] = self.expires_at.isoformat()
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EnhancedCommand':
        """
        从字典创建命令
        
        参数:
            data: 命令字典表示
            
        返回:
            EnhancedCommand: 命令对象
        """
        # 创建基本命令对象
        command = cls(
            command_type=data.get("command_type", "unknown"),
            content=data.get("content", {}),
            source_id=data.get("source_id", ""),
            target_ids=data.get("target_ids", []),
            priority=data.get("priority", 0),
            metadata=data.get("metadata", {})
        )
        
        # 设置其他字段
        if "id" in data:
            command.id = data["id"]
        
        if "created_at" in data:
            try:
                command.created_at = datetime.fromisoformat(data["created_at"])
            except (ValueError, TypeError):
                command.created_at = datetime.now()
                
        if "expires_at" in data and data["expires_at"]:
            try:
                command.expires_at = datetime.fromisoformat(data["expires_at"])
            except (ValueError, TypeError):
                pass
                
        return command
    
    def is_expired(self) -> bool:
        """
        检查命令是否过期
        
        返回:
            bool: 是否过期
        """
        if self.expires_at:
            return datetime.now() > self.expires_at
        return False
    
    def is_broadcast(self) -> bool:
        """
        检查是否为广播命令
        
        返回:
            bool: 是否广播
        """
        return not self.target_ids
    
    def targets_agent(self, agent_id: str) -> bool:
        """
        检查是否针对特定智能体
        
        参数:
            agent_id: 智能体ID
            
        返回:
            bool: 是否针对该智能体
        """
        return self.is_broadcast() or agent_id in self.target_ids
    
    def to_langgraph_command(self) -> Dict[str, Any]:
        """
        转换为LangGraph命令对象
        
        返回:
            Dict[str, Any]: LangGraph命令格式的字典
        """
        # 根据命令类型构建不同的状态更新
        if self.command_type == "action":
            update = {"actions": [self.to_dict()]}
        elif self.command_type == "message":
            update = {"messages": [self.to_dict()]}
        elif self.command_type == "query":
            update = {"queries": [self.to_dict()]}
        elif self.command_type == "response":
            update = {"responses": [self.to_dict()]}
        elif self.command_type == "control":
            update = {"control": [self.to_dict()]}
        else:
            # 默认情况，创建一个以命令类型为键的更新
            update = {f"{self.command_type}s": [self.to_dict()]}
        
        # 返回更新字典，而不是使用已移除的LangGraphCommand类
        return update


class CommandFactory:
    """
    命令工厂
    
    创建各种类型的命令对象
    """
    
    @staticmethod
    def create_action_command(
        source_id: str,
        action: str,
        parameters: Dict[str, Any],
        target_ids: List[str] = None
    ) -> EnhancedCommand:
        """
        创建动作命令
        
        参数:
            source_id: 源智能体ID
            action: 动作名称
            parameters: 动作参数
            target_ids: 目标智能体ID列表
            
        返回:
            EnhancedCommand: 动作命令
        """
        content = {
            "action": action,
            "parameters": parameters
        }
        return EnhancedCommand(
            command_type="action",
            content=content,
            source_id=source_id,
            target_ids=target_ids
        )
    
    @staticmethod
    def create_query_command(
        source_id: str,
        query: str,
        parameters: Dict[str, Any],
        target_ids: List[str] = None
    ) -> EnhancedCommand:
        """
        创建查询命令
        
        参数:
            source_id: 源智能体ID
            query: 查询内容
            parameters: 查询参数
            target_ids: 目标智能体ID列表
            
        返回:
            EnhancedCommand: 查询命令
        """
        content = {
            "query": query,
            "parameters": parameters
        }
        return EnhancedCommand(
            command_type="query",
            content=content,
            source_id=source_id,
            target_ids=target_ids
        )
    
    @staticmethod
    def create_response_command(
        source_id: str,
        response_to: str,
        content: Dict[str, Any],
        target_ids: List[str] = None
    ) -> EnhancedCommand:
        """
        创建响应命令
        
        参数:
            source_id: 源智能体ID
            response_to: 响应的命令ID
            content: 响应内容
            target_ids: 目标智能体ID列表
            
        返回:
            EnhancedCommand: 响应命令
        """
        content_with_ref = content.copy()
        content_with_ref["response_to"] = response_to
        
        return EnhancedCommand(
            command_type="response",
            content=content_with_ref,
            source_id=source_id,
            target_ids=target_ids
        )
    
    @staticmethod
    def create_control_command(
        source_id: str,
        control_type: str,
        parameters: Dict[str, Any],
        target_ids: List[str] = None
    ) -> EnhancedCommand:
        """
        创建控制命令
        
        参数:
            source_id: 源智能体ID
            control_type: 控制类型
            parameters: 控制参数
            target_ids: 目标智能体ID列表
            
        返回:
            EnhancedCommand: 控制命令
        """
        content = {
            "control_type": control_type,
            "parameters": parameters
        }
        
        return EnhancedCommand(
            command_type="control",
            content=content,
            source_id=source_id,
            target_ids=target_ids,
            priority=10  # 控制命令默认高优先级
        )
    
    @staticmethod
    def create_broadcast_command(
        source_id: str,
        message_type: str,
        content: Dict[str, Any]
    ) -> EnhancedCommand:
        """
        创建广播命令
        
        参数:
            source_id: 源智能体ID
            message_type: 消息类型
            content: 消息内容
            
        返回:
            EnhancedCommand: 广播命令
        """
        return EnhancedCommand(
            command_type="broadcast",
            content={
                "message_type": message_type,
                "payload": content
            },
            source_id=source_id,
            target_ids=[]  # 空列表表示广播
        )
