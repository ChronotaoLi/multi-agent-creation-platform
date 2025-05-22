"""
图模型定义。

该模块定义了与图处理相关的领域模型。
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """节点类型枚举。"""
    
    AGENT = "agent"           # 智能体节点
    CONCEPT = "concept"       # 概念节点
    KNOWLEDGE = "knowledge"   # 知识节点
    ACTION = "action"         # 行动节点
    TASK = "task"             # 任务节点
    EVENT = "event"           # 事件节点
    ARTIFACT = "artifact"     # 制品节点
    RESOURCE = "resource"     # 资源节点
    CUSTOM = "custom"         # 自定义节点


class EdgeType(str, Enum):
    """边类型枚举。"""
    
    CONTAINS = "contains"         # 包含关系
    DEPENDS_ON = "depends_on"     # 依赖关系
    PRODUCES = "produces"         # 产生关系
    CONSUMES = "consumes"         # 消费关系
    REFERENCES = "references"     # 引用关系
    COLLABORATES = "collaborates" # 协作关系
    DELEGATES = "delegates"       # 委派关系
    IMPLEMENTS = "implements"     # 实现关系
    CUSTOM = "custom"             # 自定义关系


class NodeProperties(BaseModel):
    """节点属性模型。"""
    
    description: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class EdgeProperties(BaseModel):
    """边属性模型。"""
    
    description: Optional[str] = None
    weight: float = 1.0
    attributes: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class Node(BaseModel):
    """节点模型。"""
    
    id: str
    name: str
    type: NodeType
    properties: NodeProperties = Field(default_factory=NodeProperties)


class Edge(BaseModel):
    """边模型。"""
    
    id: str
    source_id: str
    target_id: str
    type: EdgeType
    properties: EdgeProperties = Field(default_factory=EdgeProperties)


class GraphDefinition(BaseModel):
    """图定义模型。"""
    
    id: str
    name: str
    description: Optional[str] = None
    nodes: List[Node] = Field(default_factory=list)
    edges: List[Edge] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def add_node(self, node: Node) -> None:
        """
        添加节点。
        
        参数:
            node: 要添加的节点
        """
        # 检查是否已存在相同ID的节点
        if any(n.id == node.id for n in self.nodes):
            raise ValueError(f"节点ID已存在: {node.id}")
        
        self.nodes.append(node)
        self.updated_at = datetime.utcnow()
    
    def add_edge(self, edge: Edge) -> None:
        """
        添加边。
        
        参数:
            edge: 要添加的边
        """
        # 检查是否已存在相同ID的边
        if any(e.id == edge.id for e in self.edges):
            raise ValueError(f"边ID已存在: {edge.id}")
        
        # 检查源节点和目标节点是否存在
        source_exists = any(n.id == edge.source_id for n in self.nodes)
        target_exists = any(n.id == edge.target_id for n in self.nodes)
        
        if not source_exists:
            raise ValueError(f"源节点不存在: {edge.source_id}")
        
        if not target_exists:
            raise ValueError(f"目标节点不存在: {edge.target_id}")
        
        self.edges.append(edge)
        self.updated_at = datetime.utcnow()
    
    def remove_node(self, node_id: str) -> None:
        """
        移除节点。
        
        参数:
            node_id: 要移除的节点ID
        """
        # 移除节点
        self.nodes = [n for n in self.nodes if n.id != node_id]
        
        # 移除相关的边
        self.edges = [e for e in self.edges if e.source_id != node_id and e.target_id != node_id]
        
        self.updated_at = datetime.utcnow()
    
    def remove_edge(self, edge_id: str) -> None:
        """
        移除边。
        
        参数:
            edge_id: 要移除的边ID
        """
        self.edges = [e for e in self.edges if e.id != edge_id]
        self.updated_at = datetime.utcnow()


class SubgraphMetadata(BaseModel):
    """子图元数据模型。"""
    
    parent_graph_id: Optional[str] = None
    source_node_ids: Set[str] = Field(default_factory=set)
    target_node_ids: Set[str] = Field(default_factory=set)
    extraction_method: str = "manual"  # 可以是manual, auto, algorithm等
    extraction_parameters: Dict[str, Any] = Field(default_factory=dict)
    is_temporary: bool = False
    ttl_seconds: Optional[int] = None  # 临时子图的生存时间（秒） 