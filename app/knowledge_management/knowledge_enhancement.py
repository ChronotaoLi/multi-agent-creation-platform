"""
知识管理增强层接口

整合GraphRAG、AgenticRAG、增强版信息源管理等功能
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

from app.knowledge_management.graph_rag_engine import GraphRAGEngine
from app.knowledge_management.agentic_rag import AgenticRAG
from app.knowledge_management.query_planner import QueryPlanner
from app.knowledge_management.result_synthesizer import ResultSynthesizer
from app.knowledge_management.self_critique_agent import SelfCritiqueAgent
from app.knowledge_management.source_manager import EnhancedSourceManager
from app.knowledge_management.hybrid_knowledge import HybridKnowledgeManager
from app.data_access.vector_store.milvus_client import MilvusClient
from app.data_access.graph_store.neo4j_client import Neo4jClient
from app.data_access.llm_adapter.base_llm_provider import LLMProvider
from app.data_access.vector_store.embeddings import EmbeddingService
from app.data_access.cache.redis_client import RedisClient
from app.data_access.event_bus.redis_streams import RedisStreamsEventBus
from app.models.domain.knowledge_models import (
    KnowledgeItem, KnowledgeQuery, KnowledgeResponse, 
    EnhancedKnowledgeResponse, KnowledgeFeedback
)
from app.api.v1.schemas.knowledge_enhancement import (
    EnhancedQueryRequest, QueryPlanningRequest, KnowledgeSourceCreate,
    RelationUpdate, FormatConversionRequest, ContentType, RetrievalStrategy
)
from app.core.config import get_settings

logger = logging.getLogger(__name__)

# 获取应用配置
settings = get_settings()

class KnowledgeEnhancement:
    """
    知识管理增强层主接口
    
    整合GraphRAG、AgenticRAG、增强版信息源管理等功能，提供统一的接口
    """
    
    def __init__(
        self,
        vector_store: MilvusClient,
        graph_store: Neo4jClient,
        llm_service: LLMProvider,
        embedding_service: EmbeddingService,
        redis_client: Optional[RedisClient] = None,
        event_producer: Optional[RedisStreamsEventBus] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化知识管理增强层
        
        参数:
            vector_store: MilvusClient - 向量存储客户端
            graph_store: Neo4jClient - 图存储客户端
            llm_service: LLMProvider - LLM服务提供者
            embedding_service: EmbeddingService - 嵌入服务
            redis_client: Optional[RedisClient] - Redis客户端
            event_producer: Optional[RedisStreamsEventBus] - 事件生产者
            config: Optional[Dict[str, Any]] - 配置参数
        """
        self.config = config or {}
        self.redis_client = redis_client or RedisClient()
        
        # 初始化混合知识管理器
        self.hybrid_knowledge = HybridKnowledgeManager(
            vector_store=vector_store,
            graph_store=graph_store,
            embedding_service=embedding_service,
            redis_client=self.redis_client,
            collection_name=self.config.get("collection_name", "knowledge"),
            vector_dimension=self.config.get("vector_dimension", 1536),
            batch_size=self.config.get("batch_size", 100)
        )
        
        # 初始化GraphRAG引擎
        self.graph_rag = GraphRAGEngine(
            hybrid_knowledge=self.hybrid_knowledge,
            llm_service=llm_service,
            redis_client=self.redis_client,
            max_context_length=self.config.get("max_context_length", 4000)
        )
        
        # 初始化查询规划器
        self.query_planner = QueryPlanner(
            llm_service=llm_service,
            max_sub_queries=self.config.get("max_sub_queries", 5),
            enable_caching=self.config.get("enable_query_caching", True)
        )
        
        # 初始化结果合成器
        self.result_synthesizer = ResultSynthesizer(
            llm_service=llm_service,
            max_context_length=self.config.get("max_context_length", 8000),
            enable_reasoning=self.config.get("enable_reasoning", True)
        )
        
        # 初始化自我批评代理
        self.self_critique = SelfCritiqueAgent(
            llm_service=llm_service,
            detailed_analysis=self.config.get("detailed_analysis", True)
        )
        
        # 初始化AgenticRAG
        self.agentic_rag = AgenticRAG(
            graph_rag_engine=self.graph_rag,
            llm_service=llm_service,
            query_planner=self.query_planner,
            result_synthesizer=self.result_synthesizer,
            self_critique_agent=self.self_critique,
            max_iterations=self.config.get("max_iterations", 3),
            confidence_threshold=self.config.get("confidence_threshold", 0.7),
            debug_mode=self.config.get("debug_mode", False)
        )
        
        # 初始化增强版信息源管理器
        self.source_manager = EnhancedSourceManager(
            hybrid_knowledge=self.hybrid_knowledge,
            embedding_service=embedding_service,
            event_producer=event_producer
        )
        
        self.initialized = False
    
    async def initialize(self) -> None:
        """
        初始化所有组件
        """
        if not self.initialized:
            await self.hybrid_knowledge.initialize()
            self.initialized = True
            logger.info("KnowledgeEnhancement层初始化完成")
    
    async def enhanced_query(
        self, 
        request: EnhancedQueryRequest
    ) -> EnhancedKnowledgeResponse:
        """
        执行增强查询
        
        参数:
            request: EnhancedQueryRequest - 增强查询请求
            
        返回:
            EnhancedKnowledgeResponse - 增强查询响应
        """
        await self.initialize()
        
        # 解析查询参数
        context = {
            "session_id": request.session_id,
            "include_reasoning": request.include_reasoning,
            "include_context": request.include_context
        }
        
        start_time = datetime.now()
        
        # 使用智能体RAG或普通GraphRAG
        if request.use_agentic_rag:
            # 使用智能体RAG
            result = await self.agentic_rag.process_query(
                query=request.query,
                context=context,
                session_id=request.session_id
            )
            
            # 提取相关信息
            answer = result["answer"]
            confidence = result["confidence"]
            metadata = result["metadata"]
            iteration_count = metadata.get("iterations", 1)
            
            # 准备知识项
            context_items = []
            if request.include_context and "query_trace" in result:
                trace = result["query_trace"]
                if "retrieval_results" in trace and trace["retrieval_results"]:
                    # 从最后一次迭代获取检索结果
                    last_retrieval = trace["retrieval_results"][-1]
                    for result_group in last_retrieval:
                        if "result" in result_group and "context" in result_group["result"]:
                            for ctx in result_group["result"]["context"]:
                                if isinstance(ctx, dict) and "content" in ctx:
                                    item = KnowledgeItem(
                                        id=ctx.get("id", f"ctx_{len(context_items)}"),
                                        content=ctx["content"],
                                        metadata={k: v for k, v in ctx.items() if k not in ["id", "content"]}
                                    )
                                    context_items.append(item)
            
            # 准备质量指标
            quality_metrics = None
            if "critique_steps" in result.get("query_trace", {}) and result["query_trace"]["critique_steps"]:
                last_critique = result["query_trace"]["critique_steps"][-1]
                if "scores" in last_critique:
                    from app.api.v1.schemas.knowledge_enhancement import QualityMetrics
                    quality_metrics = QualityMetrics(
                        relevance=last_critique["scores"].get("relevance", 0),
                        coherence=last_critique["scores"].get("coherence", 0),
                        information_accuracy=last_critique["scores"].get("information_accuracy", 0),
                        completeness=last_critique["scores"].get("completeness", 0),
                        objectivity=last_critique["scores"].get("objectivity", 0),
                        clarity=last_critique["scores"].get("clarity", 0),
                        overall_score=last_critique.get("overall_score", 0)
                    )
            
            # 准备推理过程
            reasoning = None
            if request.include_reasoning and "query_trace" in result:
                if "synthesis_steps" in result["query_trace"] and result["query_trace"]["synthesis_steps"]:
                    last_synthesis = result["query_trace"]["synthesis_steps"][-1]
                    reasoning = last_synthesis.get("reasoning", "")
        else:
            # 使用普通GraphRAG
            strategy = request.strategy if isinstance(request.strategy, str) else request.strategy.value
            result = await self.graph_rag.query(
                query_text=request.query,
                strategy=strategy,
                params={"top_k": request.limit}
            )
            
            # 提取相关信息
            answer = result["answer"]
            confidence = result.get("quality_score", 0.5)
            
            # 准备知识项
            context_items = []
            if request.include_context and "context" in result:
                for i, ctx in enumerate(result["context"]):
                    if isinstance(ctx, dict) and "content" in ctx:
                        item = KnowledgeItem(
                            id=ctx.get("id", f"ctx_{i}"),
                            content=ctx["content"],
                            metadata={k: v for k, v in ctx.items() if k not in ["id", "content"]}
                        )
                        context_items.append(item)
            
            # 这种情况下没有详细的质量指标和推理过程
            quality_metrics = None
            reasoning = None
            iteration_count = 1
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        # 生成查询ID
        import uuid
        query_id = str(uuid.uuid4())
        
        # 构建响应
        return EnhancedKnowledgeResponse(
            query_id=query_id,
            original_query=request.query,
            answer=answer,
            confidence=confidence,
            quality_metrics=quality_metrics,
            reasoning=reasoning if request.include_reasoning else None,
            context_items=context_items if request.include_context else None,
            retrieval_strategy=request.strategy,
            execution_time=execution_time,
            iteration_count=iteration_count,
            session_id=request.session_id
        )
    
    async def plan_query(
        self, 
        request: QueryPlanningRequest
    ) -> Dict[str, Any]:
        """
        规划查询执行
        
        参数:
            request: QueryPlanningRequest - 查询规划请求
            
        返回:
            Dict[str, Any] - 查询规划结果
        """
        await self.initialize()
        
        # 生成查询ID
        import uuid
        query_id = str(uuid.uuid4())
        
        # 设置上下文
        context = request.context or {}
        
        # 执行查询规划
        plan = await self.query_planner.plan_query(
            query=request.query,
            context=context
        )
        
        # 构建响应
        from app.api.v1.schemas.knowledge_enhancement import QueryPlanResponse, QueryPlan, SubQuery
        
        # 转换子查询
        sub_queries = []
        for sq in plan["sub_queries"]:
            sub_query = SubQuery(
                query=sq["query"],
                strategy=sq.get("strategy", "default"),
                params=sq.get("params", {}),
                explanation=sq.get("explanation")
            )
            sub_queries.append(sub_query)
        
        # 构建查询计划
        query_plan = QueryPlan(
            sub_queries=sub_queries,
            reasoning=plan.get("reasoning")
        )
        
        # 构建最终响应
        response = {
            "query_id": query_id,
            "original_query": request.query,
            "plan": query_plan.model_dump()
        }
        
        return response
    
    async def standard_search(
        self, 
        query: str, 
        limit: int = 10, 
        filters: Optional[Dict[str, Any]] = None,
        strategy: str = "hybrid"
    ) -> KnowledgeResponse:
        """
        执行标准知识搜索
        
        参数:
            query: str - 查询文本
            limit: int - 结果限制数量
            filters: Optional[Dict[str, Any]] - 过滤条件
            strategy: str - 检索策略
            
        返回:
            KnowledgeResponse - 标准搜索响应
        """
        await self.initialize()
        
        # 执行搜索
        results = await self.hybrid_knowledge.search(
            query=query,
            limit=limit,
            filters=filters,
            strategy=strategy
        )
        
        # 转换为知识项列表
        items = []
        for result in results:
            item = KnowledgeItem(
                id=str(result.get("id", "")),
                content=result.get("content", ""),
                metadata={k: v for k, v in result.items() if k not in ["id", "content"]}
            )
            items.append(item)
        
        # 构建响应
        response = KnowledgeResponse(
            items=items,
            total=len(items),
            query=query,
            metadata={
                "strategy": strategy,
                "filters": filters,
                "limit": limit
            }
        )
        
        return response
    
    async def add_knowledge_source(
        self, 
        request: KnowledgeSourceCreate
    ) -> Dict[str, Any]:
        """
        添加知识源
        
        参数:
            request: KnowledgeSourceCreate - 创建知识源请求
            
        返回:
            Dict[str, Any] - 创建结果
        """
        await self.initialize()
        
        # 准备元数据
        metadata = EnhancedSourceMetadata(
            source_id="",  # 自动生成
            source_type=request.metadata.source_type,
            content_type=request.metadata.content_type,
            title=request.metadata.title,
            description=request.metadata.description,
            authors=request.metadata.authors,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            version=request.metadata.version,
            tags=request.metadata.tags,
            language=request.metadata.language,
            license=request.metadata.license,
            url=request.metadata.url,
            additional_metadata=request.metadata.additional_metadata
        )
        
        # 添加知识源
        source_id = await self.source_manager.add_source(
            content=request.content,
            metadata=metadata,
            chunks=request.chunks,
            relations=request.relations,
            validate=request.validate_content
        )
        
        # 获取完整的源数据
        source_data = await self.source_manager.get_source(source_id)
        
        # 如果有关系，获取关系数据
        if request.relations:
            source_data = await self.source_manager.get_source_with_relations(source_id)
        
        # 构建响应
        from app.api.v1.schemas.knowledge_enhancement import KnowledgeSourceResponse
        
        response = {
            "source_id": source_id,
            "content": source_data.get("content", ""),
            "metadata": source_data.get("metadata", {}),
            "chunks": source_data.get("chunks"),
            "relations_data": source_data.get("relations_data")
        }
        
        return response
    
    async def update_source_relations(
        self, 
        source_id: str, 
        updates: RelationUpdate
    ) -> Dict[str, Any]:
        """
        更新信息源关系
        
        参数:
            source_id: str - 信息源ID
            updates: RelationUpdate - 关系更新
            
        返回:
            Dict[str, Any] - 更新结果
        """
        await self.initialize()
        
        # 准备关系更新
        relations_to_add = None
        if updates.relations_to_add:
            relations_to_add = [
                {
                    "type": rel.type if isinstance(rel.type, str) else rel.type.value,
                    "target_id": rel.target_id
                }
                for rel in updates.relations_to_add
            ]
        
        relations_to_remove = None
        if updates.relations_to_remove:
            relations_to_remove = [
                {
                    "type": rel.type if isinstance(rel.type, str) else rel.type.value,
                    "target_id": rel.target_id
                }
                for rel in updates.relations_to_remove
            ]
        
        # 更新关系
        success = await self.source_manager.update_source_relations(
            source_id=source_id,
            relations_to_add=relations_to_add,
            relations_to_remove=relations_to_remove
        )
        
        # 获取更新后的元数据
        metadata = await self.source_manager.get_source_metadata(source_id)
        updated_relations = {}
        
        if metadata and hasattr(metadata, "get_relations"):
            updated_relations = metadata.get_relations()
        elif metadata and hasattr(metadata, "to_dict"):
            metadata_dict = metadata.to_dict()
            updated_relations = metadata_dict.get("relations", {})
        
        # 构建响应
        from app.api.v1.schemas.knowledge_enhancement import RelationUpdateResponse
        
        response = {
            "source_id": source_id,
            "success": success,
            "message": "关系更新成功" if success else "关系更新失败",
            "updated_relations": updated_relations
        }
        
        return response
    
    async def convert_source_format(
        self, 
        request: FormatConversionRequest
    ) -> Dict[str, Any]:
        """
        转换信息源格式
        
        参数:
            request: FormatConversionRequest - 格式转换请求
            
        返回:
            Dict[str, Any] - 转换结果
        """
        await self.initialize()
        
        target_format = request.target_format
        if not isinstance(target_format, str):
            target_format = target_format.value
        
        # 执行格式转换
        conversion_result = await self.source_manager.convert_source_format(
            source_id=request.source_id,
            target_format=target_format,
            conversion_params=request.conversion_params
        )
        
        # 构建响应
        from app.api.v1.schemas.knowledge_enhancement import FormatConversionResponse
        
        response = {
            "source_id": conversion_result.get("source_id", ""),
            "original_format": conversion_result.get("original_format", ""),
            "target_format": conversion_result.get("target_format", ""),
            "converted_content": conversion_result.get("converted_content", ""),
            "metadata": conversion_result.get("metadata", {})
        }
        
        return response
    
    async def provide_feedback(
        self, 
        feedback: KnowledgeFeedback
    ) -> Dict[str, Any]:
        """
        提供查询反馈
        
        参数:
            feedback: KnowledgeFeedback - 反馈信息
            
        返回:
            Dict[str, Any] - 处理结果
        """
        await self.initialize()
        
        # 处理反馈
        feedback_dict = {
            "query_id": feedback.query_id,
            "is_relevant": feedback.is_relevant,
            "feedback_text": feedback.feedback_text,
            "rating": feedback.rating,
            "selected_items": feedback.selected_items,
            "metadata": feedback.metadata,
            "created_at": feedback.created_at
        }
        
        # 将反馈传递给AgenticRAG
        result = await self.agentic_rag.feedback(feedback.query_id, feedback_dict)
        
        return result 