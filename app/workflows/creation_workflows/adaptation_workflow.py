"""
改编创作工作流实现，提供对现有内容的改编、转换和重构功能
"""

from typing import Any, Callable, Dict, List, Optional, Type, Union
from datetime import datetime
import uuid

from langgraph.graph import StateGraph, START, END

from ...agents.coordinator_agent import CoordinatorAgent
from ...agents.base_agent import BaseAgent
from .base_workflow import CreationWorkflow, CreationState


class AdaptationModeCoordinator:
    """改编模式下的协调智能体，管理内容改编和转换流程"""
    
    def analyze_source_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析源内容的结构和特性
        
        参数:
            content: Dict[str, Any] - 源内容
            
        返回:
            Dict[str, Any] - 内容分析结果
        """
        # 实际实现中应调用分析智能体进行深度分析
        # 这里提供简化的分析逻辑
        
        analysis = {
            "content_type": content.get("type", "unknown"),
            "structure": {
                "sections": [],
                "key_elements": []
            },
            "style": {
                "tone": "neutral",
                "complexity": "medium",
                "formality": "neutral"
            },
            "themes": [],
            "characters": [],
            "plot_elements": []
        }
        
        # 分析文本内容
        text = content.get("text", "")
        if text:
            # 简单字数统计
            word_count = len(text.split())
            analysis["metrics"] = {
                "word_count": word_count,
                "estimated_read_time": word_count / 200  # 假设每分钟阅读200字
            }
            
            # 简单内容类型识别
            if "Chapter" in text or "Act" in text:
                analysis["content_type"] = "narrative"
                analysis["structure"]["sections"] = ["chapter" + str(i+1) for i in range(text.count("Chapter"))]
            elif "Abstract" in text or "Introduction" in text or "Conclusion" in text:
                analysis["content_type"] = "academic"
                analysis["structure"]["sections"] = ["abstract", "introduction", "body", "conclusion"]
            elif text.count("\n\n") > text.count(".") / 10:  # 估计是诗或分段明显的内容
                analysis["content_type"] = "poetry"
                analysis["structure"]["sections"] = ["stanza" + str(i+1) for i in range(text.count("\n\n"))]
        
        # 分析元数据
        metadata = content.get("metadata", {})
        if metadata:
            analysis["genre"] = metadata.get("genre", "unknown")
            analysis["target_audience"] = metadata.get("target_audience", "general")
            analysis["original_language"] = metadata.get("language", "unknown")
            
            # 如果有角色信息
            if "characters" in metadata:
                analysis["characters"] = [
                    {"name": char.get("name", ""), "role": char.get("role", "unknown")}
                    for char in metadata.get("characters", [])
                ]
            
            # 如果有主题信息
            if "themes" in metadata:
                analysis["themes"] = metadata.get("themes", [])
        
        return analysis
    
    def generate_adaptation_plan(
        self, 
        source_analysis: Dict[str, Any], 
        target_format: str, 
        adaptation_parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        生成内容改编计划
        
        参数:
            source_analysis: Dict[str, Any] - 源内容分析结果
            target_format: str - 目标格式
            adaptation_parameters: Dict[str, Any] - 改编参数
            
        返回:
            Dict[str, Any] - 改编计划
        """
        # 实际实现中应根据源内容、目标格式和参数生成定制化改编计划
        # 这里提供简化的计划生成逻辑
        
        plan = {
            "adaptation_id": str(uuid.uuid4()),
            "source_type": source_analysis.get("content_type", "unknown"),
            "target_format": target_format,
            "steps": [],
            "estimated_completion_time": "00:30:00",  # 30分钟
            "preservation_elements": [],
            "transformation_elements": []
        }
        
        # 根据目标格式设置步骤
        if target_format == "screenplay":
            plan["steps"] = [
                {
                    "name": "dialogue_extraction",
                    "description": "从源内容中提取对话",
                    "agent_type": "dialogue_specialist"
                },
                {
                    "name": "scene_construction",
                    "description": "构建场景和场景描述",
                    "agent_type": "scene_specialist"
                },
                {
                    "name": "script_formatting",
                    "description": "按剧本格式排版内容",
                    "agent_type": "format_specialist"
                },
                {
                    "name": "character_development",
                    "description": "深化角色表现和特点",
                    "agent_type": "character_specialist"
                }
            ]
            plan["preservation_elements"] = ["core_plot", "character_relationships", "major_themes"]
            plan["transformation_elements"] = ["narrative_to_visual", "descriptions_to_actions", "exposition_to_dialogue"]
            
        elif target_format == "summary":
            plan["steps"] = [
                {
                    "name": "key_point_extraction",
                    "description": "提取关键点和主要情节",
                    "agent_type": "content_analyst"
                },
                {
                    "name": "summary_generation",
                    "description": "生成简洁摘要",
                    "agent_type": "summarization_specialist"
                },
                {
                    "name": "refinement",
                    "description": "优化和润色摘要",
                    "agent_type": "editor"
                }
            ]
            plan["preservation_elements"] = ["main_points", "conclusion", "key_arguments"]
            plan["transformation_elements"] = ["detailed_to_concise", "remove_examples", "consolidate_ideas"]
            
        elif target_format == "different_genre":
            genre = adaptation_parameters.get("target_genre", "adventure")
            plan["steps"] = [
                {
                    "name": "genre_analysis",
                    "description": f"分析目标体裁({genre})的特点",
                    "agent_type": "genre_specialist"
                },
                {
                    "name": "story_element_adaptation",
                    "description": "调整故事元素以适应新体裁",
                    "agent_type": "narrative_specialist"
                },
                {
                    "name": "style_transformation",
                    "description": "转换写作风格",
                    "agent_type": "style_specialist"
                },
                {
                    "name": "coherence_check",
                    "description": "检查和确保故事连贯性",
                    "agent_type": "editor"
                }
            ]
            plan["preservation_elements"] = ["core_plot", "character_essence", "central_conflict"]
            plan["transformation_elements"] = ["tone", "pacing", "world_building", "dialogue_style"]
            
        else:  # 通用改编计划
            plan["steps"] = [
                {
                    "name": "content_analysis",
                    "description": "深入分析源内容结构和元素",
                    "agent_type": "content_analyst"
                },
                {
                    "name": "adaptation_drafting",
                    "description": "起草改编内容",
                    "agent_type": "content_creator"
                },
                {
                    "name": "review_and_refinement",
                    "description": "审查和优化改编内容",
                    "agent_type": "editor"
                }
            ]
            plan["preservation_elements"] = ["core_message", "key_points", "essential_elements"]
            plan["transformation_elements"] = ["format", "structure", "presentation_style"]
        
        # 增加自定义设置
        if "style_adjustments" in adaptation_parameters:
            style = adaptation_parameters.get("style_adjustments", {})
            plan["style_guidelines"] = {
                "tone": style.get("tone", "neutral"),
                "complexity": style.get("complexity", "medium"),
                "formality": style.get("formality", "neutral"),
                "perspective": style.get("perspective", "third_person")
            }
        
        # 增加质量控制步骤
        plan["steps"].append({
            "name": "quality_check",
            "description": "确保改编质量和忠实度",
            "agent_type": "quality_control_specialist"
        })
        
        return plan
    
    def execute_adaptation_step(
        self, 
        step: Dict[str, Any], 
        content: Dict[str, Any], 
        plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行单个改编步骤
        
        参数:
            step: Dict[str, Any] - 要执行的步骤
            content: Dict[str, Any] - 当前内容
            plan: Dict[str, Any] - 整体改编计划
            
        返回:
            Dict[str, Any] - 更新后的内容
        """
        # 实际实现中应调用对应的专家智能体执行改编任务
        # 这里提供简化示例实现
        
        step_name = step.get("name", "unknown")
        step_description = step.get("description", "")
        agent_type = step.get("agent_type", "")
        
        # 简化实现：返回带有步骤执行标记的内容
        updated_content = {
            **content,
            "adaptation_step_results": content.get("adaptation_step_results", {})
        }
        
        # 添加步骤执行结果
        updated_content["adaptation_step_results"][step_name] = {
            "executed_at": datetime.utcnow().isoformat(),
            "agent_type": agent_type,
            "result": f"已执行 {step_description}",
            "status": "completed"
        }
        
        return updated_content
    
    def evaluate_adaptation_quality(self, original_content: Dict[str, Any], adapted_content: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估改编质量
        
        参数:
            original_content: Dict[str, Any] - 原始内容
            adapted_content: Dict[str, Any] - 改编后内容
            plan: Dict[str, Any] - 改编计划
            
        返回:
            Dict[str, Any] - 评估结果
        """
        # 实际实现中应调用评估智能体进行质量评估
        # 这里提供简化示例实现
        
        preservation_elements = plan.get("preservation_elements", [])
        transformation_elements = plan.get("transformation_elements", [])
        
        # 简化的质量评分
        preservation_score = 0.85  # 85% 的核心元素被保留
        transformation_score = 0.90  # 90% 的转换元素得到良好实现
        coherence_score = 0.80  # 80% 的连贯性维持
        
        # 综合评分
        overall_score = (preservation_score + transformation_score + coherence_score) / 3
        
        return {
            "evaluation_timestamp": datetime.utcnow().isoformat(),
            "preservation_score": preservation_score,
            "transformation_score": transformation_score,
            "coherence_score": coherence_score,
            "overall_quality_score": overall_score,
            "strengths": [
                "保留了核心情节和主题",
                "成功转换了风格和格式",
                "维持了角色一致性"
            ],
            "areas_for_improvement": [
                "部分情节转换可以更加流畅",
                "可以进一步调整语言风格"
            ],
            "recommendations": [
                "考虑进一步润色对话",
                "检查并强化主题连贯性"
            ]
        }


class AdaptationCreationWorkflow(CreationWorkflow):
    """实现改编创作模式的工作流，专注于内容的改编、转换和重构"""
    
    def __init__(
        self,
        *args, 
        coordinator_agent: Optional[CoordinatorAgent] = None,
        target_format: str = "screenplay",
        adaptation_parameters: Dict[str, Any] = None,
        **kwargs
    ):
        """
        初始化改编创作工作流
        
        参数:
            coordinator_agent: Optional[CoordinatorAgent] - 协调智能体
            target_format: str - 目标格式
            adaptation_parameters: Dict[str, Any] - 改编参数
        """
        # 设置工作流类型为"adaptation"
        kwargs["workflow_type"] = "adaptation"
        kwargs["coordinator_agent"] = coordinator_agent
        super().__init__(*args, **kwargs)
        
        # 改编模式特有属性
        self.target_format = target_format
        self.adaptation_parameters = adaptation_parameters or {}
        self.adaptation_coordinator = AdaptationModeCoordinator()
        self.current_step_index = 0
        self.source_content = {}
        self.adaptation_plan = {}
    
    def set_source_content(self, content: Dict[str, Any]) -> None:
        """
        设置源内容
        
        参数:
            content: Dict[str, Any] - 源内容
        """
        self.source_content = content
    
    def get_current_step(self) -> Dict[str, Any]:
        """
        获取当前改编步骤
        
        返回:
            Dict[str, Any] - 当前步骤
        """
        if not self.adaptation_plan or "steps" not in self.adaptation_plan:
            return {}
        
        steps = self.adaptation_plan.get("steps", [])
        if self.current_step_index >= len(steps):
            return {}
            
        return steps[self.current_step_index]
    
    def _build_graph(self) -> StateGraph:
        """
        构建改编创作工作流图
        
        返回:
            StateGraph - 工作流状态图
        """
        # 创建StateGraph构建器
        builder = StateGraph(self.creation_state_schema)
        
        # 添加通用节点
        common_nodes = self._build_common_nodes()
        for name, node_func in common_nodes.items():
            builder.add_node(name, node_func)
        
        # 添加改编模式特有节点
        adaptation_nodes = self._define_nodes()
        for name, node_func in adaptation_nodes.items():
            builder.add_node(name, node_func)
        
        # 定义边和条件
        builder = self._define_edges(builder)
        
        # 设置状态聚合器
        builder = self._setup_state_reducers(builder)
        
        return builder
    
    def _define_nodes(self) -> Dict[str, Callable]:
        """
        定义改编创作特有节点
        
        返回:
            Dict[str, Callable] - 节点名称到节点函数的映射
        """
        nodes = {}
        
        def source_content_analysis_node(state: CreationState) -> Dict[str, Any]:
            """源内容分析节点"""
            try:
                # 获取源内容
                source_content = state.get("content", {}).get("source", self.source_content)
                
                if not source_content:
                    # 如果没有源内容，创建干预点请求用户提供
                    return self._create_source_content_intervention(state)
                
                # 分析源内容
                source_analysis = self.adaptation_coordinator.analyze_source_content(source_content)
                
                return {
                    "status": "source_analyzed",
                    "progress": 0.1,
                    "metadata": {
                        **state.get("metadata", {}),
                        "source_analysis": source_analysis
                    },
                    "content": {
                        **state.get("content", {}),
                        "source": source_content
                    },
                    "updated_at": datetime.utcnow().isoformat(),
                    "creation_logs": state.get("creation_logs", []) + [{
                        "type": "source_analysis",
                        "timestamp": datetime.utcnow().isoformat()
                    }]
                }
            except Exception as e:
                return {
                    "error": {
                        "type": "source_analysis_error",
                        "message": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    "status": "error"
                }
        
        def adaptation_planning_node(state: CreationState) -> Dict[str, Any]:
            """改编计划生成节点"""
            try:
                # 获取源内容分析结果
                source_analysis = state.get("metadata", {}).get("source_analysis", {})
                
                # 生成改编计划
                adaptation_plan = self.adaptation_coordinator.generate_adaptation_plan(
                    source_analysis, 
                    self.target_format, 
                    self.adaptation_parameters
                )
                
                # 保存计划
                self.adaptation_plan = adaptation_plan
                
                return {
                    "status": "plan_generated",
                    "progress": 0.2,
                    "metadata": {
                        **state.get("metadata", {}),
                        "adaptation_plan": adaptation_plan
                    },
                    "updated_at": datetime.utcnow().isoformat(),
                    "creation_logs": state.get("creation_logs", []) + [{
                        "type": "plan_generation",
                        "plan_id": adaptation_plan.get("adaptation_id", ""),
                        "target_format": self.target_format,
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
        
        def step_execution_node(state: CreationState) -> Dict[str, Any]:
            """步骤执行节点"""
            try:
                # 获取当前步骤和计划
                current_step = self.get_current_step()
                adaptation_plan = state.get("metadata", {}).get("adaptation_plan", self.adaptation_plan)
                
                if not current_step:
                    # 所有步骤已完成
                    return {
                        "status": "all_steps_completed",
                        "progress": 0.8,
                        "updated_at": datetime.utcnow().isoformat(),
                        "creation_logs": state.get("creation_logs", []) + [{
                            "type": "adaptation_completion",
                            "message": "所有改编步骤已完成",
                            "timestamp": datetime.utcnow().isoformat()
                        }]
                    }
                
                # 获取当前内容
                current_content = state.get("content", {})
                
                # 执行步骤
                updated_content = self.adaptation_coordinator.execute_adaptation_step(
                    current_step, 
                    current_content, 
                    adaptation_plan
                )
                
                # 更新进度
                steps = adaptation_plan.get("steps", [])
                step_progress = 0.2 + (self.current_step_index / max(1, len(steps))) * 0.6
                
                return {
                    "status": "step_executed",
                    "current_stage": f"adaptation_step_{self.current_step_index}",
                    "progress": step_progress,
                    "content": updated_content,
                    "metadata": {
                        **state.get("metadata", {}),
                        "current_step": current_step,
                        "current_step_index": self.current_step_index
                    },
                    "updated_at": datetime.utcnow().isoformat(),
                    "creation_logs": state.get("creation_logs", []) + [{
                        "type": "step_execution",
                        "step_name": current_step.get("name", ""),
                        "timestamp": datetime.utcnow().isoformat()
                    }]
                }
            except Exception as e:
                return {
                    "error": {
                        "type": "step_execution_error",
                        "message": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    "status": "error"
                }
        
        def step_transition_node(state: CreationState) -> Dict[str, Any]:
            """步骤转换节点"""
            try:
                # 增加当前步骤索引
                next_step_index = self.current_step_index + 1
                self.current_step_index = next_step_index
                
                return {
                    "status": "advancing_to_next_step",
                    "metadata": {
                        **state.get("metadata", {}),
                        "current_step_index": next_step_index
                    },
                    "updated_at": datetime.utcnow().isoformat(),
                    "creation_logs": state.get("creation_logs", []) + [{
                        "type": "step_transition",
                        "from_step_index": self.current_step_index - 1,
                        "to_step_index": next_step_index,
                        "timestamp": datetime.utcnow().isoformat()
                    }]
                }
            except Exception as e:
                return {
                    "error": {
                        "type": "step_transition_error",
                        "message": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    "status": "error"
                }
        
        def quality_evaluation_node(state: CreationState) -> Dict[str, Any]:
            """质量评估节点"""
            try:
                # 获取原始和改编内容
                source_content = state.get("content", {}).get("source", {})
                adapted_content = {
                    k: v for k, v in state.get("content", {}).items() 
                    if k != "source" and k != "adaptation_step_results"
                }
                
                # 获取改编计划
                adaptation_plan = state.get("metadata", {}).get("adaptation_plan", {})
                
                # 评估质量
                evaluation_result = self.adaptation_coordinator.evaluate_adaptation_quality(
                    source_content,
                    adapted_content,
                    adaptation_plan
                )
                
                return {
                    "status": "quality_evaluated",
                    "progress": 0.9,
                    "metadata": {
                        **state.get("metadata", {}),
                        "quality_evaluation": evaluation_result
                    },
                    "updated_at": datetime.utcnow().isoformat(),
                    "creation_logs": state.get("creation_logs", []) + [{
                        "type": "quality_evaluation",
                        "quality_score": evaluation_result.get("overall_quality_score", 0.0),
                        "timestamp": datetime.utcnow().isoformat()
                    }]
                }
            except Exception as e:
                return {
                    "error": {
                        "type": "evaluation_error",
                        "message": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    "status": "error"
                }
        
        def adaptation_refinement_node(state: CreationState) -> Dict[str, Any]:
            """改编优化节点"""
            try:
                # 获取质量评估结果
                evaluation = state.get("metadata", {}).get("quality_evaluation", {})
                overall_quality = evaluation.get("overall_quality_score", 0.0)
                
                # 检查质量是否足够高
                if overall_quality >= 0.8:  # 80% 质量阈值
                    # 质量足够高，可以完成
                    return {
                        "status": "adaptation_completed",
                        "progress": 0.95,
                        "updated_at": datetime.utcnow().isoformat(),
                        "creation_logs": state.get("creation_logs", []) + [{
                            "type": "adaptation_completion",
                            "message": "改编质量满足要求，流程完成",
                            "timestamp": datetime.utcnow().isoformat()
                        }]
                    }
                else:
                    # 质量不够高，创建干预点询问用户是否需要继续优化
                    return self._create_quality_intervention(state, evaluation)
            except Exception as e:
                return {
                    "error": {
                        "type": "refinement_error",
                        "message": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    "status": "error"
                }
        
        nodes["source_content_analysis"] = source_content_analysis_node
        nodes["adaptation_planning"] = adaptation_planning_node
        nodes["step_execution"] = step_execution_node
        nodes["step_transition"] = step_transition_node
        nodes["quality_evaluation"] = quality_evaluation_node
        nodes["adaptation_refinement"] = adaptation_refinement_node
        
        return nodes
    
    def _define_edges(self, builder: StateGraph) -> StateGraph:
        """
        定义改编创作流程边
        
        参数:
            builder: StateGraph - 状态图构建器
            
        返回:
            StateGraph - 添加了边的状态图构建器
        """
        # 定义主流程
        builder.add_edge(START, "initialization")
        builder.add_edge("initialization", "source_content_analysis")
        builder.add_edge("source_content_analysis", "adaptation_planning")
        builder.add_edge("adaptation_planning", "step_execution")
        
        # 步骤执行和转换
        builder.add_conditional_edges(
            "step_execution",
            lambda state: "all_steps_completed" if state.get("status") == "all_steps_completed" else "step_executed",
            {
                "all_steps_completed": "quality_evaluation",
                "step_executed": "step_transition"
            }
        )
        builder.add_edge("step_transition", "step_execution")
        
        # 质量评估和完成
        builder.add_edge("quality_evaluation", "adaptation_refinement")
        builder.add_edge("adaptation_refinement", "result_aggregation")
        
        # 最终流程
        builder.add_edge("result_aggregation", "review")
        builder.add_edge("review", "finalization")
        builder.add_edge("finalization", END)
        
        # 错误处理
        builder.add_edge(self._handle_error, END)
        
        return builder
    
    def _create_source_content_intervention(self, state: CreationState) -> Dict[str, Any]:
        """
        创建源内容干预点
        
        参数:
            state: CreationState - 当前状态
            
        返回:
            Dict[str, Any] - 干预结果
        """
        # 创建干预信息
        intervention_info = {
            "type": "source_content",
            "question": "请提供需要改编的源内容",
            "options": [
                {"id": "upload", "text": "上传文件"},
                {"id": "paste", "text": "粘贴文本"},
                {"id": "select", "text": "选择现有内容"}
            ],
            "context": {
                "target_format": self.target_format,
                "adaptation_parameters": self.adaptation_parameters
            }
        }
        
        # 更新状态为等待干预
        intervention_updates = self.create_intervention_point(state, intervention_info)
        
        # 添加状态记录
        intervention_updates["status_before_intervention"] = state.get("status")
        intervention_updates["creation_logs"] = state.get("creation_logs", []) + [{
            "type": "intervention_needed",
            "reason": "source_content_required",
            "timestamp": datetime.utcnow().isoformat()
        }]
        
        return intervention_updates
    
    def _create_quality_intervention(self, state: CreationState, evaluation: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建质量干预点
        
        参数:
            state: CreationState - 当前创作状态
            evaluation: Dict[str, Any] - 质量评估结果
            
        返回:
            Dict[str, Any] - 干预结果
        """
        quality_score = evaluation.get("overall_quality_score", 0.0)
        strengths = evaluation.get("strengths", [])
        improvements = evaluation.get("areas_for_improvement", [])
        
        # 创建干预信息
        intervention_info = {
            "type": "quality_feedback",
            "question": f"改编质量评分为{int(quality_score*100)}%，未达到优质标准。您希望如何处理？",
            "options": [
                {"id": "refine", "text": "继续优化改编内容"},
                {"id": "complete", "text": "接受当前质量并完成改编"},
                {"id": "feedback", "text": "提供具体的反馈和改进方向"}
            ],
            "context": {
                "quality_score": quality_score,
                "strengths": strengths,
                "areas_for_improvement": improvements
            }
        }
        
        # 更新状态为等待干预
        intervention_updates = self.create_intervention_point(state, intervention_info)
        
        # 添加状态记录
        intervention_updates["status_before_intervention"] = state.get("status")
        intervention_updates["creation_logs"] = state.get("creation_logs", []) + [{
            "type": "intervention_needed",
            "reason": "quality_improvement",
            "quality_score": quality_score,
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
