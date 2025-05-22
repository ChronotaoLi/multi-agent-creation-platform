"""
工作流相关的请求/响应Pydantic模型

定义工作流相关的API请求和响应数据结构
"""
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union

from pydantic import BaseModel, Field, ConfigDict


class WorkflowType(str, Enum):
    """工作流类型枚举"""
    STORY_CREATION = "story_creation"
    CHARACTER_DESIGN = "character_design"
    SCENE_GENERATION = "scene_generation"
    SCRIPT_WRITING = "script_writing"
    CONTENT_REVIEW = "content_review"
    CONTENT_IMPROVEMENT = "content_improvement"
    CUSTOM = "custom"


class WorkflowStatus(str, Enum):
    """工作流状态枚举"""
    INIT = "init"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING = "waiting"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


class WorkflowTypeInfo(BaseModel):
    """工作流类型信息模型
    
    工作流类型的描述信息
    """
    type: str = Field(..., description="工作流类型标识符")
    name: str = Field(..., description="工作流名称")
    description: str = Field(..., description="工作流描述")
    config_schema: Dict[str, Any] = Field(..., description="配置模式")
    icon: Optional[str] = Field(None, description="工作流图标标识符")


class WorkflowStartConfig(BaseModel):
    """工作流启动配置模型
    
    用于启动工作流的配置数据
    """
    workflow_type: str = Field(..., description="工作流类型")
    project_id: int = Field(..., description="项目ID")
    config: Dict[str, Any] = Field(default_factory=dict, description="工作流配置")
    agent_configs: Optional[List[Dict[str, Any]]] = Field(None, description="智能体配置列表")
    initial_content: Optional[Dict[str, Any]] = Field(None, description="初始内容数据")


class WorkflowSessionResponse(BaseModel):
    """工作流会话响应模型
    
    API返回的工作流会话信息
    """
    session_id: str = Field(..., description="会话ID")
    workflow_type: str = Field(..., description="工作流类型")
    project_id: int = Field(..., description="项目ID")
    initial_state: Dict[str, Any] = Field(..., description="初始状态")
    config: Dict[str, Any] = Field(..., description="工作流配置")
    created_at: datetime = Field(..., description="创建时间")
    created_by: int = Field(..., description="创建者ID")
    
    model_config = ConfigDict(from_attributes=True)


class ContentUpdate(BaseModel):
    """内容更新模型
    
    工作流执行过程中产生的内容更新
    """
    content_id: Optional[int] = Field(None, description="内容ID")
    content_type: str = Field(..., description="内容类型")
    title: Optional[str] = Field(None, description="内容标题")
    content_data: Dict[str, Any] = Field(..., description="内容数据")


class WorkflowSessionStatus(BaseModel):
    """工作流会话状态模型
    
    工作流会话当前状态信息
    """
    session_id: str = Field(..., description="会话ID")
    status: WorkflowStatus = Field(..., description="状态")
    current_stage: str = Field(..., description="当前阶段")
    progress: float = Field(..., description="完成进度（0-1）")
    current_state: Dict[str, Any] = Field(..., description="当前状态")
    next_node: Optional[str] = Field(None, description="下一节点")
    awaiting_intervention: bool = Field(..., description="是否等待干预")
    intervention_data: Optional[Dict[str, Any]] = Field(None, description="干预数据")
    error: Optional[Dict[str, Any]] = Field(None, description="错误信息")
    updated_at: datetime = Field(..., description="更新时间")
    content_updates: Optional[List[ContentUpdate]] = Field(None, description="内容更新列表")
    
    model_config = ConfigDict(from_attributes=True)


class InterventionOptionType(str, Enum):
    """干预选项类型"""
    TEXT = "text"
    CHOICE = "choice"
    MULTI_CHOICE = "multi_choice"
    CONFIRM = "confirm"
    EDIT = "edit"


class InterventionData(BaseModel):
    """干预数据模型
    
    用户提交的干预决策数据
    """
    intervention_id: str = Field(..., description="干预ID")
    decision: Any = Field(..., description="决策数据")
    response_type: InterventionOptionType = Field(..., description="响应类型")
    comments: Optional[str] = Field(None, description="用户评论")


class InterventionResult(BaseModel):
    """干预结果模型
    
    干预处理结果
    """
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="处理消息")
    session_id: str = Field(..., description="会话ID")
    result_data: Optional[Dict[str, Any]] = Field(None, description="结果数据")
    next_step: Optional[str] = Field(None, description="下一步操作")
    
    model_config = ConfigDict(from_attributes=True)


class WorkflowEvent(BaseModel):
    """工作流事件模型
    
    工作流执行过程中的事件记录
    """
    timestamp: datetime = Field(..., description="事件时间")
    event_type: str = Field(..., description="事件类型")
    description: str = Field(..., description="事件描述")
    data: Optional[Dict[str, Any]] = Field(None, description="事件数据")


class StateChange(BaseModel):
    """状态变更模型
    
    工作流状态变更记录
    """
    timestamp: datetime = Field(..., description="变更时间")
    from_state: str = Field(..., description="原状态")
    to_state: str = Field(..., description="新状态")
    reason: Optional[str] = Field(None, description="变更原因")


class WorkflowHistoryResponse(BaseModel):
    """工作流历史响应模型
    
    工作流执行历史信息
    """
    session_id: str = Field(..., description="会话ID")
    events: List[WorkflowEvent] = Field(default_factory=list, description="事件记录")
    state_changes: List[StateChange] = Field(default_factory=list, description="状态变更记录")
    
    model_config = ConfigDict(from_attributes=True)


class WorkflowActionResult(BaseModel):
    """工作流操作结果模型
    
    工作流操作的结果信息
    """
    success: bool = Field(..., description="操作是否成功")
    status: str = Field(..., description="会话状态")
    message: str = Field(..., description="操作消息")
    session_id: str = Field(..., description="会话ID")
    details: Optional[Dict[str, Any]] = Field(None, description="详细信息")
    
    model_config = ConfigDict(from_attributes=True) 