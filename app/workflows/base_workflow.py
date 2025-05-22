"""
工作流基类实现。

该模块提供了工作流的基类定义，包含工作流的通用接口和行为。
"""

import abc
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field

from app.models.domain.workflow_models import (
    WorkflowDefinition,
    WorkflowExecutionEvent,
    WorkflowExecutionOptions,
    WorkflowExecutionResult,
    WorkflowStatus,
)
from app.workflows.state_management.multi_level_manager import MultiLevelStateManager, StateLevel
from app.workflows.state_management.version_controller import VersionController
from app.workflows.subgraph_manager import SubgraphManager


class WorkflowContext(BaseModel):
    """工作流执行上下文。"""
    
    workflow_id: str = Field(..., description="工作流ID")
    session_id: str = Field(..., description="会话ID")
    project_id: Optional[str] = Field(None, description="项目ID")
    job_id: Optional[str] = Field(None, description="作业ID")
    user_id: Optional[str] = Field(None, description="用户ID")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="工作流输入")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="上下文元数据")
    options: WorkflowExecutionOptions = Field(
        default_factory=WorkflowExecutionOptions, description="执行选项"
    )


class BaseWorkflow(abc.ABC):
    """
    工作流基类，定义工作流接口和通用行为。
    """
    
    def __init__(
        self,
        state_manager: MultiLevelStateManager,
        version_controller: VersionController,
        subgraph_manager: SubgraphManager,
    ) -> None:
        """
        初始化工作流。

        参数:
            state_manager: 多层级状态管理器
            version_controller: 版本控制器
            subgraph_manager: 子图管理器
        """
        self.state_manager = state_manager
        self.version_controller = version_controller
        self.subgraph_manager = subgraph_manager
        self.definition: Optional[WorkflowDefinition] = None
    
    @abc.abstractmethod
    def init_workflow(self, context: WorkflowContext) -> Dict[str, Any]:
        """
        初始化工作流。

        参数:
            context: 工作流执行上下文

        返回:
            Dict[str, Any]: 初始状态
        """
        pass
    
    @abc.abstractmethod
    def execute(
        self, context: WorkflowContext
    ) -> WorkflowExecutionResult:
        """
        执行工作流。

        参数:
            context: 工作流执行上下文

        返回:
            WorkflowExecutionResult: 执行结果
        """
        pass
    
    @abc.abstractmethod
    async def aexecute(
        self, context: WorkflowContext
    ) -> WorkflowExecutionResult:
        """
        异步执行工作流。

        参数:
            context: 工作流执行上下文

        返回:
            WorkflowExecutionResult: 执行结果
        """
        pass
    
    def stream_execute(
        self, context: WorkflowContext
    ):
        """
        流式执行工作流。

        参数:
            context: 工作流执行上下文

        返回:
            Iterator: 返回执行事件流
        """
        # 初始化工作流状态
        initial_state = self.init_workflow(context)
        if not initial_state:
            yield WorkflowExecutionEvent(
                event_type="error",
                data={"error": "工作流初始化失败"},
                workflow_id=context.workflow_id,
                session_id=context.session_id,
            )
            return
        
        # 更新会话状态
        self.state_manager.update_state(
            StateLevel.SESSION, context.session_id, initial_state
        )
        
        # 触发开始事件
        yield WorkflowExecutionEvent(
            event_type="start",
            data={
                "workflow_id": context.workflow_id,
                "session_id": context.session_id,
                "status": WorkflowStatus.RUNNING,
            },
            workflow_id=context.workflow_id,
            session_id=context.session_id,
        )
        
        try:
            # 执行工作流的具体实现
            # 子类应该重写这个方法以提供流式执行功能
            for event in self._stream_execute_impl(context):
                yield event
                
            # 工作流正常完成
            yield WorkflowExecutionEvent(
                event_type="complete",
                data={
                    "workflow_id": context.workflow_id,
                    "session_id": context.session_id,
                    "status": WorkflowStatus.COMPLETED,
                },
                workflow_id=context.workflow_id,
                session_id=context.session_id,
            )
        except Exception as e:
            # 处理异常
            yield WorkflowExecutionEvent(
                event_type="error",
                data={
                    "workflow_id": context.workflow_id,
                    "session_id": context.session_id,
                    "status": WorkflowStatus.FAILED,
                    "error": str(e),
                },
                workflow_id=context.workflow_id,
                session_id=context.session_id,
            )
    
    async def astream_execute(
        self, context: WorkflowContext
    ):
        """
        异步流式执行工作流。

        参数:
            context: 工作流执行上下文

        返回:
            AsyncIterator: 返回执行事件流
        """
        # 初始化工作流状态
        initial_state = await self._ainit_workflow(context)
        if not initial_state:
            yield WorkflowExecutionEvent(
                event_type="error",
                data={"error": "工作流初始化失败"},
                workflow_id=context.workflow_id,
                session_id=context.session_id,
            )
            return
        
        # 更新会话状态
        await self.state_manager.aupdate_state(
            StateLevel.SESSION, context.session_id, initial_state
        )
        
        # 触发开始事件
        yield WorkflowExecutionEvent(
            event_type="start",
            data={
                "workflow_id": context.workflow_id,
                "session_id": context.session_id,
                "status": WorkflowStatus.RUNNING,
            },
            workflow_id=context.workflow_id,
            session_id=context.session_id,
        )
        
        try:
            # 异步执行工作流的具体实现
            # 子类应该重写这个方法以提供异步流式执行功能
            async for event in self._astream_execute_impl(context):
                yield event
                
            # 工作流正常完成
            yield WorkflowExecutionEvent(
                event_type="complete",
                data={
                    "workflow_id": context.workflow_id,
                    "session_id": context.session_id,
                    "status": WorkflowStatus.COMPLETED,
                },
                workflow_id=context.workflow_id,
                session_id=context.session_id,
            )
        except Exception as e:
            # 处理异常
            yield WorkflowExecutionEvent(
                event_type="error",
                data={
                    "workflow_id": context.workflow_id,
                    "session_id": context.session_id,
                    "status": WorkflowStatus.FAILED,
                    "error": str(e),
                },
                workflow_id=context.workflow_id,
                session_id=context.session_id,
            )
    
    def _stream_execute_impl(self, context: WorkflowContext):
        """
        流式执行实现的默认方法。

        参数:
            context: 工作流执行上下文

        返回:
            Iterator: 返回执行事件流
        """
        # 默认实现是一次性执行并返回结果
        result = self.execute(context)
        
        # 将结果转换为事件
        yield WorkflowExecutionEvent(
            event_type="result",
            data=result.dict(),
            workflow_id=context.workflow_id,
            session_id=context.session_id,
        )
    
    async def _astream_execute_impl(self, context: WorkflowContext):
        """
        异步流式执行实现的默认方法。

        参数:
            context: 工作流执行上下文

        返回:
            AsyncIterator: 返回执行事件流
        """
        # 默认实现是异步一次性执行并返回结果
        result = await self.aexecute(context)
        
        # 将结果转换为事件
        yield WorkflowExecutionEvent(
            event_type="result",
            data=result.dict(),
            workflow_id=context.workflow_id,
            session_id=context.session_id,
        )
    
    async def _ainit_workflow(self, context: WorkflowContext) -> Dict[str, Any]:
        """
        异步初始化工作流。

        参数:
            context: 工作流执行上下文

        返回:
            Dict[str, Any]: 初始状态
        """
        # 默认使用同步版本
        return self.init_workflow(context)
    
    def get_state(self, context: WorkflowContext) -> Dict[str, Any]:
        """
        获取工作流状态。

        参数:
            context: 工作流执行上下文

        返回:
            Dict[str, Any]: 工作流状态
        """
        return self.state_manager.get_state(
            StateLevel.SESSION, context.session_id
        )
    
    async def aget_state(self, context: WorkflowContext) -> Dict[str, Any]:
        """
        异步获取工作流状态。

        参数:
            context: 工作流执行上下文

        返回:
            Dict[str, Any]: 工作流状态
        """
        return await self.state_manager.aget_state(
            StateLevel.SESSION, context.session_id
        )
    
    def get_status(self, context: WorkflowContext) -> WorkflowStatus:
        """
        获取工作流状态。

        参数:
            context: 工作流执行上下文

        返回:
            WorkflowStatus: 工作流状态
        """
        state = self.get_state(context)
        status_str = state.get("status", WorkflowStatus.PENDING.value)
        
        try:
            return WorkflowStatus(status_str)
        except ValueError:
            return WorkflowStatus.UNKNOWN
    
    async def aget_status(self, context: WorkflowContext) -> WorkflowStatus:
        """
        异步获取工作流状态。

        参数:
            context: 工作流执行上下文

        返回:
            WorkflowStatus: 工作流状态
        """
        state = await self.aget_state(context)
        status_str = state.get("status", WorkflowStatus.PENDING.value)
        
        try:
            return WorkflowStatus(status_str)
        except ValueError:
            return WorkflowStatus.UNKNOWN
    
    def get_history(self, context: WorkflowContext) -> List[Dict[str, Any]]:
        """
        获取工作流历史。

        参数:
            context: 工作流执行上下文

        返回:
            List[Dict[str, Any]]: 历史记录列表
        """
        return self.state_manager.get_history(
            StateLevel.SESSION, context.session_id
        )
    
    async def aget_history(self, context: WorkflowContext) -> List[Dict[str, Any]]:
        """
        异步获取工作流历史。

        参数:
            context: 工作流执行上下文

        返回:
            List[Dict[str, Any]]: 历史记录列表
        """
        return await self.state_manager.aget_history(
            StateLevel.SESSION, context.session_id
        )
    
    def pause(self, context: WorkflowContext) -> bool:
        """
        暂停工作流。

        参数:
            context: 工作流执行上下文

        返回:
            bool: 操作是否成功
        """
        state = self.get_state(context)
        state["status"] = WorkflowStatus.PAUSED.value
        self.state_manager.update_state(
            StateLevel.SESSION, context.session_id, state
        )
        return True
    
    async def apause(self, context: WorkflowContext) -> bool:
        """
        异步暂停工作流。

        参数:
            context: 工作流执行上下文

        返回:
            bool: 操作是否成功
        """
        state = await self.aget_state(context)
        state["status"] = WorkflowStatus.PAUSED.value
        await self.state_manager.aupdate_state(
            StateLevel.SESSION, context.session_id, state
        )
        return True
    
    def resume(self, context: WorkflowContext) -> bool:
        """
        恢复工作流。

        参数:
            context: 工作流执行上下文

        返回:
            bool: 操作是否成功
        """
        state = self.get_state(context)
        state["status"] = WorkflowStatus.RUNNING.value
        self.state_manager.update_state(
            StateLevel.SESSION, context.session_id, state
        )
        return True
    
    async def aresume(self, context: WorkflowContext) -> bool:
        """
        异步恢复工作流。

        参数:
            context: 工作流执行上下文

        返回:
            bool: 操作是否成功
        """
        state = await self.aget_state(context)
        state["status"] = WorkflowStatus.RUNNING.value
        await self.state_manager.aupdate_state(
            StateLevel.SESSION, context.session_id, state
        )
        return True
    
    def cancel(self, context: WorkflowContext) -> bool:
        """
        取消工作流。

        参数:
            context: 工作流执行上下文

        返回:
            bool: 操作是否成功
        """
        state = self.get_state(context)
        state["status"] = WorkflowStatus.CANCELED.value
        self.state_manager.update_state(
            StateLevel.SESSION, context.session_id, state
        )
        return True
    
    async def acancel(self, context: WorkflowContext) -> bool:
        """
        异步取消工作流。

        参数:
            context: 工作流执行上下文

        返回:
            bool: 操作是否成功
        """
        state = await self.aget_state(context)
        state["status"] = WorkflowStatus.CANCELED.value
        await self.state_manager.aupdate_state(
            StateLevel.SESSION, context.session_id, state
        )
        return True
    
    def rollback(self, context: WorkflowContext, version_id: str) -> Dict[str, Any]:
        """
        回滚工作流到历史版本。

        参数:
            context: 工作流执行上下文
            version_id: 历史版本ID

        返回:
            Dict[str, Any]: 回滚后的状态
        """
        return self.version_controller.rollback(
            StateLevel.SESSION, context.session_id, version_id
        )
    
    async def arollback(self, context: WorkflowContext, version_id: str) -> Dict[str, Any]:
        """
        异步回滚工作流到历史版本。

        参数:
            context: 工作流执行上下文
            version_id: 历史版本ID

        返回:
            Dict[str, Any]: 回滚后的状态
        """
        return await self.version_controller.arollback(
            StateLevel.SESSION, context.session_id, version_id
        )
    
    def create_execution_result(
        self, context: WorkflowContext, status: WorkflowStatus, outputs: Dict[str, Any]
    ) -> WorkflowExecutionResult:
        """
        创建执行结果。

        参数:
            context: 工作流执行上下文
            status: 执行状态
            outputs: 输出数据

        返回:
            WorkflowExecutionResult: 执行结果
        """
        return WorkflowExecutionResult(
            workflow_id=context.workflow_id,
            session_id=context.session_id,
            status=status,
            outputs=outputs,
        )
