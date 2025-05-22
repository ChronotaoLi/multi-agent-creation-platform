"""
工作流领域模型定义

本模块包含工作流相关的领域模型定义
"""
from enum import Enum
from typing import Dict, List, Any, Optional
from datetime import datetime

from pydantic import BaseModel, Field


class WorkflowStatus(str, Enum):
    """工作流状态枚举。"""
    
    INITIALIZED = "initialized"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowStepType(str, Enum):
    """工作流步骤类型枚举。"""
    
    START = "start"
    END = "end"
    TASK = "task"
    DECISION = "decision"
    FORK = "fork"
    JOIN = "join"
    MANUAL = "manual"
    SUBPROCESS = "subprocess"


class WorkflowDefinitionStep(BaseModel):
    """工作流步骤定义。"""
    
    id: str = Field(..., description="步骤ID")
    name: str = Field(..., description="步骤名称")
    type: WorkflowStepType = Field(..., description="步骤类型")
    config: Dict[str, Any] = Field(default_factory=dict, description="步骤配置")
    next_steps: List[str] = Field(default_factory=list, description="下一步骤ID列表")


class WorkflowDefinition(BaseModel):
    """工作流定义。"""
    
    id: str = Field(..., description="工作流ID")
    name: str = Field(..., description="工作流名称")
    description: Optional[str] = Field(None, description="工作流描述")
    version: str = Field(..., description="工作流版本")
    steps: Dict[str, WorkflowDefinitionStep] = Field(
        ..., description="工作流步骤定义，键为步骤ID"
    )
    inputs: Dict[str, Any] = Field(default_factory=dict, description="工作流输入定义")
    outputs: Dict[str, Any] = Field(default_factory=dict, description="工作流输出定义")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="工作流元数据")


class WorkflowExecutionOptions(BaseModel):
    """工作流执行选项。"""
    
    timeout_seconds: Optional[int] = Field(None, description="执行超时时间（秒）")
    max_retries: int = Field(0, description="最大重试次数")
    retry_delay_seconds: int = Field(1, description="重试延迟时间（秒）")
    trace_enabled: bool = Field(False, description="是否启用追踪")
    trace_level: str = Field("info", description="追踪级别")
    checkpoint_enabled: bool = Field(False, description="是否启用检查点")
    checkpoint_interval: int = Field(5, description="检查点间隔（步骤数）")


class WorkflowExecutionEvent(BaseModel):
    """工作流执行事件。"""
    
    event_type: str = Field(..., description="事件类型")
    workflow_id: str = Field(..., description="工作流ID")
    session_id: str = Field(..., description="会话ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="事件时间戳")
    data: Dict[str, Any] = Field(default_factory=dict, description="事件数据")


class WorkflowExecutionResult(BaseModel):
    """工作流执行结果。"""
    
    workflow_id: str = Field(..., description="工作流ID")
    session_id: str = Field(..., description="会话ID")
    status: WorkflowStatus = Field(..., description="工作流状态")
    outputs: Dict[str, Any] = Field(default_factory=dict, description="工作流输出")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="执行指标")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    duration_seconds: Optional[float] = Field(None, description="执行时长（秒）")
    error: Optional[str] = Field(None, description="错误信息")


class WorkflowInstance(BaseModel):
    """工作流实例。"""
    
    id: str = Field(..., description="实例ID")
    workflow_id: str = Field(..., description="工作流ID")
    session_id: str = Field(..., description="会话ID")
    project_id: Optional[str] = Field(None, description="项目ID")
    user_id: Optional[str] = Field(None, description="用户ID")
    status: WorkflowStatus = Field(..., description="工作流状态")
    current_step_id: Optional[str] = Field(None, description="当前步骤ID")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="工作流输入")
    state: Dict[str, Any] = Field(default_factory=dict, description="工作流状态")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="实例元数据") 