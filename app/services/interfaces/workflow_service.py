from typing import Optional, Protocol, List

from app.models.schemas import (
    WorkflowStartConfig,
    WorkflowSession,
    WorkflowSessionStatus,
    InterventionData,
    InterventionResult,
    WorkflowTypeInfo
)


class WorkflowService(Protocol):
    """
    工作流服务接口规范
    """
    
    async def get_workflow_types(self) -> List[WorkflowTypeInfo]:
        """
        获取工作流类型
        
        返回值:
            List[WorkflowTypeInfo]: 可用的工作流类型信息列表
        """
        ...
        
    async def start_workflow(self, config: WorkflowStartConfig, user_id: int) -> WorkflowSession:
        """
        启动工作流
        
        参数:
            config: WorkflowStartConfig - 工作流启动配置
            user_id: int - 用户ID
            
        返回值:
            WorkflowSession: 创建的工作流会话信息
        """
        ...
        
    async def get_session_status(self, session_id: str) -> WorkflowSessionStatus:
        """
        获取会话状态
        
        参数:
            session_id: str - 会话ID
            
        返回值:
            WorkflowSessionStatus: 会话的当前状态
        """
        ...
        
    async def process_intervention(self, session_id: str, intervention_data: InterventionData) -> InterventionResult:
        """
        处理用户干预
        
        参数:
            session_id: str - 会话ID
            intervention_data: InterventionData - 用户干预数据
            
        返回值:
            InterventionResult: 干预处理结果
        """
        ...
        
    async def pause_session(self, session_id: str) -> WorkflowSessionStatus:
        """
        暂停会话
        
        参数:
            session_id: str - 会话ID
            
        返回值:
            WorkflowSessionStatus: 暂停后的会话状态
        """
        ...
        
    async def resume_session(self, session_id: str) -> WorkflowSessionStatus:
        """
        恢复会话
        
        参数:
            session_id: str - 会话ID
            
        返回值:
            WorkflowSessionStatus: 恢复后的会话状态
        """
        ...
        
    async def cancel_session(self, session_id: str) -> WorkflowSessionStatus:
        """
        取消会话
        
        参数:
            session_id: str - 会话ID
            
        返回值:
            WorkflowSessionStatus: 取消后的会话状态
        """
        ...
