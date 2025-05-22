"""
事件消费者实现模块

本模块实现各类事件的消费者类，用于接收和处理来自事件总线的事件。
"""

import asyncio
import json
import logging
from typing import Any, Callable, Dict, List, Optional, Set, Type

from pydantic import ValidationError

from app.core.config import get_settings
from app.data_access.event_bus.event_models import (
    AgentResponseEvent, AgentTaskAssignedEvent, AgentTaskStatusChangedEvent,
    ContentCreatedEvent, ContentUpdatedEvent, Event, UserInterventionRequiredEvent,
    UserInterventionSubmittedEvent, WorkflowCompletedEvent, WorkflowStartedEvent,
    WorkflowStepCompletedEvent
)
from app.data_access.event_bus.redis_streams import RedisStreamsEventBus, StreamEventProcessor
from app.utils.common_utils import generate_ulid, get_utc_now

settings = get_settings()
logger = logging.getLogger(__name__)


class EventConsumer:
    """事件消费者基类，提供事件订阅和处理功能"""
    
    def __init__(
        self,
        event_bus: RedisStreamsEventBus,
        stream_name: str,
        group_name: str,
        consumer_name: str = None,
        event_types: List[str] = None
    ):
        """
        初始化事件消费者
        
        参数:
            event_bus: 事件总线
            stream_name: 订阅的Stream名称
            group_name: 消费者组名称
            consumer_name: 消费者名称（默认生成ULID）
            event_types: 订阅的事件类型列表（默认全部）
        """
        self.event_bus = event_bus
        self.stream_name = stream_name
        self.group_name = group_name
        self.consumer_name = consumer_name or f"consumer-{generate_ulid()}"
        self.event_types = event_types or []
        self.max_retry_count = 3
        self.running = False
        self.processor: Optional[StreamEventProcessor] = None
        self.logger = logging.getLogger(f"EventConsumer-{self.consumer_name}")
        
        # 事件类型映射，用于反序列化
        self.event_class_map = {
            "workflow.started": WorkflowStartedEvent,
            "workflow.step.completed": WorkflowStepCompletedEvent,
            "workflow.completed": WorkflowCompletedEvent,
            "agent.task.assigned": AgentTaskAssignedEvent,
            "agent.task.status_changed": AgentTaskStatusChangedEvent,
            "agent.response": AgentResponseEvent,
            "content.created": ContentCreatedEvent,
            "content.updated": ContentUpdatedEvent,
            "user.intervention.required": UserInterventionRequiredEvent,
            "user.intervention.submitted": UserInterventionSubmittedEvent
        }
    
    async def start(self) -> None:
        """启动消费者"""
        if self.running:
            return
            
        self.running = True
        
        # 创建事件处理器
        self.processor = self._create_processor()
        
        # 启动处理器
        await self.processor.start()
        
        self.logger.info(f"事件消费者启动: stream={self.stream_name}, group={self.group_name}, consumer={self.consumer_name}")
    
    async def stop(self) -> None:
        """停止消费者"""
        if not self.running:
            return
            
        self.running = False
        
        # 停止处理器
        if self.processor:
            await self.processor.stop()
            self.processor = None
        
        self.logger.info(f"事件消费者停止: stream={self.stream_name}, group={self.group_name}, consumer={self.consumer_name}")
    
    def _create_processor(self) -> StreamEventProcessor:
        """
        创建事件处理器
        
        返回:
            StreamEventProcessor对象
        """
        # 创建处理器，并实现process_event方法
        processor = StreamEventProcessor(
            event_bus=self.event_bus,
            stream_name=self.stream_name,
            group_name=self.group_name,
            consumer_name=self.consumer_name,
            max_retry_count=self.max_retry_count
        )
        
        # 覆盖处理器的process_event方法
        processor.process_event = self.process_event
        
        return processor
    
    async def process_event(self, event_id: str, event_data: Dict) -> None:
        """
        处理事件
        
        参数:
            event_id: 事件ID
            event_data: 事件数据
            
        注意:
            此方法应由子类实现
        """
        raise NotImplementedError("子类必须实现process_event方法")
    
    async def _deserialize_event(self, event_data: Dict) -> Event:
        """
        反序列化事件数据为Event对象
        
        参数:
            event_data: 事件数据
            
        返回:
            Event对象
            
        异常:
            ValidationError: 数据验证失败
        """
        if "event_type" not in event_data:
            self.logger.warning(f"事件数据缺少event_type字段: {event_data}")
            return Event(**event_data)
        
        event_type = event_data["event_type"]
        
        # 获取对应的事件类
        event_class = self.event_class_map.get(event_type, Event)
        
        try:
            # 使用对应的事件类反序列化
            return event_class(**event_data)
        except ValidationError as e:
            self.logger.error(f"事件数据验证失败，使用通用Event类: {str(e)}")
            return Event(**event_data)
    
    async def _filter_event(self, event: Event) -> bool:
        """
        过滤事件
        
        参数:
            event: 事件对象
            
        返回:
            True表示处理此事件，False表示忽略
        """
        # 如果没有指定事件类型，则处理所有事件
        if not self.event_types:
            return True
            
        # 如果指定了事件类型，只处理指定的事件类型
        return event.event_type in self.event_types
    
    async def _handle_error(self, event_id: str, event_data: Dict, error: Exception) -> None:
        """
        处理错误
        
        参数:
            event_id: 事件ID
            event_data: 事件数据
            error: 错误信息
        """
        self.logger.error(f"处理事件 {event_id} 时发生错误: {str(error)}")
        # 这里可以添加额外的错误处理逻辑，如记录日志、发送告警等
        # 基本的错误处理和重试逻辑由StreamEventProcessor实现


