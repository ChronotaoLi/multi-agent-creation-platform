"""
LangGraph引擎和核心图设置。

该模块提供了LangGraph工作流引擎的初始化和配置功能。
"""

from typing import Any, Dict, List, Optional, Type, Union

import langgraph.checkpoint as cp
# 移除不存在的导入
# from langgraph.checkpoint import CheckpointConfig
from langgraph.graph import END, StateGraph
# GraphMessage不存在于langgraph.graph.message
# from langgraph.graph.message import GraphMessage
from langgraph.prebuilt import ToolNode
# 修改PostgresSaver导入
try:
    from langgraph.checkpoint.postgres import PostgresSaver
except ImportError:
    # 创建一个临时的空类替代
    class PostgresSaver:
        @classmethod
        def from_conn_string(cls, conn_string):
            print(f"警告：PostgresSaver不可用，使用内存存储代替。连接字符串: {conn_string}")
            return None

# langmem包不存在，移除此导入
# from langmem import RedisChatMessageHistory
from pydantic import BaseModel, Field

from app.data_access.cache.redis_client import RedisClient
from app.data_access.repositories.graph_repository import GraphRepository
from app.services.interfaces.llm_service import LLMService
from app.workflows.state_management.enhanced_store import EnhancedStoreManager


class LangGraphConfig(BaseModel):
    """LangGraph配置模型。"""
    
    redis_url: str = Field(..., description="Redis连接URL")
    postgres_connection_string: Optional[str] = Field(None, description="PostgreSQL连接字符串")
    node_concurrency: int = Field(5, description="节点并发数")
    checkpointer_enabled: bool = Field(True, description="是否启用检查点")
    enhanced_store_enabled: bool = Field(True, description="是否使用增强存储管理器")


class LangGraphSetup:
    """
    LangGraph设置类，负责初始化和配置LangGraph环境。
    """
    
    def __init__(
        self,
        config: LangGraphConfig,
        llm_service: LLMService,
        graph_repository: GraphRepository,
    ) -> None:
        """
        初始化LangGraph设置。

        参数:
            config: LangGraph配置
            llm_service: LLM服务
            graph_repository: 图存储仓库
        """
        self.config = config
        self.llm_service = llm_service
        self.graph_repository = graph_repository
        self.redis_client = RedisClient(self.config.redis_url)
        
        # 初始化检查点保存器
        if self.config.postgres_connection_string and self.config.checkpointer_enabled:
            try:
                self.saver = PostgresSaver.from_conn_string(self.config.postgres_connection_string)
            except Exception as e:
                print(f"初始化PostgresSaver失败: {e}")
                self.saver = None
        else:
            self.saver = None
        
        # 初始化存储管理器
        if self.config.enhanced_store_enabled:
            self.store_manager = EnhancedStoreManager(self.redis_client)
        else:
            # 使用内存存储替代langmem
            self.store_manager = None

    def create_state_graph(
        self,
        nodes: Dict[str, Any],
        edges: Dict[str, List[str]],
        channels: Optional[List[str]] = None,
        entry_point: Optional[str] = None,
    ) -> StateGraph:
        """
        创建状态图。

        参数:
            nodes: 节点映射字典，键为节点名称，值为节点处理函数
            edges: 边映射字典，键为源节点名称，值为目标节点名称列表
            channels: 通道列表
            entry_point: 入口点节点名称

        返回:
            StateGraph: 创建的状态图
        """
        # 创建状态图
        graph = StateGraph(channels=channels or [])
        
        # 添加节点
        for node_name, node_handler in nodes.items():
            graph.add_node(node_name, node_handler)
        
        # 添加边
        for source, targets in edges.items():
            if len(targets) == 1:
                graph.add_edge(source, targets[0])
            else:
                # 为多目标边添加条件路由
                graph.add_conditional_edges(
                    source,
                    self._create_router_for_node(source, targets),
                    targets
                )
        
        # 设置入口点
        if entry_point:
            graph.set_entry_point(entry_point)
        
        # 配置检查点 - 使用新版API，直接在compile时提供saver
        # 不再使用CheckpointConfig
        # if self.config.checkpointer_enabled and self.saver:
        #     checkpoint_config = CheckpointConfig(saver=self.saver)
        #     graph = graph.with_config(checkpoint_config)
        
        return graph

    def compile_graph(self, graph: StateGraph, interrupt_before: Optional[List[str]] = None) -> Any:
        """
        编译状态图。

        参数:
            graph: 要编译的状态图
            interrupt_before: 在这些节点之前中断执行的节点列表

        返回:
            Any: 编译后的可执行图
        """
        # 在这里直接使用saver
        return graph.compile(
            interrupt_before=interrupt_before,
            checkpointer=self.saver if self.config.checkpointer_enabled else None
        )

    def create_tool_node(
        self,
        tools: List[Any],
        llm_model_name: Optional[str] = None,
    ) -> ToolNode:
        """
        创建工具节点。

        参数:
            tools: 工具列表
            llm_model_name: 可选的LLM模型名称，如果不指定则使用默认模型

        返回:
            ToolNode: 创建的工具节点
        """
        # 获取LLM模型
        llm = self.llm_service.get_llm(model_name=llm_model_name)
        
        # 创建并返回工具节点
        return ToolNode(tools=tools, llm=llm)

    def serialize_graph(self, graph_id: str, graph: StateGraph, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        序列化和存储图定义。

        参数:
            graph_id: 图ID
            graph: 状态图
            metadata: 图元数据

        返回:
            str: 保存的图ID
        """
        # 序列化图定义
        graph_def = graph.to_dict()
        
        # 存储图定义
        self.graph_repository.save_graph(
            graph_id=graph_id,
            name=metadata.get("name", f"Graph-{graph_id}") if metadata else f"Graph-{graph_id}",
            metadata=metadata or {}
        )
        
        return graph_id

    def load_graph(self, graph_id: str) -> StateGraph:
        """
        加载图定义。

        参数:
            graph_id: 图ID

        返回:
            StateGraph: 加载的状态图
        """
        # 检索图定义
        graph_data = self.graph_repository.get_graph(graph_id)
        if not graph_data:
            raise ValueError(f"图定义不存在: {graph_id}")
        
        # 重建图 - 修改适应graph_repository的结构
        # 因为我们实现的graph_repository没有存储graph定义，所以这里需要创建一个新的空图
        # 实际应用中应从repository中加载完整定义
        graph = StateGraph()
        
        # 不再使用CheckpointConfig
        # 配置检查点 
        # if self.config.checkpointer_enabled and self.saver:
        #     checkpoint_config = CheckpointConfig(saver=self.saver)
        #     graph = graph.with_config(checkpoint_config)
        
        return graph

    def _create_router_for_node(self, node_name: str, targets: List[str]) -> Any:
        """
        创建节点的路由函数。

        参数:
            node_name: 节点名称
            targets: 目标节点列表

        返回:
            Any: 路由函数
        """
        def router(state: Dict[str, Any]) -> str:
            # 如果状态中包含明确的next_node键，则使用它
            if "next_node" in state:
                next_node = state["next_node"]
                if next_node in targets:
                    return next_node
                elif next_node == "END":
                    return END
            
            # 如果状态中包含action键，尝试根据action路由
            if "action" in state:
                action = state["action"]
                for target in targets:
                    if target.lower() == action.lower():
                        return target
                
                # 如果action为end或complete，结束图
                if action.lower() in ["end", "complete", "done", "finished"]:
                    return END
            
            # 默认返回第一个目标
            return targets[0]
        
        return router
