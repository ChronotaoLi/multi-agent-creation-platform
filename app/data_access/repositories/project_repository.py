"""
项目数据Repository模块

提供项目相关的数据访问方法
"""
from typing import List, Optional, Dict, Any, Tuple

from sqlalchemy import select, and_
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.project import Project, ProjectUser
from app.models.domain.user import User
from app.data_access.repositories.base_repository import BaseRepository
from app.data_access.db_session import get_db


class ProjectRepository(BaseRepository[Project]):
    """项目数据Repository
    
    提供项目相关的数据访问方法
    """
    
    def __init__(self, db: AsyncSession):
        """初始化ProjectRepository
        
        Args:
            db: 数据库会话
        """
        super().__init__(Project, db)
    
    async def get_by_user(self, user_id: int, skip: int = 0, limit: int = 100, project_type: Optional[str] = None, status: Optional[str] = None) -> Tuple[List[Project], int]:
        """获取用户的项目列表（分页），可根据项目类型和状态过滤
        
        Args:
            user_id: 用户ID
            skip: 跳过的记录数
            limit: 返回的最大记录数
            project_type: 项目类型 (可选)
            status: 项目状态 (可选)
            
        Returns:
            Tuple[List[Project], int]: 项目列表和总数
        """
        from sqlalchemy import func

        # Base query for fetching projects
        query = (
            select(Project)
            .join(ProjectUser, ProjectUser.project_id == Project.id)
            .where(ProjectUser.user_id == user_id)
        )

        # Base query for counting projects
        count_query = (
            select(func.count(Project.id))
            .join(ProjectUser, ProjectUser.project_id == Project.id)
            .where(ProjectUser.user_id == user_id)
        )

        # Apply filters
        if project_type:
            query = query.where(Project.project_type == project_type)
            count_query = count_query.where(Project.project_type == project_type)
        
        if status:
            query = query.where(Project.status == status)
            count_query = count_query.where(Project.status == status)
        
        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one_or_none() or 0
        
        # Apply ordering and pagination to the main query
        query = query.order_by(Project.created_at.desc()).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        projects = list(result.scalars().all())
        
        return projects, total
    
    async def get_with_details(self, project_id: int) -> Optional[Project]:
        """获取项目详情，包含关联内容、智能体等
        
        Args:
            project_id: 项目ID
            
        Returns:
            Optional[Project]: 项目详情，如果不存在则返回None
        """
        # 使用joinedload加载关联内容
        query = (
            select(Project)
            .options(
                joinedload(Project.content_items),
                joinedload(Project.agents),
                joinedload(Project.project_users)
            )
            .where(Project.id == project_id)
        )
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def add_user_to_project(self, project_id: int, user_id: int, role: str) -> Dict[str, Any]:
        """添加用户到项目，或更新用户角色，并返回用户详细信息和角色
        
        Args:
            project_id: 项目ID
            user_id: 用户ID
            role: 用户在项目中的角色
            
        Returns:
            Dict[str, Any]: 包含用户ID, 用户名, 显示名称, 邮箱和角色的字典
            
        Raises:
            ValueError: 如果用户不存在 (理论上应该由服务层检查，但以防万一)
        """
        # 检查记录是否已存在
        query = (
            select(ProjectUser)
            .where(and_(
                ProjectUser.project_id == project_id,
                ProjectUser.user_id == user_id
            ))
        )
        result = await self.db.execute(query)
        project_user = result.scalars().first()
        
        if project_user:
            # 如果已存在，更新角色
            project_user.role = role
        else:
            # 否则创建新关联
            project_user = ProjectUser(
                project_id=project_id,
                user_id=user_id,
                role=role
            )
            self.db.add(project_user)
        
        await self.db.commit()
        # Ensure the project_user object is refreshed to get any DB-generated values if needed,
        # though for role and IDs, it's usually fine.
        await self.db.refresh(project_user) 

        # 获取用户详细信息
        user_details_query = (
            select(User.id, User.username, User.display_name, User.email, ProjectUser.role)
            .join(ProjectUser, User.id == ProjectUser.user_id)
            .where(and_(
                ProjectUser.project_id == project_id,
                ProjectUser.user_id == user_id
            ))
        )
        user_details_result = await self.db.execute(user_details_query)
        user_info = user_details_result.first() # .first() returns a RowProxy or None

        if not user_info:
            # This case should ideally not be reached if user_id is validated upstream
            # or if the ProjectUser record implies user existence due to FK constraints.
            # However, as a safeguard:
            raise ValueError(f"User with id {user_id} not found or not associated with project {project_id} after add/update.")

        return {
            "id": user_info.id,
            "username": user_info.username,
            "display_name": user_info.display_name,
            "email": user_info.email,
            "role": user_info.role # This is the role from ProjectUser table
        }
    
    async def remove_user_from_project(self, project_id: int, user_id: int) -> None:
        """从项目中移除用户
        
        Args:
            project_id: 项目ID
            user_id: 用户ID
        """
        # 查询要删除的记录
        query = (
            select(ProjectUser)
            .where(and_(
                ProjectUser.project_id == project_id,
                ProjectUser.user_id == user_id
            ))
        )
        result = await self.db.execute(query)
        project_user = result.scalars().first()
        
        if project_user:
            await self.db.delete(project_user)
            await self.db.commit()
    
    async def get_project_users(self, project_id: int) -> List[Dict[str, Any]]:
        """获取项目用户列表（带角色）
        
        Args:
            project_id: 项目ID
            
        Returns:
            List[Dict[str, Any]]: 用户信息列表，每个用户包含基本信息和角色
        """
        # 构建查询，获取用户信息和角色
        query = (
            select(User, ProjectUser.role)
            .join(ProjectUser, ProjectUser.user_id == User.id)
            .where(ProjectUser.project_id == project_id)
        )
        result = await self.db.execute(query)
        
        # 构建结果列表
        users_with_roles = []
        for user, role in result:
            user_dict = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "display_name": user.display_name,
                "role": role
            }
            users_with_roles.append(user_dict)
        
        return users_with_roles


# 使用依赖注入模式创建项目仓库
async def get_project_repository() -> ProjectRepository:
    """获取项目仓库实例
    
    通过依赖注入模式创建ProjectRepository实例
    
    Returns:
        ProjectRepository: 项目仓库实例
    """
    async for db in get_db():
        # 为每个请求创建新的仓库实例
        yield ProjectRepository(db)
