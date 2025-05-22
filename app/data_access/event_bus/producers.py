"""
事件生产者实现模块

本模块实现各类事件的生产者类，用于创建和发布事件到事件总线。
"""

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from app.core.config import get_settings
from app.data_access.event_bus.event_models import (
    AgentResponseEvent, AgentTaskAssignedEvent, AgentTaskStatusChangedEvent,
    ContentCreatedEvent, ContentUpdatedEvent, Event, UserInterventionRequiredEvent,
    UserInterventionSubmittedEvent, WorkflowCompletedEvent, WorkflowStartedEvent,
    WorkflowStepCompletedEvent
)
from app.data_access.event_bus.redis_streams import RedisStreamsEventBus
from app.utils.common_utils import generate_ulid, get_utc_now

settings = get_settings()


class EventProducer:
    """事件生产者基类，提供事件发布功能"""
    
    def __init__(
        self, 
        event_bus: RedisStreamsEventBus,
        source: str,
        event_id_generator: Optional[Callable[[], str]] = None
    ):
        """
        初始化事件生产者
        
        参数:
            event_bus: 事件总线
            source: 事件来源标识
            event_id_generator: 事件ID生成器（默认使用ULID）
        """
        self.event_bus = event_bus
        self.source = source
        self.event_id_generator = event_id_generator or generate_ulid
    
    async def publish_event(self, event: Event) -> str:
        """
        发布事件
        
        参数:
            event: 事件对象
        
        返回:
            事件ID
        """
        return await self.event_bus.publish_event(event)
    
    async def create_and_publish_event(
        self, 
        event_type: str, 
        data: Dict[str, Any],
        subject: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> str:
        """
        创建并发布事件
        
        参数:
            event_type: 事件类型
            data: 事件数据
            subject: 事件主题（可选）
            trace_id: 跟踪ID（可选）
        
        返回:
            事件ID
        """
        event = self._create_event(event_type, data, subject, trace_id)
        return await self.publish_event(event)
    
    def _create_event(
        self, 
        event_type: str, 
        data: Dict[str, Any],
        subject: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> Event:
        """
        创建事件对象
        
        参数:
            event_type: 事件类型
            data: 事件数据
            subject: 事件主题（可选）
            trace_id: 跟踪ID（可选）
        
        返回:
            事件对象
        """
        return Event(
            id=self.event_id_generator(),
            event_type=event_type,
            source=self.source,
            timestamp=get_utc_now(),
            data=data,
            subject=subject,
            trace_id=trace_id
        )


class WorkflowEventProducer(EventProducer):
    """工作流相关事件的生产者"""
    
    async def publish_workflow_started(
        self,
        workflow_id: str,
        workflow_type: str,
        project_id: str,
        initiator_id: str
    ) -> str:
        """
        发布工作流启动事件
        
        参数:
            workflow_id: 工作流ID
            workflow_type: 工作流类型
            project_id: 项目ID
            initiator_id: 发起人ID
        
        返回:
            事件ID
        """
        event = WorkflowStartedEvent(
            source=self.source,
            workflow_id=workflow_id,
            workflow_type=workflow_type,
            project_id=project_id,
            initiator_id=initiator_id
        )
        return await self.publish_event(event)
    
    async def publish_workflow_step_completed(
        self,
        workflow_id: str,
        step_id: str,
        step_name: str,
        status: str,
        outputs: Dict[str, Any]
    ) -> str:
        """
        发布工作流步骤完成事件
        
        参数:
            workflow_id: 工作流ID
            step_id: 步骤ID
            step_name: 步骤名称
            status: 完成状态
            outputs: 步骤输出
        
        返回:
            事件ID
        """
        event = WorkflowStepCompletedEvent(
            source=self.source,
            workflow_id=workflow_id,
            step_id=step_id,
            step_name=step_name,
            status=status,
            outputs=outputs
        )
        return await self.publish_event(event)
    
    async def publish_workflow_completed(
        self,
        workflow_id: str,
        status: str,
        results: Dict[str, Any]
    ) -> str:
        """
        发布工作流完成事件
        
        参数:
            workflow_id: 工作流ID
            status: 完成状态
            results: 工作流结果
        
        返回:
            事件ID
        """
        event = WorkflowCompletedEvent(
            source=self.source,
            workflow_id=workflow_id,
            status=status,
            results=results
        )
        return await self.publish_event(event)
    
    def _create_workflow_event_data(self, workflow_id: str, **kwargs) -> Dict[str, Any]:
        """
        创建工作流事件数据
        
        参数:
            workflow_id: 工作流ID
            **kwargs: 其他参数
        
        返回:
            事件数据字典
        """
        data = {"workflow_id": workflow_id}
        data.update(kwargs)
        return data


class AgentEventProducer(EventProducer):
    """智能体相关事件的生产者"""
    
    async def publish_task_assigned(
        self,
        agent_id: str,
        task_id: str,
        task_type: str,
        parameters: Dict[str, Any]
    ) -> str:
        """
        发布任务分配事件
        
        参数:
            agent_id: 智能体ID
            task_id: 任务ID
            task_type: 任务类型
            parameters: 任务参数
        
        返回:
            事件ID
        """
        event = AgentTaskAssignedEvent(
            source=self.source,
            agent_id=agent_id,
            task_id=task_id,
            task_type=task_type,
            parameters=parameters
        )
        return await self.publish_event(event)
    
    async def publish_task_status_changed(
        self,
        agent_id: str,
        task_id: str,
        previous_status: str,
        current_status: str,
        progress: Optional[float] = None
    ) -> str:
        """
        发布任务状态变更事件
        
        参数:
            agent_id: 智能体ID
            task_id: 任务ID
            previous_status: 之前状态
            current_status: 当前状态
            progress: 进度百分比（可选）
        
        返回:
            事件ID
        """
        event = AgentTaskStatusChangedEvent(
            source=self.source,
            agent_id=agent_id,
            task_id=task_id,
            previous_status=previous_status,
            current_status=current_status,
            progress=progress
        )
        return await self.publish_event(event)
    
    async def publish_agent_response(
        self,
        agent_id: str,
        task_id: str,
        response: Dict[str, Any]
    ) -> str:
        """
        发布智能体响应事件
        
        参数:
            agent_id: 智能体ID
            task_id: 任务ID
            response: 响应内容
        
        返回:
            事件ID
        """
        event = AgentResponseEvent(
            source=self.source,
            agent_id=agent_id,
            task_id=task_id,
            response=response
        )
        return await self.publish_event(event)


class ContentEventProducer(EventProducer):
    """内容相关事件的生产者"""
    
    async def publish_content_created(
        self,
        content_id: str,
        content_type: str,
        project_id: str,
        creator_id: str
    ) -> str:
        """
        发布内容创建事件
        
        参数:
            content_id: 内容ID
            content_type: 内容类型
            project_id: 项目ID
            creator_id: 创建者ID
        
        返回:
            事件ID
        """
        event = ContentCreatedEvent(
            source=self.source,
            content_id=content_id,
            content_type=content_type,
            project_id=project_id,
            creator_id=creator_id
        )
        return await self.publish_event(event)
    
    async def publish_content_updated(
        self,
        content_id: str,
        content_type: str,
        project_id: str,
        updater_id: str,
        changes: Dict[str, Any]
    ) -> str:
        """
        发布内容更新事件
        
        参数:
            content_id: 内容ID
            content_type: 内容类型
            project_id: 项目ID
            updater_id: 更新者ID
            changes: 变更内容
        
        返回:
            事件ID
        """
        event = ContentUpdatedEvent(
            source=self.source,
            content_id=content_id,
            content_type=content_type,
            project_id=project_id,
            updater_id=updater_id,
            changes=changes
        )
        return await self.publish_event(event)


class UserInteractionEventProducer(EventProducer):
    """用户交互相关事件的生产者"""
    
    async def publish_intervention_required(
        self,
        workflow_id: str,
        intervention_point: str,
        options: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> str:
        """
        发布需要用户干预事件
        
        参数:
            workflow_id: 工作流ID
            intervention_point: 干预点
            options: 选项列表
            context: 上下文信息
        
        返回:
            事件ID
        """
        event = UserInterventionRequiredEvent(
            source=self.source,
            workflow_id=workflow_id,
            intervention_point=intervention_point,
            options=options,
            context=context
        )
        return await self.publish_event(event)
    
    async def publish_intervention_submitted(
        self,
        workflow_id: str,
        intervention_point: str,
        selected_option: Dict[str, Any],
        custom_input: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        发布用户干预提交事件
        
        参数:
            workflow_id: 工作流ID
            intervention_point: 干预点
            selected_option: 选择的选项
            custom_input: 自定义输入（可选）
        
        返回:
            事件ID
        """
        event = UserInterventionSubmittedEvent(
            source=self.source,
            workflow_id=workflow_id,
            intervention_point=intervention_point,
            selected_option=selected_option,
            custom_input=custom_input
        )
        return await self.publish_event(event)