class WebSocketNotifier(EventConsumer):
    """通过WebSocket发送事件通知"""
    
    def __init__(
        self,
        event_bus: RedisStreamsEventBus,
        connection_manager,
        stream_name: str = "events:notifications",
        group_name: str = "websocket_notifiers",
        consumer_name: str = None,
        event_types: List[str] = None
    ):
        """
        初始化WebSocket通知器
        
        参数:
            event_bus: 事件总线
            connection_manager: WebSocket连接管理器
            stream_name: 订阅的Stream名称
            group_name: 消费者组名称
            consumer_name: 消费者名称
            event_types: 订阅的事件类型列表
        """
        super().__init__(event_bus, stream_name, group_name, consumer_name, event_types)
        self.connection_manager = connection_manager
    
    async def process_event(self, event_id: str, event_data: Dict) -> None:
        """
        处理事件并发送WebSocket通知
        
        参数:
            event_id: 事件ID
            event_data: 事件数据
        """
        try:
            # 反序列化事件
            event = await self._deserialize_event(event_data)
            
            # 过滤事件
            if not await self._filter_event(event):
                self.logger.debug(f"跳过非目标事件类型: {event.event_type}")
                await self.event_bus.acknowledge_event(self.group_name, self.stream_name, event_id)
                return
            
            # 获取应该接收此事件的客户端ID列表
            client_ids = await self._get_client_ids_for_event(event)
            
            if not client_ids:
                self.logger.debug(f"没有客户端订阅事件: {event.event_type}")
                await self.event_bus.acknowledge_event(self.group_name, self.stream_name, event_id)
                return
            
            # 转换事件数据为客户端格式
            client_message = await self._transform_event_for_client(event)
            
            # 发送通知
            for client_id in client_ids:
                await self.connection_manager.send_json(client_id, client_message)
            
            self.logger.debug(f"已向 {len(client_ids)} 个客户端发送事件通知: {event.event_type}")
            
            # 确认事件处理完成
            await self.event_bus.acknowledge_event(self.group_name, self.stream_name, event_id)
            
        except Exception as e:
            self.logger.error(f"发送WebSocket通知时发生错误: {str(e)}")
            raise
    
    async def _get_client_ids_for_event(self, event: Event) -> List[str]:
        """
        获取事件对应的客户端ID列表
        
        参数:
            event: 事件对象
            
        返回:
            客户端ID列表
        """
        # 示例实现，实际项目中应根据项目和用户的订阅关系确定
        # 这里简单地返回所有处于活动状态的WebSocket连接
        # 实际项目中应根据事件类型、事件数据中的项目ID、用户ID等筛选
        
        client_ids = []
        
        # 如果是工作流相关事件，筛选与该工作流相关的客户端
        if event.event_type.startswith("workflow."):
            workflow_id = event.data.get("workflow_id")
            if workflow_id:
                # 获取订阅了此工作流的客户端
                workflow_clients = await self.connection_manager.get_clients_by_property("workflow_id", workflow_id)
                client_ids.extend(workflow_clients)
        
        # 如果是内容相关事件，筛选与该项目相关的客户端
        elif event.event_type.startswith("content."):
            project_id = event.data.get("project_id")
            if project_id:
                # 获取订阅了此项目的客户端
                project_clients = await self.connection_manager.get_clients_by_property("project_id", project_id)
                client_ids.extend(project_clients)
        
        # 如果是用户干预事件，筛选与该工作流相关的客户端
        elif event.event_type.startswith("user.intervention."):
            workflow_id = event.data.get("workflow_id")
            if workflow_id:
                # 获取订阅了此工作流的客户端
                workflow_clients = await self.connection_manager.get_clients_by_property("workflow_id", workflow_id)
                client_ids.extend(workflow_clients)
        
        return client_ids
    
    async def _transform_event_for_client(self, event: Event) -> Dict:
        """
        转换事件数据为客户端格式
        
        参数:
            event: 事件对象
            
        返回:
            转换后的事件数据
        """
        # 创建基本事件数据
        client_event = {
            "type": "event",
            "event_type": event.event_type,
            "id": event.id,
            "timestamp": event.timestamp.isoformat(),
            "data": event.data
        }
        
        # 根据事件类型添加额外信息
        if event.event_type.startswith("workflow."):
            client_event["category"] = "workflow"
        elif event.event_type.startswith("agent."):
            client_event["category"] = "agent"
        elif event.event_type.startswith("content."):
            client_event["category"] = "content"
        elif event.event_type.startswith("user."):
            client_event["category"] = "user"
        
        return client_event


