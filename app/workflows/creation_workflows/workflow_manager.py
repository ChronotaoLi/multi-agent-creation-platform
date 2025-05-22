"""
创作工作流管理器，负责管理工作流会话和状态
"""

from typing import Any, Dict, List, Optional, Union
import uuid
from datetime import datetime

from langgraph.checkpoint.postgres import PostgresSaver

from ...data_access.repositories.project_repository import ProjectRepository
from ...data_access.repositories.user_repository import UserRepository
from ...agents.coordinator_agent import CoordinatorAgent
from ...models.domain.workflow_session import WorkflowSession, WorkflowSessionStatus, WorkflowInterventionData
from ...models.domain.project import Project
from ...data_access.event_bus.producers import EventProducer
from ...agents.communication.message_bus import MessageBus

from .workflow_factory import WorkflowFactory
from .base_workflow import CreationWorkflow


class WorkflowManager:
    """创作工作流管理器，负责创建、运行和监控工作流会话"""
    
    def __init__(
        self,
        workflow_factory: Optional[WorkflowFactory] = None,
        project_repository: Optional[ProjectRepository] = None,
        user_repository: Optional[UserRepository] = None,
        message_bus: Optional[MessageBus] = None,
        postgres_connection_string: Optional[str] = None
    ):
        """
        初始化工作流管理器
        
        参数:
            workflow_factory: Optional[WorkflowFactory] - 工作流工厂
            project_repository: Optional[ProjectRepository] - 项目仓库
            user_repository: Optional[UserRepository] - 用户仓库
            message_bus: Optional[MessageBus] - 消息总线
            postgres_connection_string: Optional[str] - PostgreSQL连接字符串
        """
        self.workflow_factory = workflow_factory or WorkflowFactory()
        self.project_repository = project_repository
        self.user_repository = user_repository
        self.message_bus = message_bus
        self.active_workflows = {}  # 活跃工作流会话字典: session_id -> workflow_instance
        self.session_states = {}  # 会话状态字典: session_id -> current_state
        
        # 初始化检查点保存器
        self.checkpointer = None
        if postgres_connection_string:
            self.checkpointer = PostgresSaver(
                connection_string=postgres_connection_string,
                table_name="workflow_checkpoints"
            )
    
    def create_workflow_session(
        self,
        workflow_type: str,
        project_id: str,
        user_id: str,
        config: Dict[str, Any] = None
    ) -> WorkflowSession:
        """
        创建工作流会话
        
        参数:
            workflow_type: str - 工作流类型
            project_id: str - 项目ID
            user_id: str - 用户ID
            config: Dict[str, Any] - 工作流配置
            
        返回:
            WorkflowSession - 创建的工作流会话
        """
        # 创建协调智能体
        coordinator_agent = CoordinatorAgent()
        
        # 创建工作流实例
        workflow = self.workflow_factory.create_workflow(
            workflow_type=workflow_type,
            coordinator_agent=coordinator_agent,
            message_bus=self.message_bus,
            checkpointer=self.checkpointer,
            **(config or {})
        )
        
        if not workflow:
            raise ValueError(f"未知的工作流类型: {workflow_type}")
        
        # 生成会话ID
        session_id = str(uuid.uuid4())
        
        # 初始化工作流
        graph = workflow.initialize(project_id, user_id, config or {})
        
        # 创建会话记录
        now = datetime.utcnow().isoformat()
        session = WorkflowSession(
            session_id=session_id,
            project_id=project_id,
            user_id=user_id,
            workflow_type=workflow_type,
            status=WorkflowSessionStatus.INITIALIZING,
            config=config or {},
            current_stage="initialization",
            progress=0.0,
            created_at=now,
            updated_at=now
        )
        
        # 保存工作流实例和初始状态
        self.active_workflows[session_id] = workflow
        self.session_states[session_id] = {
            "workflow_type": workflow_type,
            "project_id": project_id,
            "user_id": user_id,
            "session_id": session_id,
            "status": "initializing",
            "current_stage": "initialization",
            "progress": 0.0,
            "content": {},
            "messages": [],
            "error": None,
            "creation_logs": [],
            "awaiting_intervention": False,
            "intervention_data": None,
            "metadata": {"config": config or {}},
            "created_at": now,
            "updated_at": now
        }
        
        # 保存会话到项目仓库
        if self.project_repository:
            # 获取项目
            project = self.project_repository.get_project_by_id(project_id)
            if project:
                # 更新项目会话信息
                project.active_session_id = session_id
                project.status = "in_progress"
                project.updated_at = now
                self.project_repository.update_project(project)
        
        return session
    
    def run_workflow_step(self, session_id: str) -> Dict[str, Any]:
        """
        运行工作流步骤
        
        参数:
            session_id: str - 会话ID
            
        返回:
            Dict[str, Any] - 更新后的状态
        """
        # 获取工作流实例
        workflow = self.active_workflows.get(session_id)
        if not workflow:
            raise ValueError(f"未找到会话: {session_id}")
        
        # 检查当前状态是否需要干预
        current_state = self.session_states.get(session_id, {})
        if current_state.get("awaiting_intervention", False):
            # 如果需要干预，则不执行下一步
            return current_state
        
        # 执行下一步
        try:
            # 执行工作流图的下一步
            # 注意：这里假设workflow._graph已经初始化并准备好执行
            if hasattr(workflow, "_graph") and workflow._graph:
                # 使用当前状态执行下一步
                config = {"configurable": {"thread_id": session_id}}
                result = workflow._graph.invoke(current_state, config=config)
                
                # 更新会话状态
                self.session_states[session_id] = result
                
                # 更新会话记录
                self._update_session_status(session_id, result)
                
                return result
            else:
                raise RuntimeError("工作流图未初始化")
        except Exception as e:
            # 处理错误
            error_state = {
                **current_state,
                "status": "error",
                "error": {
                    "type": "execution_error",
                    "message": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                },
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # 更新会话状态
            self.session_states[session_id] = error_state
            
            # 更新会话记录
            self._update_session_status(session_id, error_state)
            
            return error_state
    
    def handle_intervention(
        self,
        session_id: str,
        intervention_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        处理用户干预
        
        参数:
            session_id: str - 会话ID
            intervention_result: Dict[str, Any] - 干预结果
            
        返回:
            Dict[str, Any] - 更新后的状态
        """
        # 获取工作流实例
        workflow = self.active_workflows.get(session_id)
        if not workflow:
            raise ValueError(f"未找到会话: {session_id}")
        
        # 获取当前状态
        current_state = self.session_states.get(session_id, {})
        
        # 检查是否在等待干预
        if not current_state.get("awaiting_intervention", False):
            raise ValueError(f"会话{session_id}当前不需要干预")
        
        # 处理干预结果
        try:
            # 调用工作流的干预处理方法
            updated_state = workflow.handle_intervention_result(current_state, intervention_result)
            
            # 更新会话状态
            merged_state = {**current_state, **updated_state}
            self.session_states[session_id] = merged_state
            
            # 更新会话记录
            self._update_session_status(session_id, merged_state)
            
            return merged_state
        except Exception as e:
            # 处理错误
            error_state = {
                **current_state,
                "status": "error",
                "error": {
                    "type": "intervention_error",
                    "message": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                },
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # 更新会话状态
            self.session_states[session_id] = error_state
            
            # 更新会话记录
            self._update_session_status(session_id, error_state)
            
            return error_state
    
    def get_session_state(self, session_id: str) -> Dict[str, Any]:
        """
        获取会话状态
        
        参数:
            session_id: str - 会话ID
            
        返回:
            Dict[str, Any] - 会话状态
        """
        state = self.session_states.get(session_id)
        if not state:
            raise ValueError(f"未找到会话: {session_id}")
        
        return state
    
    def get_workflow_session(self, session_id: str) -> Optional[WorkflowSession]:
        """
        获取工作流会话
        
        参数:
            session_id: str - 会话ID
            
        返回:
            Optional[WorkflowSession] - 工作流会话
        """
        if not self.project_repository:
            return None
        
        # 从项目仓库获取会话
        sessions = self.project_repository.get_workflow_sessions(filter_by={"session_id": session_id}, limit=1)
        return sessions[0] if sessions else None
    
    def get_project_sessions(self, project_id: str) -> List[WorkflowSession]:
        """
        获取项目的所有会话
        
        参数:
            project_id: str - 项目ID
            
        返回:
            List[WorkflowSession] - 工作流会话列表
        """
        if not self.project_repository:
            return []
        
        return self.project_repository.get_workflow_sessions(filter_by={"project_id": project_id})
    
    def end_workflow_session(self, session_id: str, status: WorkflowSessionStatus = WorkflowSessionStatus.COMPLETED) -> None:
        """
        结束工作流会话
        
        参数:
            session_id: str - 会话ID
            status: WorkflowSessionStatus - 结束状态
        """
        # 获取工作流实例
        workflow = self.active_workflows.get(session_id)
        if not workflow:
            raise ValueError(f"未找到会话: {session_id}")
        
        # 获取当前状态
        current_state = self.session_states.get(session_id, {})
        
        # 更新状态
        updated_state = {
            **current_state,
            "status": status.value.lower(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # 更新会话记录
        self._update_session_status(session_id, updated_state)
        
        # 从活跃工作流中移除
        self.active_workflows.pop(session_id, None)
        self.session_states.pop(session_id, None)
    
    def _update_session_status(self, session_id: str, state: Dict[str, Any]) -> None:
        """
        更新会话状态记录
        
        参数:
            session_id: str - 会话ID
            state: Dict[str, Any] - 当前状态
        """
        if not self.project_repository:
            return
        
        # 获取会话
        session = self.get_workflow_session(session_id)
        if not session:
            return
        
        # 更新会话状态
        status_str = state.get("status", "").upper()
        if hasattr(WorkflowSessionStatus, status_str):
            session.status = getattr(WorkflowSessionStatus, status_str)
        else:
            session.status = WorkflowSessionStatus.IN_PROGRESS
        
        session.current_stage = state.get("current_stage", session.current_stage)
        session.progress = state.get("progress", session.progress)
        session.updated_at = state.get("updated_at", datetime.utcnow().isoformat())
        
        # 如果需要干预，添加干预数据
        if state.get("awaiting_intervention", False) and state.get("intervention_data"):
            intervention_data = state.get("intervention_data")
            session.intervention_data = WorkflowInterventionData(
                intervention_id=intervention_data.get("intervention_id", ""),
                type=intervention_data.get("type", ""),
                question=intervention_data.get("question", ""),
                options=intervention_data.get("options", []),
                context=intervention_data.get("context", {})
            )
        else:
            session.intervention_data = None
        
        # 更新会话
        self.project_repository.update_workflow_session(session)
        
        # 如果状态是完成或错误，更新项目状态
        if status_str in ["COMPLETED", "ERROR"]:
            project = self.project_repository.get_project_by_id(session.project_id)
            if project:
                project.active_session_id = None
                project.status = "completed" if status_str == "COMPLETED" else "error"
                project.updated_at = datetime.utcnow().isoformat()
                self.project_repository.update_project(project) 