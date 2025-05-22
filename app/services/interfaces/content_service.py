"""
内容服务接口

定义内容相关的业务逻辑接口
"""
from typing import Optional, Protocol, List, Tuple

from app.models.schemas import ContentCreate, ContentUpdate, ContentItem, ContentVersion


class ContentService(Protocol):
    """内容服务接口
    
    定义内容相关的业务逻辑方法
    """
    
    async def create_content(self, content_data: ContentCreate, user_id: int) -> ContentItem:
        """创建内容
        
        Args:
            content_data: 内容创建数据
            user_id: 创建者用户ID
            
        Returns:
            ContentItem: 创建的内容
            
        Raises:
            ResourceNotFoundError: 项目不存在
            PermissionDeniedError: 用户无权限
        """
        ...
    
    async def get_content_by_id(self, content_id: int) -> Optional[ContentItem]:
        """通过ID获取内容
        
        Args:
            content_id: 内容ID
            
        Returns:
            Optional[ContentItem]: 找到的内容，如果不存在则返回None
        """
        ...
    
    async def get_project_contents(self, project_id: int, content_type: Optional[str] = None) -> tuple[list[ContentItem], int]:
        """获取项目内容列表
        
        Args:
            project_id: 项目ID
            content_type: 内容类型过滤（可选）
            
        Returns:
            tuple[list[ContentItem], int]: 内容列表和总数量
            
        Raises:
            ResourceNotFoundError: 项目不存在
        """
        ...
    
    async def update_content(self, content_id: int, content_data: ContentUpdate, user_id: int) -> ContentItem:
        """更新内容
        
        Args:
            content_id: 内容ID
            content_data: 内容更新数据
            user_id: 更新者用户ID
            
        Returns:
            ContentItem: 更新后的内容
            
        Raises:
            ResourceNotFoundError: 内容不存在
            PermissionDeniedError: 用户无权限
        """
        ...
    
    async def delete_content(self, content_id: int) -> None:
        """删除内容
        
        Args:
            content_id: 内容ID
            
        Raises:
            ResourceNotFoundError: 内容不存在
        """
        ...
    
    async def get_content_history(self, content_id: int) -> list[ContentVersion]:
        """获取内容历史版本
        
        Args:
            content_id: 内容ID
            
        Returns:
            list[ContentVersion]: 历史版本列表
            
        Raises:
            ResourceNotFoundError: 内容不存在
        """
        ...
    
    async def create_content_version(self, content_id: int, version_data: dict, user_id: int) -> ContentVersion:
        """创建内容版本
        
        Args:
            content_id: 内容ID
            version_data: 版本数据
            user_id: 创建者用户ID
            
        Returns:
            ContentVersion: 创建的版本
            
        Raises:
            ResourceNotFoundError: 内容不存在
            PermissionDeniedError: 用户无权限
        """
        ...
