"""
API依赖项，如获取当前用户、验证权限等

用于API路由的依赖注入功能
"""
import logging
from enum import Enum
from typing import Annotated, Any, Dict, Optional, Type, Union

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.data_access.cache.redis_cache import get_cache
from app.data_access.repositories.user_repository import UserRepository, get_user_repository
from app.data_access.repositories.project_repository import ProjectRepository, get_project_repository
from app.data_access.repositories.content_repository import ContentRepository, get_content_repository
from app.data_access.event_bus.event_bus import get_event_bus
from app.data_access.vector_store.vector_store import get_vector_store
from app.data_access.graph_store.graph_store import get_graph_store
from app.data_access.llm_adapter.llm_adapter import get_llm_adapter
from app.models.domain.user import User
from app.models.domain.project import Project
from app.models.domain.content import ContentItem
from app.services.interfaces.user_service import UserService
from app.services.interfaces.project_service import ProjectService
from app.services.interfaces.content_service import ContentService
from app.services.interfaces.agent_service import AgentService
from app.services.interfaces.workflow_service import WorkflowService
from app.services.interfaces.knowledge_service import KnowledgeService
from app.services.user_service import UserServiceImpl
from app.services.project_service import ProjectServiceImpl
from app.services.content_service import ContentServiceImpl
from app.services.agent_service import AgentServiceImpl
from app.services.workflow_service import WorkflowServiceImpl
from app.services.knowledge_service import KnowledgeServiceImpl
from app.knowledge_management.knowledge_facade import KnowledgeFacade
from app.api.v1.schemas.common import PaginationParams, SortOrder
from app.utils.error_handlers import ResourceNotFoundError, PermissionDeniedError

logger = logging.getLogger(__name__)

