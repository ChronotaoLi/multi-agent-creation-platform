"""
事件发布器模块

提供统一的事件发布接口，作为不同事件生产者的门面。
"""

from typing import Any, Dict, List, Optional

from app.data_access.event_bus.producers import (
    EventProducer, 
    WorkflowEventProducer, 
    AgentEventProducer, 
    ContentEventProducer, 
    UserInteractionEventProducer
)
from app.data_access.event_bus.redis_streams import RedisStreamsEventBus


class EventPublisher:
    """
    事件发布器
    
    统一事件发布接口，管理多个事件生产者
    """
    
    def __init__(self, event_bus: RedisStreamsEventBus, source: str = "system"):
        """
        初始化事件发布器
        
        参数:
            event_bus: 事件总线
            source: 事件源标识
        """
        self.event_bus = event_bus
        self.source = source
        
        # 初始化各类事件生产者
        self.generic_producer = EventProducer(event_bus, source)
        self.workflow_producer = WorkflowEventProducer(event_bus, source)
        self.agent_producer = AgentEventProducer(event_bus, source)
        self.content_producer = ContentEventProducer(event_bus, source)
        self.user_interaction_producer = UserInteractionEventProducer(event_bus, source)
    
    async def publish(self, event_type: str, data: Dict[str, Any], subject: Optional[str] = None) -> str:
        """
        发布通用事件
        
        参数:
            event_type: 事件类型
            data: 事件数据
            subject: 事件主题
            
        返回:
            str: 事件ID
        """
        return await self.generic_producer.create_and_publish_event(
            event_type=event_type,
            data=data,
            subject=subject
        )
    
    # 工作流事件方法
    
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
            str: 事件ID
        """
        return await self.workflow_producer.publish_workflow_started(
            workflow_id=workflow_id,
            workflow_type=workflow_type,
            project_id=project_id,
            initiator_id=initiator_id
        )
    
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
            str: 事件ID
        """
        return await self.workflow_producer.publish_workflow_completed(
            workflow_id=workflow_id,
            status=status,
            results=results
        )
    
    # 智能体事件方法
    
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
            str: 事件ID
        """
        return await self.agent_producer.publish_task_assigned(
            agent_id=agent_id,
            task_id=task_id,
            task_type=task_type,
            parameters=parameters
        )
    
    # 用户交互事件方法
    
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
            options: 干预选项
            context: 上下文信息
            
        返回:
            str: 事件ID
        """
        return await self.user_interaction_producer.publish_intervention_required(
            workflow_id=workflow_id,
            intervention_point=intervention_point,
            options=options,
            context=context
        ) 