class WorkflowEventsConsumer(EventConsumer):
    """处理工作流相关事件"""
    
    def __init__(
        self,
        event_bus: RedisStreamsEventBus,
        workflow_service,
        stream_name: str = "events:workflow",
        group_name: str = "workflow_processors",
        consumer_name: str = None
    ):
        """
        初始化工作流事件消费者
        
        参数:
            event_bus: 事件总线
            workflow_service: 工作流服务
            stream_name: 订阅的Stream名称
            group_name: 消费者组名称
            consumer_name: 消费者名称
        """
        super().__init__(
            event_bus, 
            stream_name, 
            group_name, 
            consumer_name, 
            event_types=["workflow.started", "workflow.step.completed", "workflow.completed"]
        )
        self.workflow_service = workflow_service
    
    async def process_event(self, event_id: str, event_data: Dict) -> None:
        """
        处理工作流事件
        
        参数:
            event_id: 事件ID
            event_data: 事件数据
        """
        try:
            # 反序列化事件
            event = await self._deserialize_event(event_data)
            
            # 过滤事件
            if not await self._filter_event(event):
                self.logger.debug(f"跳过非目标事件类型: {event.event_type}")
                await self.event_bus.acknowledge_event(self.group_name, self.stream_name, event_id)
                return
            
            # 根据事件类型分发处理
            if event.event_type == "workflow.started":
                await self._handle_workflow_started(event_data)
            elif event.event_type == "workflow.step.completed":
                await self._handle_workflow_step_completed(event_data)
            elif event.event_type == "workflow.completed":
                await self._handle_workflow_completed(event_data)
            
            # 确认事件处理完成
            await self.event_bus.acknowledge_event(self.group_name, self.stream_name, event_id)
            
        except Exception as e:
            self.logger.error(f"处理工作流事件时发生错误: {str(e)}")
            raise
    
    async def _handle_workflow_started(self, event_data: Dict) -> None:
        """
        处理工作流启动事件
        
        参数:
            event_data: 事件数据
        """
        workflow_id = event_data.get("workflow_id")
        workflow_type = event_data.get("workflow_type")
        project_id = event_data.get("project_id")
        
        self.logger.info(f"工作流启动: id={workflow_id}, type={workflow_type}, project={project_id}")
        
        # 更新工作流状态
        await self.workflow_service.update_workflow_status(workflow_id, "running")
    
    async def _handle_workflow_step_completed(self, event_data: Dict) -> None:
        """
        处理工作流步骤完成事件
        
        参数:
            event_data: 事件数据
        """
        workflow_id = event_data.get("workflow_id")
        step_id = event_data.get("step_id")
        step_name = event_data.get("step_name")
        status = event_data.get("status")
        
        self.logger.info(f"工作流步骤完成: workflow={workflow_id}, step={step_name}, status={status}")
        
        # 更新工作流步骤状态
        await self.workflow_service.update_step_status(workflow_id, step_id, status)
    
    async def _handle_workflow_completed(self, event_data: Dict) -> None:
        """
        处理工作流完成事件
        
        参数:
            event_data: 事件数据
        """
        workflow_id = event_data.get("workflow_id")
        status = event_data.get("status")
        
        self.logger.info(f"工作流完成: workflow={workflow_id}, status={status}")
        
        # 更新工作流状态
        await self.workflow_service.update_workflow_status(workflow_id, status)
        
        # 如果工作流成功完成，处理结果
        if status == "completed":
            results = event_data.get("results", {})
            await self.workflow_service.process_workflow_results(workflow_id, results)


