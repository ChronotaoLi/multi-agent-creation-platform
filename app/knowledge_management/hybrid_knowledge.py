"""
HybridKnowledge模型实现（基础版）及增强版HybridKnowledgeManager

结合向量存储(Milvus)和图存储(Neo4j)的混合知识模型
"""

import logging
import json
from typing import Dict, List, Optional, Tuple, Any, Union, Callable

from app.data_access.vector_store.milvus_client import MilvusClient
from app.data_access.graph_store.neo4j_client import Neo4jClient
from app.data_access.vector_store.embeddings import EmbeddingService
from app.data_access.cache.redis_client import RedisClient
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class HybridKnowledge:
    """
    结合向量存储和图存储的混合知识模型
    """
    
    def __init__(
        self,
        vector_store: MilvusClient,
        graph_store: Neo4jClient,
        embedding_service: EmbeddingService,
        collection_name: str = "knowledge",
        vector_dimension: int = 1536,
        index_params: Optional[Dict[str, Any]] = None
    ):
        """
        初始化混合知识模型
        
        参数:
            vector_store: MilvusClient - 向量存储客户端
            graph_store: Neo4jClient - 图存储客户端
            embedding_service: EmbeddingService - 嵌入服务
            collection_name: str - Milvus集合名称
            vector_dimension: int - 向量维度
            index_params: dict - 索引参数
        """
        self.vector_store = vector_store
        self.graph_store = graph_store
        self.embedding_service = embedding_service
        self.collection_name = collection_name
        self.vector_dimension = vector_dimension
        self.index_params = index_params or {
            "metric_type": "COSINE",
            "index_type": "HNSW",
            "params": {"M": 16, "efConstruction": 200}
        }
    
    async def initialize(self) -> None:
        """
        初始化索引和集合
        """
        try:
            # 确保向量存储连接
            await self.vector_store.connect()
            
            # 创建向量集合
            await self.vector_store.create_collection(
                collection_name=self.collection_name,
                vector_dimension=self.vector_dimension,
                index_params=self.index_params
            )
            
            # 确保图存储连接
            await self.graph_store.connect()
            
            logger.info(f"HybridKnowledge initialized with collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to initialize HybridKnowledge: {str(e)}")
            raise
    
    async def add_knowledge(self, content: str, metadata: Dict[str, Any] = None) -> Tuple[str, str]:
        """
        添加知识，同时存储到向量库和图数据库
        
        参数:
            content: str - 知识内容
            metadata: dict - 知识元数据
            
        返回:
            tuple[str, str] - 向量ID和节点ID
        """
        metadata = metadata or {}
        
        try:
            # 生成内容的嵌入向量
            embedding = await self.embedding_service.get_embedding(content)
            
            # 存储到Milvus
            vector_id = f"v_{metadata.get('id', '0')}"
            ids = await self.vector_store.insert(
                collection_name=self.collection_name,
                vectors=[embedding],
                contents=[content],  # 新增必需的content参数
                metadatas=[metadata],  # 调整为新名称metadatas
                ids=[vector_id]  # 明确指定ID
            )
            
            # 如果插入成功，使用返回的第一个ID
            vector_id = ids[0] if ids else vector_id
            
            # 构建图数据库节点属性
            node_props = {
                "content": content,
                "vector_id": vector_id,
                **metadata
            }
            
            # 存储到Neo4j
            labels = ["Knowledge"]
            if "type" in metadata:
                labels.append(metadata["type"])
                
            node_id = await self.graph_store.create_node(labels, node_props)
            
            logger.info(f"Added knowledge with vector_id: {vector_id}, node_id: {node_id}")
            return vector_id, node_id
        except Exception as e:
            logger.error(f"Failed to add knowledge: {str(e)}")
            raise
    
    async def search(self, query: str, limit: int = 10, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        搜索知识
        
        参数:
            query: str - 搜索查询文本
            limit: int - 结果限制数量
            filters: dict - 过滤条件
            
        返回:
            list[dict] - 搜索结果列表
        """
        try:
            # 生成查询的嵌入向量
            query_embedding = await self.embedding_service.get_embedding(query)
            
            # 构建过滤表达式
            filter_expr = None
            if filters:
                filter_parts = []
                for key, value in filters.items():
                    if isinstance(value, str):
                        filter_parts.append(f'metadata LIKE "%{key}%:{value}%"')
                    else:
                        filter_parts.append(f'metadata LIKE "%{key}%:{value}%"')
                
                if filter_parts:
                    filter_expr = " && ".join(filter_parts)
            
            # 在Milvus中搜索，使用新的API
            search_results = await self.vector_store.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                top_k=limit,  # 参数名从limit改为top_k
                output_fields=["id", "content", "metadata"],  # 新增必需的output_fields参数
                filters=filter_expr  # 参数名从filter改为filters
            )
            
            # 处理搜索结果 - 适配新的返回结构
            results = []
            for result in search_results:
                item = {
                    **result["metadata"],
                    "score": result["score"],
                    "content": result["content"],
                    "id": result["id"]
                }
                results.append(item)
            
            return results
        except Exception as e:
            logger.error(f"Failed to search knowledge: {str(e)}")
            raise
    
    async def get_relationships(self, entity_id: str, relationship_type: str = None) -> List[Dict[str, Any]]:
        """
        获取实体关系
        
        参数:
            entity_id: str - 实体ID
            relationship_type: str - 关系类型
            
        返回:
            list[dict] - 关系列表
        """
        try:
            # 构建关系查询
            if relationship_type:
                query = f"""
                MATCH (n)-[r:{relationship_type}]-(m)
                WHERE id(n) = $node_id
                RETURN m, r, id(m) AS target_id, type(r) AS rel_type
                """
            else:
                query = """
                MATCH (n)-[r]-(m)
                WHERE id(n) = $node_id
                RETURN m, r, id(m) AS target_id, type(r) AS rel_type
                """
            
            # 执行查询
            params = {"node_id": int(entity_id)}
            results = await self.graph_store.query(query, params)
            
            return results
        except Exception as e:
            logger.error(f"Failed to get relationships: {str(e)}")
            raise
    
    async def delete_knowledge(self, knowledge_id: str) -> None:
        """
        删除知识
        
        参数:
            knowledge_id: str - 知识ID
        """
        try:
            # 查找关联的向量ID
            node_data = await self.graph_store.get_node(knowledge_id)
            vector_id = node_data.get("properties", {}).get("vector_id")
            
            # 删除Neo4j节点
            await self.graph_store.delete_node(knowledge_id)
            
            # 删除Milvus向量，使用新的方法名
            if vector_id:
                await self.vector_store.delete_by_ids(self.collection_name, [vector_id])
            
            logger.info(f"Deleted knowledge with id: {knowledge_id}, vector_id: {vector_id}")
        except Exception as e:
            logger.error(f"Failed to delete knowledge: {str(e)}")
            raise
    
    async def update_knowledge(self, knowledge_id: str, updates: Dict[str, Any]) -> Tuple[str, str]:
        """
        更新知识
        
        参数:
            knowledge_id: str - 知识ID
            updates: dict - 更新内容
            
        返回:
            tuple[str, str] - 向量ID和节点ID
        """
        try:
            # 获取当前节点数据
            node_data = await self.graph_store.get_node(knowledge_id)
            current_props = node_data.get("properties", {})
            vector_id = current_props.get("vector_id")
            
            # 准备新内容和元数据
            content = updates.get("content", current_props.get("content", ""))
            metadata = {**current_props}
            
            # 移除不需要的属性
            if "content" in metadata:
                del metadata["content"]
            if "vector_id" in metadata:
                del metadata["vector_id"]
                
            # 更新元数据
            for key, value in updates.get("metadata", {}).items():
                metadata[key] = value
                
            # 检查是否需要更新向量存储
            if vector_id and "content" in updates:
                # 生成新的嵌入向量
                embedding = await self.embedding_service.get_embedding(content)
                
                # 使用新的update方法更新向量存储
                await self.vector_store.update(
                    collection_name=self.collection_name,
                    id=vector_id,
                    vector=embedding,
                    content=content,
                    metadata=metadata
                )
            
            # 更新图数据库节点
            node_props = {
                "content": content,
                "vector_id": vector_id,
                **metadata
            }
            
            # 更新Neo4j节点属性
            await self.graph_store.update_node(knowledge_id, node_props)
            
            logger.info(f"Updated knowledge {knowledge_id}")
            return vector_id, knowledge_id
        except Exception as e:
            logger.error(f"Failed to update knowledge: {str(e)}")
            raise


class KnowledgeFacade:
    """
    知识管理门面类
    
    为知识管理提供统一的高级接口，整合向量存储和图存储的操作。
    实现了外观模式，简化了服务层与底层存储系统的交互。
    """
    
    def __init__(self, hybrid_knowledge: HybridKnowledge):
        """
        初始化知识门面
        
        参数:
            hybrid_knowledge: HybridKnowledge - 混合知识模型实例
        """
        self.hybrid_knowledge = hybrid_knowledge
        self.initialized = False
    
    async def initialize(self) -> None:
        """
        初始化知识门面
        """
        if not self.initialized:
            await self.hybrid_knowledge.initialize()
            self.initialized = True
    
    async def search(self, query: str, limit: int = 10, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        搜索知识
        
        参数:
            query: str - 搜索查询文本
            limit: int - 结果限制数量
            filters: dict - 过滤条件
            
        返回:
            list[dict] - 搜索结果列表
        """
        await self.initialize()
        return await self.hybrid_knowledge.search(query, limit, filters)
    
    async def add_knowledge(self, content: str, metadata: Dict[str, Any] = None) -> Tuple[str, str]:
        """
        添加知识
        
        参数:
            content: str - 知识内容
            metadata: dict - 知识元数据
            
        返回:
            tuple[str, str] - 向量ID和节点ID
        """
        await self.initialize()
        return await self.hybrid_knowledge.add_knowledge(content, metadata)
    
    async def delete_knowledge(self, knowledge_id: str) -> None:
        """
        删除知识
        
        参数:
            knowledge_id: str - 知识ID
        """
        await self.initialize()
        await self.hybrid_knowledge.delete_knowledge(knowledge_id)
    
    async def update_knowledge(self, knowledge_id: str, updates: Dict[str, Any]) -> Tuple[str, str]:
        """
        更新知识
        
        参数:
            knowledge_id: str - 知识ID
            updates: dict - 更新内容
            
        返回:
            tuple[str, str] - 向量ID和节点ID
        """
        await self.initialize()
        return await self.hybrid_knowledge.update_knowledge(knowledge_id, updates)
    
    async def get_relationships(self, entity_id: str, relationship_type: str = None) -> List[Dict[str, Any]]:
        """
        获取实体关系
        
        参数:
            entity_id: str - 实体ID
            relationship_type: str - 关系类型
            
        返回:
            list[dict] - 关系列表
        """
        await self.initialize()
        return await self.hybrid_knowledge.get_relationships(entity_id, relationship_type)
    
    async def link_knowledge(
        self, 
        source_id: str, 
        target_id: str, 
        relation_type: str,
        properties: Dict[str, Any] = None
    ) -> None:
        """
        创建知识间的关系链接
        
        参数:
            source_id: str - 源节点ID
            target_id: str - 目标节点ID
            relation_type: str - 关系类型
            properties: Dict[str, Any] - 关系属性
        """
        await self.initialize()
        await self.hybrid_knowledge.graph_store.create_relationship(
            start_node=source_id,
            end_node=target_id,
            rel_type=relation_type,
            properties=properties or {}
        )


class CacheManager:
    """
    缓存管理器
    
    负责管理知识检索结果的缓存功能
    """
    
    def __init__(self, redis_client: RedisClient, ttl: int = 300):
        """
        初始化缓存管理器
        
        参数:
            redis_client: RedisClient - Redis客户端实例
            ttl: int - 默认缓存过期时间（秒）
        """
        self.redis_client = redis_client
        self.ttl = ttl
        self.prefix = "knowledge_cache:"
    
    async def get(self, key: str) -> Optional[Any]:
        """
        获取缓存内容
        
        参数:
            key: str - 缓存键
            
        返回:
            Optional[Any] - 缓存内容，没有则返回None
        """
        full_key = f"{self.prefix}{key}"
        data = await self.redis_client.get(full_key)
        if data:
            return json.loads(data)
        return None
    
    async def set(self, key: str, value: Any, ttl: int = None) -> None:
        """
        设置缓存内容
        
        参数:
            key: str - 缓存键
            value: Any - 缓存值
            ttl: int - 过期时间（秒），为None则使用默认值
        """
        full_key = f"{self.prefix}{key}"
        ttl = ttl if ttl is not None else self.ttl
        await self.redis_client.set(full_key, json.dumps(value), ex=ttl)
    
    async def delete(self, key: str) -> None:
        """
        删除缓存
        
        参数:
            key: str - 缓存键
        """
        full_key = f"{self.prefix}{key}"
        await self.redis_client.delete(full_key)
    
    async def compute_cache_key(self, query: str, params: Dict[str, Any]) -> str:
        """
        计算缓存键
        
        参数:
            query: str - 查询字符串
            params: Dict[str, Any] - 查询参数
            
        返回:
            str - 缓存键
        """
        # 将参数字典转换为排序的字符串表示，确保相同参数生成相同的键
        sorted_params = sorted([(k, str(v)) for k, v in params.items()])
        params_str = "&".join([f"{k}={v}" for k, v in sorted_params])
        return f"{query}:{params_str}"


class HybridKnowledgeManager:
    """
    增强版混合知识管理器
    
    整合向量存储和图存储的高级混合知识模型，提供更多高级功能
    """
    
    def __init__(
        self,
        vector_store: MilvusClient,
        graph_store: Neo4jClient,
        embedding_service: EmbeddingService,
        redis_client: RedisClient = None,
        collection_name: str = "knowledge",
        vector_dimension: int = 1536,
        index_params: Optional[Dict[str, Any]] = None,
        batch_size: int = 100
    ):
        """
        初始化混合知识管理器
        
        参数:
            vector_store: MilvusClient - 向量存储客户端
            graph_store: Neo4jClient - 图存储客户端
            embedding_service: EmbeddingService - 嵌入服务
            redis_client: RedisClient - Redis客户端实例
            collection_name: str - Milvus集合名称
            vector_dimension: int - 向量维度
            index_params: dict - 索引参数
            batch_size: int - 批处理大小
        """
        self.base_knowledge = HybridKnowledge(
            vector_store=vector_store,
            graph_store=graph_store,
            embedding_service=embedding_service,
            collection_name=collection_name,
            vector_dimension=vector_dimension,
            index_params=index_params
        )
        self.batch_size = batch_size
        self.redis_client = redis_client or RedisClient()
        self.cache_manager = CacheManager(self.redis_client)
        self.initialized = False
    
    async def initialize(self) -> None:
        """
        初始化混合知识管理器
        """
        if not self.initialized:
            await self.base_knowledge.initialize()
            self.initialized = True
            logger.info("HybridKnowledgeManager initialized")
    
    async def add_knowledge(
        self, 
        content: str, 
        metadata: Dict[str, Any] = None, 
        relationships: List[Dict[str, Any]] = None
    ) -> Tuple[str, str]:
        """
        添加知识，支持关系建模
        
        参数:
            content: str - 知识内容
            metadata: Dict[str, Any] - 知识元数据
            relationships: List[Dict[str, Any]] - 关系列表，每项包含target_id, type, properties
            
        返回:
            Tuple[str, str] - 向量ID和节点ID
        """
        await self.initialize()
        
        # 添加基础知识
        vector_id, node_id = await self.base_knowledge.add_knowledge(content, metadata)
        
        # 添加关系
        if relationships:
            for rel in relationships:
                target_id = rel.get("target_id")
                rel_type = rel.get("type")
                properties = rel.get("properties", {})
                
                if target_id and rel_type:
                    await self.base_knowledge.graph_store.create_relationship(
                        start_node=node_id,
                        end_node=target_id,
                        rel_type=rel_type,
                        properties=properties
                    )
        
        return vector_id, node_id
    
    async def batch_add_knowledge(self, items: List[Dict[str, Any]]) -> List[Tuple[str, str]]:
        """
        批量添加知识
        
        参数:
            items: List[Dict[str, Any]] - 知识项列表，每项包含content, metadata, relationships
            
        返回:
            List[Tuple[str, str]] - 向量ID和节点ID列表
        """
        await self.initialize()
        
        results = []
        # 分批处理
        for i in range(0, len(items), self.batch_size):
            batch = items[i:i + self.batch_size]
            
            # 收集所有内容和元数据，为向量存储批量插入准备
            contents = []
            metadatas = []
            for item in batch:
                contents.append(item.get("content", ""))
                metadatas.append(item.get("metadata", {}))
            
            # 批量生成嵌入
            embeddings = await self.embedding_service.batch_get_embeddings(contents)
            
            # 准备IDs
            ids = [f"v_{i}_{j}" for j in range(len(batch))]
            
            # 批量插入向量存储
            vector_ids = await self.base_knowledge.vector_store.insert(
                collection_name=self.base_knowledge.collection_name,
                vectors=embeddings,
                contents=contents,
                metadatas=metadatas,
                ids=ids
            )
            
            # 批量插入图存储并创建关系
            for j, item in enumerate(batch):
                metadata = item.get("metadata", {})
                relationships = item.get("relationships", [])
                
                # 构建节点属性
                node_props = {
                    "content": contents[j],
                    "vector_id": vector_ids[j],
                    **metadata
                }
                
                # 构建标签
                labels = ["Knowledge"]
                if "type" in metadata:
                    labels.append(metadata["type"])
                
                # 创建节点
                node_id = await self.base_knowledge.graph_store.create_node(labels, node_props)
                
                # 添加关系
                if relationships:
                    for rel in relationships:
                        target_id = rel.get("target_id")
                        rel_type = rel.get("type")
                        properties = rel.get("properties", {})
                        
                        if target_id and rel_type:
                            await self.base_knowledge.graph_store.create_relationship(
                                start_node=node_id,
                                end_node=target_id,
                                rel_type=rel_type,
                                properties=properties
                            )
                
                results.append((vector_ids[j], node_id))
        
        return results
    
    async def search(
        self, 
        query: str, 
        limit: int = 10, 
        filters: Dict[str, Any] = None, 
        strategy: str = "hybrid"
    ) -> List[Dict[str, Any]]:
        """
        搜索知识，支持多种策略
        
        参数:
            query: str - 搜索查询文本
            limit: int - 结果限制数量
            filters: Dict[str, Any] - 过滤条件
            strategy: str - 搜索策略，可选 "vector", "graph", "hybrid"
            
        返回:
            List[Dict[str, Any]] - 搜索结果列表
        """
        await self.initialize()
        
        # 构建缓存键
        cache_key = await self.cache_manager.compute_cache_key(
            query, {"limit": limit, "filters": filters, "strategy": strategy}
        )
        
        # 尝试从缓存获取
        cached_result = await self.cache_manager.get(cache_key)
        if cached_result:
            logger.debug(f"Cache hit for query: {query}")
            return cached_result
        
        # 根据搜索策略执行不同的搜索
        if strategy == "vector":
            # 仅使用向量搜索
            results = await self.base_knowledge.search(query, limit, filters)
        
        elif strategy == "graph":
            # 仅使用图搜索
            # 将文本查询转换为Cypher模式搜索
            cypher_query = """
            MATCH (n:Knowledge)
            WHERE n.content CONTAINS $query_text
            RETURN id(n) as id, n.content as content, n.vector_id as vector_id, 
                   n as properties, 0.8 as score
            LIMIT $limit
            """
            params = {"query_text": query, "limit": limit}
            
            # 执行图查询
            graph_results = await self.base_knowledge.graph_store.query(cypher_query, params)
            
            # 转换为标准格式
            results = []
            for item in graph_results:
                properties = item.get("properties", {})
                result = {
                    "id": item.get("id"),
                    "content": item.get("content"),
                    "vector_id": item.get("vector_id"),
                    "score": item.get("score", 0.0),
                    **properties
                }
                results.append(result)
        
        else:  # hybrid
            # 向量搜索
            vector_results = await self.base_knowledge.search(query, limit, filters)
            
            # 图搜索
            cypher_query = """
            MATCH (n:Knowledge)
            WHERE n.content CONTAINS $query_text
            RETURN id(n) as id, n.content as content, n.vector_id as vector_id, 
                   n as properties, 0.8 as score
            LIMIT $limit
            """
            params = {"query_text": query, "limit": limit}
            
            graph_results = await self.base_knowledge.graph_store.query(cypher_query, params)
            
            # 合并结果
            results = await self._build_hybrid_query(vector_results, graph_results)
            results = await self._rank_and_deduplicate(results)
            
            # 截断到限制数量
            results = results[:limit]
        
        # 缓存结果
        await self.cache_manager.set(cache_key, results)
        
        return results
    
    async def get_entity_relationships(
        self, 
        entity_id: str, 
        relationship_types: List[str] = None, 
        depth: int = 1
    ) -> List[Dict[str, Any]]:
        """
        获取实体关系网络
        
        参数:
            entity_id: str - 实体ID
            relationship_types: List[str] - 关系类型列表
            depth: int - 关系深度
            
        返回:
            List[Dict[str, Any]] - 关系网络
        """
        await self.initialize()
        
        # 构建Cypher查询
        if relationship_types:
            rel_types = "|".join([f":{rel_type}" for rel_type in relationship_types])
            cypher = f"""
            MATCH path = (n)-[r {rel_types}*1..{depth}]-(m)
            WHERE id(n) = $node_id
            RETURN path, m, r, id(m) AS target_id
            """
        else:
            cypher = f"""
            MATCH path = (n)-[r*1..{depth}]-(m)
            WHERE id(n) = $node_id
            RETURN path, m, r, id(m) AS target_id
            """
        
        # 执行查询
        params = {"node_id": int(entity_id)}
        results = await self.base_knowledge.graph_store.query(cypher, params)
        
        return results
    
    async def update_entity_attributes(self, entity_id: str, attributes: Dict[str, Any]) -> None:
        """
        更新实体属性
        
        参数:
            entity_id: str - 实体ID
            attributes: Dict[str, Any] - 属性字典
        """
        await self.initialize()
        
        # 使用update_knowledge方法更新实体
        await self.base_knowledge.update_knowledge(entity_id, {"metadata": attributes})
    
    async def merge_entities(self, source_entity_id: str, target_entity_id: str) -> str:
        """
        合并两个实体
        
        参数:
            source_entity_id: str - 源实体ID
            target_entity_id: str - 目标实体ID
            
        返回:
            str - 合并后的实体ID（通常为target_entity_id）
        """
        await self.initialize()
        
        try:
            # 获取源实体数据
            source_data = await self.base_knowledge.graph_store.get_node(source_entity_id)
            source_props = source_data.get("properties", {})
            source_vector_id = source_props.get("vector_id")
            
            # 获取目标实体数据
            target_data = await self.base_knowledge.graph_store.get_node(target_entity_id)
            target_props = target_data.get("properties", {})
            
            # 合并属性，以目标实体为基础
            merged_props = {**source_props, **target_props}
            
            # 更新目标实体
            await self.base_knowledge.graph_store.update_node(target_entity_id, merged_props)
            
            # 获取源实体的所有关系并迁移到目标实体
            # 获取入关系
            in_cypher = """
            MATCH (n)-[r]->(s)
            WHERE id(s) = $node_id
            RETURN id(n) AS node_id, type(r) AS rel_type, r AS properties
            """
            in_params = {"node_id": int(source_entity_id)}
            in_relations = await self.base_knowledge.graph_store.query(in_cypher, in_params)
            
            # 创建新的入关系到目标实体
            for rel in in_relations:
                node_id = rel.get("node_id")
                rel_type = rel.get("rel_type")
                properties = rel.get("properties", {})
                
                # 跳过已存在的关系
                if node_id == int(target_entity_id):
                    continue
                
                # 创建新关系
                await self.base_knowledge.graph_store.create_relationship(
                    start_node=str(node_id),
                    end_node=target_entity_id,
                    rel_type=rel_type,
                    properties=properties
                )
            
            # 获取出关系
            out_cypher = """
            MATCH (s)-[r]->(n)
            WHERE id(s) = $node_id
            RETURN id(n) AS node_id, type(r) AS rel_type, r AS properties
            """
            out_params = {"node_id": int(source_entity_id)}
            out_relations = await self.base_knowledge.graph_store.query(out_cypher, out_params)
            
            # 创建新的出关系从目标实体
            for rel in out_relations:
                node_id = rel.get("node_id")
                rel_type = rel.get("rel_type")
                properties = rel.get("properties", {})
                
                # 跳过已存在的关系
                if node_id == int(target_entity_id):
                    continue
                
                # 创建新关系
                await self.base_knowledge.graph_store.create_relationship(
                    start_node=target_entity_id,
                    end_node=str(node_id),
                    rel_type=rel_type,
                    properties=properties
                )
            
            # 删除源实体
            await self.delete_knowledge(source_entity_id)
            
            logger.info(f"Merged entity {source_entity_id} into {target_entity_id}")
            return target_entity_id
            
        except Exception as e:
            logger.error(f"Failed to merge entities: {str(e)}")
            raise
    
    async def delete_knowledge(self, knowledge_id: str) -> None:
        """
        删除知识
        
        参数:
            knowledge_id: str - 知识ID
        """
        await self.initialize()
        await self.base_knowledge.delete_knowledge(knowledge_id)
    
    async def _build_hybrid_query(
        self, 
        vector_results: List[Dict[str, Any]], 
        graph_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        构建混合查询结果
        
        参数:
            vector_results: List[Dict[str, Any]] - 向量搜索结果
            graph_results: List[Dict[str, Any]] - 图搜索结果
            
        返回:
            List[Dict[str, Any]] - 合并后的结果
        """
        # 使用ID作为键合并结果
        merged = {}
        
        # 处理向量结果
        for result in vector_results:
            result_id = result.get("id")
            if result_id:
                # 标记来源并调整分数
                result["source"] = "vector"
                result["score"] = float(result.get("score", 0)) * 1.0  # 向量分数权重
                merged[result_id] = result
        
        # 处理图结果
        for result in graph_results:
            result_id = str(result.get("id"))
            if result_id:
                if result_id in merged:
                    # 已存在，调整分数
                    merged[result_id]["score"] = max(
                        merged[result_id]["score"],
                        float(result.get("score", 0)) * 0.8  # 图分数权重
                    )
                    merged[result_id]["source"] = "hybrid"
                else:
                    # 新结果
                    result["source"] = "graph"
                    result["score"] = float(result.get("score", 0)) * 0.8  # 图分数权重
                    merged[result_id] = result
        
        # 转换回列表
        return list(merged.values())
    
    async def _rank_and_deduplicate(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        对结果进行排序和去重
        
        参数:
            results: List[Dict[str, Any]] - 检索结果
            
        返回:
            List[Dict[str, Any]] - 排序和去重后的结果
        """
        # 按分数降序排序
        sorted_results = sorted(results, key=lambda x: float(x.get("score", 0)), reverse=True)
        
        # 去重（基于内容哈希）
        unique_results = []
        seen_contents = set()
        
        for result in sorted_results:
            content = result.get("content", "")
            content_hash = hash(content)
            
            if content_hash not in seen_contents:
                seen_contents.add(content_hash)
                unique_results.append(result)
        
        return unique_results
