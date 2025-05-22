"""
搜索工具模块

提供各种基于向量存储和图数据库的搜索工具
"""

import logging
from typing import Any, Dict, List, Optional, Union

from app.agents.tools import BaseTool
from app.data_access.vector_store.milvus_client import MilvusClient
from app.data_access.graph_store.neo4j_client import Neo4jClient
from app.data_access.llm_adapter.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class VectorSearchTool(BaseTool):
    """
    向量搜索工具
    
    基于向量相似度的搜索工具
    """
    
    def __init__(self, vector_store: MilvusClient, embedding_service: EmbeddingService):
        """
        初始化向量搜索工具
        
        参数:
            vector_store: 向量存储客户端
            embedding_service: 嵌入服务
        """
        super().__init__(
            name="vector_search",
            description="使用向量相似度搜索文本或文档"
        )
        self.vector_store = vector_store
        self.embedding_service = embedding_service
    
    async def __call__(self, query: str, limit: int = 10, filter_dict: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        执行向量搜索
        
        参数:
            query: 搜索查询
            limit: 返回结果数量限制
            filter_dict: 过滤条件字典
            
        返回:
            List[Dict[str, Any]]: 搜索结果列表
        """
        try:
            # 生成查询嵌入
            query_embedding = await self.embedding_service.get_embedding(query)
            
            # 执行搜索
            results = await self.vector_store.search(
                collection_name="documents",  # 假设使用名为documents的集合
                query_vector=query_embedding,
                limit=limit,
                filter_expr=filter_dict
            )
            
            return results
        except Exception as e:
            logger.error(f"向量搜索失败: {str(e)}")
            return []


class GraphSearchTool(BaseTool):
    """
    图搜索工具
    
    基于图结构的搜索工具
    """
    
    def __init__(self, graph_store: Neo4jClient):
        """
        初始化图搜索工具
        
        参数:
            graph_store: 图存储客户端
        """
        super().__init__(
            name="graph_search",
            description="使用图数据库查询相关信息和关系"
        )
        self.graph_store = graph_store
    
    async def __call__(self, query: str, limit: int = 10, node_labels: List[str] = None) -> List[Dict[str, Any]]:
        """
        执行图搜索
        
        参数:
            query: 搜索查询
            limit: 返回结果数量限制
            node_labels: 节点标签列表，用于限制搜索范围
            
        返回:
            List[Dict[str, Any]]: 搜索结果列表
        """
        try:
            # 构建Cypher查询
            cypher_query = self._build_semantic_search_query(query, limit, node_labels)
            
            # 执行查询
            results = await self.graph_store.execute_query(cypher_query)
            
            return results
        except Exception as e:
            logger.error(f"图搜索失败: {str(e)}")
            return []
    
    def _build_semantic_search_query(self, query: str, limit: int, node_labels: List[str] = None) -> str:
        """
        构建语义搜索的Cypher查询
        
        参数:
            query: 搜索查询
            limit: 返回结果数量限制
            node_labels: 节点标签列表
            
        返回:
            str: Cypher查询语句
        """
        # 设置标签限制
        label_condition = ""
        if node_labels and len(node_labels) > 0:
            label_str = ":".join(node_labels)
            label_condition = f":{label_str}"
        
        # 基本查询模板，使用全文索引搜索
        # 假设存在名为document_fulltext的全文索引
        cypher_query = f"""
        CALL db.index.fulltext.queryNodes("document_fulltext", $query) 
        YIELD node, score
        WHERE node{label_condition}
        RETURN node {{
            .*,
            id: id(node),
            labels: labels(node),
            score: score,
            relationships: [(node)-[r]->(related) | {{
                type: type(r),
                properties: properties(r),
                target: {{
                    id: id(related),
                    labels: labels(related),
                    name: related.name
                }}
            }}]
        }} AS result
        ORDER BY score DESC
        LIMIT {limit}
        """
        
        return cypher_query


class SearchToolRegistry:
    """
    搜索工具注册表
    
    管理和提供各种搜索工具
    """
    
    def __init__(
        self,
        vector_store: Optional[MilvusClient] = None,
        graph_store: Optional[Neo4jClient] = None,
        embedding_service: Optional[EmbeddingService] = None
    ):
        """
        初始化搜索工具注册表
        
        参数:
            vector_store: 向量存储客户端
            graph_store: 图存储客户端
            embedding_service: 嵌入服务
        """
        self.tools: Dict[str, BaseTool] = {}
        self.vector_store = vector_store
        self.graph_store = graph_store
        self.embedding_service = embedding_service
        
        # 初始化默认工具
        self._init_default_tools()
    
    def _init_default_tools(self) -> None:
        """初始化默认搜索工具"""
        # 如果提供了必要的服务，创建向量搜索工具
        if self.vector_store and self.embedding_service:
            vector_search = VectorSearchTool(
                vector_store=self.vector_store,
                embedding_service=self.embedding_service
            )
            self.register_tool(vector_search)
            
        # 如果提供了图存储，创建图搜索工具
        if self.graph_store:
            graph_search = GraphSearchTool(
                graph_store=self.graph_store
            )
            self.register_tool(graph_search)
    
    def register_tool(self, tool: BaseTool) -> None:
        """
        注册工具
        
        参数:
            tool: 要注册的工具
        """
        self.tools[tool.name] = tool
        logger.info(f"注册搜索工具: {tool.name}")
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """
        获取工具
        
        参数:
            tool_name: 工具名称
            
        返回:
            Optional[BaseTool]: 找到的工具，不存在则返回None
        """
        return self.tools.get(tool_name)
    
    def list_tools(self) -> List[str]:
        """
        列出所有工具
        
        返回:
            List[str]: 工具名称列表
        """
        return list(self.tools.keys())
    
    async def search_vector_store(
        self,
        query: str,
        limit: int = 10,
        filter_dict: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索向量存储
        
        参数:
            query: 搜索查询
            limit: 返回结果数量限制
            filter_dict: 过滤条件字典
            
        返回:
            List[Dict[str, Any]]: 搜索结果列表
        """
        if "vector_search" not in self.tools:
            logger.warning("向量搜索工具未注册")
            return []
            
        tool = self.tools["vector_search"]
        return await tool(query, limit, filter_dict)
    
    async def search_graph_store(
        self,
        query: str,
        limit: int = 10,
        node_labels: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索图存储
        
        参数:
            query: 搜索查询
            limit: 返回结果数量限制
            node_labels: 节点标签列表
            
        返回:
            List[Dict[str, Any]]: 搜索结果列表
        """
        if "graph_search" not in self.tools:
            logger.warning("图搜索工具未注册")
            return []
            
        tool = self.tools["graph_search"]
        return await tool(query, limit, node_labels)
    
    async def hybrid_search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        混合搜索策略
        
        将向量搜索和图搜索结果结合
        
        参数:
            query: 搜索查询
            limit: 返回结果数量限制
            
        返回:
            List[Dict[str, Any]]: 搜索结果列表
        """
        # 并行执行向量搜索和图搜索
        import asyncio
        
        vector_results_future = self.search_vector_store(query, limit)
        graph_results_future = self.search_graph_store(query, limit)
        
        # 等待两个搜索完成
        vector_results, graph_results = await asyncio.gather(
            vector_results_future,
            graph_results_future
        )
        
        # 简单合并结果（实际应用中可能需要更复杂的融合策略）
        combined_results = []
        
        # 添加向量结果，并标记来源
        for result in vector_results:
            result["source"] = "vector"
            combined_results.append(result)
            
        # 添加图结果，并标记来源
        for result in graph_results:
            result["source"] = "graph"
            combined_results.append(result)
            
        # 简单去重（基于ID）
        seen_ids = set()
        unique_results = []
        
        for result in combined_results:
            result_id = result.get("id")
            if result_id and result_id not in seen_ids:
                seen_ids.add(result_id)
                unique_results.append(result)
                
        # 按相关性排序（假设结果中有score字段）
        sorted_results = sorted(
            unique_results,
            key=lambda x: x.get("score", 0),
            reverse=True
        )
        
        # 限制返回数量
        return sorted_results[:limit]
    
    def create_tool_node(self) -> 'ToolNode':
        """
        创建LangGraph工具节点
        
        返回:
            ToolNode: 工具节点
        """
        try:
            from app.agents.patterns.tool_use import ToolNode
            from app.services.interfaces.llm_service import get_llm_service
            
            llm_service = get_llm_service()
            
            return ToolNode(
                llm_service=llm_service,
                tools=list(self.tools.values())
            )
        except ImportError as e:
            logger.error(f"创建工具节点失败: {str(e)}")
            raise
    
    def setup_tools_condition(self) -> callable:
        """
        设置工具条件路由函数
        
        返回:
            callable: 条件函数
        """
        def route_to_tools(state):
            """工具路由条件函数"""
            # 检查状态中是否有工具使用标志
            return "use_tool" in state and state["use_tool"]
            
        return route_to_tools
