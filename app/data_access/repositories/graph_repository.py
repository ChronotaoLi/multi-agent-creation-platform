"""
图存储仓库实现。

该模块提供了对图数据的存储和检索功能。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


class GraphRepository:
    """
    图存储仓库，负责图数据的持久化。
    """
    
    def __init__(self) -> None:
        """初始化图存储仓库。"""
        # 使用内存字典作为临时存储，实际应用中应使用图数据库
        self._graphs: Dict[str, Dict[str, Any]] = {}
        self._nodes: Dict[str, Dict[str, Any]] = {}
        self._edges: Dict[str, Dict[str, Any]] = {}
    
    def save_graph(
        self,
        graph_id: str,
        name: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        保存图数据。

        参数:
            graph_id: 图ID
            name: 图名称
            description: 图描述
            metadata: 元数据
            created_at: 创建时间
            updated_at: 更新时间

        返回:
            Dict[str, Any]: 图数据
        """
        now = datetime.utcnow()
        graph_data = {
            "graph_id": graph_id,
            "name": name,
            "description": description,
            "metadata": metadata or {},
            "created_at": created_at or now,
            "updated_at": updated_at or now
        }
        self._graphs[graph_id] = graph_data
        return graph_data
    
    async def asave_graph(
        self,
        graph_id: str,
        name: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        异步保存图数据。

        参数:
            graph_id: 图ID
            name: 图名称
            description: 图描述
            metadata: 元数据
            created_at: 创建时间
            updated_at: 更新时间

        返回:
            Dict[str, Any]: 图数据
        """
        # 异步版本，在内存实现中与同步版本相同
        return self.save_graph(
            graph_id, name, description, metadata, created_at, updated_at
        )
    
    def get_graph(self, graph_id: str) -> Optional[Dict[str, Any]]:
        """
        获取图数据。

        参数:
            graph_id: 图ID

        返回:
            Dict[str, Any]: 图数据，若不存在则返回None
        """
        return self._graphs.get(graph_id)
    
    async def aget_graph(self, graph_id: str) -> Optional[Dict[str, Any]]:
        """
        异步获取图数据。

        参数:
            graph_id: 图ID

        返回:
            Dict[str, Any]: 图数据，若不存在则返回None
        """
        # 异步版本，在内存实现中与同步版本相同
        return self.get_graph(graph_id)
    
    def list_graphs(
        self, filter_criteria: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        列出图。

        参数:
            filter_criteria: 过滤条件（可选）

        返回:
            List[Dict[str, Any]]: 图列表
        """
        graphs = list(self._graphs.values())
        
        # 根据条件过滤
        if filter_criteria:
            filtered_graphs = []
            for graph in graphs:
                match = True
                for key, value in filter_criteria.items():
                    if key in graph and graph[key] != value:
                        match = False
                        break
                if match:
                    filtered_graphs.append(graph)
            graphs = filtered_graphs
        
        # 排序：最新的排在前面
        graphs.sort(key=lambda x: x["updated_at"], reverse=True)
        
        return graphs
    
    async def alist_graphs(
        self, filter_criteria: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        异步列出图。

        参数:
            filter_criteria: 过滤条件（可选）

        返回:
            List[Dict[str, Any]]: 图列表
        """
        # 异步版本，在内存实现中与同步版本相同
        return self.list_graphs(filter_criteria)
    
    def save_node(
        self,
        node_id: str,
        graph_id: str,
        name: str,
        node_type: str,
        properties: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        保存节点数据。

        参数:
            node_id: 节点ID
            graph_id: 图ID
            name: 节点名称
            node_type: 节点类型
            properties: 节点属性
            created_at: 创建时间
            updated_at: 更新时间

        返回:
            Dict[str, Any]: 节点数据
        """
        now = datetime.utcnow()
        node_data = {
            "node_id": node_id,
            "graph_id": graph_id,
            "name": name,
            "node_type": node_type,
            "properties": properties or {},
            "created_at": created_at or now,
            "updated_at": updated_at or now
        }
        self._nodes[node_id] = node_data
        return node_data
    
    async def asave_node(
        self,
        node_id: str,
        graph_id: str,
        name: str,
        node_type: str,
        properties: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        异步保存节点数据。

        参数:
            node_id: 节点ID
            graph_id: 图ID
            name: 节点名称
            node_type: 节点类型
            properties: 节点属性
            created_at: 创建时间
            updated_at: 更新时间

        返回:
            Dict[str, Any]: 节点数据
        """
        # 异步版本，在内存实现中与同步版本相同
        return self.save_node(
            node_id, graph_id, name, node_type, properties, created_at, updated_at
        )
    
    def save_edge(
        self,
        edge_id: str,
        graph_id: str,
        source_id: str,
        target_id: str,
        edge_type: str,
        properties: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        保存边数据。

        参数:
            edge_id: 边ID
            graph_id: 图ID
            source_id: 源节点ID
            target_id: 目标节点ID
            edge_type: 边类型
            properties: 边属性
            created_at: 创建时间
            updated_at: 更新时间

        返回:
            Dict[str, Any]: 边数据
        """
        now = datetime.utcnow()
        edge_data = {
            "edge_id": edge_id,
            "graph_id": graph_id,
            "source_id": source_id,
            "target_id": target_id,
            "edge_type": edge_type,
            "properties": properties or {},
            "created_at": created_at or now,
            "updated_at": updated_at or now
        }
        self._edges[edge_id] = edge_data
        return edge_data
    
    async def asave_edge(
        self,
        edge_id: str,
        graph_id: str,
        source_id: str,
        target_id: str,
        edge_type: str,
        properties: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        异步保存边数据。

        参数:
            edge_id: 边ID
            graph_id: 图ID
            source_id: 源节点ID
            target_id: 目标节点ID
            edge_type: 边类型
            properties: 边属性
            created_at: 创建时间
            updated_at: 更新时间

        返回:
            Dict[str, Any]: 边数据
        """
        # 异步版本，在内存实现中与同步版本相同
        return self.save_edge(
            edge_id, graph_id, source_id, target_id, edge_type, properties, created_at, updated_at
        )
        
    def get_graph_nodes(self, graph_id: str) -> List[Dict[str, Any]]:
        """
        获取图的所有节点。

        参数:
            graph_id: 图ID

        返回:
            List[Dict[str, Any]]: 节点列表
        """
        return [node for node in self._nodes.values() if node["graph_id"] == graph_id]
    
    async def aget_graph_nodes(self, graph_id: str) -> List[Dict[str, Any]]:
        """
        异步获取图的所有节点。

        参数:
            graph_id: 图ID

        返回:
            List[Dict[str, Any]]: 节点列表
        """
        # 异步版本，在内存实现中与同步版本相同
        return self.get_graph_nodes(graph_id)
    
    def get_graph_edges(self, graph_id: str) -> List[Dict[str, Any]]:
        """
        获取图的所有边。

        参数:
            graph_id: 图ID

        返回:
            List[Dict[str, Any]]: 边列表
        """
        return [edge for edge in self._edges.values() if edge["graph_id"] == graph_id]
    
    async def aget_graph_edges(self, graph_id: str) -> List[Dict[str, Any]]:
        """
        异步获取图的所有边。

        参数:
            graph_id: 图ID

        返回:
            List[Dict[str, Any]]: 边列表
        """
        # 异步版本，在内存实现中与同步版本相同
        return self.get_graph_edges(graph_id)
    
    def delete_graph(self, graph_id: str) -> bool:
        """
        删除图。

        参数:
            graph_id: 图ID

        返回:
            bool: 操作是否成功
        """
        if graph_id in self._graphs:
            del self._graphs[graph_id]
            
            # 删除关联的节点和边
            self._nodes = {k: v for k, v in self._nodes.items() if v["graph_id"] != graph_id}
            self._edges = {k: v for k, v in self._edges.items() if v["graph_id"] != graph_id}
            
            return True
        return False
    
    async def adelete_graph(self, graph_id: str) -> bool:
        """
        异步删除图。

        参数:
            graph_id: 图ID

        返回:
            bool: 操作是否成功
        """
        # 异步版本，在内存实现中与同步版本相同
        return self.delete_graph(graph_id) 