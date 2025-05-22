"""
项目服务接口

定义项目相关的业务逻辑接口
"""
from typing import Optional, Protocol, List, Tuple

from app.models.schemas import ProjectCreate, ProjectUpdate, Project, UserWithRole


class ProjectService(Protocol):
    """项目服务接口
    
    定义项目相关的业务逻辑方法
    """
    
    async def create_project(self, project_data: ProjectCreate, user_id: int) -> Project:
        """创建新项目
        
        Args:
            project_data: 项目创建数据
            user_id: 创建者用户ID
            
        Returns:
            Project: 创建的项目
            
        Raises:
            ResourceNotFoundError: 用户不存在
        """
        ...
    
    async def get_project_by_id(self, project_id: int) -> Optional[Project]:
        """通过ID获取项目
        
        Args:
            project_id: 项目ID
            
        Returns:
            Optional[Project]: 找到的项目，如果不存在则返回None
        """
        ...
    
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
        ...
    
    async def update_project(self, project_id: int, project_data: ProjectUpdate) -> Project:
        """更新项目
        
        Args:
            project_id: 项目ID
            project_data: 项目更新数据
            
        Returns:
            Project: 更新后的项目
            
        Raises:
            ResourceNotFoundError: 项目不存在
        """
        ...
    
    async def delete_project(self, project_id: int) -> None:
        """删除项目
        
        Args:
            project_id: 项目ID
            
        Raises:
            ResourceNotFoundError: 项目不存在
        """
        ...
    
    async def check_user_project_access(self, project_id: int, user_id: int, required_role: Optional[str] = None) -> bool:
        """检查用户是否有项目访问权限
        
        Args:
            project_id: 项目ID
            user_id: 用户ID
            required_role: 所需角色，如果为None，则只检查是否有任何权限
            
        Returns:
            bool: 是否有访问权限
        """
        ...
    
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
        ...
    
    async def get_project_users(self, project_id: int) -> list[UserWithRole]:
        """获取项目用户列表
        
        Args:
            project_id: 项目ID
            
        Returns:
            list[UserWithRole]: 用户列表（带角色信息）
            
        Raises:
            ResourceNotFoundError: 项目不存在
        """
        ...
