"""
事件数据模型定义模块

定义事件基类和各种具体事件类型，遵循CloudEvents规范。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.utils.common_utils import generate_ulid, get_utc_now


class Event(BaseModel):
    """
    事件基类，遵循CloudEvents规范
    """
    id: str = Field(default_factory=generate_ulid)
    event_type: str
    source: str
    timestamp: datetime = Field(default_factory=get_utc_now)
    data: Dict[str, Any]
    subject: Optional[str] = None
    trace_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """将事件转换为字典"""
        return self.model_dump()

    def to_json(self) -> str:
        """将事件转换为JSON字符串"""
        return self.model_dump_json()


# 工作流相关事件
class WorkflowStartedEvent(Event):
    """工作流启动事件"""
    event_type: str = "workflow.started"
    workflow_id: str
    workflow_type: str
    project_id: str
    initiator_id: str

    @property
    def data(self) -> Dict[str, Any]:
        """获取事件数据"""
        return {
            "workflow_id": self.workflow_id,
            "workflow_type": self.workflow_type,
            "project_id": self.project_id,
            "initiator_id": self.initiator_id
        }


class WorkflowStepCompletedEvent(Event):
    """工作流步骤完成事件"""
    event_type: str = "workflow.step.completed"
    workflow_id: str
    step_id: str
    step_name: str
    status: str
    outputs: Dict[str, Any]

    @property
    def data(self) -> Dict[str, Any]:
        """获取事件数据"""
        return {
            "workflow_id": self.workflow_id,
            "step_id": self.step_id,
            "step_name": self.step_name,
            "status": self.status,
            "outputs": self.outputs
        }


class WorkflowCompletedEvent(Event):
    """工作流完成事件"""
    event_type: str = "workflow.completed"
    workflow_id: str
    status: str
    results: Dict[str, Any]

    @property
    def data(self) -> Dict[str, Any]:
        """获取事件数据"""
        return {
            "workflow_id": self.workflow_id,
            "status": self.status,
            "results": self.results
        }


# 智能体相关事件
class AgentTaskAssignedEvent(Event):
    """智能体任务分配事件"""
    event_type: str = "agent.task.assigned"
    agent_id: str
    task_id: str
    task_type: str
    parameters: Dict[str, Any]

    @property
    def data(self) -> Dict[str, Any]:
        """获取事件数据"""
        return {
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "task_type": self.task_type,
            "parameters": self.parameters
        }


class AgentTaskStatusChangedEvent(Event):
    """智能体任务状态变更事件"""
    event_type: str = "agent.task.status_changed"
    agent_id: str
    task_id: str
    previous_status: str
    current_status: str
    progress: Optional[float] = None

    @property
    def data(self) -> Dict[str, Any]:
        """获取事件数据"""
        return {
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "previous_status": self.previous_status,
            "current_status": self.current_status,
            "progress": self.progress
        }


class AgentResponseEvent(Event):
    """智能体响应事件"""
    event_type: str = "agent.response"
    agent_id: str
    task_id: str
    response: Dict[str, Any]

    @property
    def data(self) -> Dict[str, Any]:
        """获取事件数据"""
        return {
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "response": self.response
        }


# 内容相关事件
class ContentCreatedEvent(Event):
    """内容创建事件"""
    event_type: str = "content.created"
    content_id: str
    content_type: str
    project_id: str
    creator_id: str

    @property
    def data(self) -> Dict[str, Any]:
        """获取事件数据"""
        return {
            "content_id": self.content_id,
            "content_type": self.content_type,
            "project_id": self.project_id,
            "creator_id": self.creator_id
        }


class ContentUpdatedEvent(Event):
    """内容更新事件"""
    event_type: str = "content.updated"
    content_id: str
    content_type: str
    project_id: str
    updater_id: str
    changes: Dict[str, Any]

    @property
    def data(self) -> Dict[str, Any]:
        """获取事件数据"""
        return {
            "content_id": self.content_id,
            "content_type": self.content_type,
            "project_id": self.project_id,
            "updater_id": self.updater_id,
            "changes": self.changes
        }


# 用户交互事件
class UserInterventionRequiredEvent(Event):
    """需要用户干预事件"""
    event_type: str = "user.intervention.required"
    workflow_id: str
    intervention_point: str
    options: List[Dict[str, Any]]
    context: Dict[str, Any]

    @property
    def data(self) -> Dict[str, Any]:
        """获取事件数据"""
        return {
            "workflow_id": self.workflow_id,
            "intervention_point": self.intervention_point,
            "options": self.options,
            "context": self.context
        }


class UserInterventionSubmittedEvent(Event):
    """用户干预提交事件"""
    event_type: str = "user.intervention.submitted"
    workflow_id: str
    intervention_point: str
    selected_option: Dict[str, Any]
    custom_input: Optional[Dict[str, Any]] = None

    @property
    def data(self) -> Dict[str, Any]:
        """获取事件数据"""
        result = {
            "workflow_id": self.workflow_id,
            "intervention_point": self.intervention_point,
            "selected_option": self.selected_option,
        }
        if self.custom_input is not None:
            result["custom_input"] = self.custom_input
        return result
