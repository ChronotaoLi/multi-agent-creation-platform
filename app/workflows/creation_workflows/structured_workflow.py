"""
结构化创作工作流实现，提供预定义结构和严格控制的创作过程
"""

from typing import Any, Callable, Dict, List, Optional, Type, Union
from datetime import datetime

from langgraph.graph import StateGraph, START, END
from langgraph.types import Command, interrupt

from ...agents.coordinator_agent import CoordinatorAgent
from ...agents.base_agent import BaseAgent
from .base_workflow import CreationWorkflow, CreationState


class StructuredModeCoordinator:
    """结构化模式下的协调智能体，管理预定义模板和创作流程"""
    
    def load_creation_template(self, template_type: str, template_id: str) -> Dict[str, Any]:
        """
        加载创作模板
        
        参数:
            template_type: str - 模板类型
            template_id: str - 模板ID
            
        返回:
            Dict[str, Any] - 模板内容
        """
        # 实际实现中应从数据库或配置中加载模板
        # 这里提供简化的模板示例
        templates = {
            "novel": {
                "basic": {
                    "name": "基础小说模板",
                    "description": "标准三幕结构的小说创作模板",
                    "structure": [
                        {
                            "name": "设置",
                            "description": "介绍主要角色、场景和初始情况",
                            "required_elements": ["protagonist", "setting", "initial_situation"],
                            "suggested_length": 5000,
                            "completion_criteria": {
                                "min_characters": 3,
                                "min_scenes": 2,
                                "required_plot_points": ["inciting_incident"]
                            }
                        },
                        {
                            "name": "冲突",
                            "description": "主角面对挑战和障碍",
                            "required_elements": ["main_conflict", "rising_action", "complications"],
                            "suggested_length": 15000,
                            "completion_criteria": {
                                "min_obstacles": 3,
                                "min_scenes": 5,
                                "required_plot_points": ["midpoint"]
                            }
                        },
                        {
                            "name": "解决",
                            "description": "冲突解决和故事结局",
                            "required_elements": ["climax", "resolution", "conclusion"],
                            "suggested_length": 5000,
                            "completion_criteria": {
                                "min_scenes": 2,
                                "required_plot_points": ["climax", "resolution"]
                            }
                        }
                    ]
                }
            },
            "article": {
                "academic": {
                    "name": "学术论文模板",
                    "description": "标准学术论文创作模板",
                    "structure": [
                        {
                            "name": "摘要与引言",
                            "description": "研究背景、问题陈述与研究意义",
                            "required_elements": ["abstract", "background", "research_question", "significance"],
                            "suggested_length": 1000,
                            "completion_criteria": {
                                "min_words": 500,
                                "required_sections": ["abstract", "introduction"]
                            }
                        },
                        {
                            "name": "文献综述",
                            "description": "相关研究回顾与理论框架",
                            "required_elements": ["literature_review", "theoretical_framework"],
                            "suggested_length": 2000,
                            "completion_criteria": {
                                "min_references": 10,
                                "min_words": 1000
                            }
                        },
                        {
                            "name": "方法",
                            "description": "研究方法与数据收集",
                            "required_elements": ["methodology", "data_collection", "analysis_approach"],
                            "suggested_length": 1500,
                            "completion_criteria": {
                                "min_words": 800,
                                "required_sections": ["methodology", "data_collection"]
                            }
                        },
                        {
                            "name": "结果与讨论",
                            "description": "研究发现与分析",
                            "required_elements": ["results", "findings", "discussion", "limitations"],
                            "suggested_length": 3000,
                            "completion_criteria": {
                                "min_words": 1500,
                                "required_sections": ["results", "discussion"]
                            }
                        },
                        {
                            "name": "结论",
                            "description": "总结与未来研究方向",
                            "required_elements": ["conclusion", "implications", "future_research"],
                            "suggested_length": 1000,
                            "completion_criteria": {
                                "min_words": 500,
                                "required_sections": ["conclusion"]
                            }
                        }
                    ]
                }
            }
        }
        
        if template_type in templates and template_id in templates[template_type]:
            return templates[template_type][template_id]
        
        # 如果找不到模板，返回默认空模板
        return {
            "name": "默认模板",
            "description": "基本创作模板",
            "structure": [
                {
                    "name": "开始",
                    "description": "创作起始",
                    "required_elements": [],
                    "suggested_length": 1000,
                    "completion_criteria": {}
                },
                {
                    "name": "中间",
                    "description": "创作中间部分",
                    "required_elements": [],
                    "suggested_length": 2000,
                    "completion_criteria": {}
                },
                {
                    "name": "结束",
                    "description": "创作结束",
                    "required_elements": [],
                    "suggested_length": 1000,
                    "completion_criteria": {}
                }
            ]
        }
    
    def evaluate_section_completion(self, section: Dict[str, Any], content: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估章节完成情况
        
        参数:
            section: Dict[str, Any] - 章节定义
            content: Dict[str, Any] - 当前内容
            
        返回:
            Dict[str, Any] - 评估结果
        """
        # 获取章节名称
        section_name = section.get("name", "未知章节")
        
        # 获取该章节的内容
        section_content = content.get(f"{section_name}_content", {})
        
        # 如果没有内容，则未完成
        if not section_content:
            return {
                "section_name": section_name,
                "is_completed": False,
                "completion_rate": 0.0,
                "missing_elements": section.get("required_elements", []),
                "suggestions": [f"开始创作{section_name}部分"]
            }
        
        # 检查必要元素是否存在
        required_elements = section.get("required_elements", [])
        existing_elements = section_content.get("elements", {}).keys()
        missing_elements = [elem for elem in required_elements if elem not in existing_elements]
        
        # 检查完成标准
        completion_criteria = section.get("completion_criteria", {})
        criteria_met = []
        criteria_not_met = []
        
        # 字数检查
        if "min_words" in completion_criteria:
            min_words = completion_criteria["min_words"]
            current_words = len(section_content.get("text", "").split())
            if current_words >= min_words:
                criteria_met.append(f"达到最小字数要求：{current_words}/{min_words}")
            else:
                criteria_not_met.append(f"未达到最小字数要求：{current_words}/{min_words}")
        
        # 场景数量检查
        if "min_scenes" in completion_criteria:
            min_scenes = completion_criteria["min_scenes"]
            current_scenes = len(section_content.get("scenes", []))
            if current_scenes >= min_scenes:
                criteria_met.append(f"达到最小场景数量要求：{current_scenes}/{min_scenes}")
            else:
                criteria_not_met.append(f"未达到最小场景数量要求：{current_scenes}/{min_scenes}")
        
        # 角色数量检查
        if "min_characters" in completion_criteria:
            min_characters = completion_criteria["min_characters"]
            current_characters = len(section_content.get("characters", []))
            if current_characters >= min_characters:
                criteria_met.append(f"达到最小角色数量要求：{current_characters}/{min_characters}")
            else:
                criteria_not_met.append(f"未达到最小角色数量要求：{current_characters}/{min_characters}")
        
        # 必要情节点检查
        if "required_plot_points" in completion_criteria:
            required_points = completion_criteria["required_plot_points"]
            existing_points = section_content.get("plot_points", [])
            missing_points = [point for point in required_points if point not in existing_points]
            if not missing_points:
                criteria_met.append(f"包含所有必要情节点")
            else:
                criteria_not_met.append(f"缺少必要情节点：{', '.join(missing_points)}")
        
        # 计算完成率
        total_criteria = len(completion_criteria.keys())
        if total_criteria == 0:
            completion_rate = 0.0 if missing_elements else 1.0
        else:
            completion_rate = len(criteria_met) / total_criteria
        
        # 生成建议
        suggestions = []
        if missing_elements:
            suggestions.append(f"添加以下必要元素：{', '.join(missing_elements)}")
        for criterion in criteria_not_met:
            suggestions.append(f"完善内容以满足：{criterion}")
        
        return {
            "section_name": section_name,
            "is_completed": not missing_elements and not criteria_not_met,
            "completion_rate": completion_rate,
            "missing_elements": missing_elements,
            "criteria_met": criteria_met,
            "criteria_not_met": criteria_not_met,
            "suggestions": suggestions
        }
    
    def generate_section_guidance(self, section: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成章节创作指南
        
        参数:
            section: Dict[str, Any] - 章节定义
            
        返回:
            Dict[str, Any] - 章节指南
        """
        section_name = section.get("name", "未知章节")
        section_description = section.get("description", "")
        required_elements = section.get("required_elements", [])
        suggested_length = section.get("suggested_length", 1000)
        
        # 为必要元素生成指导说明
        elements_guidance = {}
        for element in required_elements:
            elements_guidance[element] = self._get_element_guidance(element)
        
        return {
            "section_name": section_name,
            "description": section_description,
            "required_elements": required_elements,
            "elements_guidance": elements_guidance,
            "suggested_length": suggested_length,
            "tips": self._get_section_tips(section_name),
            "examples": self._get_section_examples(section_name)
        }
    
    def _get_element_guidance(self, element: str) -> Dict[str, Any]:
        """获取元素指导信息"""
        # 实际实现中应从知识库或配置中加载
        guidance_map = {
            "protagonist": {
                "description": "故事的主要角色",
                "tips": [
                    "确保主角有明确的动机",
                    "设计有深度的性格特征",
                    "建立可信的成长轨迹"
                ]
            },
            "setting": {
                "description": "故事发生的时间和地点",
                "tips": [
                    "创建有特色的环境",
                    "考虑环境如何影响角色和情节",
                    "注意细节以增强真实感"
                ]
            },
            "conflict": {
                "description": "故事的核心冲突",
                "tips": [
                    "确保冲突与主角息息相关",
                    "设计足够强的对立力量",
                    "使冲突随情节发展而升级"
                ]
            },
            "abstract": {
                "description": "研究的简要概述",
                "tips": [
                    "明确说明研究目的和方法",
                    "简洁地总结主要发现",
                    "控制在250字以内"
                ]
            },
            "introduction": {
                "description": "研究背景与问题陈述",
                "tips": [
                    "清晰阐述研究问题",
                    "解释研究的重要性",
                    "概述文章的结构"
                ]
            }
        }
        
        # 如果没有特定指导，返回通用指导
        if element not in guidance_map:
            return {
                "description": f"{element}元素",
                "tips": ["确保元素与整体结构协调", "关注质量与完整性"]
            }
        
        return guidance_map[element]
    
    def _get_section_tips(self, section_name: str) -> List[str]:
        """获取章节创作提示"""
        # 实际实现中应从知识库或配置中加载
        tips_map = {
            "设置": [
                "建立鲜明的世界观和氛围",
                "介绍主要角色时突出其独特性",
                "埋下后续发展的伏笔"
            ],
            "冲突": [
                "确保冲突与主角的目标直接相关",
                "设计层层递进的挑战",
                "适时加入转折和意外"
            ],
            "解决": [
                "确保结局与前文的发展一致",
                "处理好所有主要情节线",
                "留给读者深思的空间"
            ],
            "摘要与引言": [
                "清晰界定研究范围和目标",
                "强调研究的创新点和意义",
                "简洁准确地概述研究方法"
            ],
            "文献综述": [
                "按主题或时间顺序组织文献",
                "突出与本研究直接相关的文献",
                "指出现有研究的不足之处"
            ]
        }
        
        if section_name in tips_map:
            return tips_map[section_name]
        
        return ["关注内容质量和完整性", "确保与整体结构保持一致", "注意与前后章节的连贯性"]
    
    def _get_section_examples(self, section_name: str) -> List[Dict[str, Any]]:
        """获取章节示例"""
        # 实际实现中应从知识库或数据库中检索
        # 简化实现，返回空示例
        return []


class StructuredCreationWorkflow(CreationWorkflow):
    """实现结构化创作模式的工作流，提供预定义模板和严格的创作流程控制"""
    
    def __init__(
        self,
        *args, 
        coordinator_agent: Optional[CoordinatorAgent] = None,
        template_type: str = "novel",
        template_id: str = "basic",
        **kwargs
    ):
        """
        初始化结构化创作工作流
        
        参数:
            coordinator_agent: Optional[CoordinatorAgent] - 协调智能体
            template_type: str - 模板类型
            template_id: str - 模板ID
        """
        # 设置工作流类型为"structured"
        kwargs["workflow_type"] = "structured"
        kwargs["coordinator_agent"] = coordinator_agent
        super().__init__(*args, **kwargs)
        
        # 结构化创作特有属性
        self.template_type = template_type
        self.template_id = template_id
        self.structured_coordinator = StructuredModeCoordinator()
        self.creation_template = self.structured_coordinator.load_creation_template(template_type, template_id)
        self.current_section_index = 0
        self.agent_assignments = {}  # 智能体分配情况
    
    def assign_agent_to_section(self, agent: BaseAgent, section_name: str) -> None:
        """
        将智能体分配给特定章节
        
        参数:
            agent: BaseAgent - 要分配的智能体
            section_name: str - 章节名称
        """
        if section_name not in self.agent_assignments:
            self.agent_assignments[section_name] = []
        
        self.agent_assignments[section_name].append(agent)
        self.add_agents([agent])
    
    def get_current_section(self) -> Dict[str, Any]:
        """
        获取当前章节定义
        
        返回:
            Dict[str, Any] - 当前章节的定义
        """
        structure = self.creation_template.get("structure", [])
        if not structure or self.current_section_index >= len(structure):
            return {}
        
        return structure[self.current_section_index]
    
    def get_section_by_name(self, section_name: str) -> Dict[str, Any]:
        """
        通过名称获取章节定义
        
        参数:
            section_name: str - 章节名称
            
        返回:
            Dict[str, Any] - 章节定义
        """
        structure = self.creation_template.get("structure", [])
        for section in structure:
            if section.get("name") == section_name:
                return section
        
        return {}
    
    def _build_graph(self) -> StateGraph:
        """
        构建结构化创作工作流图
        
        返回:
            StateGraph - 工作流状态图
        """
        # 创建StateGraph构建器
        builder = StateGraph(self.creation_state_schema)
        
        # 添加通用节点
        common_nodes = self._build_common_nodes()
        for name, node_func in common_nodes.items():
            builder.add_node(name, node_func)
        
        # 添加结构化模式特有节点
        structured_nodes = self._define_nodes()
        for name, node_func in structured_nodes.items():
            builder.add_node(name, node_func)
        
        # 定义边和条件
        builder = self._define_edges(builder)
        
        # 设置状态聚合器
        builder = self._setup_state_reducers(builder)
        
        return builder
    
    def _define_nodes(self) -> Dict[str, Callable]:
        """
        定义结构化创作特有节点
        
        返回:
            Dict[str, Callable] - 节点名称到节点函数的映射
        """
        nodes = {}
        
        def template_initialization_node(state: CreationState) -> Dict[str, Any]:
            """模板初始化节点"""
            try:
                # 添加模板信息到状态
                return {
                    "status": "template_initialized",
                    "progress": 0.1,
                    "metadata": {
                        **state.get("metadata", {}),
                        "template": {
                            "type": self.template_type,
                            "id": self.template_id,
                            "name": self.creation_template.get("name", "默认模板"),
                            "description": self.creation_template.get("description", ""),
                            "structure": self.creation_template.get("structure", [])
                        },
                        "current_section_index": 0
                    },
                    "updated_at": datetime.utcnow().isoformat(),
                    "creation_logs": state.get("creation_logs", []) + [{
                        "type": "template_initialization",
                        "template_name": self.creation_template.get("name", "默认模板"),
                        "timestamp": datetime.utcnow().isoformat()
                    }]
                }
            except Exception as e:
                return {
                    "error": {
                        "type": "template_initialization_error",
                        "message": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    "status": "error"
                }
        
        def section_selection_node(state: CreationState) -> Dict[str, Any]:
            """章节选择节点"""
            try:
                # 获取当前章节索引
                current_section_index = state.get("metadata", {}).get("current_section_index", 0)
                
                # 更新当前章节索引
                self.current_section_index = current_section_index
                
                # 获取章节结构
                structure = self.creation_template.get("structure", [])
                
                # 检查是否还有章节可选
                if current_section_index >= len(structure):
                    # 所有章节已完成
                    return {
                        "status": "all_sections_completed",
                        "progress": 0.9,
                        "updated_at": datetime.utcnow().isoformat(),
                        "creation_logs": state.get("creation_logs", []) + [{
                            "type": "section_selection",
                            "message": "所有章节已完成",
                            "timestamp": datetime.utcnow().isoformat()
                        }]
                    }
                
                # 获取当前章节
                current_section = structure[current_section_index]
                current_section_name = current_section.get("name", f"章节{current_section_index + 1}")
                
                return {
                    "status": "section_selected",
                    "current_stage": f"section_{current_section_index}",
                    "progress": 0.1 + (current_section_index / len(structure)) * 0.8,
                    "metadata": {
                        **state.get("metadata", {}),
                        "current_section": current_section,
                        "current_section_name": current_section_name
                    },
                    "updated_at": datetime.utcnow().isoformat(),
                    "creation_logs": state.get("creation_logs", []) + [{
                        "type": "section_selection",
                        "selected_section": current_section_name,
                        "timestamp": datetime.utcnow().isoformat()
                    }]
                }
            except Exception as e:
                return {
                    "error": {
                        "type": "section_selection_error",
                        "message": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    "status": "error"
                }
        
        def generate_section_guidance_node(state: CreationState) -> Dict[str, Any]:
            """生成章节指南节点"""
            try:
                # 获取当前章节
                current_section = state.get("metadata", {}).get("current_section", {})
                
                # 生成章节指南
                section_guidance = self.structured_coordinator.generate_section_guidance(current_section)
                
                return {
                    "status": "guidance_generated",
                    "progress": state.get("progress", 0.0) + 0.05,
                    "metadata": {
                        **state.get("metadata", {}),
                        "section_guidance": section_guidance
                    },
                    "updated_at": datetime.utcnow().isoformat(),
                    "creation_logs": state.get("creation_logs", []) + [{
                        "type": "guidance",
                        "section": current_section.get("name", ""),
                        "timestamp": datetime.utcnow().isoformat()
                    }]
                }
            except Exception as e:
                return {
                    "error": {
                        "type": "guidance_error",
                        "message": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    "status": "error"
                }
        
        def structured_creation_node(state: CreationState) -> Dict[str, Any]:
            """结构化创作节点"""
            try:
                # 获取当前章节和指南
                current_section = state.get("metadata", {}).get("current_section", {})
                section_guidance = state.get("metadata", {}).get("section_guidance", {})
                section_name = current_section.get("name", "未知章节")
                
                # 在实际实现中，这里应该调用分配给该章节的智能体执行创作任务
                assigned_agents = self.agent_assignments.get(section_name, [])
                
                # 示例创作内容（简化实现）
                created_content = {
                    f"{section_name}_content": {
                        "timestamp": datetime.utcnow().isoformat(),
                        "guided_by": section_guidance.get("description", ""),
                        "elements": {elem: {"content": f"示例{elem}内容"} for elem in current_section.get("required_elements", [])},
                        "text": f"示例{section_name}章节内容...",
                        "scenes": [{"title": f"场景{i}", "content": f"场景{i}内容"} for i in range(1, 3)],
                        "characters": [{"name": f"角色{i}", "role": "主要" if i == 1 else "次要"} for i in range(1, 4)],
                        "plot_points": current_section.get("completion_criteria", {}).get("required_plot_points", [])
                    }
                }
                
                # 评估章节完成情况
                completion_result = self.structured_coordinator.evaluate_section_completion(
                    current_section,
                    {**state.get("content", {}), **created_content}
                )
                
                return {
                    "status": "creation_in_progress",
                    "progress": state.get("progress", 0.0) + 0.1,
                    "content": {
                        **state.get("content", {}),
                        **created_content
                    },
                    "metadata": {
                        **state.get("metadata", {}),
                        "section_completion": completion_result
                    },
                    "updated_at": datetime.utcnow().isoformat(),
                    "creation_logs": state.get("creation_logs", []) + [{
                        "type": "structured_creation",
                        "section": section_name,
                        "completion_rate": completion_result.get("completion_rate", 0.0),
                        "timestamp": datetime.utcnow().isoformat()
                    }]
                }
            except Exception as e:
                return {
                    "error": {
                        "type": "structured_creation_error",
                        "message": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    "status": "error"
                }
        
        def section_review_node(state: CreationState) -> Dict[str, Any]:
            """章节审查节点"""
            try:
                # 获取当前章节和完成情况
                current_section = state.get("metadata", {}).get("current_section", {})
                section_completion = state.get("metadata", {}).get("section_completion", {})
                section_name = current_section.get("name", "未知章节")
                
                # 在实际实现中，这里应该调用审查智能体进行质量检查
                
                # 示例审查结果
                review_result = {
                    "quality_score": 0.85,
                    "strengths": ["结构清晰", "内容符合要求"],
                    "weaknesses": ["细节可以进一步完善"],
                    "improvement_suggestions": ["增加更多感官描述", "深化角色动机"]
                }
                
                return {
                    "status": "section_reviewed",
                    "progress": state.get("progress", 0.0) + 0.05,
                    "metadata": {
                        **state.get("metadata", {}),
                        "section_review": review_result
                    },
                    "updated_at": datetime.utcnow().isoformat(),
                    "creation_logs": state.get("creation_logs", []) + [{
                        "type": "section_review",
                        "section": section_name,
                        "quality_score": review_result.get("quality_score", 0.0),
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
        
        def section_transition_node(state: CreationState) -> Dict[str, Any]:
            """章节转换节点"""
            try:
                # 获取当前章节索引和完成情况
                current_section_index = state.get("metadata", {}).get("current_section_index", 0)
                section_completion = state.get("metadata", {}).get("section_completion", {})
                
                # 检查章节是否完成
                is_completed = section_completion.get("is_completed", False)
                
                if is_completed:
                    # 更新为下一个章节
                    next_section_index = current_section_index + 1
                    
                    # 更新完成章节列表
                    completed_sections = state.get("metadata", {}).get("completed_sections", [])
                    current_section_name = state.get("metadata", {}).get("current_section_name", "")
                    if current_section_name and current_section_name not in completed_sections:
                        completed_sections.append(current_section_name)
                    
                    return {
                        "status": "advancing_to_next_section",
                        "metadata": {
                            **state.get("metadata", {}),
                            "current_section_index": next_section_index,
                            "completed_sections": completed_sections
                        },
                        "updated_at": datetime.utcnow().isoformat(),
                        "creation_logs": state.get("creation_logs", []) + [{
                            "type": "section_transition",
                            "from_section_index": current_section_index,
                            "to_section_index": next_section_index,
                            "timestamp": datetime.utcnow().isoformat()
                        }]
                    }
                else:
                    # 章节未完成，创建干预点
                    return self._create_section_completion_intervention(state)
            except Exception as e:
                return {
                    "error": {
                        "type": "section_transition_error",
                        "message": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    "status": "error"
                }
        
        nodes["template_initialization"] = template_initialization_node
        nodes["section_selection"] = section_selection_node
        nodes["generate_section_guidance"] = generate_section_guidance_node
        nodes["structured_creation"] = structured_creation_node
        nodes["section_review"] = section_review_node
        nodes["section_transition"] = section_transition_node
        
        return nodes
    
    def _define_edges(self, builder: StateGraph) -> StateGraph:
        """
        定义结构化创作流程边
        
        参数:
            builder: StateGraph - 状态图构建器
            
        返回:
            StateGraph - 添加了边的状态图构建器
        """
        # 定义主流程
        builder.add_edge(START, "initialization")
        builder.add_edge("initialization", "template_initialization")
        builder.add_edge("template_initialization", "section_selection")
        
        # 检查是否所有章节已完成
        builder.add_conditional_edges(
            "section_selection",
            lambda state: "all_sections_completed" if state.get("status") == "all_sections_completed" else "section_selected",
            {
                "all_sections_completed": "result_aggregation",
                "section_selected": "generate_section_guidance"
            }
        )
        
        # 章节创作流程
        builder.add_edge("generate_section_guidance", "structured_creation")
        builder.add_edge("structured_creation", "section_review")
        builder.add_edge("section_review", "section_transition")
        builder.add_edge("section_transition", "section_selection")
        
        # 最终流程
        builder.add_edge("result_aggregation", "review")
        builder.add_edge("review", "finalization")
        builder.add_edge("finalization", END)
        
        # 错误处理
        builder.add_edge(self._handle_error, END)
        
        return builder
    
    def _create_section_completion_intervention(self, state: CreationState) -> Dict[str, Any]:
        """
        创建章节完成干预点
        
        参数:
            state: CreationState - 当前创作状态
            
        返回:
            Dict[str, Any] - 干预结果
        """
        current_section = state.get("metadata", {}).get("current_section", {})
        section_name = current_section.get("name", "未知章节")
        completion = state.get("metadata", {}).get("section_completion", {})
        completion_rate = completion.get("completion_rate", 0.0)
        suggestions = completion.get("suggestions", [])
        missing_elements = completion.get("missing_elements", [])
        criteria_not_met = completion.get("criteria_not_met", [])
        
        # 创建干预信息
        intervention_info = {
            "type": "section_completion",
            "question": f"{section_name}章节完成度为{int(completion_rate*100)}%，但未满足所有要求。您希望如何处理？",
            "options": [
                {"id": "continue", "text": f"继续完善{section_name}章节"},
                {"id": "force_complete", "text": f"将{section_name}章节标记为完成并继续"},
                {"id": "get_suggestions", "text": "获取改进建议"}
            ],
            "context": {
                "section_name": section_name,
                "completion_rate": completion_rate,
                "missing_elements": missing_elements,
                "criteria_not_met": criteria_not_met,
                "suggestions": suggestions
            }
        }
        
        # 更新状态为等待干预
        intervention_updates = self.create_intervention_point(state, intervention_info)
        
        # 添加状态记录
        intervention_updates["status_before_intervention"] = state.get("status")
        intervention_updates["creation_logs"] = state.get("creation_logs", []) + [{
            "type": "intervention_needed",
            "reason": "incomplete_section",
            "section": section_name,
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