class AgentEventsConsumer(EventConsumer):
    """处理智能体相关事件"""
    
    def __init__(
        self,
        event_bus: RedisStreamsEventBus,
        agent_service,
        stream_name: str = "events:agent",
        group_name: str = "agent_processors",
        consumer_name: str = None
    ):
        """
        初始化智能体事件消费者
        
        参数:
            event_bus: 事件总线
            agent_service: 智能体服务
            stream_name: 订阅的Stream名称
            group_name: 消费者组名称
            consumer_name: 消费者名称
        """
        super().__init__(
            event_bus, 
            stream_name, 
            group_name, 
            consumer_name, 
            event_types=["agent.task.assigned", "agent.task.status_changed", "agent.response"]
        )
        self.agent_service = agent_service
    
    async def process_event(self, event_id: str, event_data: Dict) -> None:
        """
        处理智能体事件
        
        参数:
            event_id: 事件ID
            event_data: 事件数据
        """
        try:
            # 反序列化事件
            event = await self._deserialize_event(event_data)
            
            # 过滤事件
            if not await self._filter_event(event):
                self.logger.debug(f"跳过非目标事件类型: {event.event_type}")
                await self.event_bus.acknowledge_event(self.group_name, self.stream_name, event_id)
                return
            
            # 根据事件类型分发处理
            if event.event_type == "agent.task.assigned":
                await self._handle_task_assigned(event_data)
            elif event.event_type == "agent.task.status_changed":
                await self._handle_task_status_changed(event_data)
            elif event.event_type == "agent.response":
                await self._handle_agent_response(event_data)
            
            # 确认事件处理完成
            await self.event_bus.acknowledge_event(self.group_name, self.stream_name, event_id)
            
        except Exception as e:
            self.logger.error(f"处理智能体事件时发生错误: {str(e)}")
            raise
    
    async def _handle_task_assigned(self, event_data: Dict) -> None:
        """
        处理任务分配事件
        
        参数:
            event_data: 事件数据
        """
        agent_id = event_data.get("agent_id")
        task_id = event_data.get("task_id")
        task_type = event_data.get("task_type")
        
        self.logger.info(f"任务分配: agent={agent_id}, task={task_id}, type={task_type}")
        
        # 记录任务分配
        await self.agent_service.record_task_assigned(agent_id, task_id, task_type)
    
    async def _handle_task_status_changed(self, event_data: Dict) -> None:
        """
        处理任务状态变更事件
        
        参数:
            event_data: 事件数据
        """
        agent_id = event_data.get("agent_id")
        task_id = event_data.get("task_id")
        current_status = event_data.get("current_status")
        progress = event_data.get("progress")
        
        self.logger.info(f"任务状态变更: agent={agent_id}, task={task_id}, status={current_status}, progress={progress}")
        
        # 更新任务状态
        await self.agent_service.update_task_status(task_id, current_status, progress)
    
    async def _handle_agent_response(self, event_data: Dict) -> None:
        """
        处理智能体响应事件
        
        参数:
            event_data: 事件数据
        """
        agent_id = event_data.get("agent_id")
        task_id = event_data.get("task_id")
        response = event_data.get("response")
        
        self.logger.info(f"智能体响应: agent={agent_id}, task={task_id}")
        
        # 处理智能体响应
        await self.agent_service.process_agent_response(agent_id, task_id, response)