# OAuth2密码认证
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/login")


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    """获取当前用户
    
    根据令牌获取当前已验证的用户
    
    Args:
        token: 访问令牌
        
    Returns:
        User: 已验证的用户实体
        
    Raises:
        HTTPException: 如果令牌无效或用户不存在
    """
    settings = get_settings()
    user_repository = get_user_repository()
    cache = get_cache()
    
    try:
        # 尝试从缓存获取用户
        cache_key = f"user:token:{token}"
        cached_user_id = await cache.get(cache_key)
        
        if cached_user_id:
            user = await user_repository.get_by_id(cached_user_id)
            if user:
                return user
        
        # 解码和验证JWT令牌
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证凭据",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # 从数据库获取用户
        user = await user_repository.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在或已删除",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # 缓存用户ID，过期时间短于令牌
        token_expiry = payload.get("exp", 0) - payload.get("iat", 0)
        cache_expiry = max(1, token_expiry - 60)  # 比令牌早60秒过期
        await cache.set(cache_key, user_id, expiry=cache_expiry)
        
        return user
        
    except JWTError as e:
        logger.warning(f"JWT验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"认证过程中出错: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="认证过程中出错",
        )


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """获取活跃用户
    
    检查用户是否处于活跃状态
    
    Args:
        current_user: 当前用户
        
    Returns:
        User: 确认为活跃状态的用户实体
        
    Raises:
        HTTPException: 如果用户未激活
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户未激活",
        )
    return current_user


async def pagination_params(
    page: int = 1,
    page_size: int = 20,
    sort_by: Optional[str] = None,
    sort_order: SortOrder = SortOrder.desc
) -> PaginationParams:
    """解析和验证分页参数
    
    Args:
        page: 页码，从1开始
        page_size: 每页项目数
        sort_by: 排序字段
        sort_order: 排序顺序
        
    Returns:
        PaginationParams: 验证后的分页参数
        
    Raises:
        HTTPException: 如果参数值无效
    """
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="页码必须大于等于1",
        )
    
    if page_size < 1 or page_size > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="每页项目数必须在1到100之间",
        )
    
    return PaginationParams(
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order
    )


async def validate_project_access(
    project_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    project_service: Annotated[ProjectService, Depends(lambda: get_project_service())]
) -> Project:
    """验证用户对项目的访问权限
    
    Args:
        project_id: 项目ID
        current_user: 当前用户
        project_service: 项目服务
        
    Returns:
        Project: 项目信息
        
    Raises:
        HTTPException: 如果项目不存在或用户无访问权限
    """
    try:
        # 获取项目
        project = await project_service.get_project_by_id(project_id)
        
        # 检查访问权限
        if not await project_service.check_project_access(project_id, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此项目"
            )
        
        return project
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在"
        )
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此项目"
        )
    except Exception as e:
        logger.error(f"验证项目访问权限时出错: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="验证项目访问权限失败"
        )


async def validate_project_edit_access(
    project: Annotated[Project, Depends(validate_project_access)],
    current_user: Annotated[User, Depends(get_current_user)],
    project_service: Annotated[ProjectService, Depends(lambda: get_project_service())]
) -> Project:
    """验证用户对项目的编辑权限
    
    Args:
        project: 项目信息
        current_user: 当前用户
        project_service: 项目服务
        
    Returns:
        Project: 项目信息
        
    Raises:
        HTTPException: 如果用户无编辑权限
    """
    try:
        # 检查编辑权限
        if not await project_service.check_project_edit_access(project.id, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权编辑此项目"
            )
        
        return project
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权编辑此项目"
        )
    except Exception as e:
        logger.error(f"验证项目编辑权限时出错: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="验证项目编辑权限失败"
        )


async def validate_project_owner(
    project: Annotated[Project, Depends(validate_project_access)],
    current_user: Annotated[User, Depends(get_current_user)]
) -> Project:
    """验证用户是否为项目所有者
    
    Args:
        project: 项目信息
        current_user: 当前用户
        
    Returns:
        Project: 项目信息
        
    Raises:
        HTTPException: 如果用户不是项目所有者
    """
    # 检查是否为项目所有者
    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有项目所有者可以执行此操作"
        )
    
    return project


async def validate_content_access(
    content_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    content_service: Annotated[ContentService, Depends(lambda: get_content_service())]
) -> ContentItem:
    """验证用户对内容的访问权限
    
    Args:
        content_id: 内容ID
        current_user: 当前用户
        content_service: 内容服务
        
    Returns:
        ContentItem: 内容信息
        
    Raises:
        HTTPException: 如果内容不存在或用户无访问权限
    """
    try:
        # 获取内容
        content = await content_service.get_content_by_id(content_id)
        
        # 获取关联项目
        project_service = get_project_service()
        if not content.project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="内容项无关联项目"
            )
        
        # 检查项目访问权限
        if not await project_service.check_project_access(content.project_id, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此内容"
            )
        
        return content
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="内容不存在"
        )
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此内容"
        )
    except Exception as e:
        logger.error(f"验证内容访问权限时出错: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="验证内容访问权限失败"
        )


async def validate_content_edit_access(
    content: Annotated[ContentItem, Depends(validate_content_access)],
    current_user: Annotated[User, Depends(get_current_user)]
) -> ContentItem:
    """验证用户对内容的编辑权限
    
    Args:
        content: 内容信息
        current_user: 当前用户
        
    Returns:
        ContentItem: 内容信息
        
    Raises:
        HTTPException: 如果用户无编辑权限
    """
    try:
        # 获取项目服务
        project_service = get_project_service()
        
        # 检查项目编辑权限
        if not await project_service.check_project_edit_access(content.project_id, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权编辑此内容"
            )
        
        return content
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权编辑此内容"
        )
    except Exception as e:
        logger.error(f"验证内容编辑权限时出错: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="验证内容编辑权限失败"
        )


async def validate_session_access(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    workflow_service: Annotated[WorkflowService, Depends(lambda: get_workflow_service())]
) -> Dict[str, Any]:
    """验证用户对工作流会话的访问权限
    
    Args:
        session_id: 会话ID
        current_user: 当前用户
        workflow_service: 工作流服务
        
    Returns:
        Dict[str, Any]: 会话信息
        
    Raises:
        HTTPException: 如果会话不存在或用户无访问权限
    """
    try:
        # 获取会话信息
        session = await workflow_service.get_session_info(session_id)
        
        if not session:
            raise ResourceNotFoundError(f"会话 {session_id} 不存在")
        
        # 获取关联项目
        project_id = session.get("project_id")
        if not project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话无关联项目"
            )
        
        # 检查项目访问权限
        project_service = get_project_service()
        if not await project_service.check_project_access(project_id, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此会话"
            )
        
        return session
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此会话"
        )
    except Exception as e:
        logger.error(f"验证会话访问权限时出错: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="验证会话访问权限失败"
        )


async def validate_agent_access(
    agent_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    agent_service: Annotated[AgentService, Depends(lambda: get_agent_service())]
) -> Dict[str, Any]:
    """验证用户对智能体的访问权限
    
    Args:
        agent_id: 智能体ID
        current_user: 当前用户
        agent_service: 智能体服务
        
    Returns:
        Dict[str, Any]: 智能体信息
        
    Raises:
        HTTPException: 如果智能体不存在或用户无访问权限
    """
    try:
        # 获取智能体信息
        agent = await agent_service.get_agent_by_id(agent_id)
        
        # 获取关联项目
        project_id = agent.get("project_id")
        if not project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="智能体无关联项目"
            )
        
        # 检查项目访问权限
        project_service = get_project_service()
        if not await project_service.check_project_access(project_id, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此智能体"
            )
        
        return agent
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此智能体"
        )
    except Exception as e:
        logger.error(f"验证智能体访问权限时出错: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="验证智能体访问权限失败"
        )


def get_user_service() -> UserService:
    """获取用户服务实例
    
    Returns:
        UserService: 用户服务实例
    """
    # 获取依赖
    user_repository = get_user_repository()
    event_bus = get_event_bus()
    cache = get_cache()
    
    # 创建服务实例
    return UserServiceImpl(
        user_repository=user_repository,
        event_bus=event_bus,
        cache=cache
    )


def get_project_service() -> ProjectService:
    """获取项目服务实例
    
    Returns:
        ProjectService: 项目服务实例
    """
    # 获取依赖
    project_repository = get_project_repository()
    user_repository = get_user_repository()
    event_bus = get_event_bus()
    cache = get_cache()
    
    # 创建服务实例
    return ProjectServiceImpl(
        project_repository=project_repository,
        user_repository=user_repository,
        event_bus=event_bus,
        cache=cache
    )


def get_content_service() -> ContentService:
    """获取内容服务实例
    
    Returns:
        ContentService: 内容服务实例
    """
    # 获取依赖
    content_repository = get_content_repository()
    project_repository = get_project_repository()
    event_bus = get_event_bus()
    cache = get_cache()
    
    # 创建服务实例
    return ContentServiceImpl(
        content_repository=content_repository,
        project_repository=project_repository,
        event_bus=event_bus,
        cache=cache
    )


def get_agent_service() -> AgentService:
    """获取智能体服务实例
    
    Returns:
        AgentService: 智能体服务实例
    """
    # 获取依赖
    project_service = get_project_service()
    event_bus = get_event_bus()
    llm_adapter = get_llm_adapter()
    
    # 创建服务实例
    return AgentServiceImpl(
        project_service=project_service,
        event_bus=event_bus,
        llm_adapter=llm_adapter
    )


def get_workflow_service() -> WorkflowService:
    """获取工作流服务实例
    
    Returns:
        WorkflowService: 工作流服务实例
    """
    # 获取依赖
    agent_service = get_agent_service()
    event_bus = get_event_bus()
    
    # 创建简化的LangGraphManager和StateManager实例
    from app.services.workflow_service import LangGraphManager, StateManager
    
    # 创建实例
    langgraph_manager = LangGraphManager()
    state_manager = StateManager()
    
    # 创建服务实例
    return WorkflowServiceImpl(
        langgraph_manager=langgraph_manager,
        state_manager=state_manager,
        agent_service=agent_service,
        event_bus=event_bus
    )


def get_knowledge_service() -> KnowledgeService:
    """获取知识服务实例
    
    Returns:
        KnowledgeService: 知识服务实例
    """
    # 获取配置
    settings = get_settings()
    
    # 创建KnowledgeFacade
    use_enhanced = settings.knowledge_manager.use_enhanced_version
    knowledge_facade = KnowledgeFacade(settings.knowledge_manager.to_dict(), use_enhanced)
    
    # 初始化门面
    knowledge_facade.initialize()
    
    # 获取依赖
    vector_store = get_vector_store()
    graph_store = get_graph_store()
    llm_adapter = get_llm_adapter()
    event_bus = get_event_bus()
    
    # 创建服务实例
    return KnowledgeServiceImpl(
        knowledge_facade=knowledge_facade,
        vector_store=vector_store,
        graph_store=graph_store,
        llm_adapter=llm_adapter,
        event_bus=event_bus
    )
