"""
项目服务单元测试模块

测试项目服务的核心功能：创建、查询、更新项目等
"""
import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from app.models.schemas import ProjectCreate, ProjectUpdate
from app.services.project_service import ProjectServiceImpl
from app.utils.error_handlers import ResourceNotFoundError, ResourceConflictError


@pytest.fixture
def mock_project_repo():
    """模拟项目仓库"""
    mock = AsyncMock()
    return mock


@pytest.fixture
def mock_user_repo():
    """模拟用户仓库"""
    mock = AsyncMock()
    return mock


@pytest.fixture
def mock_event_bus():
    """模拟事件总线"""
    mock = AsyncMock()
    return mock


@pytest.fixture
def project_service(mock_project_repo, mock_user_repo, mock_event_bus):
    """创建项目服务实例"""
    return ProjectServiceImpl(
        project_repository=mock_project_repo,
        user_repository=mock_user_repo,
        event_bus=mock_event_bus
    )


class TestProjectService:
    """项目服务测试类"""

    @pytest.mark.asyncio
    async def test_create_project_success(self, project_service, mock_project_repo, mock_user_repo):
        """测试成功创建项目"""
        # 准备测试数据
        user_id = 1
        project_create = ProjectCreate(
            title="测试项目",
            description="这是一个测试项目",
            project_type="story"
        )

        # 模拟用户存在
        mock_user = Mock()
        mock_user.id = user_id
        mock_user_repo.get_by_id.return_value = mock_user

        # 模拟创建项目后的返回值
        created_project = Mock()
        created_project.id = 1
        created_project.title = project_create.title
        created_project.description = project_create.description
        created_project.project_type = project_create.project_type
        created_project.created_by = user_id
        created_project.status = "active"
        created_project.created_at = datetime.now()
        created_project.updated_at = datetime.now()

        mock_project_repo.create.return_value = created_project

        # 执行测试
        result = await project_service.create_project(project_create, user_id)

        # 验证结果
        assert result is not None
        assert result.title == project_create.title
        assert result.description == project_create.description
        assert result.project_type == project_create.project_type
        assert result.created_by == user_id

        # 验证repository方法调用
        mock_user_repo.get_by_id.assert_called_once_with(user_id)
        mock_project_repo.create.assert_called_once()
        mock_project_repo.add_user_to_project.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_project_by_id_success(self, project_service, mock_project_repo):
        """测试通过ID获取项目成功"""
        # 准备测试数据
        project_id = 1

        # 模拟项目查询结果
        mock_project = Mock()
        mock_project.id = project_id
        mock_project.title = "测试项目"
        mock_project.description = "这是一个测试项目"
        mock_project.project_type = "story"
        mock_project.status = "active"
        mock_project.created_by = 1
        mock_project.created_at = datetime.now()
        mock_project.updated_at = datetime.now()

        mock_project_repo.get_by_id.return_value = mock_project

        # 执行测试
        result = await project_service.get_project_by_id(project_id)

        # 验证结果
        assert result is not None
        assert result.id == project_id
        assert result.title == "测试项目"
        assert result.description == "这是一个测试项目"

        # 验证repository方法调用
        mock_project_repo.get_by_id.assert_called_once_with(project_id)

    @pytest.mark.asyncio
    async def test_get_project_by_id_not_found(self, project_service, mock_project_repo):
        """测试通过ID获取项目失败 - 项目不存在"""
        # 准备测试数据
        project_id = 999

        # 模拟项目不存在的情况
        mock_project_repo.get_by_id.return_value = None

        # 执行测试
        result = await project_service.get_project_by_id(project_id)

        # 验证结果
        assert result is None

        # 验证repository方法调用
        mock_project_repo.get_by_id.assert_called_once_with(project_id)

    @pytest.mark.asyncio
    async def test_update_project_success(self, project_service, mock_project_repo):
        """测试成功更新项目"""
        # 准备测试数据
        project_id = 1
        project_update = ProjectUpdate(
            title="更新的标题",
            description="更新的描述",
            status="completed"
        )

        # 模拟查询结果 - 项目存在
        original_project = Mock()
        original_project.id = project_id
        original_project.title = "原标题"
        original_project.description = "原描述"
        original_project.status = "active"
        original_project.created_by = 1

        mock_project_repo.get_by_id.return_value = original_project

        # 模拟更新后的项目
        updated_project = Mock()
        updated_project.id = project_id
        updated_project.title = project_update.title
        updated_project.description = project_update.description
        updated_project.status = project_update.status
        updated_project.created_by = 1
        updated_project.updated_at = datetime.now()

        mock_project_repo.update.return_value = updated_project

        # 执行测试
        result = await project_service.update_project(project_id, project_update)

        # 验证结果
        assert result is not None
        assert result.id == project_id
        assert result.title == project_update.title
        assert result.description == project_update.description
        assert result.status == project_update.status

        # 验证repository方法调用
        mock_project_repo.get_by_id.assert_called_once_with(project_id)
        mock_project_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_project_not_found(self, project_service, mock_project_repo):
        """测试更新项目失败 - 项目不存在"""
        # 准备测试数据
        project_id = 999
        project_update = ProjectUpdate(
            title="更新的标题",
            description="更新的描述"
        )

        # 模拟项目不存在的情况
        mock_project_repo.get_by_id.return_value = None

        # 执行并验证异常
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await project_service.update_project(project_id, project_update)

        # 验证错误消息
        assert f"项目(ID: {project_id})不存在" in str(exc_info.value)

        # 验证repository方法调用
        mock_project_repo.get_by_id.assert_called_once_with(project_id)
        mock_project_repo.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_project_unauthorized(self, project_service, mock_project_repo):
        """测试更新项目失败 - 用户无权限"""
        # 此测试不再适用，因为ProjectServiceImpl中update_project不再检查用户权限
        # 跳过这个测试
        pytest.skip("ProjectServiceImpl中update_project不再检查用户权限")

    @pytest.mark.asyncio
    async def test_delete_project_success(self, project_service, mock_project_repo):
        """测试成功删除项目"""
        # 准备测试数据
        project_id = 1

        # 模拟查询结果 - 项目存在
        project = Mock()
        project.id = project_id
        project.created_by = 1

        mock_project_repo.get_by_id.return_value = project
        mock_project_repo.delete.return_value = True

        # 执行测试
        await project_service.delete_project(project_id)

        # 验证repository方法调用
        mock_project_repo.get_by_id.assert_called_once_with(project_id)
        mock_project_repo.delete.assert_called_once_with(project_id)

    @pytest.mark.asyncio
    async def test_delete_project_not_found(self, project_service, mock_project_repo):
        """测试删除项目失败 - 项目不存在"""
        # 准备测试数据
        project_id = 999

        # 模拟项目不存在的情况
        mock_project_repo.get_by_id.return_value = None

        # 执行并验证异常
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await project_service.delete_project(project_id)

        # 验证错误消息
        assert f"项目(ID: {project_id})不存在" in str(exc_info.value)

        # 验证repository方法调用
        mock_project_repo.get_by_id.assert_called_once_with(project_id)
        mock_project_repo.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_user_projects_success(self, project_service, mock_project_repo, mock_user_repo):
        """测试成功获取用户项目列表"""
        # 准备测试数据
        user_id = 1
        skip = 0
        limit = 10

        # 模拟用户存在
        mock_user = Mock()
        mock_user.id = user_id
        mock_user_repo.get_by_id.return_value = mock_user

        # 模拟用户项目列表
        mock_projects = [
            Mock(
                id=1,
                title="项目1",
                description="描述1",
                project_type="story",
                status="active",
                created_by=user_id,
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            Mock(
                id=2,
                title="项目2",
                description="描述2",
                project_type="novel",
                status="completed",
                created_by=user_id,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        ]
        total_count = len(mock_projects)

        # Update the mock to use get_by_user and expect new parameters
        mock_project_repo.get_by_user.return_value = (mock_projects, total_count)

        # 执行测试
        result, count = await project_service.get_projects_by_user(user_id, skip, limit) # project_type and status default to None

        # 验证结果
        assert result is not None
        assert len(result) == 2
        assert result[0].id == 1
        assert result[0].title == "项目1"
        assert result[1].id == 2
        assert result[1].title == "项目2"
        assert count == total_count

        # 验证repository方法调用
        mock_user_repo.get_by_id.assert_called_once_with(user_id)
        # Update assertion to check for the new parameters
        mock_project_repo.get_by_user.assert_called_once_with(
            user_id=user_id,
            skip=skip,
            limit=limit,
            project_type=None,  # Explicitly check for None
            status=None         # Explicitly check for None
        )

    @pytest.mark.asyncio
    async def test_get_user_projects_empty(self, project_service, mock_project_repo, mock_user_repo):
        """测试获取用户项目列表 - 无项目"""
        # 准备测试数据
        user_id = 1
        skip = 0
        limit = 10

        # 模拟用户存在
        mock_user = Mock()
        mock_user.id = user_id
        mock_user_repo.get_by_id.return_value = mock_user

        # 模拟用户无项目的情况
        # Update the mock to use get_by_user
        mock_project_repo.get_by_user.return_value = ([], 0)

        # 执行测试
        result, count = await project_service.get_projects_by_user(user_id, skip, limit) # project_type and status default to None

        # 验证结果
        assert result == []
        assert count == 0

        # 验证repository方法调用
        mock_user_repo.get_by_id.assert_called_once_with(user_id)
        # Update assertion to check for the new parameters
        mock_project_repo.get_by_user.assert_called_once_with(
            user_id=user_id,
            skip=skip,
            limit=limit,
            project_type=None,
            status=None
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "filter_project_type, filter_status",
        [
            ("story", "active"),
            ("novel", None),
            (None, "completed"),
            (None, None), # Covered by existing tests but good to have explicitly
        ],
    )
    async def test_get_projects_by_user_with_filters(
        self,
        project_service,
        mock_project_repo,
        mock_user_repo,
        filter_project_type,
        filter_status,
    ):
        user_id = 1
        skip = 0
        limit = 10

        mock_user = Mock()
        mock_user.id = user_id
        mock_user_repo.get_by_id.return_value = mock_user

        # Mock the repository's get_by_user method to return an empty list and 0 count
        mock_project_repo.get_by_user.return_value = ([], 0)

        await project_service.get_projects_by_user(
            user_id, skip, limit, project_type=filter_project_type, status=filter_status
        )

        mock_user_repo.get_by_id.assert_called_once_with(user_id)
        mock_project_repo.get_by_user.assert_called_once_with(
            user_id=user_id,
            skip=skip,
            limit=limit,
            project_type=filter_project_type,
            status=filter_status,
        )