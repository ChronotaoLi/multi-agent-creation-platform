"""
API依赖项

定义API路由中使用的依赖项，如认证、服务注入等。
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from typing import Annotated, Optional

from app.core.config import get_settings
from app.services.interfaces.knowledge_service import KnowledgeService
from app.data_access.llm_adapter.base_llm_provider import LLMProvider
from app.data_access.vector_store.milvus_client import MilvusClient
from app.data_access.graph_store.neo4j_client import Neo4jClient

# 使用OAuth2PasswordBearer处理令牌认证
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

# 模拟用户模型，实际项目中应使用真实用户模型
class User:
    def __init__(self, id: int, username: str, is_active: bool = True):
        self.id = id
        self.username = username
        self.is_active = is_active

# 服务单例
_knowledge_service: Optional[KnowledgeService] = None
_llm_service: Optional[LLMProvider] = None
_vector_store: Optional[MilvusClient] = None
_graph_store: Optional[Neo4jClient] = None

async def get_knowledge_service() -> KnowledgeService:
    """
    获取知识服务实例
    
    返回:
        KnowledgeService: 知识服务实例
    """
    # 注意: 实际实现中，应该从服务容器或工厂获取服务实例
    # 这里是一个简化的示例
    global _knowledge_service
    
    if _knowledge_service is None:
        # 从依赖注入容器获取实例，这里只是占位代码
        # 实际项目中应该实现依赖注入容器
        from app.services.knowledge_service import KnowledgeServiceImpl
        _knowledge_service = KnowledgeServiceImpl()
        
    return _knowledge_service

async def get_llm_service() -> LLMProvider:
    """
    获取LLM服务实例
    
    返回:
        LLMProvider: LLM服务提供者实例
    """
    global _llm_service
    
    if _llm_service is None:
        # 从依赖注入容器获取实例，这里使用默认的OpenAI提供者
        from app.data_access.llm_adapter.openai_provider import OpenAIProvider
        _llm_service = OpenAIProvider()
        
    return _llm_service

async def get_vector_store() -> MilvusClient:
    """
    获取向量存储客户端实例
    
    返回:
        MilvusClient: 向量存储客户端
    """
    global _vector_store
    
    if _vector_store is None:
        _vector_store = MilvusClient()
        
    return _vector_store

async def get_graph_store() -> Neo4jClient:
    """
    获取图存储客户端实例
    
    返回:
        Neo4jClient: 图存储客户端
    """
    global _graph_store
    
    if _graph_store is None:
        _graph_store = Neo4jClient()
        
    return _graph_store

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    根据令牌获取当前用户
    
    参数:
        token: str - 认证令牌
        
    返回:
        User: 当前用户
        
    异常:
        HTTPException: 认证失败
    """
    # 注意: 实际实现中，应该验证JWT令牌并从数据库获取用户
    # 这里是一个简化的示例，模拟一个用户
    
    # 模拟令牌验证，实际项目中需要正确验证JWT令牌
    if token != "fake-token":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # 模拟用户，实际项目中应从数据库获取
    return User(id=1, username="test_user")

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    获取当前活跃用户，检查用户是否被禁用
    
    参数:
        current_user: User - 当前用户
        
    返回:
        User: 活跃用户
        
    异常:
        HTTPException: 用户被禁用
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user 