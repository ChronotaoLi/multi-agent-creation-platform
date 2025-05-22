"""
创作工作流工厂，负责创建和管理各种创作工作流
"""

from typing import Any, Dict, List, Optional, Type, Protocol

from ...agents.coordinator_agent import CoordinatorAgent
from ...agents.communication.message_bus import MessageBus
# 移除对不存在的BaseSaver的导入，改为使用Protocol
# from langgraph.checkpoint.base import BaseSaver

# 定义BaseSaver协议，替代导入
class BaseSaver(Protocol):
    """检查点保存器协议。"""
    
    def get(self, config: Dict[str, Any]) -> Any:
        """获取检查点。"""
        ...
    
    def put(self, config: Dict[str, Any], checkpoint: Any, metadata: Dict[str, Any], new_versions: Dict[str, Any]) -> Dict[str, Any]:
        """存储检查点。"""
        ...
    
    def list(self, config: Dict[str, Any], **kwargs) -> List[Dict[str, Any]]:
        """列出检查点。"""
        ...

from .base_workflow import CreationWorkflow
from .free_workflow import FreeCreationWorkflow
from .guided_workflow import GuidedCreationWorkflow
from .structured_workflow import StructuredCreationWorkflow


class WorkflowRegistry:
    """创作工作流注册器，管理可用的工作流类型"""
    
    def __init__(self):
        """初始化工作流注册器"""
        self._workflows = {}
    
    def register(self, workflow_type: str, workflow_class: Type[CreationWorkflow]) -> None:
        """
        注册工作流类型
        
        参数:
            workflow_type: str - 工作流类型标识
            workflow_class: Type[CreationWorkflow] - 工作流类
        """
        self._workflows[workflow_type] = workflow_class
    
    def get(self, workflow_type: str) -> Optional[Type[CreationWorkflow]]:
        """
        获取工作流类
        
        参数:
            workflow_type: str - 工作流类型标识
            
        返回:
            Optional[Type[CreationWorkflow]] - 工作流类，如果不存在则返回None
        """
        return self._workflows.get(workflow_type)
    
    def get_available_types(self) -> List[str]:
        """
        获取所有可用的工作流类型
        
        返回:
            List[str] - 可用工作流类型列表
        """
        return list(self._workflows.keys())


class WorkflowFactory:
    """创作工作流工厂，负责创建各种类型的工作流实例"""
    
    def __init__(self):
        """初始化工作流工厂"""
        self.registry = WorkflowRegistry()
        self._register_default_workflows()
    
    def _register_default_workflows(self) -> None:
        """注册默认工作流类型"""
        self.registry.register("free", FreeCreationWorkflow)
        self.registry.register("guided", GuidedCreationWorkflow)
        self.registry.register("structured", StructuredCreationWorkflow)
    
    def create_workflow(
        self,
        workflow_type: str,
        coordinator_agent: Optional[CoordinatorAgent] = None,
        message_bus: Optional[MessageBus] = None,
        checkpointer: Optional[BaseSaver] = None,
        **kwargs
    ) -> Optional[CreationWorkflow]:
        """
        创建工作流实例
        
        参数:
            workflow_type: str - 工作流类型
            coordinator_agent: Optional[CoordinatorAgent] - 协调智能体
            message_bus: Optional[MessageBus] - 消息总线
            checkpointer: Optional[BaseSaver] - 检查点保存器
            **kwargs - 其他工作流特定参数
            
        返回:
            Optional[CreationWorkflow] - 创建的工作流实例，如果类型不存在则返回None
        """
        workflow_class = self.registry.get(workflow_type)
        if not workflow_class:
            return None
        
        # 创建工作流实例
        workflow = workflow_class(
            workflow_type=workflow_type,
            coordinator_agent=coordinator_agent,
            message_bus=message_bus,
            checkpointer=checkpointer,
            **kwargs
        )
        
        return workflow
    
    def get_workflow_config_schema(self, workflow_type: str) -> Dict[str, Any]:
        """
        获取工作流配置模式
        
        参数:
            workflow_type: str - 工作流类型
            
        返回:
            Dict[str, Any] - 配置模式
        """
        # 定义各种工作流的配置模式
        schemas = {
            "free": {
                "properties": {
                    "inspiration_threshold": {
                        "type": "number",
                        "description": "灵感质量阈值，低于此值触发干预",
                        "default": 0.6
                    }
                }
            },
            "guided": {
                "properties": {
                    "work_type": {
                        "type": "string",
                        "description": "作品类型",
                        "enum": ["story", "article", "poem"],
                        "default": "story"
                    }
                }
            },
            "structured": {
                "properties": {
                    "template_type": {
                        "type": "string",
                        "description": "模板类型",
                        "enum": ["novel", "article"],
                        "default": "novel"
                    },
                    "template_id": {
                        "type": "string",
                        "description": "模板ID",
                        "enum": ["basic", "academic"],
                        "default": "basic"
                    }
                }
            }
        }
        
        return schemas.get(workflow_type, {"properties": {}}) 