class ContentEventsConsumer(EventConsumer):
    """处理内容相关事件"""
    
    def __init__(
        self,
        event_bus: RedisStreamsEventBus,
        content_service,
        stream_name: str = "events:content",
        group_name: str = "content_processors",
        consumer_name: str = None
    ):
        """
        初始化内容事件消费者
        
        参数:
            event_bus: 事件总线
            content_service: 内容服务
            stream_name: 订阅的Stream名称
            group_name: 消费者组名称
            consumer_name: 消费者名称
        """
        super().__init__(
            event_bus, 
            stream_name, 
            group_name, 
            consumer_name, 
            event_types=["content.created", "content.updated"]
        )
        self.content_service = content_service
    
    async def process_event(self, event_id: str, event_data: Dict) -> None:
        """
        处理内容事件
        
        参数:
            event_id: 事件ID
            event_data: 事件数据
        """
        try:
            # 反序列化事件
            event = await self._deserialize_event(event_data)
            
            # 过滤事件
            if not await self._filter_event(event):
                self.logger.debug(f"跳过非目标事件类型: {event.event_type}")
                await self.event_bus.acknowledge_event(self.group_name, self.stream_name, event_id)
                return
            
            # 根据事件类型分发处理
            if event.event_type == "content.created":
                await self._handle_content_created(event_data)
            elif event.event_type == "content.updated":
                await self._handle_content_updated(event_data)
            
            # 确认事件处理完成
            await self.event_bus.acknowledge_event(self.group_name, self.stream_name, event_id)
            
        except Exception as e:
            self.logger.error(f"处理内容事件时发生错误: {str(e)}")
            raise
    
    async def _handle_content_created(self, event_data: Dict) -> None:
        """
        处理内容创建事件
        
        参数:
            event_data: 事件数据
        """
        content_id = event_data.get("content_id")
        content_type = event_data.get("content_type")
        project_id = event_data.get("project_id")
        
        self.logger.info(f"内容创建: id={content_id}, type={content_type}, project={project_id}")
        
        # 处理内容创建后的操作，如索引、通知等
        await self.content_service.handle_content_created(content_id, content_type)
    
    async def _handle_content_updated(self, event_data: Dict) -> None:
        """
        处理内容更新事件
        
        参数:
            event_data: 事件数据
        """
        content_id = event_data.get("content_id")
        content_type = event_data.get("content_type")
        changes = event_data.get("changes")
        
        self.logger.info(f"内容更新: id={content_id}, type={content_type}")
        
        # 处理内容更新后的操作，如重新索引、通知、版本管理等
        await self.content_service.handle_content_updated(content_id, content_type, changes)
