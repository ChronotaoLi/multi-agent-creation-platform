"""
记忆智能体模块

实现记忆智能体，负责管理智能体系统的长短期记忆，提供记忆检索和存储功能。
结合向量存储和图存储实现高效的记忆检索。
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Set, Union

import numpy as np
from langgraph.graph import StateGraph
from langgraph.memory import SummarizationNode

from app.agents.base_agent import BaseAgent
from app.data_access.graph_store.neo4j_client import Neo4jClient
from app.data_access.vector_store.milvus_client import MilvusClient
from app.data_access.vector_store.embeddings import EmbeddingService
from app.services.interfaces.llm_service import LLMService

logger = logging.getLogger(__name__)


class MemoryStore:
    """
    记忆存储类
    
    提供记忆存储和检索的底层实现，结合向量存储和图存储
    """
    
    def __init__(
        self,
        vector_store: MilvusClient,
        graph_store: Neo4jClient,
        embedding_service: EmbeddingService,
        collection_name: str = "agent_memories",
        vector_dimension: int = 1536
    ):
        """
        初始化记忆存储
        
        参数:
            vector_store: MilvusClient - 向量存储客户端
            graph_store: Neo4jClient - 图存储客户端
            embedding_service: EmbeddingService - 嵌入服务
            collection_name: str - 向量集合名称
            vector_dimension: int - 向量维度
        """
        self.vector_store = vector_store
        self.graph_store = graph_store
        self.embedding_service = embedding_service
        self.collection_name = collection_name
        self.vector_dimension = vector_dimension
        
        # 向量ID到图节点ID的映射
        self.vector_to_graph_map: Dict[str, str] = {}
        
        # 记忆类型到标签的映射
        self.memory_type_to_label = {
            "conversation": "ConversationMemory",
            "fact": "FactMemory",
            "event": "EventMemory",
            "concept": "ConceptMemory",
            "procedural": "ProceduralMemory",
            "episodic": "EpisodicMemory",
        }
    
    async def initialize(self) -> None:
        """
        初始化存储系统
        """
        # 创建向量集合
        await self.vector_store.create_collection(
            self.collection_name,
            self.vector_dimension,
            description="智能体记忆存储"
        )
        
        # 初始化图数据库连接
        if not hasattr(self.graph_store, "_driver") or self.graph_store._driver is None:
            await self.graph_store.connect()
            
        logger.info(f"记忆存储初始化完成: 集合[{self.collection_name}], 维度[{self.vector_dimension}]")
    
    async def store(
        self,
        memory_data: Dict[str, Any],
        embeddings: Optional[List[float]] = None
    ) -> str:
        """
        存储记忆数据
        
        参数:
            memory_data: Dict[str, Any] - 记忆数据
            embeddings: Optional[List[float]] - 记忆的嵌入向量，如不提供则自动生成
            
        返回:
            str: 记忆ID
        """
        # 验证必要字段
        required_fields = ["content", "type", "source", "importance"]
        for field in required_fields:
            if field not in memory_data:
                raise ValueError(f"记忆数据缺少必要字段: {field}")
        
        # 生成记忆ID
        memory_id = memory_data.get("id", str(uuid.uuid4()))
        memory_data["id"] = memory_id
        
        # 添加时间戳
        if "created_at" not in memory_data:
            memory_data["created_at"] = datetime.utcnow().isoformat()
            
        # 生成嵌入向量
        if embeddings is None:
            embeddings = await self.embedding_service.get_embedding(memory_data["content"])
        
        # 转换为JSON字符串
        metadata_json = json.dumps(memory_data)
        
        # 存储到向量数据库
        try:
            await self.vector_store.insert(
                self.collection_name,
                [embeddings],
                [memory_data["content"]],
                [memory_data],
                [memory_id]
            )
            logger.debug(f"记忆已存储到向量数据库: {memory_id}")
        except Exception as e:
            logger.error(f"存储记忆到向量数据库失败: {str(e)}")
            raise
        
        # 存储到图数据库
        try:
            # 确定节点标签
            memory_type = memory_data["type"]
            label = self.memory_type_to_label.get(memory_type, "Memory")
            
            # 创建节点
            node_properties = {
                "memory_id": memory_id,
                "content": memory_data["content"],
                "importance": memory_data["importance"],
                "source": memory_data["source"],
                "created_at": memory_data["created_at"]
            }
            
            # 添加其他属性
            for key, value in memory_data.items():
                if key not in node_properties and not isinstance(value, (dict, list)):
                    node_properties[key] = value
            
            # 创建节点并获取节点ID
            graph_node_id = await self.graph_store.create_node(
                labels=["Memory", label],
                properties=node_properties
            )
            
            # 记录映射关系
            self.vector_to_graph_map[memory_id] = graph_node_id
            
            logger.debug(f"记忆已存储到图数据库: {memory_id} -> {graph_node_id}")
            
            # 处理关系
            if "relations" in memory_data and isinstance(memory_data["relations"], list):
                await self._create_memory_relations(graph_node_id, memory_data["relations"])
                
            return memory_id
        except Exception as e:
            logger.error(f"存储记忆到图数据库失败: {str(e)}")
            # 尝试从向量数据库删除已添加的记录
            try:
                await self.vector_store.delete_by_ids(self.collection_name, [memory_id])
            except Exception as cleanup_error:
                logger.error(f"清理向量数据库失败: {str(cleanup_error)}")
            raise e
    
    async def _create_memory_relations(
        self,
        source_node_id: str,
        relations: List[Dict[str, Any]]
    ) -> None:
        """
        创建记忆关系
        
        参数:
            source_node_id: str - 源节点ID
            relations: List[Dict[str, Any]] - 关系列表
        """
        for relation in relations:
            if "target_id" not in relation or "type" not in relation:
                logger.warning(f"关系定义不完整: {relation}")
                continue
                
            target_id = relation["target_id"]
            rel_type = relation["type"]
            properties = {k: v for k, v in relation.items() 
                         if k not in ["target_id", "type"]}
            
            # 查找目标节点的图ID
            target_graph_id = self.vector_to_graph_map.get(target_id)
            if not target_graph_id:
                # 尝试从图数据库查找
                query = """
                MATCH (n:Memory {memory_id: $memory_id})
                RETURN id(n) as node_id
                """
                result = await self.graph_store.query(query, {"memory_id": target_id})
                if result and len(result) > 0:
                    target_graph_id = str(result[0]["node_id"])
                    self.vector_to_graph_map[target_id] = target_graph_id
                else:
                    logger.warning(f"找不到目标记忆节点: {target_id}")
                    continue
            
            # 创建关系
            try:
                await self.graph_store.create_relationship(
                    source_node_id, 
                    target_graph_id,
                    rel_type,
                    properties
                )
                logger.debug(f"已创建记忆关系: ({source_node_id})-[{rel_type}]->({target_graph_id})")
            except Exception as e:
                logger.error(f"创建记忆关系失败: {str(e)}")
    
    async def retrieve_by_similarity(
        self,
        query_embedding: List[float],
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        基于向量相似度检索记忆
        
        参数:
            query_embedding: List[float] - 查询向量
            limit: int - 返回结果数量限制
            filters: Optional[Dict[str, Any]] - 过滤条件
            
        返回:
            List[Dict[str, Any]] - 检索结果
        """
        # 构建Milvus过滤条件
        filter_expr = ""
        if filters:
            conditions = []
            for key, value in filters.items():
                if isinstance(value, str):
                    # 字符串值需要加引号
                    conditions.append(f"JSON_CONTAINS(metadata, '{{\"{key}\": \"{value}\"}}') == true")
                else:
                    conditions.append(f"JSON_CONTAINS(metadata, '{{\"{key}\": {value}}}') == true")
            
            if conditions:
                filter_expr = " && ".join(conditions)
        
        # 搜索向量数据库
        try:
            search_results = await self.vector_store.search(
                self.collection_name,
                query_embedding,
                top_k=limit,
                output_fields=["id", "content", "metadata"],
                filters=filter_expr if filter_expr else None
            )
            
            # 解析结果
            memories = []
            for result in search_results:
                try:
                    metadata = result.get("metadata", "{}")
                    if isinstance(metadata, str):
                        metadata = json.loads(metadata)
                    
                    # 确保元数据包含所有必要字段
                    memory_data = {
                        "id": result.get("id"),
                        "content": result.get("content", ""),
                        "score": result.get("score", 0.0),
                        **metadata
                    }
                    
                    memories.append(memory_data)
                except json.JSONDecodeError as e:
                    logger.error(f"解析记忆元数据失败: {str(e)}")
                    continue
            
            return memories
        except Exception as e:
            logger.error(f"基于相似度检索记忆失败: {str(e)}")
            raise
    
    async def retrieve_by_relation(
        self,
        start_entity: str,
        relation_type: Optional[str] = None,
        depth: int = 1,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        基于关系检索记忆
        
        参数:
            start_entity: str - 起始实体ID
            relation_type: Optional[str] - 关系类型，None表示任意关系
            depth: int - 搜索深度
            limit: int - 返回结果数量限制
            
        返回:
            List[Dict[str, Any]] - 检索结果
        """
        # 构建图查询
        relation_clause = ""
        if relation_type:
            relation_clause = f":{relation_type}"
            
        # 根据深度调整查询
        if depth == 1:
            query = f"""
            MATCH (a:Memory {{memory_id: $start_id}})-[r{relation_clause}]->(b:Memory)
            RETURN b.memory_id as memory_id, b.content as content, b.importance as importance,
                   b.source as source, b.created_at as created_at, type(r) as relation_type
            LIMIT $limit
            """
        else:
            # 对于多层深度，使用可变长度路径
            query = f"""
            MATCH (a:Memory {{memory_id: $start_id}})-[r{relation_clause}*1..{depth}]->(b:Memory)
            RETURN b.memory_id as memory_id, b.content as content, b.importance as importance,
                   b.source as source, b.created_at as created_at,
                   [rel in r | type(rel)] as relation_types
            LIMIT $limit
            """
        
        # 执行查询
        try:
            results = await self.graph_store.query(
                query,
                {"start_id": start_entity, "limit": limit}
            )
            
            # 对于找到的每个记忆ID，尝试从向量数据库获取完整信息
            memories = []
            for result in results:
                memory_id = result.get("memory_id")
                if not memory_id:
                    continue
                    
                # 获取完整记忆
                memory_data = await self.vector_store.get_by_id(
                    self.collection_name,
                    memory_id
                )
                
                if memory_data:
                    # 解析元数据
                    metadata = memory_data.get("metadata", "{}")
                    if isinstance(metadata, str):
                        try:
                            metadata = json.loads(metadata)
                        except json.JSONDecodeError:
                            metadata = {}
                    
                    # 合并结果
                    full_memory = {
                        "id": memory_id,
                        "content": memory_data.get("content", result.get("content", "")),
                        "relation_info": {
                            "types": result.get("relation_types", [result.get("relation_type")]),
                            "start_entity": start_entity
                        },
                        **metadata
                    }
                    
                    memories.append(full_memory)
                else:
                    # 如果向量数据库中没有，使用图数据库的有限信息
                    basic_memory = {
                        "id": memory_id,
                        "content": result.get("content", ""),
                        "importance": result.get("importance", 0.5),
                        "source": result.get("source", "unknown"),
                        "created_at": result.get("created_at", ""),
                        "relation_info": {
                            "types": result.get("relation_types", [result.get("relation_type")]),
                            "start_entity": start_entity
                        }
                    }
                    
                    memories.append(basic_memory)
            
            return memories
        except Exception as e:
            logger.error(f"基于关系检索记忆失败: {str(e)}")
            raise
    
    async def update(
        self,
        memory_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        更新记忆
        
        参数:
            memory_id: str - 记忆ID
            updates: Dict[str, Any] - 更新内容
            
        返回:
            Dict[str, Any] - 更新后的记忆数据
        """
        # 首先获取现有记忆
        try:
            existing_memory = await self.vector_store.get_by_id(
                self.collection_name,
                memory_id
            )
            
            if not existing_memory:
                raise ValueError(f"记忆不存在: {memory_id}")
                
            # 解析元数据
            metadata = existing_memory.get("metadata", "{}")
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
                
            # 合并更新
            updated_metadata = {**metadata, **updates}
            
            # 如果更新内容，需要重新生成嵌入
            content = existing_memory.get("content", "")
            vector = None
            
            if "content" in updates and updates["content"] != content:
                content = updates["content"]
                vector = await self.embedding_service.get_embedding(content)
            
            # 更新向量数据库
            await self.vector_store.update(
                self.collection_name,
                memory_id,
                vector=vector,
                content=content if "content" in updates else None,
                metadata=updated_metadata
            )
            
            # 更新图数据库
            graph_node_id = self.vector_to_graph_map.get(memory_id)
            if not graph_node_id:
                # 查找图节点ID
                query = """
                MATCH (n:Memory {memory_id: $memory_id})
                RETURN id(n) as node_id
                """
                result = await self.graph_store.query(query, {"memory_id": memory_id})
                if result and len(result) > 0:
                    graph_node_id = str(result[0]["node_id"])
                    self.vector_to_graph_map[memory_id] = graph_node_id
            
            if graph_node_id:
                # 准备更新属性
                node_updates = {}
                for key, value in updates.items():
                    if not isinstance(value, (dict, list)):
                        node_updates[key] = value
                
                if node_updates:
                    await self.graph_store.update_node(graph_node_id, node_updates)
                    
                # 如果有关系更新
                if "relations" in updates and isinstance(updates["relations"], list):
                    await self._create_memory_relations(graph_node_id, updates["relations"])
            
            # 返回更新后的记忆
            return {
                **updated_metadata,
                "id": memory_id,
                "content": content
            }
        except Exception as e:
            logger.error(f"更新记忆失败: {str(e)}")
            raise
    
    async def delete(self, memory_id: str) -> bool:
        """
        删除记忆
        
        参数:
            memory_id: str - 记忆ID
            
        返回:
            bool - 是否成功删除
        """
        try:
            # 删除向量数据库中的记录
            await self.vector_store.delete_by_ids(self.collection_name, [memory_id])
            
            # 删除图数据库中的节点
            graph_node_id = self.vector_to_graph_map.get(memory_id)
            if not graph_node_id:
                # 查找图节点ID
                query = """
                MATCH (n:Memory {memory_id: $memory_id})
                RETURN id(n) as node_id
                """
                result = await self.graph_store.query(query, {"memory_id": memory_id})
                if result and len(result) > 0:
                    graph_node_id = str(result[0]["node_id"])
            
            if graph_node_id:
                await self.graph_store.delete_node(graph_node_id)
                # 从映射中移除
                if memory_id in self.vector_to_graph_map:
                    del self.vector_to_graph_map[memory_id]
            
            return True
        except Exception as e:
            logger.error(f"删除记忆失败: {str(e)}")
            return False

class ImportanceEvaluator:
    """
    记忆重要性评估器
    
    评估记忆的重要性，用于记忆管理和优先级划分
    """
    
    def __init__(
        self,
        llm_service: LLMService,
        default_importance: float = 0.5,
        importance_criteria: Dict[str, float] = None
    ):
        """
        初始化重要性评估器
        
        参数:
            llm_service: LLMService - LLM服务实例，用于评估重要性
            default_importance: float - 默认重要性值
            importance_criteria: Dict[str, float] - 重要性评估标准及权重
        """
        self.llm_service = llm_service
        self.default_importance = default_importance
        self.importance_criteria = importance_criteria or {
            "relevance": 0.3,   # 与当前任务的相关性
            "novelty": 0.2,     # 信息的新颖性
            "salience": 0.2,    # 信息的显著性
            "utility": 0.3,     # 实用价值
        }
        
        # 确保权重总和为1
        total_weight = sum(self.importance_criteria.values())
        if total_weight != 1.0:
            # 归一化权重
            self.importance_criteria = {
                k: v / total_weight for k, v in self.importance_criteria.items()
            }
            
        # 评估提示模板
        self.evaluation_prompt = """
        你是一个记忆评估专家，需要评估以下信息的重要性。根据提供的标准，为每个方面打分(0-10分)，其中0表示最不重要，10表示最重要。
        
        信息内容：
        {content}
        
        上下文信息：
        {context}
        
        评估标准：
        1. 相关性 (Relevance)：信息与上下文/当前任务的相关程度
        2. 新颖性 (Novelty)：信息的新颖程度，是否包含新的见解
        3. 显著性 (Salience)：信息的突出程度和关注价值
        4. 实用性 (Utility)：信息的实用价值和可操作性
        
        请严格按照以下JSON格式回答，不要添加任何其他解释：
        {{
            "relevance": 评分(0-10),
            "novelty": 评分(0-10),
            "salience": 评分(0-10),
            "utility": 评分(0-10),
            "reasoning": "简短的评分理由"
        }}
        """
    
    async def evaluate_importance(
        self,
        memory: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        评估记忆的重要性
        
        参数:
            memory: Dict[str, Any] - 记忆数据
            context: Optional[Dict[str, Any]] - 评估上下文
            
        返回:
            float - 重要性分数 (0.0-1.0)
        """
        # 如果已有重要性分数且没有提供上下文，直接返回
        if "importance" in memory and context is None:
            return float(memory["importance"])
        
        # 提取内容
        content = memory.get("content", "")
        if not content:
            return self.default_importance
        
        # 准备上下文描述
        context_description = "没有提供上下文。"
        if context:
            context_items = []
            for key, value in context.items():
                if isinstance(value, str) and value:
                    context_items.append(f"{key}: {value}")
            
            if context_items:
                context_description = "\n".join(context_items)
        
        # 使用LLM评估重要性
        try:
            formatted_prompt = self.evaluation_prompt.format(
                content=content,
                context=context_description
            )
            
            response = await self.llm_service.chat_complete_json(
                [{"role": "user", "content": formatted_prompt}],
                response_format={"type": "json_object"}
            )
            
            # 解析响应
            evaluation = json.loads(response)
            
            # 计算加权分数
            total_score = 0.0
            for criterion, weight in self.importance_criteria.items():
                if criterion in evaluation:
                    # 将0-10的分数转换为0-1
                    score = float(evaluation[criterion]) / 10.0
                    total_score += score * weight
            
            # 确保分数在0-1范围内
            importance = max(0.0, min(1.0, total_score))
            
            logger.debug(f"记忆重要性评估: {importance:.2f}, 理由: {evaluation.get('reasoning', '未提供')}")
            return importance
        
        except Exception as e:
            logger.warning(f"重要性评估失败: {str(e)}，使用默认值")
            return self.default_importance
    
    async def batch_evaluate_importance(
        self,
        memories: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[float]:
        """
        批量评估记忆的重要性
        
        参数:
            memories: List[Dict[str, Any]] - 记忆数据列表
            context: Optional[Dict[str, Any]] - 评估上下文
            
        返回:
            List[float] - 重要性分数列表
        """
        results = []
        for memory in memories:
            importance = await self.evaluate_importance(memory, context)
            results.append(importance)
        return results
    
    async def rank_memories_by_importance(
        self,
        memories: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        按重要性对记忆进行排序
        
        参数:
            memories: List[Dict[str, Any]] - 记忆数据列表
            context: Optional[Dict[str, Any]] - 评估上下文
            
        返回:
            List[Dict[str, Any]] - 按重要性排序的记忆列表
        """
        # 评估重要性
        scores = await self.batch_evaluate_importance(memories, context)
        
        # 将分数添加到记忆中
        for memory, score in zip(memories, scores):
            memory["importance"] = score
        
        # 排序并返回
        return sorted(memories, key=lambda x: x.get("importance", 0.0), reverse=True)

class SummarizationNode:
    """
    基于LangGraph的摘要节点
    
    用于智能地压缩和管理记忆内容，保留重要信息
    """
    
    def __init__(
        self,
        llm_service: LLMService,
        max_tokens: int = 4000,
        compression_factor: float = 0.5
    ):
        """
        初始化摘要节点
        
        参数:
            llm_service: LLMService - LLM服务实例
            max_tokens: int - 最大token数量
            compression_factor: float - 压缩因子(0.0-1.0)
        """
        self.llm_service = llm_service
        self.max_tokens = max_tokens
        self.compression_factor = compression_factor
        
        # 摘要提示模板
        self.summarization_prompt = """
        你是一个专业的内容摘要专家。请根据以下内容生成一个简明扼要的摘要，确保保留所有重要信息和关键细节。
        
        内容:
        {content}
        
        要求:
        1. 摘要长度应该是原文长度的约{compression_factor:.0%}
        2. 保留所有关键事实、人物和事件
        3. 按时间顺序或逻辑顺序组织信息
        4. 使用简洁、清晰的语言
        5. 不要添加原文中不存在的信息
        6. 不要使用"内容提到"、"文章讨论"等元语言
        
        请直接提供摘要，不需要额外的解释或前缀。
        """
        
        # 多文档摘要提示模板
        self.multi_doc_summarization_prompt = """
        你是一个专业的内容摘要专家。请根据以下多个相关内容生成一个统一的、连贯的摘要，确保保留所有重要信息并消除冗余。
        
        内容列表:
        {content_list}
        
        要求:
        1. 摘要应该抓住所有来源的核心观点和关键事实
        2. 识别并合并相似或相关的信息点
        3. 解决不同来源之间可能存在的矛盾
        4. 确保摘要的连贯性和逻辑流程
        5. 摘要应不超过{max_length}个字符
        6. 不要添加原文中不存在的信息
        7. 不要使用"根据内容"、"文档表明"等元语言
        
        请直接提供摘要，不需要额外的解释或前缀。
        """
    
    async def summarize(self, content: str) -> str:
        """
        对单个内容进行摘要
        
        参数:
            content: str - 需要摘要的内容
            
        返回:
            str - 摘要结果
        """
        if not content:
            return ""
            
        try:
            # 格式化提示
            prompt = self.summarization_prompt.format(
                content=content,
                compression_factor=self.compression_factor
            )
            
            # 调用LLM生成摘要
            summary = await self.llm_service.text_complete(prompt)
            
            # 返回去除前后空白的摘要
            return summary.strip()
        except Exception as e:
            logger.error(f"内容摘要生成失败: {str(e)}")
            # 作为备选方案，返回截断的原文
            max_chars = int(len(content) * self.compression_factor)
            return content[:max_chars] + ("..." if len(content) > max_chars else "")
    
    async def summarize_multiple(
        self,
        contents: List[str],
        max_length: int = 2000
    ) -> str:
        """
        对多个内容进行统一摘要
        
        参数:
            contents: List[str] - 需要摘要的内容列表
            max_length: int - 摘要最大长度(字符数)
            
        返回:
            str - 摘要结果
        """
        if not contents:
            return ""
            
        # 过滤空内容
        valid_contents = [c for c in contents if c]
        if not valid_contents:
            return ""
            
        # 如果只有一个内容，直接调用单文档摘要
        if len(valid_contents) == 1:
            return await self.summarize(valid_contents[0])
        
        try:
            # 构建内容列表字符串
            content_list = "\n\n---\n\n".join([
                f"文档 {i+1}:\n{content}" 
                for i, content in enumerate(valid_contents)
            ])
            
            # 格式化提示
            prompt = self.multi_doc_summarization_prompt.format(
                content_list=content_list,
                max_length=max_length
            )
            
            # 调用LLM生成摘要
            summary = await self.llm_service.text_complete(prompt)
            
            # 返回去除前后空白的摘要
            return summary.strip()
        except Exception as e:
            logger.error(f"多内容摘要生成失败: {str(e)}")
            # 作为备选方案，连接所有内容并截断
            combined = " ".join(valid_contents)
            return combined[:max_length] + ("..." if len(combined) > max_length else "")
    
    async def progressive_summarize(
        self,
        memory_chunks: List[Dict[str, Any]],
        key_field: str = "content",
        importance_field: str = "importance"
    ) -> str:
        """
        根据重要性渐进式摘要
        
        参数:
            memory_chunks: List[Dict[str, Any]] - 记忆块列表
            key_field: str - 内容字段名
            importance_field: str - 重要性字段名
            
        返回:
            str - 摘要结果
        """
        if not memory_chunks:
            return ""
            
        # 按重要性排序
        sorted_chunks = sorted(
            memory_chunks,
            key=lambda x: x.get(importance_field, 0.0),
            reverse=True
        )
        
        # 提取内容
        contents = [chunk.get(key_field, "") for chunk in sorted_chunks if chunk.get(key_field)]
        if not contents:
            return ""
            
        # 计算总字符数
        total_chars = sum(len(c) for c in contents)
        
        # 如果总长度已经足够短，直接合并
        target_length = int(total_chars * self.compression_factor)
        if total_chars <= self.max_tokens * 4:  # 粗略估计，假设1个token约等于4个字符
            return await self.summarize_multiple(contents, max_length=target_length)
            
        # 否则，分批处理
        result = ""
        batch = []
        batch_chars = 0
        batch_max = self.max_tokens * 4  # 每批最大字符数
        
        for content in contents:
            content_len = len(content)
            
            # 如果当前批次加上新内容超过限制，先处理当前批次
            if batch_chars + content_len > batch_max and batch:
                intermediate_summary = await self.summarize_multiple(
                    batch, 
                    max_length=int(batch_chars * self.compression_factor)
                )
                if result:
                    result = await self.summarize_multiple(
                        [result, intermediate_summary],
                        max_length=target_length
                    )
                else:
                    result = intermediate_summary
                
                # 重置批次
                batch = []
                batch_chars = 0
            
            # 添加到当前批次
            batch.append(content)
            batch_chars += content_len
        
        # 处理最后一个批次
        if batch:
            intermediate_summary = await self.summarize_multiple(
                batch, 
                max_length=int(batch_chars * self.compression_factor)
            )
            if result:
                result = await self.summarize_multiple(
                    [result, intermediate_summary],
                    max_length=target_length
                )
            else:
                result = intermediate_summary
        
        return result

class MemoryAgent(BaseAgent):
    """
    记忆智能体
    
    管理智能体系统的长短期记忆，提供记忆检索和存储功能
    """
    
    def __init__(
        self,
        id: str,
        name: str,
        llm_service: LLMService,
        memory_store: MemoryStore,
        embedding_service: EmbeddingService,
        config: Dict[str, Any] = None
    ):
        """
        初始化记忆智能体
        
        参数:
            id: str - 智能体唯一标识符
            name: str - 智能体名称
            llm_service: LLMService - LLM服务实例
            memory_store: MemoryStore - 记忆存储实例
            embedding_service: EmbeddingService - 嵌入服务实例
            config: Dict[str, Any] - 智能体配置信息
        """
        super().__init__(id, name, "memory", llm_service, config)
        self.memory_store = memory_store
        self.embedding_service = embedding_service
        
        # 初始化子组件
        self.importance_evaluator = ImportanceEvaluator(
            llm_service=llm_service,
            importance_criteria=config.get("importance_criteria") if config else None
        )
        
        self.summarization_node = SummarizationNode(
            llm_service=llm_service,
            max_tokens=config.get("max_tokens", 4000) if config else 4000,
            compression_factor=config.get("compression_factor", 0.5) if config else 0.5
        )
        
        # 记忆保留策略
        self.memory_retention_policy = config.get("memory_retention_policy", {
            "default_ttl": 2592000,  # 默认30天(秒)
            "max_memories_per_agent": 1000,
            "importance_threshold": 0.3  # 低于此值的记忆可能被清理
        }) if config else {
            "default_ttl": 2592000,
            "max_memories_per_agent": 1000,
            "importance_threshold": 0.3
        }
        
        # 私有状态
        self._initialized = False
        
        # 记忆类型配置
        self.memory_types = {
            "conversation": {
                "description": "对话记忆，用于追踪与其他实体的交互历史",
                "default_ttl": 604800  # 7天(秒)
            },
            "fact": {
                "description": "事实记忆，用于存储确定性的信息",
                "default_ttl": 5184000  # 60天(秒)
            },
            "event": {
                "description": "事件记忆，用于记录关键事件",
                "default_ttl": 2592000  # 30天(秒)
            },
            "concept": {
                "description": "概念记忆，用于存储抽象概念和定义",
                "default_ttl": 7776000  # 90天(秒)
            },
            "procedural": {
                "description": "程序性记忆，用于存储操作步骤和流程",
                "default_ttl": 5184000  # 60天(秒)
            },
            "episodic": {
                "description": "情景记忆，用于存储完整的经历和体验",
                "default_ttl": 1209600  # 14天(秒)
            }
        }
    
    async def initialize(self) -> None:
        """初始化记忆智能体"""
        if not self._initialized:
            await self.memory_store.initialize()
            self._initialized = True
            logger.info(f"记忆智能体 {self.id} 初始化完成")
    
    async def store_memory(
        self,
        memory: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> str:
        """
        存储记忆
        
        参数:
            memory: Dict[str, Any] - 记忆数据
            context: Dict[str, Any] - 上下文信息，用于辅助重要性评估
            
        返回:
            str - 记忆ID
        """
        # 确保已初始化
        if not self._initialized:
            await self.initialize()
        
        # 验证必要字段
        required_fields = ["content", "type", "source"]
        missing_fields = [field for field in required_fields if field not in memory]
        if missing_fields:
            raise ValueError(f"记忆数据缺少必要字段: {', '.join(missing_fields)}")
        
        # 验证记忆类型
        memory_type = memory.get("type")
        if memory_type not in self.memory_types:
            valid_types = ", ".join(self.memory_types.keys())
            raise ValueError(f"无效的记忆类型: {memory_type}。有效类型: {valid_types}")
        
        # 添加ID和时间戳(如果没有)
        memory_id = memory.get("id", str(uuid.uuid4()))
        memory["id"] = memory_id
        
        if "created_at" not in memory:
            memory["created_at"] = datetime.utcnow().isoformat()
        
        # 评估重要性(如果没有提供)
        if "importance" not in memory:
            importance = await self.importance_evaluator.evaluate_importance(memory, context)
            memory["importance"] = importance
        
        # 设置过期时间(如果没有提供)
        if "ttl" not in memory:
            # 获取该类型的默认TTL
            default_ttl = self.memory_types[memory_type].get(
                "default_ttl", 
                self.memory_retention_policy.get("default_ttl")
            )
            memory["ttl"] = default_ttl
        
        # 生成嵌入向量
        content = memory.get("content", "")
        embedding = await self.embedding_service.get_embedding(content)
        
        # 存储记忆
        memory_id = await self.memory_store.store(memory, embedding)
        
        logger.debug(f"记忆已存储: ID={memory_id}, 类型={memory_type}, 重要性={memory['importance']:.2f}")
        return memory_id
    
    async def retrieve_memories(
        self,
        query: str,
        limit: int = 10,
        filters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        检索记忆
        
        参数:
            query: str - 查询文本
            limit: int - 返回记忆的最大数量
            filters: Dict[str, Any] - 过滤条件
            
        返回:
            List[Dict[str, Any]] - 检索到的记忆列表
        """
        # 确保已初始化
        if not self._initialized:
            await self.initialize()
        
        # 生成查询嵌入向量
        query_embedding = await self.embedding_service.get_embedding(query)
        
        # 执行检索
        memories = await self.memory_store.retrieve_by_similarity(
            query_embedding,
            limit=limit,
            filters=filters
        )
        
        logger.debug(f"检索到 {len(memories)} 条记忆，查询: \"{query[:50]}...\"")
        return memories
    
    async def update_memory(
        self,
        memory_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        更新记忆
        
        参数:
            memory_id: str - 记忆ID
            updates: Dict[str, Any] - 更新内容
            
        返回:
            Dict[str, Any] - 更新后的记忆
        """
        # 确保已初始化
        if not self._initialized:
            await self.initialize()
        
        # 如果更新重要性，先评估
        if "importance" not in updates and "content" in updates:
            # 只有内容更新时才重新评估重要性
            try:
                importance = await self.importance_evaluator.evaluate_importance(
                    {"content": updates["content"]}
                )
                updates["importance"] = importance
            except Exception as e:
                logger.warning(f"重新评估重要性失败: {str(e)}")
        
        # 更新记忆
        updated_memory = await self.memory_store.update(memory_id, updates)
        
        logger.debug(f"记忆已更新: ID={memory_id}")
        return updated_memory
    
    async def summarize_memories(
        self,
        memories: List[Dict[str, Any]]
    ) -> str:
        """
        总结记忆
        
        参数:
            memories: List[Dict[str, Any]] - 记忆列表
            
        返回:
            str - 记忆摘要
        """
        # 确保已初始化
        if not self._initialized:
            await self.initialize()
        
        if not memories:
            return ""
        
        # 使用摘要节点生成摘要
        summary = await self.summarization_node.progressive_summarize(memories)
        
        logger.debug(f"已生成 {len(memories)} 条记忆的摘要，长度为 {len(summary)} 字符")
        return summary
    
    async def evaluate_importance(
        self,
        memory: Dict[str, Any]
    ) -> float:
        """
        评估记忆重要性
        
        参数:
            memory: Dict[str, Any] - 记忆数据
            
        返回:
            float - 重要性分数(0.0-1.0)
        """
        # 确保已初始化
        if not self._initialized:
            await self.initialize()
        
        importance = await self.importance_evaluator.evaluate_importance(memory)
        return importance
    
    async def forget_memories(
        self,
        filters: Dict[str, Any]
    ) -> int:
        """
        遗忘符合条件的记忆
        
        参数:
            filters: Dict[str, Any] - 过滤条件
            
        返回:
            int - 成功遗忘的记忆数量
        """
        # TODO: 实现记忆遗忘逻辑
        # 这需要与向量存储和图存储的具体删除实现结合
        logger.warning("记忆遗忘功能尚未实现")
        return 0
    
    async def get_context_for_agent(
        self,
        agent_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        获取适合特定智能体的上下文
        
        参数:
            agent_id: str - 智能体ID
            context: Dict[str, Any] - 当前上下文信息
            
        返回:
            Dict[str, Any] - 增强的上下文
        """
        # 确保已初始化
        if not self._initialized:
            await self.initialize()
        
        # 获取任务相关信息
        task_id = context.get("task_id")
        if not task_id:
            logger.warning(f"获取上下文时缺少task_id")
            return context
        
        # 构建查询
        query = f"Agent: {agent_id}, Task: {task_id}"
        if "query" in context:
            query += f", Query: {context['query']}"
        
        # 构建过滤条件
        filters = {
            "source": agent_id  # 智能体自己的记忆
        }
        
        # 检索相关记忆
        memories = await self.retrieve_memories(query, limit=10, filters=filters)
        
        # 构建增强上下文
        enhanced_context = context.copy()
        if memories:
            # 生成记忆摘要
            memory_summary = await self.summarize_memories(memories)
            
            # 添加到上下文
            enhanced_context["memory_summary"] = memory_summary
            enhanced_context["related_memories"] = [
                {
                    "id": memory.get("id"),
                    "content": memory.get("content"),
                    "importance": memory.get("importance"),
                    "created_at": memory.get("created_at")
                }
                for memory in memories[:3]  # 只包含前3条最相关的完整记忆
            ]
        
        return enhanced_context
    
    async def _handle_query(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        处理查询类消息
        
        参数:
            message: Dict[str, Any] - 消息内容
            
        返回:
            Optional[Dict[str, Any]] - 响应消息
        """
        # 从通用处理逻辑派生
        await super()._handle_query(message)
        
        content = message.get("content", {})
        action = content.get("action")
        
        if action == "retrieve":
            # 检索记忆
            query = content.get("query", "")
            limit = content.get("limit", 10)
            filters = content.get("filters")
            
            memories = await self.retrieve_memories(query, limit, filters)
            
            return {
                "command_type": "response",
                "content": {
                    "status": "success",
                    "memories": memories,
                    "total": len(memories),
                    "query": query
                },
                "source_id": self.id,
                "target_ids": [message.get("source_id")]
            }
            
        elif action == "summarize":
            # 总结记忆
            memories = content.get("memories", [])
            
            summary = await self.summarize_memories(memories)
            
            return {
                "command_type": "response",
                "content": {
                    "status": "success",
                    "summary": summary,
                    "memory_count": len(memories)
                },
                "source_id": self.id,
                "target_ids": [message.get("source_id")]
            }
            
        elif action == "get_context":
            # 获取上下文
            agent_id = content.get("agent_id")
            context_info = content.get("context", {})
            
            if not agent_id:
                return {
                    "command_type": "response",
                    "content": {
                        "status": "error",
                        "message": "缺少agent_id参数"
                    },
                    "source_id": self.id,
                    "target_ids": [message.get("source_id")]
                }
            
            enhanced_context = await self.get_context_for_agent(agent_id, context_info)
            
            return {
                "command_type": "response",
                "content": {
                    "status": "success",
                    "context": enhanced_context
                },
                "source_id": self.id,
                "target_ids": [message.get("source_id")]
            }
            
        else:
            # 未知操作
            return {
                "command_type": "response",
                "content": {
                    "status": "error",
                    "message": f"不支持的操作: {action}"
                },
                "source_id": self.id,
                "target_ids": [message.get("source_id")]
            }
    
    async def _handle_action(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        处理动作类消息
        
        参数:
            message: Dict[str, Any] - 消息内容
            
        返回:
            Optional[Dict[str, Any]] - 响应消息
        """
        # 从通用处理逻辑派生
        await super()._handle_action(message)
        
        content = message.get("content", {})
        action = content.get("action")
        
        if action == "store":
            # 存储记忆
            memory_data = content.get("memory")
            context = content.get("context")
            
            if not memory_data:
                return {
                    "command_type": "response",
                    "content": {
                        "status": "error",
                        "message": "缺少memory参数"
                    },
                    "source_id": self.id,
                    "target_ids": [message.get("source_id")]
                }
            
            try:
                memory_id = await self.store_memory(memory_data, context)
                
                return {
                    "command_type": "response",
                    "content": {
                        "status": "success",
                        "memory_id": memory_id
                    },
                    "source_id": self.id,
                    "target_ids": [message.get("source_id")]
                }
            except ValueError as e:
                return {
                    "command_type": "response",
                    "content": {
                        "status": "error",
                        "message": str(e)
                    },
                    "source_id": self.id,
                    "target_ids": [message.get("source_id")]
                }
                
        elif action == "update":
            # 更新记忆
            memory_id = content.get("memory_id")
            updates = content.get("updates")
            
            if not memory_id or not updates:
                return {
                    "command_type": "response",
                    "content": {
                        "status": "error",
                        "message": "缺少memory_id或updates参数"
                    },
                    "source_id": self.id,
                    "target_ids": [message.get("source_id")]
                }
            
            try:
                updated_memory = await self.update_memory(memory_id, updates)
                
                return {
                    "command_type": "response",
                    "content": {
                        "status": "success",
                        "memory": updated_memory
                    },
                    "source_id": self.id,
                    "target_ids": [message.get("source_id")]
                }
            except ValueError as e:
                return {
                    "command_type": "response",
                    "content": {
                        "status": "error",
                        "message": str(e)
                    },
                    "source_id": self.id,
                    "target_ids": [message.get("source_id")]
                }
                
        elif action == "evaluate":
            # 评估记忆重要性
            memory_data = content.get("memory")
            
            if not memory_data:
                return {
                    "command_type": "response",
                    "content": {
                        "status": "error",
                        "message": "缺少memory参数"
                    },
                    "source_id": self.id,
                    "target_ids": [message.get("source_id")]
                }
            
            importance = await self.evaluate_importance(memory_data)
            
            return {
                "command_type": "response",
                "content": {
                    "status": "success",
                    "importance": importance
                },
                "source_id": self.id,
                "target_ids": [message.get("source_id")]
            }
            
        else:
            # 未知操作
            return {
                "command_type": "response",
                "content": {
                    "status": "error",
                    "message": f"不支持的操作: {action}"
                },
                "source_id": self.id,
                "target_ids": [message.get("source_id")]
            }
