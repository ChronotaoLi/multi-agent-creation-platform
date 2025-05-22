"""
智能体相关的请求/响应Pydantic模型

定义智能体相关的API请求和响应数据结构
"""
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field, ConfigDict


class AgentType(str, Enum):
    """智能体类型枚举"""
    COORDINATOR = "coordinator"
    CHARACTER = "character"
    CONTENT = "content"
    REVIEW = "review"
    MEMORY = "memory"
    ANALYSIS = "analysis"
    INFORMATION = "information"


class AgentBase(BaseModel):
    """智能体基础模型
    
    包含智能体的基本信息字段
    """
    name: str = Field(..., description="智能体名称", min_length=1, max_length=100)
    agent_type: AgentType = Field(..., description="智能体类型")
    config: Dict[str, Any] = Field(default_factory=dict, description="智能体配置数据")


class AgentCreate(AgentBase):
    """智能体创建请求模型
    
    用于创建新智能体的请求数据
    """
    template_id: Optional[int] = Field(None, description="模板ID（如果基于模板创建）")


class AgentUpdate(BaseModel):
    """智能体更新请求模型
    
    用于更新智能体的请求数据
    """
    name: Optional[str] = Field(None, description="智能体名称", min_length=1, max_length=100)
    config: Optional[Dict[str, Any]] = Field(None, description="智能体配置数据")


class AgentResponse(AgentBase):
    """智能体响应模型
    
    API返回的智能体信息
    """
    id: int = Field(..., description="智能体ID")
    project_id: int = Field(..., description="所属项目ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    status: str = Field("active", description="智能体状态")
    
    model_config = ConfigDict(from_attributes=True)


class AgentTypeInfo(BaseModel):
    """智能体类型信息模型
    
    智能体类型的描述信息
    """
    type: str = Field(..., description="类型标识")
    name: str = Field(..., description="类型名称")
    description: str = Field(..., description="类型描述")
    config_schema: Dict[str, Any] = Field(..., description="配置模式")
    icon: Optional[str] = Field(None, description="图标标识符")


class AgentCapability(BaseModel):
    """智能体能力模型
    
    智能体支持的能力
    """
    name: str = Field(..., description="能力名称")
    description: str = Field(..., description="能力描述")
    parameters: Optional[Dict[str, Any]] = Field(None, description="能力参数")


class AgentHistoryItem(BaseModel):
    """智能体历史记录项模型
    
    智能体活动的历史记录
    """
    timestamp: datetime = Field(..., description="时间戳")
    action_type: str = Field(..., description="活动类型")
    details: Dict[str, Any] = Field(default_factory=dict, description="详细信息")


class AgentDetail(AgentResponse):
    """智能体详细信息模型
    
    包含智能体的详细信息
    """
    capabilities: Dict[str, Any] = Field(default_factory=dict, description="智能体能力")
    status: Dict[str, Any] = Field(default_factory=dict, description="当前状态信息")
    history: List[AgentHistoryItem] = Field(default_factory=list, description="历史记录")


class AgentTemplateBase(BaseModel):
    """智能体模板基础模型
    
    包含智能体模板的基本信息
    """
    name: str = Field(..., description="模板名称")
    agent_type: AgentType = Field(..., description="智能体类型")
    description: str = Field(..., description="模板描述")
    default_config: Dict[str, Any] = Field(default_factory=dict, description="默认配置")


class AgentTemplateCreate(AgentTemplateBase):
    """智能体模板创建请求模型
    
    用于创建新模板的请求数据
    """
    is_public: bool = Field(False, description="是否公开")


class AgentTemplateUpdate(BaseModel):
    """智能体模板更新请求模型
    
    用于更新模板的请求数据
    """
    name: Optional[str] = Field(None, description="模板名称")
    description: Optional[str] = Field(None, description="模板描述")
    default_config: Optional[Dict[str, Any]] = Field(None, description="默认配置")
    is_public: Optional[bool] = Field(None, description="是否公开")


class AgentTemplateResponse(AgentTemplateBase):
    """智能体模板响应模型
    
    API返回的模板信息
    """
    id: int = Field(..., description="模板ID")
    created_by: int = Field(..., description="创建者ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    is_public: bool = Field(..., description="是否公开")
    
    model_config = ConfigDict(from_attributes=True)


class AgentMessageBase(BaseModel):
    """智能体消息基础模型
    
    智能体消息的基本结构
    """
    content: str = Field(..., description="消息内容")
    message_type: str = Field("text", description="消息类型")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="消息元数据")


class AgentMessageCreate(AgentMessageBase):
    """智能体消息创建请求模型
    
    发送给智能体的消息
    """
    pass


class AgentMessageResponse(AgentMessageBase):
    """智能体消息响应模型
    
    收到的智能体消息
    """
    id: str = Field(..., description="消息ID")
    sender: str = Field(..., description="发送者")
    receiver: str = Field(..., description="接收者")
    timestamp: datetime = Field(..., description="时间戳")
    
    model_config = ConfigDict(from_attributes=True)


class AgentTaskCreate(BaseModel):
    """智能体任务创建请求模型
    
    分配给智能体的任务
    """
    task_type: str = Field(..., description="任务类型")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="任务参数")
    priority: int = Field(5, description="优先级（1-10）", ge=1, le=10)


class AgentTaskResponse(AgentTaskCreate):
    """智能体任务响应模型
    
    任务状态和结果
    """
    id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    result: Optional[Dict[str, Any]] = Field(None, description="任务结果")
    
    model_config = ConfigDict(from_attributes=True)


class MultiAgentSystemCreate(BaseModel):
    """多智能体系统创建请求模型
    
    创建多智能体协作系统
    """
    name: str = Field(..., description="系统名称")
    description: Optional[str] = Field(None, description="系统描述")
    agent_ids: List[int] = Field(..., description="参与的智能体ID列表")
    config: Dict[str, Any] = Field(default_factory=dict, description="系统配置")


class MultiAgentSystemResponse(BaseModel):
    """多智能体系统响应模型
    
    多智能体协作系统信息
    """
    id: int = Field(..., description="系统ID")
    name: str = Field(..., description="系统名称")
    description: Optional[str] = Field(None, description="系统描述")
    agents: List[AgentResponse] = Field(..., description="参与的智能体")
    config: Dict[str, Any] = Field(default_factory=dict, description="系统配置")
    created_at: datetime = Field(..., description="创建时间")
    status: str = Field(..., description="系统状态")
    
    model_config = ConfigDict(from_attributes=True) 