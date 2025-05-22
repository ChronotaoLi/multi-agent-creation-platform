"""
工作流服务模块

管理工作流的启动、状态查询、用户干预等操作
"""
import json
import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

from app.services.interfaces.workflow_service import WorkflowService
from app.models.schemas import (
    WorkflowStartConfig, 
    WorkflowSession, 
    WorkflowSessionStatus,
    WorkflowType,
    WorkflowTypeInfo,
    InterventionData,
    InterventionResult
)
from app.utils.error_handlers import ResourceNotFoundError, InvalidInputError
from app.services.interfaces.agent_service import AgentService
from app.workflows.state_management.state_manager import StateManager
from app.workflows.creation_workflows.langgraph_manager import LangGraphManager
from app.data_access.event_bus.event_publisher import EventPublisher

# 简化的LangGraphManager和StateManager实现，避免复杂依赖
class LangGraphManager:
    """简化的LangGraph管理器实现"""
    
    def get_workflow_type(self, workflow_type: str):
        """获取工作流类型"""
        return {"id": workflow_type, "name": workflow_type}
    
    def get_or_create_workflow(self, workflow_type: str, config: Dict):
        """获取或创建工作流"""
        return {"type": workflow_type, "config": config}
    
    def get_workflow(self, workflow_type: str):
        """获取工作流"""
        return {"type": workflow_type}
    
    def get_available_workflow_types(self):
        """获取可用的工作流类型"""
        return []

class StateManager:
    """简化的状态管理器实现"""
    
    async def initialize_session_state(self, session_id: str, state: Dict):
        """初始化会话状态"""
        pass
    
    async def get_session_state(self, session_id: str) -> Dict:
        """获取会话状态"""
        return {"status": "initialized", "workflow_type": "default"}
    
    async def update_session_state(self, session_id: str, updates: Dict):
        """更新会话状态"""
        pass

