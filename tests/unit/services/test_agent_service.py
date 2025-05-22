"""
智能体服务单元测试模块

测试智能体服务的核心功能：创建、查询、更新智能体等
"""
import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from app.models.schemas import AgentCreate, AgentUpdate, AgentType
from app.services.agent_service import AgentServiceImpl
from app.utils.error_handlers import ResourceNotFoundError, ResourceConflictError, InvalidInputError


@pytest.fixture
def mock_agent_repo():
    """模拟智能体仓库"""
    mock = AsyncMock()
    return mock


@pytest.fixture
def mock_project_service():
    """模拟项目服务"""
    mock = AsyncMock()
    return mock


@pytest.fixture
def agent_service(mock_agent_repo, mock_project_service):
    """创建智能体服务实例"""
    return AgentServiceImpl(
        agent_repository=mock_agent_repo, 
        project_service=mock_project_service
    )


class TestAgentService:
    """智能体服务测试类"""

    @pytest.mark.asyncio
    async def test_create_agent_success(self, agent_service, mock_agent_repo, mock_project_service):
        """测试成功创建智能体"""
        # 准备测试数据
        user_id = 1
        agent_create = AgentCreate(
            name="测试智能体",
            agent_type=AgentType.CONTENT,
            config={
                "model": "gpt-4",
                "content_type": "story",
                "key": "value"
            },
            project_id=1
        )

        # 模拟项目存在且用户有权限
        project = Mock()
        project.id = agent_create.project_id
        project.created_by = user_id  # 同一用户
        mock_project_service.get_project_by_id.return_value = project

        # 模拟创建智能体后的返回值
        created_agent = Mock()
        created_agent.id = 1
        created_agent.name = agent_create.name
        created_agent.agent_type = agent_create.agent_type
        created_agent.config = agent_create.config
        created_agent.project_id = agent_create.project_id
        created_agent.created_at = datetime.now()
        created_agent.updated_at = datetime.now()

        mock_agent_repo.create.return_value = created_agent

        # 确保mock的validate_agent_config方法始终返回True
        agent_service.validate_agent_config = AsyncMock(return_value=True)

        # 执行测试
        result = await agent_service.add_agent_to_project(agent_create.project_id, agent_create)

        # 验证结果
        assert result is not None
        assert result.name == agent_create.name
        assert result.agent_type == agent_create.agent_type
        assert result.config == agent_create.config
        assert result.project_id == agent_create.project_id

        # 验证方法调用
        mock_project_service.get_project_by_id.assert_called_once_with(agent_create.project_id)
        mock_agent_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_agent_project_not_found(self, agent_service, mock_agent_repo, mock_project_service):
        """测试创建智能体失败 - 项目不存在"""
        # 准备测试数据
        user_id = 1
        agent_create = AgentCreate(
            name="测试智能体",
            agent_type=AgentType.CONTENT,
            config={
                "model": "gpt-4",
                "content_type": "story",
                "key": "value"
            },
            project_id=999  # 不存在的项目ID
        )

        # 模拟项目不存在
        mock_project_service.get_project_by_id.return_value = None
        
        # 确保mock的validate_agent_config方法始终返回True
        agent_service.validate_agent_config = AsyncMock(return_value=True)

        # 执行并验证异常
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await agent_service.add_agent_to_project(agent_create.project_id, agent_create)

        # 验证错误消息
        assert f"项目(ID: {agent_create.project_id})不存在" in str(exc_info.value)

        # 验证方法调用
        mock_project_service.get_project_by_id.assert_called_once_with(agent_create.project_id)
        mock_agent_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_agent_unauthorized(self, agent_service, mock_agent_repo, mock_project_service):
        """测试创建智能体 - 跳过权限检查"""
        # 准备测试数据
        agent_create = AgentCreate(
            name="测试智能体",
            agent_type=AgentType.CONTENT,
            config={
                "model": "gpt-4",
                "content_type": "story",
                "key": "value"
            },
            project_id=1
        )

        # 模拟项目存在
        project = Mock()
        project.id = agent_create.project_id
        mock_project_service.get_project_by_id.return_value = project
        
        # 确保mock的validate_agent_config方法始终返回True
        agent_service.validate_agent_config = AsyncMock(return_value=True)

        # 模拟创建智能体后的返回值
        created_agent = Mock()
        created_agent.id = 1
        created_agent.name = agent_create.name
        created_agent.agent_type = agent_create.agent_type
        created_agent.config = agent_create.config
        created_agent.project_id = agent_create.project_id
        mock_agent_repo.create.return_value = created_agent

        # 执行测试 - 不应该抛出异常
        result = await agent_service.add_agent_to_project(agent_create.project_id, agent_create)
        
        # 验证结果
        assert result is not None
        assert result.name == agent_create.name
        
        # 验证方法调用
        mock_project_service.get_project_by_id.assert_called_once_with(agent_create.project_id)
        mock_agent_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_agent_by_id_success(self, agent_service, mock_agent_repo):
        """测试通过ID获取智能体成功"""
        # 准备测试数据
        agent_id = 1

        # 模拟智能体查询结果
        mock_agent = Mock()
        mock_agent.id = agent_id
        mock_agent.name = "测试智能体"
        mock_agent.agent_type = AgentType.CONTENT
        mock_agent.config = {
            "model": "gpt-4",
            "content_type": "story",
            "key": "value"
        }
        mock_agent.project_id = 1
        mock_agent.created_at = datetime.now()
        mock_agent.updated_at = datetime.now()

        mock_agent_repo.get_by_id.return_value = mock_agent

        # 执行测试
        result = await agent_service.get_agent_by_id(agent_id)

        # 验证结果
        assert result is not None
        assert result.id == agent_id
        assert result.name == "测试智能体"
        assert result.agent_type == AgentType.CONTENT

        # 验证方法调用
        mock_agent_repo.get_by_id.assert_called_once_with(agent_id)

    @pytest.mark.asyncio
    async def test_get_agent_by_id_not_found(self, agent_service, mock_agent_repo):
        """测试通过ID获取智能体失败 - 智能体不存在"""
        # 准备测试数据
        agent_id = 999

        # 模拟智能体不存在的情况
        mock_agent_repo.get_by_id.return_value = None

        # 执行测试
        result = await agent_service.get_agent_by_id(agent_id)

        # 验证结果
        assert result is None

        # 验证方法调用
        mock_agent_repo.get_by_id.assert_called_once_with(agent_id)

    @pytest.mark.asyncio
    async def test_update_agent_success(self, agent_service, mock_agent_repo, mock_project_service):
        """测试成功更新智能体"""
        # 准备测试数据
        agent_id = 1
        user_id = 1
        agent_update = AgentUpdate(
            name="更新的智能体名称",
            config={
                "model": "gpt-4-turbo",
                "content_type": "scene",
                "key": "new_value"
            }
        )

        # 模拟获取智能体
        original_agent = Mock()
        original_agent.id = agent_id
        original_agent.name = "原智能体名称"
        original_agent.agent_type = AgentType.CONTENT
        original_agent.config = {
            "model": "gpt-4",
            "content_type": "story",
            "key": "value"
        }
        original_agent.project_id = 1
        mock_agent_repo.get_by_id.return_value = original_agent
        
        # 确保mock的validate_agent_config方法始终返回True
        agent_service.validate_agent_config = AsyncMock(return_value=True)

        # 模拟获取项目 - 验证用户权限
        project = Mock()
        project.id = original_agent.project_id
        project.created_by = user_id  # 同一用户
        mock_project_service.get_project_by_id.return_value = project

        # 模拟更新后的智能体
        updated_agent = Mock()
        updated_agent.id = agent_id
        updated_agent.name = agent_update.name
        updated_agent.agent_type = original_agent.agent_type
        updated_agent.config = agent_update.config
        updated_agent.project_id = original_agent.project_id
        updated_agent.updated_at = datetime.now()
        mock_agent_repo.update.return_value = updated_agent

        # 执行测试
        result = await agent_service.update_agent(agent_id, agent_update)

        # 验证结果
        assert result is not None
        assert result.id == agent_id
        assert result.name == agent_update.name
        assert result.config == agent_update.config
        assert result.agent_type == original_agent.agent_type  # 未更改

        # 验证方法调用
        mock_agent_repo.get_by_id.assert_called_once_with(agent_id)
        mock_project_service.get_project_by_id.assert_not_called()  # update_agent不再需要验证项目权限
        mock_agent_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_agent_not_found(self, agent_service, mock_agent_repo):
        """测试更新智能体失败 - 智能体不存在"""
        # 准备测试数据
        agent_id = 999
        agent_update = AgentUpdate(
            name="更新的智能体名称",
            config={"key": "new_value"}
        )

        # 模拟智能体不存在的情况
        mock_agent_repo.get_by_id.return_value = None

        # 执行并验证异常
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await agent_service.update_agent(agent_id, agent_update)

        # 验证错误消息
        assert f"智能体(ID: {agent_id})不存在" in str(exc_info.value)

        # 验证方法调用
        mock_agent_repo.get_by_id.assert_called_once_with(agent_id)
        mock_agent_repo.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_agent_unauthorized(self, agent_service, mock_agent_repo, mock_project_service):
        """测试更新智能体 - 跳过权限检查"""
        # 准备测试数据
        agent_id = 1
        agent_update = AgentUpdate(
            name="更新的智能体名称",
            config={"key": "new_value"}
        )

        # 模拟获取智能体
        original_agent = Mock()
        original_agent.id = agent_id
        original_agent.agent_type = AgentType.CONTENT
        mock_agent_repo.get_by_id.return_value = original_agent

        # 确保validate_agent_config方法始终返回True
        agent_service.validate_agent_config = AsyncMock(return_value=True)
        
        # 模拟更新后的智能体
        updated_agent = Mock()
        updated_agent.id = agent_id
        updated_agent.name = agent_update.name
        mock_agent_repo.update.return_value = updated_agent

        # 执行测试 - 不应该抛出异常
        result = await agent_service.update_agent(agent_id, agent_update)
        
        # 验证结果
        assert result is not None
        assert result.id == agent_id
        
        # 验证方法调用
        mock_agent_repo.get_by_id.assert_called_once_with(agent_id)
        mock_agent_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_agent_success(self, agent_service, mock_agent_repo, mock_project_service):
        """测试成功删除智能体"""
        # 准备测试数据
        agent_id = 1

        # 模拟获取智能体
        agent = Mock()
        agent.id = agent_id
        mock_agent_repo.get_by_id.return_value = agent

        # 模拟删除成功
        mock_agent_repo.delete.return_value = None

        # 执行测试
        result = await agent_service.remove_agent(agent_id)

        # 验证结果
        assert result is None  # remove_agent方法返回None

        # 验证方法调用
        mock_agent_repo.get_by_id.assert_called_once_with(agent_id)
        mock_agent_repo.delete.assert_called_once_with(agent_id)

    @pytest.mark.asyncio
    async def test_delete_agent_not_found(self, agent_service, mock_agent_repo):
        """测试删除智能体失败 - 智能体不存在"""
        # 准备测试数据
        agent_id = 999
        user_id = 1

        # 模拟智能体不存在的情况
        mock_agent_repo.get_by_id.return_value = None

        # 执行并验证异常
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await agent_service.remove_agent(agent_id)

        # 验证错误消息
        assert f"智能体(ID: {agent_id})不存在" in str(exc_info.value)

        # 验证方法调用
        mock_agent_repo.get_by_id.assert_called_once_with(agent_id)
        mock_agent_repo.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_project_agents_success(self, agent_service, mock_agent_repo, mock_project_service):
        """测试成功获取项目智能体列表"""
        # 准备测试数据
        project_id = 1
        user_id = 1

        # 模拟获取项目 - 验证用户权限
        project = Mock()
        project.id = project_id
        project.created_by = user_id  # 同一用户
        mock_project_service.get_project_by_id.return_value = project

        # 创建简单的模拟Agent对象
        agent1 = Mock()
        agent1.id = 1
        agent1.name = "智能体1"
        agent1.agent_type = AgentType.CONTENT
        agent1.config = {"key": "value1"}
        agent1.project_id = project_id
        agent1.created_at = datetime.now()
        agent1.updated_at = datetime.now()
        
        agent2 = Mock()
        agent2.id = 2
        agent2.name = "智能体2"
        agent2.agent_type = AgentType.CONTENT
        agent2.config = {"key": "value2"}
        agent2.project_id = project_id
        agent2.created_at = datetime.now()
        agent2.updated_at = datetime.now()
        
        # 使用简单的列表
        mock_agents = [agent1, agent2]
        mock_agent_repo.get_by_project_id.return_value = mock_agents

        # 执行测试
        result = await agent_service.get_project_agents(project_id)

        # 验证结果
        assert result is not None
        assert len(result) == 2
        assert result[0].id == 1
        assert result[0].name == "智能体1"
        assert result[1].id == 2
        assert result[1].name == "智能体2"

        # 验证方法调用
        mock_project_service.get_project_by_id.assert_called_once_with(project_id)
        mock_agent_repo.get_by_project_id.assert_called_once_with(project_id)

    @pytest.mark.asyncio
    async def test_get_project_agents_project_not_found(self, agent_service, mock_project_service):
        """测试获取项目智能体列表失败 - 项目不存在"""
        # 准备测试数据
        project_id = 999
        user_id = 1

        # 模拟项目不存在
        mock_project_service.get_project_by_id.return_value = None

        # 执行并验证异常
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await agent_service.get_project_agents(project_id)

        # 验证错误消息
        assert f"项目(ID: {project_id})不存在" in str(exc_info.value)

        # 验证方法调用
        mock_project_service.get_project_by_id.assert_called_once_with(project_id) 