"""
创作工作流基类，定义所有创作模式共有的结构和行为
"""

from typing import Any, Callable, Dict, List, Optional, Type, TypedDict, Protocol, Iterator
import uuid
from datetime import datetime

from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from typing import Annotated

from ...agents.base_agent import BaseAgent
from ...agents.coordinator_agent import CoordinatorAgent
from ...data_access.event_bus.producers import EventProducer
from ...agents.communication.message_bus import MessageBus


class CreationState(TypedDict):
    """创作工作流状态模型"""
    workflow_type: str  # 工作流类型
    project_id: str  # 项目ID
    user_id: str  # 用户ID
    session_id: str  # 会话ID
    status: str  # 状态：initializing, planning, executing, reviewing, completed, error
    current_stage: str  # 当前阶段
    progress: float  # 进度（0-1）
    content: Dict[str, Any]  # 生成的内容
    messages: Annotated[List[Dict[str, Any]], add_messages]  # 消息历史
    error: Optional[Dict[str, Any]]  # 错误信息
    creation_logs: List[Dict[str, Any]]  # 创作日志
    awaiting_intervention: bool  # 是否等待用户干预
    intervention_data: Optional[Dict[str, Any]]  # 干预数据
    metadata: Dict[str, Any]  # 元数据
    created_at: str  # 创建时间
    updated_at: str  # 更新时间


class BaseWorkflow:
    """所有工作流的抽象基类"""
    pass


class BaseSaver(Protocol):
    """检查点保存器协议"""
    
    def get(self, config: Dict[str, Any]) -> Any:
        """获取检查点"""
        ...
    
    def put(self, config: Dict[str, Any], checkpoint: Any, metadata: Dict[str, Any], new_versions: Dict[str, Any]) -> Dict[str, Any]:
        """保存检查点"""
        ...
    
    def list(self, config: Dict[str, Any], **kwargs) -> Iterator[Dict[str, Any]]:
        """列出检查点"""
        ...


