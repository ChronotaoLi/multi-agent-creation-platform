"""
自由创作工作流实现，允许高度灵活的创作过程
"""

from typing import Any, Callable, Dict, List, Optional, Tuple
from datetime import datetime

from langgraph.graph import StateGraph, START, END
from langgraph.types import Command, interrupt

from ...agents.content_agent import ContentAgent
from ...agents.character_agent import CharacterAgent
from .base_workflow import CreationWorkflow, CreationState


class FreeModeCoordinator:
    """自由模式下的协调智能体，采用更灵活的任务分配和管理策略"""
    
    def generate_inspiration(self, state: CreationState) -> Dict[str, Any]:
        """
        生成创作灵感
        
        参数:
            state: CreationState - 当前创作状态
            
        返回:
            Dict[str, Any] - 包含灵感的字典
        """
        # 这里应该调用底层的LLM或专门的灵感生成模型
        # 简化实现，返回模拟的灵感
        return {
            "inspiration": {
                "themes": ["自由", "探索", "发现"],
                "concepts": ["未知世界", "内心旅程"],
                "potential_elements": ["角色成长", "意外发现", "考验与选择"],
                "score": 0.78  # 灵感质量评分
            }
        }
    
    def coordinate_free_exploration(self, agents: List[Any], state: CreationState) -> Dict[str, Any]:
        """
        协调自由探索
        
        参数:
            agents: List[Any] - 可用智能体列表
            state: CreationState - 当前创作状态
            
        返回:
            Dict[str, Any] - 协调结果
        """
        # 在自由模式下，协调更多是提供方向而非强制控制
        # 允许各智能体更自由地发挥创造力
        inspiration = state.get("metadata", {}).get("inspiration", {})
        
        exploration_paths = []
        for agent in agents:
            # 为每个智能体分配探索方向，但不限制其创造力
            if hasattr(agent, "explore"):
                path = {
                    "agent_id": getattr(agent, "agent_id", "unknown"),
                    "focus_area": self._assign_focus_area(agent, inspiration),
                    "constraints": []  # 自由模式下约束最少
                }
                exploration_paths.append(path)
        
        return {
            "exploration_plan": {
                "paths": exploration_paths,
                "coordination_level": "low",  # 低协调度
                "freedom_level": "high"  # 高自由度
            }
        }
    
    def integrate_independent_contributions(self, contributions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        整合独立贡献
        
        参数:
            contributions: List[Dict[str, Any]] - 各智能体的贡献
            
        返回:
            Dict[str, Any] - 整合结果
        """
        # 自由模式下，整合更关注保留多样性而非强制一致性
        integrated_result = {
            "elements": [],
            "connections": [],
            "potential_conflicts": []
        }
        
        for contribution in contributions:
            integrated_result["elements"].extend(contribution.get("elements", []))
            
            # 识别潜在的连接点，但不强制解决冲突
            for element in contribution.get("elements", []):
                for existing_element in integrated_result["elements"]:
                    if element != existing_element and self._has_connection_potential(element, existing_element):
                        integrated_result["connections"].append({
                            "from": element.get("id"),
                            "to": existing_element.get("id"),
                            "strength": "suggested"  # 仅建议性连接
                        })
        
        return integrated_result
    
    def _assign_focus_area(self, agent: Any, inspiration: Dict[str, Any]) -> str:
        """根据智能体类型和灵感分配焦点区域"""
        # 简化实现
        agent_type = type(agent).__name__
        if "Character" in agent_type:
            return "character_development"
        elif "Content" in agent_type:
            return "narrative_exploration"
        else:
            return "general_creation"
    
    def _has_connection_potential(self, element1: Dict[str, Any], element2: Dict[str, Any]) -> bool:
        """检查两个元素之间是否有潜在连接可能"""
        # 简化实现
        return True


class FreeCreationWorkflow(CreationWorkflow):
    """实现自由创作模式的工作流，最大程度保留智能体的创造性"""
    
    def __init__(self, *args, **kwargs):
        """
        初始化自由创作工作流
        """
        # 设置工作流类型为"free"
        kwargs["workflow_type"] = "free"
        super().__init__(*args, **kwargs)
        
        # 自由创作特有属性
        self.content_agents = []  # 内容创作智能体列表
        self.character_agents = []  # 角色创作智能体列表
        self.free_coordinator = FreeModeCoordinator()  # 自由模式协调器
        self.inspiration_threshold = 0.6  # 灵感阈值，低于此值触发干预
    
    def add_content_agent(self, agent: ContentAgent) -> None:
        """
        添加内容创作智能体
        
        参数:
            agent: ContentAgent - 内容创作智能体
        """
        self.content_agents.append(agent)
        self.add_agents([agent])
    
    def add_character_agent(self, agent: CharacterAgent) -> None:
        """
        添加角色创作智能体
        
        参数:
            agent: CharacterAgent - 角色创作智能体
        """
        self.character_agents.append(agent)
        self.add_agents([agent])
    
    def _build_graph(self) -> StateGraph:
        """
        构建自由创作工作流图
        
        返回:
            StateGraph - 工作流状态图
        """
        # 创建StateGraph构建器
        builder = StateGraph(self.creation_state_schema)
        
        # 添加通用节点
        common_nodes = self._build_common_nodes()
        for name, node_func in common_nodes.items():
            builder.add_node(name, node_func)
        
        # 添加自由模式特有节点
        free_nodes = self._define_nodes()
        for name, node_func in free_nodes.items():
            builder.add_node(name, node_func)
        
        # 定义边和条件
        builder = self._define_edges(builder)
        
        # 设置状态聚合器
        builder = self._setup_state_reducers(builder)
        
        return builder
    
    def _define_nodes(self) -> Dict[str, Callable]:
        """
        定义自由创作特有节点
        
        返回:
            Dict[str, Callable] - 节点名称到节点函数的映射
        """
        nodes = {}
        
        def inspiration_generation_node(state: CreationState) -> Dict[str, Any]:
            """灵感生成节点"""
            try:
                # 调用协调器生成灵感
                inspiration = self.free_coordinator.generate_inspiration(state)
                
                return {
                    "status": "inspiration_generated",
                    "current_stage": "inspiration",
                    "progress": 0.2,
                    "metadata": {
                        **state.get("metadata", {}),
                        "inspiration": inspiration.get("inspiration")
                    },
                    "updated_at": datetime.utcnow().isoformat(),
                    "creation_logs": state.get("creation_logs", []) + [{
                        "type": "inspiration",
                        "inspiration": inspiration.get("inspiration"),
                        "timestamp": datetime.utcnow().isoformat()
                    }]
                }
            except Exception as e:
                return {
                    "error": {
                        "type": "inspiration_error",
                        "message": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    "status": "error"
                }
        
        def free_exploration_node(state: CreationState) -> Dict[str, Any]:
            """自由探索节点"""
            try:
                # 获取灵感
                inspiration = state.get("metadata", {}).get("inspiration", {})
                
                # 获取所有可用的智能体
                agents = self.content_agents + self.character_agents
                
                # 协调自由探索
                exploration_plan = self.free_coordinator.coordinate_free_exploration(agents, state)
                
                # 模拟自由探索过程
                exploration_results = []
                for path in exploration_plan.get("exploration_plan", {}).get("paths", []):
                    # 在实际实现中，应该调用相应的智能体执行探索
                    agent_id = path.get("agent_id")
                    focus_area = path.get("focus_area")
                    
                    # 模拟一个探索结果
                    result = {
                        "agent_id": agent_id,
                        "focus_area": focus_area,
                        "elements": [
                            {
                                "id": f"element_{agent_id}_{i}",
                                "type": "concept" if i % 2 == 0 else "scene",
                                "content": f"自由创作的{focus_area}元素{i}"
                            }
                            for i in range(3)
                        ]
                    }
                    exploration_results.append(result)
                
                # 整合独立贡献
                integrated_result = self.free_coordinator.integrate_independent_contributions(exploration_results)
                
                return {
                    "status": "exploration_completed",
                    "current_stage": "exploration",
                    "progress": 0.5,
                    "content": {
                        **state.get("content", {}),
                        "exploration_results": exploration_results,
                        "integrated_result": integrated_result
                    },
                    "metadata": {
                        **state.get("metadata", {}),
                        "exploration_plan": exploration_plan.get("exploration_plan")
                    },
                    "updated_at": datetime.utcnow().isoformat(),
                    "creation_logs": state.get("creation_logs", []) + [{
                        "type": "exploration",
                        "results_count": len(exploration_results),
                        "timestamp": datetime.utcnow().isoformat()
                    }]
                }
            except Exception as e:
                return {
                    "error": {
                        "type": "exploration_error",
                        "message": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    "status": "error"
                }
        
        nodes["inspiration_generation"] = inspiration_generation_node
        nodes["free_exploration"] = free_exploration_node
        
        return nodes
    
    def _define_edges(self, builder: StateGraph) -> StateGraph:
        """
        定义自由创作流程边
        
        参数:
            builder: StateGraph - 状态图构建器
            
        返回:
            StateGraph - 添加了边的状态图构建器
        """
        # 定义主流程
        builder.add_edge(START, "initialization")
        builder.add_edge("initialization", "inspiration_generation")
        
        # 在灵感生成后检查灵感质量
        builder.add_conditional_edges(
            "inspiration_generation",
            self._check_inspiration_quality,
            {
                "good_inspiration": "free_exploration",
                "low_inspiration": "create_inspiration_intervention"
            }
        )
        
        # 自由探索后进入结果聚合
        builder.add_edge("free_exploration", "result_aggregation")
        builder.add_edge("result_aggregation", "review")
        builder.add_edge("review", "finalization")
        builder.add_edge("finalization", END)
        
        # 错误处理
        builder.add_edge(self._handle_error, END)
        
        return builder
    
    def _check_inspiration_quality(self, state: CreationState) -> str:
        """
        检查灵感质量，决定是否需要用户干预
        
        参数:
            state: CreationState - 当前创作状态
            
        返回:
            str - 决策结果: "good_inspiration" 或 "low_inspiration"
        """
        inspiration = state.get("metadata", {}).get("inspiration", {})
        inspiration_score = inspiration.get("score", 0)
        
        if inspiration_score >= self.inspiration_threshold:
            return "good_inspiration"
        else:
            return "low_inspiration"
    
    def _create_inspiration_intervention(self, state: CreationState) -> Dict[str, Any]:
        """
        创建灵感相关干预点
        
        参数:
            state: CreationState - 当前创作状态
            
        返回:
            Dict[str, Any] - 干预结果
        """
        inspiration = state.get("metadata", {}).get("inspiration", {})
        
        # 使用interrupt函数创建干预点
        intervention_info = {
            "type": "inspiration",
            "question": "生成的灵感质量较低，您希望如何处理？",
            "options": [
                {"id": "regenerate", "text": "重新生成灵感"},
                {"id": "provide_direction", "text": "提供创作方向"},
                {"id": "continue", "text": "继续使用当前灵感"}
            ],
            "context": {
                "current_inspiration": inspiration,
                "threshold": self.inspiration_threshold
            }
        }
        
        # 更新状态为等待干预
        intervention_updates = self.create_intervention_point(state, intervention_info)
        
        # 添加状态记录
        intervention_updates["status_before_intervention"] = state.get("status")
        intervention_updates["creation_logs"] = state.get("creation_logs", []) + [{
            "type": "intervention_needed",
            "reason": "low_inspiration_quality",
            "timestamp": datetime.utcnow().isoformat()
        }]
        
        return intervention_updates
    
    def _handle_error(self, state: CreationState) -> bool:
        """
        错误处理条件函数
        
        参数:
            state: CreationState - 当前创作状态
            
        返回:
            bool - 是否存在错误
        """
        return state.get("status") == "error" and state.get("error") is not None
