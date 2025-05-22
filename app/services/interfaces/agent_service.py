"""
智能体服务接口模块

该模块定义了智能体服务的接口，用于管理和协调多智能体系统中的各种智能体。
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union, Tuple

from app.models.domain.agent import Agent, AgentInstance, AgentTemplate
from app.models.schemas import (
    AgentCreate, 
    AgentUpdate, 
    AgentTemplateCreate, 
    AgentTemplateUpdate,
    AgentInstanceCreate,
    AgentMessage,
    AgentTask
)


class AgentService(ABC):
    """
    智能体服务接口
    
    提供智能体管理和协调的业务逻辑
    """
    
    @abstractmethod
    async def create_agent(self, agent_data: AgentCreate, user_id: int) -> Agent:
        """
        创建智能体
        
        参数:
            agent_data: 智能体创建数据
            user_id: 用户ID
            
        返回值:
            创建的智能体
        """
        pass
    
    @abstractmethod
    async def get_agent(self, agent_id: int) -> Optional[Agent]:
        """
        获取智能体
        
        参数:
            agent_id: 智能体ID
            
        返回值:
            智能体，如果不存在则返回None
        """
        pass
    
    @abstractmethod
    async def update_agent(self, agent_id: int, agent_data: AgentUpdate) -> Agent:
        """
        更新智能体
        
        参数:
            agent_id: 智能体ID
            agent_data: 智能体更新数据
            
        返回值:
            更新后的智能体
        """
        pass
    
    @abstractmethod
    async def delete_agent(self, agent_id: int) -> None:
        """
        删除智能体
        
        参数:
            agent_id: 智能体ID
        """
        pass
    
    @abstractmethod
    async def list_agents(
        self, user_id: Optional[int] = None, agent_type: Optional[str] = None,
        skip: int = 0, limit: int = 100
    ) -> List[Agent]:
        """
        列出智能体
        
        参数:
            user_id: 用户ID，如果提供则只返回该用户的智能体
            agent_type: 智能体类型，如果提供则只返回该类型的智能体
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        返回值:
            智能体列表
        """
        pass
    
    @abstractmethod
    async def create_agent_instance(
        self, instance_data: AgentInstanceCreate, user_id: int
    ) -> AgentInstance:
        """
        创建智能体实例
        
        参数:
            instance_data: 实例创建数据
            user_id: 用户ID
            
        返回值:
            创建的智能体实例
        """
        pass
    
    @abstractmethod
    async def get_agent_instance(self, instance_id: int) -> Optional[AgentInstance]:
        """
        获取智能体实例
        
        参数:
            instance_id: 实例ID
            
        返回值:
            智能体实例，如果不存在则返回None
        """
        pass
    
    @abstractmethod
    async def terminate_agent_instance(self, instance_id: int) -> None:
        """
        终止智能体实例
        
        参数:
            instance_id: 实例ID
        """
        pass
    
    @abstractmethod
    async def list_agent_instances(
        self, agent_id: Optional[int] = None, user_id: Optional[int] = None,
        status: Optional[str] = None, skip: int = 0, limit: int = 100
    ) -> List[AgentInstance]:
        """
        列出智能体实例
        
        参数:
            agent_id: 智能体ID，如果提供则只返回该智能体的实例
            user_id: 用户ID，如果提供则只返回该用户的实例
            status: 实例状态，如果提供则只返回该状态的实例
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        返回值:
            智能体实例列表
        """
        pass
    
    @abstractmethod
    async def send_message_to_agent(
        self, instance_id: int, message: AgentMessage
    ) -> Dict[str, Any]:
        """
        向智能体发送消息
        
        参数:
            instance_id: 实例ID
            message: 消息内容
            
        返回值:
            响应结果
        """
        pass
    
    @abstractmethod
    async def get_agent_messages(
        self, instance_id: int, skip: int = 0, limit: int = 100
    ) -> List[AgentMessage]:
        """
        获取智能体消息历史
        
        参数:
            instance_id: 实例ID
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        返回值:
            消息列表
        """
        pass
    
    @abstractmethod
    async def assign_task_to_agent(
        self, instance_id: int, task: AgentTask
    ) -> Dict[str, Any]:
        """
        分配任务给智能体
        
        参数:
            instance_id: 实例ID
            task: 任务数据
            
        返回值:
            任务接收结果
        """
        pass
    
    @abstractmethod
    async def get_agent_tasks(
        self, instance_id: int, status: Optional[str] = None,
        skip: int = 0, limit: int = 100
    ) -> List[AgentTask]:
        """
        获取智能体任务列表
        
        参数:
            instance_id: 实例ID
            status: 任务状态，如果提供则只返回该状态的任务
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        返回值:
            任务列表
        """
        pass
    
    @abstractmethod
    async def create_agent_template(
        self, template_data: AgentTemplateCreate, user_id: int
    ) -> AgentTemplate:
        """
        创建智能体模板
        
        参数:
            template_data: 模板创建数据
            user_id: 用户ID
            
        返回值:
            创建的智能体模板
        """
        pass
    
    @abstractmethod
    async def get_agent_template(self, template_id: int) -> Optional[AgentTemplate]:
        """
        获取智能体模板
        
        参数:
            template_id: 模板ID
            
        返回值:
            智能体模板，如果不存在则返回None
        """
        pass
    
    @abstractmethod
    async def update_agent_template(
        self, template_id: int, template_data: AgentTemplateUpdate
    ) -> AgentTemplate:
        """
        更新智能体模板
        
        参数:
            template_id: 模板ID
            template_data: 模板更新数据
            
        返回值:
            更新后的智能体模板
        """
        pass
    
    @abstractmethod
    async def delete_agent_template(self, template_id: int) -> None:
        """
        删除智能体模板
        
        参数:
            template_id: 模板ID
        """
        pass
    
    @abstractmethod
    async def list_agent_templates(
        self, user_id: Optional[int] = None, agent_type: Optional[str] = None,
        is_public: Optional[bool] = None, skip: int = 0, limit: int = 100
    ) -> List[AgentTemplate]:
        """
        列出智能体模板
        
        参数:
            user_id: 用户ID，如果提供则只返回该用户创建的模板
            agent_type: 智能体类型，如果提供则只返回该类型的模板
            is_public: 是否公开，如果提供则只返回公开/非公开的模板
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        返回值:
            智能体模板列表
        """
        pass
    
    @abstractmethod
    async def create_agent_from_template(
        self, template_id: int, agent_data: AgentCreate, user_id: int
    ) -> Agent:
        """
        从模板创建智能体
        
        参数:
            template_id: 模板ID
            agent_data: 智能体创建数据，用于覆盖模板中的默认值
            user_id: 用户ID
            
        返回值:
            创建的智能体
        """
        pass
    
    @abstractmethod
    async def get_agent_capabilities(self, agent_id: int) -> Dict[str, Any]:
        """
        获取智能体能力
        
        参数:
            agent_id: 智能体ID
            
        返回值:
            能力描述字典
        """
        pass
    
    @abstractmethod
    async def get_agent_status(self, instance_id: int) -> Dict[str, Any]:
        """
        获取智能体实例状态
        
        参数:
            instance_id: 实例ID
            
        返回值:
            状态信息字典
        """
        pass
    
    @abstractmethod
    async def create_multi_agent_system(
        self, agents: List[int], system_config: Dict[str, Any], user_id: int
    ) -> Dict[str, Any]:
        """
        创建多智能体系统
        
        参数:
            agents: 智能体ID列表
            system_config: 系统配置
            user_id: 用户ID
            
        返回值:
            创建结果，包含系统ID和创建的实例列表
        """
        pass
    
    @abstractmethod
    async def get_multi_agent_system(self, system_id: int) -> Dict[str, Any]:
        """
        获取多智能体系统信息
        
        参数:
            system_id: 系统ID
            
        返回值:
            系统信息，包含实例列表和通信记录
        """
        pass
