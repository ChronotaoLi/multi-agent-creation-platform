"""
子图管理器实现。

该模块提供了创建、管理和执行子图的功能，支持动态构建和执行LangGraph子图。
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, Union

from langgraph.graph import Graph, StateGraph
# 移除对 GraphMessage 的导入，这可能是在更新的 langgraph 版本中不存在的
# from langgraph.graph.message import GraphMessage
from pydantic import BaseModel

from app.data_access.repositories.graph_repository import GraphRepository
from app.models.domain.graph_models import GraphDefinition, SubgraphMetadata
from app.services.interfaces.llm_service import LLMService
from app.workflows.langgraph_setup import LangGraphSetup


class SubgraphManager:
    """
    子图管理器，负责创建和执行子图。
    
    提供子图的创建、存储、加载和执行功能。
    """
    
    def __init__(
        self,
        langgraph_setup: LangGraphSetup,
        graph_repository: GraphRepository,
        llm_service: LLMService
    ) -> None:
        """
        初始化子图管理器。

        参数:
            langgraph_setup: LangGraph设置
            graph_repository: 图存储仓库
            llm_service: LLM服务
        """
        self.langgraph_setup = langgraph_setup
        self.graph_repository = graph_repository
        self.llm_service = llm_service
        self.active_subgraphs: Dict[str, Any] = {}
        
    def create_subgraph(
        self, 
        name: str, 
        nodes: Dict[str, Any], 
        edges: Dict[str, List[str]],
        channels: Optional[List[str]] = None,
        entry_point: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        project_id: Optional[str] = None
    ) -> str:
        """
        创建子图并将其存储在仓库中。

        参数:
            name: 子图名称
            nodes: 节点映射字典，键为节点名称，值为节点处理函数
            edges: 边映射字典，键为源节点名称，值为目标节点名称列表
            channels: 通道列表
            entry_point: 入口点节点名称
            metadata: 子图元数据
            project_id: 关联的项目ID

        返回:
            str: 子图ID
        """
        # 生成子图ID
        graph_id = str(uuid.uuid4())
        
        # 创建状态图
        graph = self.langgraph_setup.create_state_graph(
            nodes=nodes,
            edges=edges,
            channels=channels,
            entry_point=entry_point
        )
        
        # 准备元数据
        full_metadata = metadata or {}
        full_metadata.update({
            "name": name,
            "type": "subgraph",
            "project_id": project_id,
            "created_at": str(datetime.utcnow()),
            "node_count": len(nodes),
            "edge_count": len(edges)
        })
        
        # 序列化和存储图定义
        self.langgraph_setup.serialize_graph(graph_id, graph, full_metadata)
        
        return graph_id
    
    def load_subgraph(self, graph_id: str) -> StateGraph:
        """
        加载子图定义。

        参数:
            graph_id: 子图ID

        返回:
            StateGraph: 加载的状态图
        """
        return self.langgraph_setup.load_graph(graph_id)
    
    def get_compiled_subgraph(self, graph_id: str) -> Any:
        """
        获取已编译的子图。

        参数:
            graph_id: 子图ID

        返回:
            Any: 编译后的可执行子图
        """
        # 如果子图已经在活跃缓存中，直接返回
        if graph_id in self.active_subgraphs:
            return self.active_subgraphs[graph_id]
        
        # 否则加载并编译子图
        graph = self.load_subgraph(graph_id)
        compiled_graph = self.langgraph_setup.compile_graph(graph)
        
        # 缓存编译后的图
        self.active_subgraphs[graph_id] = compiled_graph
        
        return compiled_graph
    
    def execute_subgraph(
        self, 
        graph_id: str, 
        inputs: Dict[str, Any], 
        config: Optional[Dict[str, Any]] = None,
        thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        执行子图。

        参数:
            graph_id: 子图ID
            inputs: 输入数据
            config: 执行配置
            thread_id: 线程ID，用于检查点恢复

        返回:
            Dict[str, Any]: 执行结果
        """
        # 获取已编译的子图
        graph = self.get_compiled_subgraph(graph_id)
        
        # 准备执行配置
        execution_config = config or {}
        if thread_id:
            execution_config["configurable"] = {"thread_id": thread_id}
        
        # 执行图
        try:
            result = graph.invoke(inputs, execution_config)
            return result
        except Exception as e:
            raise RuntimeError(f"子图执行失败: {str(e)}") from e
    
    async def aexecute_subgraph(
        self, 
        graph_id: str, 
        inputs: Dict[str, Any], 
        config: Optional[Dict[str, Any]] = None,
        thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        异步执行子图。

        参数:
            graph_id: 子图ID
            inputs: 输入数据
            config: 执行配置
            thread_id: 线程ID，用于检查点恢复

        返回:
            Dict[str, Any]: 执行结果
        """
        # 获取已编译的子图
        graph = self.get_compiled_subgraph(graph_id)
        
        # 准备执行配置
        execution_config = config or {}
        if thread_id:
            execution_config["configurable"] = {"thread_id": thread_id}
        
        # 异步执行图
        try:
            result = await graph.ainvoke(inputs, execution_config)
            return result
        except Exception as e:
            raise RuntimeError(f"子图异步执行失败: {str(e)}") from e
    
    def stream_subgraph(
        self, 
        graph_id: str, 
        inputs: Dict[str, Any], 
        config: Optional[Dict[str, Any]] = None,
        thread_id: Optional[str] = None
    ):
        """
        流式执行子图。

        参数:
            graph_id: 子图ID
            inputs: 输入数据
            config: 执行配置
            thread_id: 线程ID，用于检查点恢复

        返回:
            Iterator: 执行结果流
        """
        # 获取已编译的子图
        graph = self.get_compiled_subgraph(graph_id)
        
        # 准备执行配置
        execution_config = config or {}
        if thread_id:
            execution_config["configurable"] = {"thread_id": thread_id}
        
        # 流式执行图
        try:
            return graph.stream(inputs, execution_config)
        except Exception as e:
            raise RuntimeError(f"子图流式执行失败: {str(e)}") from e
    
    async def astream_subgraph(
        self, 
        graph_id: str, 
        inputs: Dict[str, Any], 
        config: Optional[Dict[str, Any]] = None,
        thread_id: Optional[str] = None
    ):
        """
        异步流式执行子图。

        参数:
            graph_id: 子图ID
            inputs: 输入数据
            config: 执行配置
            thread_id: 线程ID，用于检查点恢复

        返回:
            AsyncIterator: 执行结果流
        """
        # 获取已编译的子图
        graph = self.get_compiled_subgraph(graph_id)
        
        # 准备执行配置
        execution_config = config or {}
        if thread_id:
            execution_config["configurable"] = {"thread_id": thread_id}
        
        # 异步流式执行图
        try:
            async for event in graph.astream(inputs, execution_config):
                yield event
        except Exception as e:
            raise RuntimeError(f"子图异步流式执行失败: {str(e)}") from e
    
    def list_subgraphs(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        列出子图。

        参数:
            project_id: 可选的项目ID过滤

        返回:
            List[Dict[str, Any]]: 子图元数据列表
        """
        filters = {"metadata.type": "subgraph"}
        if project_id:
            filters["metadata.project_id"] = project_id
            
        return self.graph_repository.list_graphs(filters)
    
    def delete_subgraph(self, graph_id: str) -> bool:
        """
        删除子图。

        参数:
            graph_id: 子图ID

        返回:
            bool: 操作是否成功
        """
        # 从活跃缓存中移除
        if graph_id in self.active_subgraphs:
            del self.active_subgraphs[graph_id]
        
        # 从仓库中删除
        return self.graph_repository.delete_graph(graph_id)
    
    def update_subgraph_metadata(self, graph_id: str, metadata: Dict[str, Any]) -> bool:
        """
        更新子图元数据。

        参数:
            graph_id: 子图ID
            metadata: 更新的元数据

        返回:
            bool: 操作是否成功
        """
        graph_data = self.graph_repository.get_graph(graph_id)
        if not graph_data:
            return False
            
        # 更新元数据
        updated_metadata = graph_data["metadata"].copy()
        updated_metadata.update(metadata)
        
        return self.graph_repository.update_graph_metadata(graph_id, updated_metadata)