class WorkflowServiceImpl:
    """
    工作流控制业务逻辑实现
    """
    
    def __init__(
        self,
        langgraph_manager: LangGraphManager,
        state_manager: StateManager,
        agent_service: AgentService,
        event_bus: EventPublisher
    ):
        """
        初始化工作流服务
        
        参数:
            langgraph_manager: LangGraphManager - LangGraph核心图设置
            state_manager: StateManager - 状态管理器
            agent_service: AgentService - 智能体服务
            event_bus: EventPublisher - 事件发布器
        """
        self.langgraph_manager = langgraph_manager
        self.state_manager = state_manager
        self.agent_service = agent_service
        self.event_bus = event_bus
        
    async def get_workflow_types(self) -> List[WorkflowTypeInfo]:
        """
        获取工作流类型
        
        返回值:
            List[WorkflowTypeInfo]: 可用的工作流类型信息列表
        """
        # 直接从LangGraphManager获取可用的工作流类型
        workflow_types = []
        
        # 这里简化为返回固定的工作流类型列表
        # 在实际实现中，应从LangGraphManager获取
        workflow_types.append(WorkflowTypeInfo(
            id="free",
            name="自由创作工作流",
            description="适用于自由创作的工作流程",
            capabilities=["自由创作", "多智能体协作"],
            config_schema={}
        ))
        
        workflow_types.append(WorkflowTypeInfo(
            id="guided",
            name="引导式创作工作流",
            description="提供创作引导的工作流程",
            capabilities=["引导式创作", "结构化输出"],
            config_schema={}
        ))
        
        return workflow_types
        
    async def start_workflow(self, config: WorkflowStartConfig, user_id: int) -> WorkflowSession:
        """
        根据配置启动工作流
        
        参数:
            config: WorkflowStartConfig - 工作流启动配置
            user_id: int - 用户ID
            
        返回值:
            WorkflowSession: 创建的工作流会话信息
        """
        # 验证工作流类型是否存在
        workflow_types = await self.get_workflow_types()
        workflow_type = next((wt for wt in workflow_types if wt.id == config.workflow_type), None)
        if workflow_type is None:
            raise ResourceNotFoundError(f"工作流类型 {config.workflow_type} 不存在")
        
        # 验证智能体配置
        if config.agents:
            for agent_id in config.agents:
                agent = await self.agent_service.get_agent_by_id(agent_id)
                if not agent:
                    raise ResourceNotFoundError(f"智能体 {agent_id} 不存在")
        
        # 生成会话ID
        session_id = str(uuid.uuid4())
        
        # 从 LangGraph 获取工作流图
        workflow_graph = self.langgraph_manager.get_or_create_workflow(
            config.workflow_type, config.model_dump()
        )
        
        # 初始化工作流状态
        initial_state = {
            "project_id": config.project_id,
            "workflow_type": config.workflow_type,
            "user_id": user_id,
            "config": config.model_dump(),
            "status": "initializing",
            "current_stage": "initialization",
            "start_time": datetime.now().isoformat(),
            "update_time": datetime.now().isoformat()
        }
        
        # 在状态管理器中注册会话状态
        await self.state_manager.initialize_session_state(
            session_id, initial_state
        )
        
        # 创建会话对象
        session = WorkflowSession(
            session_id=session_id,
            workflow_type=config.workflow_type,
            project_id=config.project_id,
            user_id=user_id,
            status="initializing",
            current_stage="initialization",
            data=config.initial_data or {},
            start_time=datetime.now(),
            update_time=datetime.now()
        )
        
        # 发布工作流启动事件
        await self.event_bus.publish(
            "workflow.session.started",
            {
                "session_id": session_id,
                "user_id": user_id,
                "project_id": config.project_id,
                "workflow_type": config.workflow_type
            }
        )
        
        # 异步启动工作流执行
        # 注: 实际实现中，这可能是一个后台任务或Celery任务
        await self._execute_workflow(session_id, workflow_graph, initial_state)
        
        return session
        
    async def get_session_status(self, session_id: str) -> WorkflowSessionStatus:
        """
        获取会话状态
        
        参数:
            session_id: str - 会话ID
            
        返回值:
            WorkflowSessionStatus: 会话的当前状态
        """
        # 从状态管理器获取会话状态
        state = await self.state_manager.get_session_state(session_id)
        if not state:
            raise ResourceNotFoundError(f"会话 {session_id} 不存在")
        
        # 构建会话状态响应
        update_time_str = state.get("update_time")
        if isinstance(update_time_str, str):
            try:
                update_time = datetime.fromisoformat(update_time_str)
            except (ValueError, TypeError):
                update_time = datetime.now()
        else:
            update_time = datetime.now()
            
        return WorkflowSessionStatus(
            session_id=session_id,
            status=state.get("status", "unknown"),
            current_stage=state.get("current_stage", ""),
            progress=state.get("progress", 0),
            next_steps=state.get("next_steps", []),
            messages=state.get("messages", []),
            update_time=update_time
        )
        
    async def process_intervention(self, session_id: str, intervention_data: InterventionData) -> InterventionResult:
        """
        处理用户干预
        
        参数:
            session_id: str - 会话ID
            intervention_data: InterventionData - 干预数据
            
        返回值:
            InterventionResult: 干预处理结果
        """
        # 验证会话存在
        state = await self.state_manager.get_session_state(session_id)
        if not state:
            raise ResourceNotFoundError(f"会话 {session_id} 不存在")
        
        # 检查会话是否在等待输入
        waiting_for_input = state.get("waiting_for_input")
        if isinstance(waiting_for_input, bool) and not waiting_for_input:
            # 记录但继续处理，因为某些干预类型可能不需要等待输入
            self.logger.warning(f"处理干预：会话 {session_id} 不在等待输入状态")
        
        # 获取当前工作流类型
        workflow_type = state.get("workflow_type", "default")
        current_stage = state.get("current_stage", "")
        
        # 确定目标阶段 - 如果未指定，则使用当前阶段
        target_stage = intervention_data.target_stage or current_stage
        
        # 准备干预信息
        intervention_info = {
            "intervention_type": intervention_data.intervention_type,
            "content": intervention_data.content,
            "from_stage": current_stage,
            "to_stage": target_stage,
            "timestamp": datetime.now().isoformat()
        }
        
        # 获取工作流实例
        workflow_graph = self.langgraph_manager.get_workflow_instance(workflow_type)
        
        # 准备更新状态 - 记录干预，更新阶段，设置为运行中
        await self.state_manager.update_session_state(
            session_id, 
            {
                "status": "processing",
                "waiting_for_input": False,
                "current_stage": target_stage,
                "last_intervention": intervention_info,
                "update_time": datetime.now().isoformat()
            }
        )
        
        # 将干预数据发送到工作流
        try:
            # 执行工作流图，传入干预数据
            response = await workflow_graph.invoke(
                inputs={
                    "intervention": intervention_info,
                    "session_id": session_id
                }
            )
            
            # 更新会话状态
            await self.state_manager.update_session_state(
                session_id, 
                {
                    "status": response.get("status", "in_progress"),
                    "current_stage": response.get("current_stage", target_stage),
                    "messages": response.get("messages", []),
                    "next_steps": response.get("next_steps", []),
                    "update_time": datetime.now().isoformat()
                }
            )
            
            # 发布干预处理事件
            await self.event_bus.publish(
                "workflow.intervention.processed",
                {
                    "session_id": session_id,
                    "intervention_type": intervention_data.intervention_type,
                    "success": True
                }
            )
            
            # 获取更新后的会话状态
            updated_status = await self.get_session_status(session_id)
            
            # 返回成功结果
            return InterventionResult(
                success=True,
                message="成功处理干预请求",
                status=updated_status
            )
            
        except Exception as e:
            # 更新状态为错误
            await self.state_manager.update_session_state(
                session_id, 
                {
                    "status": "error",
                    "error": str(e),
                    "update_time": datetime.now().isoformat()
                }
            )
            
            # 发布干预失败事件
            await self.event_bus.publish(
                "workflow.intervention.failed",
                {
                    "session_id": session_id,
                    "intervention_type": intervention_data.intervention_type,
                    "error": str(e)
                }
            )
            
            # 获取更新后的会话状态
            updated_status = await self.get_session_status(session_id)
            
            # 返回失败结果
            return InterventionResult(
                success=False,
                message=f"处理干预失败: {str(e)}",
                status=updated_status
            )
        
    async def pause_session(self, session_id: str) -> WorkflowSessionStatus:
        """
        暂停会话
        
        参数:
            session_id: str - 会话ID
            
        返回值:
            WorkflowSessionStatus: 暂停后的会话状态
        """
        # 检查会话是否存在
        state = await self.state_manager.get_session_state(session_id)
        if not state:
            raise ResourceNotFoundError(f"会话 {session_id} 不存在")
        
        # 检查会话是否可以暂停
        status = state.get("status")
        if isinstance(status, str) and status in ["completed", "cancelled", "paused"]:
            raise InvalidInputError(f"会话状态为 {status}，无法暂停")
        
        # 更新会话状态
        await self.state_manager.update_session_state(
            session_id, 
            {
                "status": "paused",
                "update_time": datetime.now().isoformat()
            }
        )
        
        # 发布工作流暂停事件
        await self.event_bus.publish(
            "workflow.session.paused",
            {
                "session_id": session_id
            }
        )
        
        # 返回更新后的会话状态
        return await self.get_session_status(session_id)
        
    async def resume_session(self, session_id: str) -> WorkflowSessionStatus:
        """
        恢复已暂停会话
        
        参数:
            session_id: str - 会话ID
            
        返回值:
            WorkflowSessionStatus: 恢复后的会话状态
        """
        # 检查会话是否存在
        state = await self.state_manager.get_session_state(session_id)
        if not state:
            raise ResourceNotFoundError(f"会话 {session_id} 不存在")
        
        # 检查会话是否处于暂停状态
        status = state.get("status")
        if isinstance(status, str) and status != "paused":
            raise InvalidInputError(f"会话不是处于暂停状态，当前状态: {status}")
        
        # 获取工作流类型
        workflow_type = state.get("workflow_type", "")
        
        # 获取工作流图
        workflow_graph = self.langgraph_manager.get_workflow_instance(workflow_type)
        
        # 准备更新状态
        updates = {
            "status": "in_progress",
            "update_time": datetime.now().isoformat()
        }
        
        # 更新会话状态
        await self.state_manager.update_session_state(session_id, updates)
        
        # 发布工作流恢复事件
        await self.event_bus.publish(
            "workflow.session.resumed",
            {
                "session_id": session_id,
                "workflow_type": workflow_type
            }
        )
        
        # 异步恢复工作流执行
        # 注: 实际实现中，这可能是一个后台任务或Celery任务
        self._resume_workflow_execution(session_id, workflow_graph, {})
        
        # 返回更新后的会话状态
        return await self.get_session_status(session_id)
        
    async def cancel_session(self, session_id: str) -> WorkflowSessionStatus:
        """
        取消会话
        
        参数:
            session_id: str - 会话ID
            
        返回值:
            WorkflowSessionStatus: 取消后的会话状态
        """
        # 检查会话是否存在
        state = await self.state_manager.get_session_state(session_id)
        if not state:
            raise ResourceNotFoundError(f"会话 {session_id} 不存在")
        
        # 检查会话是否可以取消
        status = state.get("status")
        if isinstance(status, str) and status in ["completed", "cancelled"]:
            raise InvalidInputError(f"会话已经处于终态: {status}，无法取消")
        
        # 更新会话状态
        await self.state_manager.update_session_state(
            session_id, 
            {
                "status": "cancelled",
                "update_time": datetime.now().isoformat()
            }
        )
        
        # 发布工作流取消事件
        await self.event_bus.publish(
            "workflow.session.cancelled",
            {
                "session_id": session_id
            }
        )
        
        # 返回更新后的会话状态
        return await self.get_session_status(session_id)
        
    async def _execute_workflow(self, session_id: str, workflow_graph: Any, initial_state: Dict):
        """
        执行工作流图
        
        参数:
            session_id: str - 会话ID
            workflow_graph: Any - LangGraph工作流图对象
            initial_state: Dict - 初始状态
        """
        try:
            # 更新会话状态为运行中
            await self.state_manager.update_session_state(
                session_id, 
                {
                    "status": "running",
                    "update_time": datetime.now().isoformat()
                }
            )
            
            # 使用LangGraph的执行机制，使用会话ID作为thread_id
            config = {"configurable": {"thread_id": session_id}}
            
            # 执行工作流
            result = await self._run_workflow_async(workflow_graph, initial_state, config)
            
            # 处理工作流完成
            await self._handle_workflow_completion(session_id, result)
            
        except Exception as e:
            # 处理执行过程中的错误
            await self._handle_workflow_error(session_id, e)
            
    async def _run_workflow_async(self, workflow_graph, initial_state, config):
        """
        异步运行工作流
        
        在实际实现中，这将使用LangGraph的异步执行API或使用后台任务
        
        参数:
            workflow_graph: Any - LangGraph工作流图
            initial_state: Dict - 初始状态
            config: Dict - 配置参数，包括thread_id等
            
        返回值:
            Any: 工作流执行结果
        """
        # 简化的模拟实现
        # 实际上应该使用workflow_graph.ainvoke()或在后台任务中调用workflow_graph.invoke()
        return {"status": "completed", "result": "工作流执行成功"}
            
    async def _resume_workflow_execution(self, session_id: str, workflow_graph: Any, response_data: Dict):
        """
        恢复工作流执行
        
        参数:
            session_id: str - 会话ID
            workflow_graph: Any - LangGraph工作流图对象
            response_data: Dict - 恢复执行所需的响应数据
        """
        # 在实际实现中，这将使用LangGraph的恢复执行API
        # 如果是基于事件的架构，也可以发布恢复事件让消费者处理
        pass
            
    async def _handle_workflow_completion(self, session_id: str, result: Dict):
        """
        处理工作流完成
        
        参数:
            session_id: str - 会话ID
            result: Dict - 工作流执行结果
        """
        # 更新会话状态为已完成
        await self.state_manager.update_session_state(
            session_id, 
            {
                "status": "completed", 
                "result": result,
                "update_time": datetime.now().isoformat()
            }
        )
        
        # 发布工作流完成事件
        await self.event_bus.publish(
            "workflow.session.completed",
            {"session_id": session_id, "result": result}
        )
            
    async def _handle_workflow_error(self, session_id: str, error: Exception):
        """
        处理工作流执行错误
        
        参数:
            session_id: str - 会话ID
            error: Exception - 错误对象
        """
        error_message = str(error)
        
        # 更新会话状态为错误
        await self.state_manager.update_session_state(
            session_id, 
            {
                "status": "error", 
                "error": error_message,
                "update_time": datetime.now().isoformat()
            }
        )
        
        # 发布工作流错误事件
        await self.event_bus.publish(
            "workflow.session.error",
            {"session_id": session_id, "error": error_message}
        )
