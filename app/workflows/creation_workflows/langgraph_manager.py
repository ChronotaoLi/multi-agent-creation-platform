"""
LangGraph管理器模块

负责管理LangGraph工作流图的创建、配置和运行
"""
from typing import Dict, List, Any, Optional

from ..langgraph_setup import LangGraphSetup
from .workflow_factory import WorkflowFactory


class LangGraphManager:
    """
    LangGraph管理器
    
    管理LangGraph工作流图的创建、配置和运行
    """
    
    def __init__(
        self,
        langgraph_setup: Optional[LangGraphSetup] = None,
        workflow_factory: Optional[WorkflowFactory] = None
    ):
        """
        初始化LangGraph管理器
        
        参数:
            langgraph_setup: Optional[LangGraphSetup] - LangGraph引擎配置
            workflow_factory: Optional[WorkflowFactory] - 工作流工厂
        """
        self.langgraph_setup = langgraph_setup
        self.workflow_factory = workflow_factory or WorkflowFactory()
        self._workflow_instances = {}  # 工作流实例缓存
    
    def get_workflow_type(self, workflow_type: str) -> Dict[str, Any]:
        """
        获取工作流类型信息
        
        参数:
            workflow_type: str - 工作流类型
            
        返回:
            Dict[str, Any] - 工作流类型信息
        """
        config_schema = self.workflow_factory.get_workflow_config_schema(workflow_type)
        return {
            "id": workflow_type,
            "name": workflow_type.capitalize(),
            "config_schema": config_schema
        }
    
    def get_or_create_workflow(self, workflow_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取或创建工作流实例
        
        参数:
            workflow_type: str - 工作流类型
            config: Dict[str, Any] - 工作流配置
            
        返回:
            Dict[str, Any] - 工作流信息
        """
        # 如果已有实例，直接返回
        if workflow_type in self._workflow_instances:
            return {
                "type": workflow_type,
                "config": config,
                "instance": self._workflow_instances[workflow_type]
            }
        
        # 创建新实例
        workflow = self.workflow_factory.create_workflow(
            workflow_type=workflow_type,
            **config.get("config", {})
        )
        
        if not workflow:
            raise ValueError(f"无法创建工作流类型: {workflow_type}")
        
        # 缓存实例
        self._workflow_instances[workflow_type] = workflow
        
        return {
            "type": workflow_type,
            "config": config,
            "instance": workflow
        }
    
    def get_workflow(self, workflow_type: str) -> Dict[str, Any]:
        """
        获取工作流实例
        
        参数:
            workflow_type: str - 工作流类型
            
        返回:
            Dict[str, Any] - 工作流信息
        """
        if workflow_type not in self._workflow_instances:
            return {"type": workflow_type, "instance": None}
        
        return {
            "type": workflow_type,
            "instance": self._workflow_instances[workflow_type]
        }
    
    def get_available_workflow_types(self) -> List[Dict[str, Any]]:
        """
        获取可用的工作流类型
        
        返回:
            List[Dict[str, Any]] - 可用的工作流类型信息列表
        """
        workflow_types = self.workflow_factory.registry.get_available_types()
        
        return [
            {
                "id": wt,
                "name": wt.capitalize(),
                "config_schema": self.workflow_factory.get_workflow_config_schema(wt)
            }
            for wt in workflow_types
        ] 