"""
用户服务单元测试模块

测试用户服务的核心功能：创建、认证、更新等
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import pytest_asyncio
from datetime import datetime
from passlib.context import CryptContext

from app.models.schemas import UserCreate, UserUpdate
from app.services.user_service import UserServiceImpl
from app.utils.error_handlers import ResourceConflictError, ResourceNotFoundError


@pytest.fixture
def mock_user_repo():
    """模拟用户仓库"""
    mock = AsyncMock()
    # 设置默认返回值
    mock.get_by_email.return_value = None
    mock.get_by_username.return_value = None
    return mock


@pytest.fixture
def mock_password_context():
    """模拟密码上下文"""
    mock = Mock(spec=CryptContext)
    return mock


@pytest.fixture
def test_user_data():
    """测试用户数据"""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "Password123!",
        "display_name": "Test User"
    }


@pytest.fixture
def user_service(mock_user_repo, mock_password_context):
    """创建用户服务实例"""
    service = UserServiceImpl(
        user_repository=mock_user_repo,
        password_context=mock_password_context
    )
    
    # 配置mock方法
    mock_password_context.hash.return_value = "hashed_password"
    mock_password_context.verify.return_value = True
    
    return service


class TestUserService:
    """用户服务测试类"""

    @pytest.mark.asyncio
    async def test_create_user_success(self, user_service, mock_user_repo, test_user_data):
        """测试成功创建用户"""
        # 准备测试数据
        user_create = UserCreate(
            username=test_user_data["username"],
            email=test_user_data["email"],
            password=test_user_data["password"],
            display_name=test_user_data["display_name"]
        )

        # 配置模拟仓库
        mock_user_repo.get_by_username.return_value = None
        mock_user_repo.get_by_email.return_value = None
        
        # 模拟创建用户后的返回值
        created_user = Mock()
        created_user.id = 1
        created_user.username = user_create.username
        created_user.email = user_create.email
        created_user.display_name = user_create.display_name
        created_user.is_active = True
        created_user.created_at = datetime.now()
        created_user.updated_at = datetime.now()
        
        mock_user_repo.create.return_value = created_user

        # 执行测试
        result = await user_service.create_user(user_create)

        # 验证结果
        assert result is not None
        assert result.username == user_create.username
        assert result.email == user_create.email
        assert result.display_name == user_create.display_name
        assert result.is_active is True

        # 验证repository方法调用
        mock_user_repo.get_by_username.assert_called_once_with(user_create.username)
        mock_user_repo.get_by_email.assert_called_once_with(user_create.email)
        mock_user_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_username_exists(self, user_service, mock_user_repo, test_user_data):
        """测试创建用户失败 - 用户名已存在"""
        # 准备测试数据
        user_create = UserCreate(
            username=test_user_data["username"],
            email=test_user_data["email"],
            password=test_user_data["password"],
            display_name=test_user_data["display_name"]
        )

        # 模拟用户名已存在的情况
        existing_user = Mock()
        existing_user.username = user_create.username
        mock_user_repo.get_by_username.return_value = existing_user
        
        # 执行并验证异常
        with pytest.raises(ResourceConflictError) as exc_info:
            await user_service.create_user(user_create)

        # 验证错误消息
        assert f"用户名 '{user_create.username}' 已存在" in str(exc_info.value)
        
        # 验证repository方法调用
        mock_user_repo.get_by_username.assert_called_once_with(user_create.username)
        mock_user_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_user_email_exists(self, user_service, mock_user_repo, test_user_data):
        """测试创建用户失败 - 邮箱已存在"""
        # 准备测试数据
        user_create = UserCreate(
            username=test_user_data["username"],
            email=test_user_data["email"],
            password=test_user_data["password"],
            display_name=test_user_data["display_name"]
        )

        # 模拟邮箱已存在的情况
        mock_user_repo.get_by_username.return_value = None
        
        existing_user = Mock()
        existing_user.email = user_create.email
        mock_user_repo.get_by_email.return_value = existing_user
        
        # 执行并验证异常
        with pytest.raises(ResourceConflictError) as exc_info:
            await user_service.create_user(user_create)

        # 验证错误消息
        assert f"邮箱 '{user_create.email}' 已被注册" in str(exc_info.value)
        
        # 验证repository方法调用
        mock_user_repo.get_by_username.assert_called_once_with(user_create.username)
        mock_user_repo.get_by_email.assert_called_once_with(user_create.email)
        mock_user_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, user_service, mock_user_repo):
        """测试用户认证成功"""
        # 准备测试数据
        username = "testuser"
        password = "testpassword"
        
        # 模拟用户查询 - 创建具有具体属性值的Mock
        user = Mock()
        user.id = 1
        user.username = "testuser"
        user.email = "test@example.com"
        user.display_name = "Test User"
        user.is_active = True
        user.created_at = datetime.now()
        user.updated_at = datetime.now()
        user.hashed_password = "$2b$12$TestHashedPassword"  # 模拟哈希密码
        
        mock_user_repo.get_by_username.return_value = user
        
        # 修改测试 - 直接断言返回结果
        with patch('app.services.user_service.verify_password', return_value=True):
            # 执行测试
            result = await user_service.authenticate_user(username, password)
        
        # 验证结果
        assert result is not None
        assert result.username == user.username
        
        # 验证repository方法调用
        mock_user_repo.get_by_username.assert_called_once_with(username)

    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self, user_service, mock_user_repo):
        """测试用户认证失败 - 用户不存在"""
        # 准备测试数据
        username = "nonexistent"
        password = "testpassword"
        
        # 模拟用户查询 - 用户不存在
        mock_user_repo.get_by_username.return_value = None
        
        # 执行测试
        result = await user_service.authenticate_user(username, password)
        
        # 验证结果
        assert result is None
        
        # 验证repository方法调用
        mock_user_repo.get_by_username.assert_called_once_with(username)

    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self, user_service, mock_user_repo):
        """测试用户认证失败 - 密码错误"""
        # 准备测试数据
        username = "testuser"
        password = "wrongpassword"
        
        # 模拟用户查询
        user = Mock()
        user.hashed_password = "$2b$12$TestHashedPassword"  # 模拟哈希密码
        mock_user_repo.get_by_username.return_value = user
        
        # 模拟验证密码的行为 - 密码不匹配
        with patch('app.services.user_service.verify_password', return_value=False):
            # 执行测试
            result = await user_service.authenticate_user(username, password)
        
        # 验证结果
        assert result is None
        
        # 验证repository方法调用
        mock_user_repo.get_by_username.assert_called_once_with(username)

    @pytest.mark.asyncio
    async def test_update_user_success(self, user_service, mock_user_repo):
        """测试成功更新用户"""
        # 准备测试数据
        user_id = 1
        user_update = UserUpdate(
            username="newusername",
            email="newemail@example.com",
            display_name="New Name"
        )
        
        # 模拟用户查询
        user = Mock()
        user.id = user_id
        user.username = "oldusername"
        user.email = "oldemail@example.com"
        user.display_name = "Old Name"
        mock_user_repo.get_by_id.return_value = user
        
        # 确保新的用户名和邮箱不重复
        mock_user_repo.get_by_username.return_value = None
        mock_user_repo.get_by_email.return_value = None
        
        # 模拟更新后的用户 - 创建具有具体属性值的Mock
        updated_user = Mock()
        updated_user.id = user_id
        updated_user.username = user_update.username
        updated_user.email = user_update.email
        updated_user.display_name = user_update.display_name
        updated_user.is_active = True
        updated_user.created_at = datetime.now()
        updated_user.updated_at = datetime.now()
        
        mock_user_repo.update.return_value = updated_user
        
        # 执行测试
        result = await user_service.update_user(user_id, user_update)
        
        # 验证结果
        assert result is not None
        assert result.username == user_update.username
        assert result.email == user_update.email
        assert result.display_name == user_update.display_name
        
        # 验证repository方法调用
        mock_user_repo.get_by_id.assert_called_once_with(user_id)
        mock_user_repo.get_by_username.assert_called_once_with(user_update.username)
        mock_user_repo.get_by_email.assert_called_once_with(user_update.email)
        mock_user_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_not_found(self, user_service, mock_user_repo):
        """测试更新用户失败 - 用户不存在"""
        # 准备测试数据
        user_id = 999
        user_update = UserUpdate(
            username="newusername",
            email="newemail@example.com"
        )
        
        # 模拟用户查询 - 用户不存在
        mock_user_repo.get_by_id.return_value = None
        
        # 执行并验证异常
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await user_service.update_user(user_id, user_update)

        # 验证错误消息
        assert f"用户ID '{user_id}' 不存在" in str(exc_info.value)
        
        # 验证repository方法调用
        mock_user_repo.get_by_id.assert_called_once_with(user_id)
        mock_user_repo.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_user_username_conflict(self, user_service, mock_user_repo):
        """测试更新用户失败 - 用户名冲突"""
        # 准备测试数据
        user_id = 1
        user_update = UserUpdate(
            username="newusername",
            email="newemail@example.com"
        )
        
        # 模拟用户查询
        user = Mock()
        user.id = user_id
        user.username = "oldusername"
        user.email = "oldemail@example.com"
        mock_user_repo.get_by_id.return_value = user
        
        # 模拟用户名已被其他用户使用
        existing_user = Mock()
        existing_user.id = 2  # 不同的用户ID
        existing_user.username = user_update.username
        mock_user_repo.get_by_username.return_value = existing_user
        
        # 执行并验证异常
        with pytest.raises(ResourceConflictError) as exc_info:
            await user_service.update_user(user_id, user_update)

        # 验证错误消息
        assert f"用户名 '{user_update.username}' 已存在" in str(exc_info.value)
        
        # 验证repository方法调用
        mock_user_repo.get_by_id.assert_called_once_with(user_id)
        mock_user_repo.get_by_username.assert_called_once_with(user_update.username)
        mock_user_repo.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_user_by_id_success(self, user_service, mock_user_repo):
        """测试通过ID查询用户成功"""
        # 准备测试数据
        user_id = 1
        
        # 模拟用户查询 - 创建具有具体属性值的Mock
        expected_user = Mock()
        expected_user.id = user_id
        expected_user.username = "testuser"
        expected_user.email = "test@example.com"
        expected_user.display_name = "Test User"
        expected_user.is_active = True
        expected_user.created_at = datetime.now()
        expected_user.updated_at = datetime.now()
        
        mock_user_repo.get_by_id.return_value = expected_user
        
        # 执行测试
        result = await user_service.get_user_by_id(user_id)
        
        # 验证结果
        assert result is not None
        assert result.id == user_id
        assert result.username == "testuser"
        
        # 验证repository方法调用
        mock_user_repo.get_by_id.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, user_service, mock_user_repo):
        """测试通过ID查询用户失败 - 用户不存在"""
        # 准备测试数据
        user_id = 999
        
        # 模拟用户查询 - 用户不存在
        mock_user_repo.get_by_id.return_value = None
        
        # 执行测试
        result = await user_service.get_user_by_id(user_id)
        
        # 验证结果
        assert result is None
        
        # 验证repository方法调用
        mock_user_repo.get_by_id.assert_called_once_with(user_id) 