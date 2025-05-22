"""
内容创作与管理服务实现

实现内容相关的业务逻辑
"""
from typing import Optional, List, Tuple
import logging
from datetime import datetime

from app.data_access.repositories.content_repository import ContentRepository
from app.data_access.event_bus.event_bus import EventBus
from app.models.schemas import ContentCreate, ContentUpdate, ContentItem, ContentVersion
from app.services.interfaces.content_service import ContentService
from app.services.interfaces.project_service import ProjectService
from app.utils.error_handlers import ResourceNotFoundError, PermissionDeniedError, InvalidInputError


class ContentServiceImpl:
    """内容创作与管理服务实现类
    
    实现ContentService接口的所有方法
    """
    
    # 有效的内容类型列表
    VALID_CONTENT_TYPES = ["story", "character", "scene", "dialogue", "plot", "world", "note"]
    
    def __init__(
        self,
        content_repository: ContentRepository,
        project_service: ProjectService,
        event_bus: EventBus,
    ):
        """初始化内容服务
        
        Args:
            content_repository: 内容数据Repository
            project_service: 项目服务
            event_bus: 事件总线
        """
        self.content_repository = content_repository
        self.project_service = project_service
        self.event_bus = event_bus
        self.logger = logging.getLogger(__name__)
    
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
            InvalidInputError: 内容类型无效
        """
        # 验证项目是否存在并且用户有访问权限
        if not await self.project_service.check_user_project_access(content_data.project_id, user_id):
            self.logger.error(f"User {user_id} has no access to project {content_data.project_id}")
            raise PermissionDeniedError(f"用户无权访问项目(ID: {content_data.project_id})")
        
        # 验证内容类型
        if content_data.content_type not in self.VALID_CONTENT_TYPES:
            self.logger.error(f"Invalid content type: {content_data.content_type}")
            raise InvalidInputError(f"内容类型 '{content_data.content_type}' 无效")
        
        # 创建内容
        content = await self.content_repository.create(
            title=content_data.title,
            content=content_data.content,
            content_type=content_data.content_type,
            metadata=content_data.metadata,
            project_id=content_data.project_id,
            created_by=user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        # 创建初始版本
        await self.create_content_version(
            content_id=content.id,
            version_data={
                "content": content_data.content,
                "metadata": content_data.metadata,
                "version_notes": "Initial version",
            },
            user_id=user_id
        )
        
        # 发布内容创建事件
        await self.event_bus.publish(
            "contents",
            {
                "type": "content_created",
                "content_id": content.id,
                "user_id": user_id,
                "project_id": content_data.project_id,
                "content_type": content_data.content_type,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        self.logger.info(f"Content created: {content.id} by user: {user_id}")
        return content
    
    async def get_content_by_id(self, content_id: int) -> Optional[ContentItem]:
        """通过ID获取内容
        
        Args:
            content_id: 内容ID
            
        Returns:
            Optional[ContentItem]: 找到的内容，如果不存在则返回None
        """
        return await self.content_repository.get_by_id(content_id)
    
    async def get_project_contents(self, project_id: int, content_type: Optional[str] = None) -> tuple[list[ContentItem], int]:
        """获取项目内容列表
        
        Args:
            project_id: 项目ID
            content_type: 内容类型过滤（可选）
            
        Returns:
            tuple[list[ContentItem], int]: 内容列表和总数量
            
        Raises:
            ResourceNotFoundError: 项目不存在
            InvalidInputError: 内容类型无效
        """
        # 验证项目是否存在
        project = await self.project_service.get_project_by_id(project_id)
        if not project:
            self.logger.error(f"Project with id {project_id} not found when getting contents")
            raise ResourceNotFoundError(f"项目(ID: {project_id})不存在")
        
        # 验证内容类型（如果提供）
        if content_type and content_type not in self.VALID_CONTENT_TYPES:
            self.logger.error(f"Invalid content type filter: {content_type}")
            raise InvalidInputError(f"内容类型 '{content_type}' 无效")
        
        return await self.content_repository.get_by_project_id(project_id, content_type)
    
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
        # 验证内容是否存在
        content = await self.content_repository.get_by_id(content_id)
        if not content:
            self.logger.error(f"Content with id {content_id} not found when updating")
            raise ResourceNotFoundError(f"内容(ID: {content_id})不存在")
        
        # 验证用户是否有权限
        if not await self.project_service.check_user_project_access(content.project_id, user_id):
            self.logger.error(f"User {user_id} has no access to project {content.project_id}")
            raise PermissionDeniedError(f"用户无权更新内容(ID: {content_id})")
        
        # 准备更新数据
        update_data = content_data.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow()
        update_data["updated_by"] = user_id
        
        # 更新内容
        updated_content = await self.content_repository.update(content_id, update_data)
        
        # 如果内容本身更新了，创建新版本
        if "content" in update_data:
            await self.create_content_version(
                content_id=content_id,
                version_data={
                    "content": update_data["content"],
                    "metadata": update_data.get("metadata", content.metadata),
                    "version_notes": content_data.version_notes if hasattr(content_data, "version_notes") else "Updated version",
                },
                user_id=user_id
            )
        
        # 发布内容更新事件
        await self.event_bus.publish(
            "contents",
            {
                "type": "content_updated",
                "content_id": content_id,
                "user_id": user_id,
                "project_id": content.project_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        self.logger.info(f"Content updated: {content_id} by user: {user_id}")
        return updated_content
    
    async def delete_content(self, content_id: int) -> None:
        """删除内容
        
        Args:
            content_id: 内容ID
            
        Raises:
            ResourceNotFoundError: 内容不存在
        """
        # 验证内容是否存在
        content = await self.content_repository.get_by_id(content_id)
        if not content:
            self.logger.error(f"Content with id {content_id} not found when deleting")
            raise ResourceNotFoundError(f"内容(ID: {content_id})不存在")
        
        # 删除内容
        await self.content_repository.delete(content_id)
        
        # 发布内容删除事件
        await self.event_bus.publish(
            "contents",
            {
                "type": "content_deleted",
                "content_id": content_id,
                "project_id": content.project_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        self.logger.info(f"Content deleted: {content_id}")
    
    async def get_content_history(self, content_id: int) -> list[ContentVersion]:
        """获取内容历史版本
        
        Args:
            content_id: 内容ID
            
        Returns:
            list[ContentVersion]: 历史版本列表
            
        Raises:
            ResourceNotFoundError: 内容不存在
        """
        # 验证内容是否存在
        content = await self.content_repository.get_by_id(content_id)
        if not content:
            self.logger.error(f"Content with id {content_id} not found when getting history")
            raise ResourceNotFoundError(f"内容(ID: {content_id})不存在")
        
        return await self.content_repository.get_content_versions(content_id)
    
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
        # 验证内容是否存在
        content = await self.content_repository.get_by_id(content_id)
        if not content:
            self.logger.error(f"Content with id {content_id} not found when creating version")
            raise ResourceNotFoundError(f"内容(ID: {content_id})不存在")
        
        # 验证用户是否有权限
        if not await self.project_service.check_user_project_access(content.project_id, user_id):
            self.logger.error(f"User {user_id} has no access to project {content.project_id}")
            raise PermissionDeniedError(f"用户无权创建内容版本")
        
        # 创建版本
        version = await self.content_repository.create_version(
            content_id=content_id,
            content=version_data.get("content"),
            metadata=version_data.get("metadata"),
            version_notes=version_data.get("version_notes", ""),
            created_by=user_id,
            created_at=datetime.utcnow()
        )
        
        self.logger.info(f"Content version created: {version.id} for content: {content_id}")
        return version
