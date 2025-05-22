"""
项目管理服务实现

实现项目相关的业务逻辑
"""
from typing import Optional, List, Tuple
import logging
from datetime import datetime

from app.data_access.repositories.project_repository import ProjectRepository
from app.data_access.repositories.user_repository import UserRepository
from app.data_access.event_bus.event_bus import EventBus
from app.models.schemas import ProjectCreate, ProjectUpdate, Project, UserWithRole
from app.services.interfaces.project_service import ProjectService
from app.utils.error_handlers import ResourceNotFoundError, ResourceConflictError, PermissionDeniedError


class ProjectServiceImpl:
    """项目管理服务实现类
    
    实现ProjectService接口的所有方法
    """
    
    def __init__(
        self,
        project_repository: ProjectRepository,
        user_repository: UserRepository,
        event_bus: EventBus,
    ):
        """初始化项目服务
        
        Args:
            project_repository: 项目数据Repository
            user_repository: 用户数据Repository
            event_bus: 事件总线
        """
        self.project_repository = project_repository
        self.user_repository = user_repository
        self.event_bus = event_bus
        self.logger = logging.getLogger(__name__)
    
    async def create_project(self, project_data: ProjectCreate, user_id: int) -> Project:
        """创建项目，分配用户权限
        
        Args:
            project_data: 项目创建数据
            user_id: 创建者用户ID
            
        Returns:
            Project: 创建的项目
            
        Raises:
            ResourceNotFoundError: 用户不存在
        """
        # 验证用户是否存在
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            self.logger.error(f"User with id {user_id} not found when creating project")
            raise ResourceNotFoundError(f"用户(ID: {user_id})不存在")
        
        # 创建项目
        project = await self.project_repository.create(
            title=project_data.title,
            description=project_data.description,
            project_type=project_data.project_type,
            created_by=user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        # 将创建者添加为项目所有者
        await self.project_repository.add_user_to_project(
            project_id=project.id,
            user_id=user_id,
            role="owner"
        )
        
        # 发布项目创建事件
        await self.event_bus.publish(
            "projects",
            {
                "type": "project_created",
                "project_id": project.id,
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        self.logger.info(f"Project created: {project.id} by user: {user_id}")
        return project
    
    async def get_project_by_id(self, project_id: int) -> Optional[Project]:
        """通过ID获取项目
        
        Args:
            project_id: 项目ID
            
        Returns:
            Optional[Project]: 找到的项目，如果不存在则返回None
        """
        return await self.project_repository.get_by_id(project_id)
    
    async def get_projects_by_user(self, user_id: int, skip: int, limit: int) -> tuple[list[Project], int]:
        """获取用户的项目列表
        
        Args:
            user_id: 用户ID
            skip: 分页起始位置
            limit: 每页数量
            
        Returns:
            tuple[list[Project], int]: 项目列表和总数量
            
        Raises:
            ResourceNotFoundError: 用户不存在
        """
        # 验证用户是否存在
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            self.logger.error(f"User with id {user_id} not found when getting projects")
            raise ResourceNotFoundError(f"用户(ID: {user_id})不存在")
        
        return await self.project_repository.get_by_user_id(user_id, skip, limit)
    
    async def update_project(self, project_id: int, project_data: ProjectUpdate) -> Project:
        """更新项目信息
        
        Args:
            project_id: 项目ID
            project_data: 项目更新数据
            
        Returns:
            Project: 更新后的项目
            
        Raises:
            ResourceNotFoundError: 项目不存在
        """
        # 验证项目是否存在
        project = await self.project_repository.get_by_id(project_id)
        if not project:
            self.logger.error(f"Project with id {project_id} not found when updating")
            raise ResourceNotFoundError(f"项目(ID: {project_id})不存在")
        
        # 更新项目
        update_data = project_data.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow()
        
        updated_project = await self.project_repository.update(project_id, update_data)
        
        # 发布项目更新事件
        await self.event_bus.publish(
            "projects",
            {
                "type": "project_updated",
                "project_id": project_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        self.logger.info(f"Project updated: {project_id}")
        return updated_project
    
    async def delete_project(self, project_id: int) -> None:
        """删除项目
        
        Args:
            project_id: 项目ID
            
        Raises:
            ResourceNotFoundError: 项目不存在
        """
        # 验证项目是否存在
        project = await self.project_repository.get_by_id(project_id)
        if not project:
            self.logger.error(f"Project with id {project_id} not found when deleting")
            raise ResourceNotFoundError(f"项目(ID: {project_id})不存在")
        
        # 删除项目
        await self.project_repository.delete(project_id)
        
        # 发布项目删除事件
        await self.event_bus.publish(
            "projects",
            {
                "type": "project_deleted",
                "project_id": project_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        self.logger.info(f"Project deleted: {project_id}")
    
    async def check_user_project_access(self, project_id: int, user_id: int, required_role: Optional[str] = None) -> bool:
        """验证用户项目访问权限
        
        Args:
            project_id: 项目ID
            user_id: 用户ID
            required_role: 所需角色，如果为None，则只检查是否有任何权限
            
        Returns:
            bool: 是否有访问权限
        """
        return await self.project_repository.check_user_access(project_id, user_id, required_role)
    
    async def add_user_to_project(self, project_id: int, user_id: int, role: str) -> None:
        """添加用户到项目
        
        Args:
            project_id: 项目ID
            user_id: 用户ID
            role: 用户在项目中的角色
            
        Raises:
            ResourceNotFoundError: 项目或用户不存在
            ResourceConflictError: 用户已经在项目中
        """
        # 验证项目是否存在
        project = await self.project_repository.get_by_id(project_id)
        if not project:
            self.logger.error(f"Project with id {project_id} not found when adding user")
            raise ResourceNotFoundError(f"项目(ID: {project_id})不存在")
        
        # 验证用户是否存在
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            self.logger.error(f"User with id {user_id} not found when adding to project")
            raise ResourceNotFoundError(f"用户(ID: {user_id})不存在")
        
        # 检查用户是否已在项目中
        if await self.check_user_project_access(project_id, user_id):
            self.logger.error(f"User with id {user_id} already in project {project_id}")
            raise ResourceConflictError(f"用户(ID: {user_id})已经在项目中")
        
        # 添加用户到项目
        await self.project_repository.add_user_to_project(project_id, user_id, role)
        
        # 发布用户添加到项目事件
        await self.event_bus.publish(
            "projects",
            {
                "type": "user_added_to_project",
                "project_id": project_id,
                "user_id": user_id,
                "role": role,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        self.logger.info(f"User {user_id} added to project {project_id} with role {role}")
    
    async def get_project_users(self, project_id: int) -> list[UserWithRole]:
        """获取项目用户列表
        
        Args:
            project_id: 项目ID
            
        Returns:
            list[UserWithRole]: 用户列表（带角色信息）
            
        Raises:
            ResourceNotFoundError: 项目不存在
        """
        # 验证项目是否存在
        project = await self.project_repository.get_by_id(project_id)
        if not project:
            self.logger.error(f"Project with id {project_id} not found when getting users")
            raise ResourceNotFoundError(f"项目(ID: {project_id})不存在")
        
        return await self.project_repository.get_project_users(project_id)
