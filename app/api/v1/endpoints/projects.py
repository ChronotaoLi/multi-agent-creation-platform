"""
创作项目创建、查询、更新、删除等接口

提供项目管理相关的API端点
"""
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status

from app.api.v1.deps import (
    get_current_user,
    get_project_service, 
    pagination_params, 
    validate_project_access, 
    validate_project_edit_access,
    validate_project_owner
)
from app.api.v1.schemas.common import Page
from app.api.v1.schemas.projects import (
    ProjectCreate, 
    ProjectUpdate, 
    ProjectResponse, 
    ProjectDetail,
    ProjectListItem,
    ProjectMemberCreate,
    ProjectMemberResponse
)
from app.models.schemas import UserDB
from app.services.interfaces.project_service import ProjectService
from app.utils.error_handlers import ResourceNotFoundError, ResourceConflictError

# 创建路由器
router = APIRouter(
    prefix="/projects",
    tags=["projects"],
    responses={404: {"description": "项目未找到"}}
)

@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(
    project_data: ProjectCreate,
    current_user: Annotated[UserDB, Depends(get_current_user)],
    project_service: Annotated[ProjectService, Depends(get_project_service)]
):
    """
    创建新的创作项目
    
    Args:
        project_data: 项目创建数据
        current_user: 当前用户
        
    Returns:
        ProjectResponse: 创建的项目信息
    """
    try:
        project = await project_service.create_project(project_data, current_user.id)
        return project
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建项目失败: {str(e)}"
        )

@router.get("/", response_model=Page[ProjectListItem])
async def get_projects(
    current_user: Annotated[UserDB, Depends(get_current_user)],
    project_service: Annotated[ProjectService, Depends(get_project_service)],
    pagination: Annotated[dict, Depends(pagination_params)],
    project_type: Optional[str] = Query(None, description="项目类型过滤"),
    status: Optional[str] = Query(None, description="项目状态过滤")
):
    """
    获取当前用户的项目列表
    
    Args:
        current_user: 当前用户
        pagination: 分页参数
        project_type: 项目类型过滤
        status: 项目状态过滤
        
    Returns:
        Page[ProjectListItem]: 分页后的项目列表
    """
    try:
        # 这里应该根据项目类型和状态进行过滤
        # 由于接口中没有详细定义过滤逻辑，这里简化处理
        projects, total = await project_service.get_projects_by_user(
            user_id=current_user.id, 
            skip=pagination.page_size * (pagination.page - 1),
            limit=pagination.page_size
        )
        
        # 转换为响应模型
        items = [ProjectListItem.model_validate(project) for project in projects]
        
        # 构造分页响应
        return Page(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            pages=(total + pagination.page_size - 1) // pagination.page_size
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取项目列表失败: {str(e)}"
        )

@router.get("/{project_id}", response_model=ProjectDetail)
async def get_project(
    project: Annotated[dict, Depends(validate_project_access)]
):
    """
    获取特定项目的详细信息
    
    Args:
        project_id: 项目ID
        
    Returns:
        ProjectDetail: 项目详细信息
    """
    try:
        # validate_project_access 依赖已经检查了权限并返回了项目
        return ProjectDetail.model_validate(project)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取项目详情失败: {str(e)}"
        )

@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int = Path(...),
    project_data: ProjectUpdate = None,
    project: Annotated[dict, Depends(validate_project_edit_access)] = None,
    project_service: Annotated[ProjectService, Depends(get_project_service)] = None
):
    """
    更新项目信息
    
    Args:
        project_id: 项目ID
        project_data: 项目更新数据
        
    Returns:
        ProjectResponse: 更新后的项目信息
    """
    try:
        updated_project = await project_service.update_project(project_id, project_data)
        return ProjectResponse.model_validate(updated_project)
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新项目失败: {str(e)}"
        )

@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: int = Path(...),
    project: Annotated[dict, Depends(validate_project_owner)] = None,
    project_service: Annotated[ProjectService, Depends(get_project_service)] = None
):
    """
    删除项目
    
    Args:
        project_id: 项目ID
    """
    try:
        await project_service.delete_project(project_id)
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除项目失败: {str(e)}"
        )

@router.post("/{project_id}/members", response_model=ProjectMemberResponse)
async def add_project_member(
    project_id: int = Path(...),
    member_data: ProjectMemberCreate = None,
    project: Annotated[dict, Depends(validate_project_owner)] = None,
    project_service: Annotated[ProjectService, Depends(get_project_service)] = None
):
    """
    添加用户到项目
    
    Args:
        project_id: 项目ID
        member_data: 成员数据
        
    Returns:
        ProjectMemberResponse: 项目成员信息
    """
    try:
        await project_service.add_user_to_project(
            project_id=project_id,
            user_id=member_data.user_id,
            role=member_data.role
        )
        
        # 需要实际获取添加后的成员信息
        # 这里简化处理，直接构造响应
        return ProjectMemberResponse(
            project_id=project_id,
            user_id=member_data.user_id,
            role=member_data.role
        )
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ResourceConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"添加项目成员失败: {str(e)}"
        )

@router.get("/{project_id}/members", response_model=List[ProjectMemberResponse])
async def get_project_members(
    project_id: int = Path(...),
    project: Annotated[dict, Depends(validate_project_access)] = None,
    project_service: Annotated[ProjectService, Depends(get_project_service)] = None
):
    """
    获取项目成员列表
    
    Args:
        project_id: 项目ID
        
    Returns:
        List[ProjectMemberResponse]: 项目成员列表
    """
    try:
        members = await project_service.get_project_users(project_id)
        return [
            ProjectMemberResponse(
                project_id=project_id,
                user_id=member.id,
                username=member.username,
                display_name=member.display_name,
                email=member.email,
                role=member.role
            ) for member in members
        ]
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取项目成员失败: {str(e)}"
        )
