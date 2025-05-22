"""
知识管理工厂类

负责创建知识管理相关的实例，包括基础层和增强层
"""

import logging
from typing import Dict, Any, Optional, Union

from app.knowledge_management.hybrid_knowledge import HybridKnowledge, HybridKnowledgeManager
from app.knowledge_management.source_manager import KnowledgeSourceManager, EnhancedSourceManager
from app.knowledge_management.graph_rag_engine import GraphRAGEngine
from app.knowledge_management.agentic_rag import AgenticRAG
from app.knowledge_management.knowledge_enhancement import KnowledgeEnhancement
from app.data_access.vector_store.milvus_client import MilvusClient
from app.data_access.graph_store.neo4j_client import Neo4jClient
from app.data_access.llm_adapter.base_llm_provider import LLMProvider
from app.data_access.vector_store.embeddings import EmbeddingService
from app.data_access.cache.redis_client import RedisClient
from app.data_access.event_bus.redis_streams import RedisStreamsEventBus
from app.core.config import get_settings

logger = logging.getLogger(__name__)

# 获取应用配置
settings = get_settings()

class KnowledgeFactory:
    """
    知识管理工厂类
    
    负责创建和配置知识管理相关的组件实例
    """
    
    @staticmethod
    async def create_hybrid_knowledge(
        vector_store: Optional[MilvusClient] = None,
        graph_store: Optional[Neo4jClient] = None,
        embedding_service: Optional[EmbeddingService] = None,
        collection_name: str = "knowledge",
        vector_dimension: int = 1536
    ) -> HybridKnowledge:
        """
        创建基础混合知识模型实例
        
        参数:
            vector_store: Optional[MilvusClient] - 向量存储客户端
            graph_store: Optional[Neo4jClient] - 图存储客户端
            embedding_service: Optional[EmbeddingService] - 嵌入服务
            collection_name: str - 集合名称
            vector_dimension: int - 向量维度
            
        返回:
            HybridKnowledge - 混合知识模型实例
        """
        # 创建默认客户端（如果未提供）
        if vector_store is None:
            vector_store = MilvusClient()
        
        if graph_store is None:
            graph_store = Neo4jClient()
        
        if embedding_service is None:
            embedding_service = EmbeddingService()
        
        # 创建混合知识模型
        hybrid_knowledge = HybridKnowledge(
            vector_store=vector_store,
            graph_store=graph_store,
            embedding_service=embedding_service,
            collection_name=collection_name,
            vector_dimension=vector_dimension
        )
        
        # 初始化
        await hybrid_knowledge.initialize()
        
        return hybrid_knowledge
    
    @staticmethod
    async def create_hybrid_knowledge_manager(
        vector_store: Optional[MilvusClient] = None,
        graph_store: Optional[Neo4jClient] = None,
        embedding_service: Optional[EmbeddingService] = None,
        redis_client: Optional[RedisClient] = None,
        collection_name: str = "knowledge",
        vector_dimension: int = 1536,
        batch_size: int = 100
    ) -> HybridKnowledgeManager:
        """
        创建增强版混合知识管理器实例
        
        参数:
            vector_store: Optional[MilvusClient] - 向量存储客户端
            graph_store: Optional[Neo4jClient] - 图存储客户端
            embedding_service: Optional[EmbeddingService] - 嵌入服务
            redis_client: Optional[RedisClient] - Redis客户端
            collection_name: str - 集合名称
            vector_dimension: int - 向量维度
            batch_size: int - 批处理大小
            
        返回:
            HybridKnowledgeManager - 混合知识管理器实例
        """
        # 创建默认客户端（如果未提供）
        if vector_store is None:
            vector_store = MilvusClient()
        
        if graph_store is None:
            graph_store = Neo4jClient()
        
        if embedding_service is None:
            embedding_service = EmbeddingService()
        
        if redis_client is None:
            redis_client = RedisClient()
        
        # 创建混合知识管理器
        knowledge_manager = HybridKnowledgeManager(
            vector_store=vector_store,
            graph_store=graph_store,
            embedding_service=embedding_service,
            redis_client=redis_client,
            collection_name=collection_name,
            vector_dimension=vector_dimension,
            batch_size=batch_size
        )
        
        # 初始化
        await knowledge_manager.initialize()
        
        return knowledge_manager
    
    @staticmethod
    async def create_source_manager(
        vector_store: Optional[MilvusClient] = None,
        graph_store: Optional[Neo4jClient] = None,
        embedding_service: Optional[EmbeddingService] = None,
        use_enhanced: bool = True,
        event_producer: Optional[RedisStreamsEventBus] = None,
        enable_versioning: bool = True
    ) -> Union[KnowledgeSourceManager, EnhancedSourceManager]:
        """
        创建信息源管理器实例
        
        参数:
            vector_store: Optional[MilvusClient] - 向量存储客户端
            graph_store: Optional[Neo4jClient] - 图存储客户端
            embedding_service: Optional[EmbeddingService] - 嵌入服务
            use_enhanced: bool - 是否使用增强版
            event_producer: Optional[RedisStreamsEventBus] - 事件生产者
            enable_versioning: bool - 是否启用版本控制
            
        返回:
            Union[KnowledgeSourceManager, EnhancedSourceManager] - 信息源管理器实例
        """
        # 创建默认客户端（如果未提供）
        if vector_store is None:
            vector_store = MilvusClient()
        
        if graph_store is None:
            graph_store = Neo4jClient()
        
        if embedding_service is None:
            embedding_service = EmbeddingService()
        
        # 创建混合知识模型
        hybrid_knowledge = await KnowledgeFactory.create_hybrid_knowledge(
            vector_store=vector_store,
            graph_store=graph_store,
            embedding_service=embedding_service
        )
        
        # 根据需要创建基础版或增强版
        if use_enhanced:
            source_manager = EnhancedSourceManager(
                hybrid_knowledge=hybrid_knowledge,
                embedding_service=embedding_service,
                event_producer=event_producer
            )
        else:
            source_manager = KnowledgeSourceManager(
                hybrid_knowledge=hybrid_knowledge,
                embedding_service=embedding_service
            )
        
        return source_manager
    
    @staticmethod
    async def create_knowledge_enhancement(
        vector_store: Optional[MilvusClient] = None,
        graph_store: Optional[Neo4jClient] = None,
        llm_service: Optional[LLMProvider] = None,
        embedding_service: Optional[EmbeddingService] = None,
        redis_client: Optional[RedisClient] = None,
        event_producer: Optional[RedisStreamsEventBus] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> KnowledgeEnhancement:
        """
        创建知识管理增强层实例
        
        参数:
            vector_store: Optional[MilvusClient] - 向量存储客户端
            graph_store: Optional[Neo4jClient] - 图存储客户端
            llm_service: Optional[LLMProvider] - LLM服务提供者
            embedding_service: Optional[EmbeddingService] - 嵌入服务
            redis_client: Optional[RedisClient] - Redis客户端
            event_producer: Optional[RedisStreamsEventBus] - 事件生产者
            config: Optional[Dict[str, Any]] - 配置参数
            
        返回:
            KnowledgeEnhancement - 知识管理增强层实例
        """
        # 创建默认客户端（如果未提供）
        if vector_store is None:
            vector_store = MilvusClient()
        
        if graph_store is None:
            graph_store = Neo4jClient()
        
        if llm_service is None:
            from app.data_access.llm_adapter.openai_provider import OpenAIProvider
            llm_service = OpenAIProvider()
        
        if embedding_service is None:
            embedding_service = EmbeddingService()
        
        if redis_client is None:
            redis_client = RedisClient()
        
        # 配置参数
        config = config or {}
        default_config = {
            "collection_name": "knowledge",
            "vector_dimension": 1536,
            "batch_size": 100,
            "max_context_length": 4000,
            "max_sub_queries": 5,
            "enable_query_caching": True,
            "enable_reasoning": True,
            "detailed_analysis": True,
            "max_iterations": 3,
            "confidence_threshold": 0.7,
            "debug_mode": False,
            "metadata_cache_ttl": 3600,
            "enable_versioning": True,
            "max_relation_depth": 3
        }
        
        # 合并配置
        merged_config = {**default_config, **config}
        
        # 创建知识管理增强层
        enhancement = KnowledgeEnhancement(
            vector_store=vector_store,
            graph_store=graph_store,
            llm_service=llm_service,
            embedding_service=embedding_service,
            redis_client=redis_client,
            event_producer=event_producer,
            config=merged_config
        )
        
        # 初始化
        await enhancement.initialize()
        
        return enhancement 