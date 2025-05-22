"""
故事、角色、场景等内容管理接口

提供内容创建、查询、更新、删除等API端点
"""
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status

from app.api.v1.deps import (
    get_current_user,
    get_content_service,
    pagination_params,
    validate_project_access,
    validate_project_edit_access,
    validate_content_access,
    validate_content_edit_access
)
from app.api.v1.schemas.common import Page
from app.api.v1.schemas.content import (
    ContentCreate,
    ContentUpdate,
    ContentResponse,
    ContentDetail,
    ContentListItem,
    ContentVersionResponse
)
from app.models.schemas import UserDB, ContentCreate as ModelContentCreate, ContentUpdate as ModelContentUpdate
from app.services.interfaces.content_service import ContentService
from app.utils.error_handlers import ResourceNotFoundError, PermissionDeniedError

# 创建路由器
router = APIRouter(
    prefix="/content",
    tags=["content"],
    responses={404: {"description": "内容未找到"}}
)

@router.post("/project/{project_id}", response_model=ContentResponse, status_code=201)
async def create_content(
    project_id: int = Path(...),
    content_data: ContentCreate = None,
    project: Annotated[dict, Depends(validate_project_edit_access)] = None,
    content_service: Annotated[ContentService, Depends(get_content_service)] = None,
    current_user: Annotated[UserDB, Depends(get_current_user)] = None
):
    """
    创建新的内容项（故事、角色、场景等）
    
    Args:
        project_id: 项目ID
        content_data: 内容创建数据
        
    Returns:
        ContentResponse: 创建的内容信息
    """
    try:
        # 转换API模型到服务层模型
        model_content_data = ModelContentCreate(
            title=content_data.title,
            content_type=content_data.content_type,
            content_data=content_data.content_data,
            project_id=project_id,
            metadata=content_data.metadata
        )
        
        # 调用服务创建内容
        content = await content_service.create_content(model_content_data, current_user.id)
        
        return ContentResponse.model_validate(content)
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
            detail=f"创建内容失败: {str(e)}"
        )

@router.get("/project/{project_id}", response_model=Page[ContentListItem])
async def get_project_contents(
    project_id: int = Path(...),
    content_type: Optional[str] = Query(None, description="内容类型过滤"),
    project: Annotated[dict, Depends(validate_project_access)] = None,
    content_service: Annotated[ContentService, Depends(get_content_service)] = None,
    pagination: Annotated[dict, Depends(pagination_params)] = None
):
    """
    获取项目的内容列表
    
    Args:
        project_id: 项目ID
        content_type: 可选，内容类型过滤
        pagination: 分页参数
        
    Returns:
        Page[ContentListItem]: 分页后的内容列表
    """
    try:
        # 获取项目内容
        contents, total = await content_service.get_project_contents(
            project_id=project_id, 
            content_type=content_type
        )
        
        # 计算分页
        skip = pagination.page_size * (pagination.page - 1)
        limit = pagination.page_size
        
        # 获取当前页内容
        paginated_contents = contents[skip:skip + limit]
        
        # 转换为响应模型
        items = [ContentListItem.model_validate(content) for content in paginated_contents]
        
        # 构造分页响应
        return Page(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            pages=(total + pagination.page_size - 1) // pagination.page_size
        )
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取项目内容列表失败: {str(e)}"
        )

@router.get("/{content_id}", response_model=ContentDetail)
async def get_content_detail(
    content_id: int = Path(...),
    content: Annotated[dict, Depends(validate_content_access)] = None,
    content_service: Annotated[ContentService, Depends(get_content_service)] = None
):
    """
    获取特定内容的详细信息
    
    Args:
        content_id: 内容ID
        
    Returns:
        ContentDetail: 内容详细信息
    """
    try:
        # validate_content_access 依赖已经验证了访问权限并返回了内容
        # 获取内容历史版本
        versions = await content_service.get_content_history(content_id)
        
        # 构建详细响应
        content_detail = ContentDetail(
            **ContentResponse.model_validate(content).model_dump(),
            version_count=len(versions),
            latest_version_at=versions[0].created_at if versions else content.updated_at,
            # 可以添加更多详细信息
        )
        
        return content_detail
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取内容详情失败: {str(e)}"
        )

