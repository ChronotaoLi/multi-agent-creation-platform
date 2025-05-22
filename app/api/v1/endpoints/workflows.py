"""
工作流启动、状态查询、用户干预等接口

提供工作流管理相关的API端点
"""
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.api.v1.deps import (
    get_current_user,
    get_workflow_service,
    validate_project_access,
    validate_session_access
)
from app.api.v1.schemas.workflows import (
    WorkflowTypeInfo,
    WorkflowStartConfig,
    WorkflowSessionResponse,
    WorkflowSessionStatus,
    InterventionData,
    InterventionResult,
    WorkflowHistoryResponse,
    WorkflowActionResult
)
from app.models.schemas import UserDB, WorkflowStartConfig as ModelWorkflowStartConfig
from app.services.interfaces.workflow_service import WorkflowService
from app.utils.error_handlers import ResourceNotFoundError, PermissionDeniedError

# 创建路由器
router = APIRouter(
    prefix="/workflows",
    tags=["workflows"],
    responses={404: {"description": "工作流会话未找到"}}
)

@router.get("/types", response_model=List[WorkflowTypeInfo])
async def get_workflow_types(
    current_user: Annotated[UserDB, Depends(get_current_user)],
    workflow_service: Annotated[WorkflowService, Depends(get_workflow_service)]
):
    """
    获取支持的工作流类型列表
    
    Returns:
        List[WorkflowTypeInfo]: 工作流类型信息列表
    """
    try:
        workflow_types = await workflow_service.get_workflow_types()
        return workflow_types
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取工作流类型失败: {str(e)}"
        )

@router.post("/start", response_model=WorkflowSessionResponse)
async def start_workflow(
    config: WorkflowStartConfig,
    current_user: Annotated[UserDB, Depends(get_current_user)],
    workflow_service: Annotated[WorkflowService, Depends(get_workflow_service)]
):
    """
    启动新的工作流会话
    
    Args:
        config: 工作流启动配置
        
    Returns:
        WorkflowSessionResponse: 工作流会话信息
    """
    try:
        # 检查用户是否有权限访问相关项目
        # 在实际实现中，这里可能需要更复杂的验证逻辑
        
        # 转换API模型到服务层模型
        model_config = ModelWorkflowStartConfig(
            workflow_type=config.workflow_type,
            project_id=config.project_id,
            config=config.config,
            agent_configs=config.agent_configs,
            initial_content=config.initial_content
        )
        
        # 启动工作流
        session = await workflow_service.start_workflow(model_config, current_user.id)
        
        return WorkflowSessionResponse.model_validate(session)
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"启动工作流失败: {str(e)}"
        )

@router.get("/{session_id}/status", response_model=WorkflowSessionStatus)
async def get_session_status(
    session: Annotated[dict, Depends(validate_session_access)],
    workflow_service: Annotated[WorkflowService, Depends(get_workflow_service)]
):
    """
    获取工作流会话状态
    
    Args:
        session_id: 会话ID
        
    Returns:
        WorkflowSessionStatus: 工作流会话状态信息
    """
    try:
        # validate_session_access 依赖已经验证了访问权限
        session_id = session.get("session_id")
        
        # 获取会话状态
        status_info = await workflow_service.get_session_status(session_id)
        
        return WorkflowSessionStatus.model_validate(status_info)
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取会话状态失败: {str(e)}"
        )

@router.post("/{session_id}/intervention", response_model=InterventionResult)
async def handle_intervention(
    session_id: str = Path(...),
    intervention_data: InterventionData = None,
    session: Annotated[dict, Depends(validate_session_access)] = None,
    workflow_service: Annotated[WorkflowService, Depends(get_workflow_service)] = None
):
    """
    提交用户干预决策
    
    Args:
        session_id: 会话ID
        intervention_data: 干预数据
        
    Returns:
        InterventionResult: 干预处理结果
    """
    try:
        # 处理用户干预
        result = await workflow_service.process_intervention(
            session_id, 
            intervention_data
        )
        
        return InterventionResult.model_validate(result)
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理干预失败: {str(e)}"
        )

@router.get("/{session_id}/history", response_model=WorkflowHistoryResponse)
async def get_session_history(
    session: Annotated[dict, Depends(validate_session_access)],
    workflow_service: Annotated[WorkflowService, Depends(get_workflow_service)]
):
    """
    获取工作流会话执行历史
    
    Args:
        session_id: 会话ID
        
    Returns:
        WorkflowHistoryResponse: 会话历史信息
    """
    try:
        # 在此处添加获取会话历史的逻辑
        # 由于接口中没有定义获取历史的方法，这里提供一个基本实现
        session_id = session.get("session_id")
        
        # 这部分应该根据实际的服务层实现来调整
        # 目前假设有一个get_session_history的方法
        # history = await workflow_service.get_session_history(session_id)
        
        # 临时模拟数据
        history = {
            "session_id": session_id,
            "events": [],
            "state_changes": []
        }
        
        return WorkflowHistoryResponse.model_validate(history)
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取会话历史失败: {str(e)}"
        )

@router.post("/{session_id}/pause", response_model=WorkflowActionResult)
async def pause_session(
    session_id: str = Path(...),
    session: Annotated[dict, Depends(validate_session_access)] = None,
    workflow_service: Annotated[WorkflowService, Depends(get_workflow_service)] = None
):
    """
    暂停工作流会话
    
    Args:
        session_id: 会话ID
        
    Returns:
        WorkflowActionResult: 操作结果
    """
    try:
        # 暂停会话
        status_info = await workflow_service.pause_session(session_id)
        
        return WorkflowActionResult(
            success=True,
            status=status_info.status,
            message="会话已暂停",
            session_id=session_id
        )
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"暂停会话失败: {str(e)}"
        )

@router.post("/{session_id}/resume", response_model=WorkflowActionResult)
async def resume_session(
    session_id: str = Path(...),
    session: Annotated[dict, Depends(validate_session_access)] = None,
    workflow_service: Annotated[WorkflowService, Depends(get_workflow_service)] = None
):
    """
    恢复已暂停的工作流会话
    
    Args:
        session_id: 会话ID
        
    Returns:
        WorkflowActionResult: 操作结果
    """
    try:
        # 恢复会话
        status_info = await workflow_service.resume_session(session_id)
        
        return WorkflowActionResult(
            success=True,
            status=status_info.status,
            message="会话已恢复",
            session_id=session_id
        )
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"恢复会话失败: {str(e)}"
        )

@router.post("/{session_id}/cancel", response_model=WorkflowActionResult)
async def cancel_session(
    session_id: str = Path(...),
    session: Annotated[dict, Depends(validate_session_access)] = None,
    workflow_service: Annotated[WorkflowService, Depends(get_workflow_service)] = None
):
    """
    取消工作流会话
    
    Args:
        session_id: 会话ID
        
    Returns:
        WorkflowActionResult: 操作结果
    """
    try:
        # 取消会话
        status_info = await workflow_service.cancel_session(session_id)
        
        return WorkflowActionResult(
            success=True,
            status=status_info.status,
            message="会话已取消",
            session_id=session_id
        )
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"取消会话失败: {str(e)}"
        )
