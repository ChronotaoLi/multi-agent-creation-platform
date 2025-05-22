"""
内容数据Repository模块

提供内容（故事、角色、脚本等）相关的数据访问方法
"""
from typing import List, Optional, Dict, Any

from sqlalchemy import select, and_
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.content import ContentItem, ContentVersion
from app.data_access.repositories.base_repository import BaseRepository
from app.data_access.db_session import get_db


class ContentRepository(BaseRepository[ContentItem]):
    """内容数据Repository
    
    提供内容相关的数据访问方法
    """
    
    def __init__(self, db: AsyncSession):
        """初始化ContentRepository
        
        Args:
            db: 数据库会话
        """
        super().__init__(ContentItem, db)
    
    async def get_by_project_id(self, project_id: int) -> List[ContentItem]:
        """获取项目下的所有内容
        
        Args:
            project_id: 项目ID
            
        Returns:
            List[ContentItem]: 内容列表
        """
        query = select(ContentItem).where(ContentItem.project_id == project_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_by_type(self, project_id: int, content_type: str) -> List[ContentItem]:
        """获取项目下指定类型的内容
        
        Args:
            project_id: 项目ID
            content_type: 内容类型
            
        Returns:
            List[ContentItem]: 内容列表
        """
        query = select(ContentItem).where(
            ContentItem.project_id == project_id,
            ContentItem.content_type == content_type
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_with_versions(self, content_id: int) -> Optional[ContentItem]:
        """获取内容项及其所有版本历史
        
        Args:
            content_id: 内容项ID
            
        Returns:
            Optional[ContentItem]: 内容项及版本，如果不存在则返回None
        """
        # 使用joinedload加载关联版本
        query = (
            select(ContentItem)
            .options(joinedload(ContentItem.versions))
            .where(ContentItem.id == content_id)
        )
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def create_version(self, content_id: int, data: Dict[str, Any], created_by_id: int) -> ContentVersion:
        """创建内容版本
        
        Args:
            content_id: 内容ID
            data: 版本数据
            created_by_id: 创建者用户ID
            
        Returns:
            ContentVersion: 创建的版本
        """
        version = ContentVersion(
            content_id=content_id,
            data=data,
            created_by_id=created_by_id
        )
        self.db.add(version)
        await self.db.commit()
        await self.db.refresh(version)
        return version
    
    async def get_latest_version(self, content_id: int) -> Optional[ContentVersion]:
        """获取内容最新版本
        
        Args:
            content_id: 内容ID
            
        Returns:
            Optional[ContentVersion]: 最新版本，如果不存在则返回None
        """
        query = (
            select(ContentVersion)
            .where(ContentVersion.content_id == content_id)
            .order_by(ContentVersion.created_at.desc())
        )
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def get_versions(self, content_id: int) -> List[ContentVersion]:
        """获取内容所有版本
        
        Args:
            content_id: 内容ID
            
        Returns:
            List[ContentVersion]: 版本列表
        """
        query = (
            select(ContentVersion)
            .where(ContentVersion.content_id == content_id)
            .order_by(ContentVersion.created_at.desc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())


# 使用依赖注入模式创建内容仓库
async def get_content_repository() -> ContentRepository:
    """获取内容仓库实例
    
    通过依赖注入模式创建ContentRepository实例
    
    Returns:
        ContentRepository: 内容仓库实例
    """
    async for db in get_db():
        # 为每个请求创建新的仓库实例
        yield ContentRepository(db)