@router.patch("/{content_id}", response_model=ContentResponse)
async def update_content(
    content_id: int = Path(...),
    content_data: ContentUpdate = None,
    content: Annotated[dict, Depends(validate_content_edit_access)] = None,
    content_service: Annotated[ContentService, Depends(get_content_service)] = None,
    current_user: Annotated[UserDB, Depends(get_current_user)] = None
):
    """
    更新内容信息
    
    Args:
        content_id: 内容ID
        content_data: 内容更新数据
        
    Returns:
        ContentResponse: 更新后的内容信息
    """
    try:
        # 转换API模型到服务层模型
        model_content_data = ModelContentUpdate(
            title=content_data.title,
            content_data=content_data.content_data,
            metadata=content_data.metadata
        )
        
        # 调用服务更新内容
        updated_content = await content_service.update_content(
            content_id, 
            model_content_data, 
            current_user.id
        )
        
        # 自动创建版本历史记录（如果服务层未处理）
        # 触发内容更新事件（在实际实现中）
        # await event_bus.publish("content.updated", {"content_id": content_id})
        
        return ContentResponse.model_validate(updated_content)
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
            detail=f"更新内容失败: {str(e)}"
        )

@router.delete("/{content_id}", status_code=204)
async def delete_content(
    content_id: int = Path(...),
    content: Annotated[dict, Depends(validate_content_edit_access)] = None,
    content_service: Annotated[ContentService, Depends(get_content_service)] = None
):
    """
    删除内容
    
    Args:
        content_id: 内容ID
    """
    try:
        await content_service.delete_content(content_id)
        
        # 触发内容删除事件（在实际实现中）
        # await event_bus.publish("content.deleted", {"content_id": content_id})
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除内容失败: {str(e)}"
        )

@router.get("/{content_id}/history", response_model=List[ContentVersionResponse])
async def get_content_history(
    content_id: int = Path(...),
    content: Annotated[dict, Depends(validate_content_access)] = None,
    content_service: Annotated[ContentService, Depends(get_content_service)] = None
):
    """
    获取内容的版本历史
    
    Args:
        content_id: 内容ID
        
    Returns:
        List[ContentVersionResponse]: 内容版本历史列表
    """
    try:
        versions = await content_service.get_content_history(content_id)
        return [ContentVersionResponse.model_validate(version) for version in versions]
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取内容历史版本失败: {str(e)}"
        )

@router.post("/{content_id}/restore/{version_id}", response_model=ContentResponse)
async def restore_content_version(
    content_id: int = Path(...),
    version_id: int = Path(...),
    content: Annotated[dict, Depends(validate_content_edit_access)] = None,
    content_service: Annotated[ContentService, Depends(get_content_service)] = None,
    current_user: Annotated[UserDB, Depends(get_current_user)] = None
):
    """
    将内容恢复到之前的版本
    
    Args:
        content_id: 内容ID
        version_id: 版本ID
        
    Returns:
        ContentResponse: 恢复后的内容信息
    """
    try:
        # 获取历史版本
        versions = await content_service.get_content_history(content_id)
        target_version = next((v for v in versions if v.id == version_id), None)
        
        if not target_version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"版本 {version_id} 不存在"
            )
        
        # 创建更新模型，使用版本数据
        model_content_data = ModelContentUpdate(
            content_data=target_version.version_data,
            title=content.title,  # 保留当前标题
            metadata=content.metadata  # 保留当前元数据
        )
        
        # 更新内容为历史版本
        updated_content = await content_service.update_content(
            content_id, 
            model_content_data, 
            current_user.id
        )
        
        # 触发内容恢复事件（在实际实现中）
        # await event_bus.publish("content.restored", {
        #     "content_id": content_id, 
        #     "version_id": version_id
        # })
        
        return ContentResponse.model_validate(updated_content)
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
            detail=f"恢复内容版本失败: {str(e)}"
        )