class CreationWorkflow(BaseWorkflow):
    """所有创作工作流的抽象基类，提供共通的创作流程框架"""
    
    def __init__(
        self,
        workflow_type: str,
        creation_state_schema: Type[CreationState] = CreationState,
        coordinator_agent: Optional[CoordinatorAgent] = None,
        message_bus: Optional[MessageBus] = None,
        checkpointer: Optional[BaseSaver] = None,
        checkpoint_interval: int = 5
    ):
        """
        初始化创作工作流

        参数:
            workflow_type: str - 工作流类型标识
            creation_state_schema: Type[CreationState] - 创作状态模式
            coordinator_agent: Optional[CoordinatorAgent] - 协调智能体实例
            message_bus: Optional[MessageBus] - 消息总线
            checkpointer: Optional[BaseSaver] - 检查点保存器
            checkpoint_interval: int - 检查点保存间隔
        """
        self.workflow_type = workflow_type
        self.creation_state_schema = creation_state_schema
        self.coordinator_agent = coordinator_agent
        self.agents_registry = {}  # 智能体注册表
        self.message_bus = message_bus
        self.event_producers = {}  # 事件生产者
        self.checkpoint_interval = checkpoint_interval
        self.checkpointer = checkpointer
        self._graph = None  # 工作流图实例
    
    def initialize(self, project_id: str, user_id: str, config: Dict[str, Any]) -> StateGraph:
        """
        初始化创作工作流图

        参数:
            project_id: str - 项目ID
            user_id: str - 用户ID
            config: Dict[str, Any] - 工作流配置

        返回:
            StateGraph - 初始化后的状态图
        """
        # 创建初始状态
        initial_state = self._create_initial_state(project_id, user_id, config)
        
        # 构建工作流图
        graph = self._build_graph()
        
        # 编译图
        self._graph = graph.compile(checkpointer=self.checkpointer)
        
        return self._graph
    
    def add_agents(self, agents: List[BaseAgent]) -> None:
        """
        向工作流添加智能体

        参数:
            agents: List[BaseAgent] - 要添加的智能体列表
        """
        for agent in agents:
            self.agents_registry[agent.agent_id] = agent
    
    def register_event_producer(self, name: str, producer: EventProducer) -> None:
        """
        注册事件生产者

        参数:
            name: str - 事件生产者名称
            producer: EventProducer - 事件生产者实例
        """
        self.event_producers[name] = producer
    
    def create_intervention_point(self, state: Dict[str, Any], intervention_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建用户干预点

        参数:
            state: Dict[str, Any] - 当前状态
            intervention_info: Dict[str, Any] - 干预信息

        返回:
            Dict[str, Any] - 包含干预信息的更新状态
        """
        # 这里使用LangGraph的interrupt函数创建干预点
        # 为每个干预点生成唯一ID
        intervention_id = str(uuid.uuid4())
        
        intervention_data = {
            "intervention_id": intervention_id,
            "type": intervention_info.get("type", "general"),
            "question": intervention_info.get("question", "需要您的输入"),
            "options": intervention_info.get("options", []),
            "context": intervention_info.get("context", {}),
            "created_at": datetime.utcnow().isoformat(),
        }
        
        # 更新状态以等待干预
        return {
            "awaiting_intervention": True,
            "intervention_data": intervention_data,
            "status": "awaiting_intervention"
        }
    
    def handle_intervention_result(self, state: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理用户干预结果

        参数:
            state: Dict[str, Any] - 当前状态
            result: Dict[str, Any] - 干预结果

        返回:
            Dict[str, Any] - 更新后的状态
        """
        # 记录用户干预结果
        intervention_log = {
            "type": "user_intervention",
            "intervention_id": state.get("intervention_data", {}).get("intervention_id"),
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # 添加到创作日志
        creation_logs = state.get("creation_logs", []) + [intervention_log]
        
        # 清除干预状态
        return {
            "awaiting_intervention": False,
            "intervention_data": None,
            "creation_logs": creation_logs,
            "status": state.get("status_before_intervention", "executing")
        }
    
    def create_checkpoint(self, state: Dict[str, Any]) -> None:
        """
        创建工作流状态检查点

        参数:
            state: Dict[str, Any] - 当前状态
        """
        if self.checkpointer:
            config = {
                "configurable": {
                    "thread_id": state.get("session_id"),
                    "user_id": state.get("user_id"),
                }
            }
            # 这个实现假设checkpointer是通过graph的compile方法设置的
            # 实际使用时需确保checkpointer正确设置
            pass
    
    def get_state_history(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        获取状态历史

        参数:
            config: Dict[str, Any] - 配置信息

        返回:
            List[Dict[str, Any]] - 状态历史列表
        """
        if self._graph:
            return list(self._graph.get_state_history(config))
        return []
    
    def _create_initial_state(self, project_id: str, user_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建初始创作状态

        参数:
            project_id: str - 项目ID
            user_id: str - 用户ID
            config: Dict[str, Any] - 工作流配置

        返回:
            Dict[str, Any] - 初始状态字典
        """
        session_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        return {
            "workflow_type": self.workflow_type,
            "project_id": project_id,
            "user_id": user_id,
            "session_id": session_id,
            "status": "initializing",
            "current_stage": "initialization",
            "progress": 0.0,
            "content": {},
            "messages": [],
            "error": None,
            "creation_logs": [],
            "awaiting_intervention": False,
            "intervention_data": None,
            "metadata": {
                "config": config,
            },
            "created_at": now,
            "updated_at": now
        }
    
    def _build_graph(self) -> StateGraph:
        """
        构建创作工作流图
        
        返回:
            StateGraph - 工作流状态图
        """
        # 创建StateGraph构建器
        builder = StateGraph(self.creation_state_schema)
        
        # 添加通用节点
        nodes = self._build_common_nodes()
        for name, node_func in nodes.items():
            builder.add_node(name, node_func)
        
        # 设置状态聚合器
        builder = self._setup_state_reducers(builder)
        
        # 此方法应由子类覆盖以添加特定的边和条件
        return builder
    
    def _build_common_nodes(self) -> Dict[str, Callable]:
        """
        构建所有创作工作流共用的节点
        
        返回:
            Dict[str, Callable] - 节点名称到节点函数的映射
        """
        nodes = {}
        
        def initialization_node(state: CreationState) -> Dict[str, Any]:
            """初始化创作状态"""
            # 这个方法会更新状态，表示初始化完成
            return {
                "status": "planning",
                "current_stage": "planning",
                "progress": 0.1,
                "updated_at": datetime.utcnow().isoformat(),
                "creation_logs": state.get("creation_logs", []) + [{
                    "type": "system",
                    "message": "创作工作流初始化完成",
                    "timestamp": datetime.utcnow().isoformat()
                }]
            }
        
        def coordinator_planning_node(state: CreationState) -> Dict[str, Any]:
            """协调智能体规划创作过程"""
            if not self.coordinator_agent:
                return {
                    "error": {
                        "type": "system_error",
                        "message": "协调智能体未初始化",
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    "status": "error"
                }
            
            try:
                # 调用协调智能体进行规划
                planning_result = self.coordinator_agent.plan_creation(state)
                
                return {
                    "status": "executing",
                    "current_stage": "execution",
                    "progress": 0.3,
                    "metadata": {
                        **state.get("metadata", {}),
                        "plan": planning_result.get("plan")
                    },
                    "updated_at": datetime.utcnow().isoformat(),
                    "creation_logs": state.get("creation_logs", []) + [{
                        "type": "planning",
                        "plan": planning_result.get("plan"),
                        "timestamp": datetime.utcnow().isoformat()
                    }]
                }
            except Exception as e:
                return {
                    "error": {
                        "type": "planning_error",
                        "message": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    "status": "error"
                }
        
        def agents_execution_node(state: CreationState) -> Dict[str, Any]:
            """执行各专业智能体的任务"""
            try:
                # 从规划中获取任务分配
                plan = state.get("metadata", {}).get("plan", {})
                tasks = plan.get("tasks", [])
                
                # 这里需要实现根据任务分配调用相应的智能体
                # 为简化示例，这里使用一个模拟的执行结果
                execution_results = {
                    "results": [{"task_id": task.get("id"), "status": "completed"} for task in tasks]
                }
                
                return {
                    "status": "reviewing",
                    "current_stage": "review",
                    "progress": 0.7,
                    "content": {
                        **state.get("content", {}),
                        "generated_content": execution_results
                    },
                    "updated_at": datetime.utcnow().isoformat(),
                    "creation_logs": state.get("creation_logs", []) + [{
                        "type": "execution",
                        "results": execution_results,
                        "timestamp": datetime.utcnow().isoformat()
                    }]
                }
            except Exception as e:
                return {
                    "error": {
                        "type": "execution_error",
                        "message": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    "status": "error"
                }
        
        def result_aggregation_node(state: CreationState) -> Dict[str, Any]:
            """汇聚所有智能体的结果"""
            try:
                # 聚合所有执行结果
                content = state.get("content", {})
                
                # 模拟内容聚合过程
                aggregated_content = {
                    "final_content": content.get("generated_content", {})
                }
                
                return {
                    "content": {
                        **content,
                        "aggregated_content": aggregated_content
                    },
                    "updated_at": datetime.utcnow().isoformat(),
                    "creation_logs": state.get("creation_logs", []) + [{
                        "type": "aggregation",
                        "timestamp": datetime.utcnow().isoformat()
                    }]
                }
            except Exception as e:
                return {
                    "error": {
                        "type": "aggregation_error",
                        "message": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    "status": "error"
                }
        
        def review_node(state: CreationState) -> Dict[str, Any]:
            """审查和质量检查"""
            try:
                # 模拟审查过程
                review_result = {
                    "quality_score": 0.85,
                    "issues": [],
                    "recommendations": []
                }
                
                return {
                    "metadata": {
                        **state.get("metadata", {}),
                        "review": review_result
                    },
                    "updated_at": datetime.utcnow().isoformat(),
                    "creation_logs": state.get("creation_logs", []) + [{
                        "type": "review",
                        "result": review_result,
                        "timestamp": datetime.utcnow().isoformat()
                    }]
                }
            except Exception as e:
                return {
                    "error": {
                        "type": "review_error",
                        "message": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    "status": "error"
                }
        
        def finalization_node(state: CreationState) -> Dict[str, Any]:
            """完成创作，整理最终输出"""
            return {
                "status": "completed",
                "current_stage": "completed",
                "progress": 1.0,
                "updated_at": datetime.utcnow().isoformat(),
                "creation_logs": state.get("creation_logs", []) + [{
                    "type": "system",
                    "message": "创作工作流完成",
                    "timestamp": datetime.utcnow().isoformat()
                }]
            }
        
        nodes["initialization"] = initialization_node
        nodes["coordinator_planning"] = coordinator_planning_node
        nodes["agents_execution"] = agents_execution_node
        nodes["result_aggregation"] = result_aggregation_node
        nodes["review"] = review_node
        nodes["finalization"] = finalization_node
        
        return nodes
    
    def _setup_state_reducers(self, builder: StateGraph) -> StateGraph:
        """
        设置状态聚合器
        
        参数:
            builder: StateGraph - 状态图构建器
            
        返回:
            StateGraph - 设置了聚合器的状态图构建器
        """
        # 在这里，我们可以添加自定义的状态聚合器
        # 例如，如果需要为特定字段添加聚合逻辑
        # 由于我们已经在创作状态定义中使用了add_messages注解，所以此处不需要额外设置messages字段的聚合器
        
        return builder 