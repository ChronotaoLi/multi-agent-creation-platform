"""
用户管理业务逻辑实现

实现用户相关的业务逻辑功能
"""
from typing import Optional, List

from passlib.context import CryptContext
from sqlalchemy.exc import IntegrityError

from app.core.security import verify_password, get_password_hash
from app.models.schemas import UserCreate, UserUpdate, User
from app.data_access.repositories.user_repository import UserRepository
from app.utils.error_handlers import ResourceNotFoundError, ResourceConflictError


class UserServiceImpl:
    """用户服务实现
    
    实现UserService接口的业务逻辑方法
    """
    
    def __init__(
        self,
        user_repository: UserRepository,
        password_context: CryptContext
    ):
        """初始化用户服务
        
        Args:
            user_repository: 用户数据Repository
            password_context: 密码哈希上下文
        """
        self.user_repository = user_repository
        self.password_context = password_context
    
    async def create_user(self, user_data: UserCreate) -> User:
        """创建新用户
        
        Args:
            user_data: 用户创建数据
            
        Returns:
            User: 创建的用户
            
        Raises:
            ResourceConflictError: 用户名或邮箱已存在
        """
        # 检查用户名是否已存在
        existing_user = await self.user_repository.get_by_username(user_data.username)
        if existing_user:
            raise ResourceConflictError(f"用户名 '{user_data.username}' 已存在")
        
        # 检查邮箱是否已存在
        existing_user = await self.user_repository.get_by_email(user_data.email)
        if existing_user:
            raise ResourceConflictError(f"邮箱 '{user_data.email}' 已被注册")
        
        # 创建用户数据
        user_in_db = {
            "username": user_data.username,
            "email": user_data.email,
            "display_name": user_data.display_name,
            "hashed_password": get_password_hash(user_data.password),
            "is_active": True,
        }
        
        try:
            user = await self.user_repository.create(user_in_db)
            
            # 转换为返回模型
            return User(
                id=user.id,
                username=user.username,
                email=user.email,
                display_name=user.display_name,
                is_active=user.is_active,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )
        except IntegrityError:
            raise ResourceConflictError("用户名或邮箱已存在")
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """通过ID获取用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            Optional[User]: 找到的用户，如果不存在则返回None
        """
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            return None
        
        # 转换为返回模型
        return User(
            id=user.id,
            username=user.username,
            email=user.email,
            display_name=user.display_name,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """通过用户名获取用户
        
        Args:
            username: 用户名
            
        Returns:
            Optional[User]: 找到的用户，如果不存在则返回None
        """
        user = await self.user_repository.get_by_username(username)
        if not user:
            return None
        
        # 转换为返回模型
        return User(
            id=user.id,
            username=user.username,
            email=user.email,
            display_name=user.display_name,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """通过邮箱获取用户
        
        Args:
            email: 邮箱地址
            
        Returns:
            Optional[User]: 找到的用户，如果不存在则返回None
        """
        user = await self.user_repository.get_by_email(email)
        if not user:
            return None
        
        # 转换为返回模型
        return User(
            id=user.id,
            username=user.username,
            email=user.email,
            display_name=user.display_name,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
    
    async def update_user(self, user_id: int, user_data: UserUpdate) -> User:
        """更新用户信息
        
        Args:
            user_id: 用户ID
            user_data: 用户更新数据
            
        Returns:
            User: 更新后的用户
            
        Raises:
            ResourceNotFoundError: 用户不存在
            ResourceConflictError: 更新的用户名或邮箱已存在
        """
        # 检查用户是否存在
        current_user = await self.user_repository.get_by_id(user_id)
        if not current_user:
            raise ResourceNotFoundError(f"用户ID '{user_id}' 不存在")
        
        update_data = {}
        
        # 检查用户名是否已被其他用户使用
        if user_data.username and user_data.username != current_user.username:
            existing_user = await self.user_repository.get_by_username(user_data.username)
            if existing_user and existing_user.id != user_id:
                raise ResourceConflictError(f"用户名 '{user_data.username}' 已存在")
            update_data["username"] = user_data.username
        
        # 检查邮箱是否已被其他用户使用
        if user_data.email and user_data.email != current_user.email:
            existing_user = await self.user_repository.get_by_email(user_data.email)
            if existing_user and existing_user.id != user_id:
                raise ResourceConflictError(f"邮箱 '{user_data.email}' 已被注册")
            update_data["email"] = user_data.email
        
        # 更新其他字段
        if user_data.display_name is not None:
            update_data["display_name"] = user_data.display_name
        
        if user_data.is_active is not None:
            update_data["is_active"] = user_data.is_active
        
        # 如果有更新数据，则执行更新
        if update_data:
            updated_user = await self.user_repository.update(user_id, update_data)
            if not updated_user:
                raise ResourceNotFoundError(f"用户ID '{user_id}' 不存在")
            
            # 转换为返回模型
            return User(
                id=updated_user.id,
                username=updated_user.username,
                email=updated_user.email,
                display_name=updated_user.display_name,
                is_active=updated_user.is_active,
                created_at=updated_user.created_at,
                updated_at=updated_user.updated_at,
            )
        
        # 如果没有更新数据，则直接返回当前用户
        return User(
            id=current_user.id,
            username=current_user.username,
            email=current_user.email,
            display_name=current_user.display_name,
            is_active=current_user.is_active,
            created_at=current_user.created_at,
            updated_at=current_user.updated_at,
        )
    
    async def authenticate_user(self, username_or_email: str, password: str) -> Optional[User]:
        """认证用户
        
        Args:
            username_or_email: 用户名或邮箱
            password: 密码
            
        Returns:
            Optional[User]: 认证成功的用户，如果认证失败则返回None
        """
        # 根据输入判断是用户名还是邮箱
        if "@" in username_or_email:
            # 邮箱登录
            db_user = await self.user_repository.get_by_email(username_or_email)
        else:
            # 用户名登录
            db_user = await self.user_repository.get_by_username(username_or_email)
        
        # 用户不存在或者密码不匹配
        if not db_user or not verify_password(password, db_user.hashed_password):
            return None
        
        # 转换为返回模型
        return User(
            id=db_user.id,
            username=db_user.username,
            email=db_user.email,
            display_name=db_user.display_name,
            is_active=db_user.is_active,
            created_at=db_user.created_at,
            updated_at=db_user.updated_at,
        )
    
    async def is_active(self, user: User) -> bool:
        """检查用户是否活跃
        
        Args:
            user: 用户
            
        Returns:
            bool: 用户是否活跃
        """
        return user.is_active
    
    async def assign_role(self, user_id: int, role_id: int) -> None:
        """分配角色给用户
        
        Args:
            user_id: 用户ID
            role_id: 角色ID
            
        Raises:
            ResourceNotFoundError: 用户不存在
        """
        # 检查用户是否存在
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise ResourceNotFoundError(f"用户ID '{user_id}' 不存在")
        
        # 分配角色
        await self.user_repository.assign_role(user_id, role_id)
    
    async def get_user_permissions(self, user_id: int) -> list[str]:
        """获取用户权限
        
        Args:
            user_id: 用户ID
            
        Returns:
            list[str]: 权限列表
            
        Raises:
            ResourceNotFoundError: 用户不存在
        """
        # 检查用户是否存在
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise ResourceNotFoundError(f"用户ID '{user_id}' 不存在")
        
        # 获取用户角色
        roles = await self.user_repository.get_user_roles(user_id)
        
        # 从角色中提取权限（示例实现，实际需要根据角色权限模型调整）
        # 这里简单示例，假设角色有一个permissions属性
        permissions = []
        for role in roles:
            if hasattr(role, 'permissions'):
                for perm in role.permissions:
                    if perm not in permissions:
                        permissions.append(perm)
        
        return permissions
