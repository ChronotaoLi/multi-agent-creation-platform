"""
引导式创作工作流实现，提供结构化的创作引导和支持
"""

from typing import Any, Callable, Dict, List, Optional
from datetime import datetime

from langgraph.graph import StateGraph, START, END
from langgraph.types import Command, interrupt

from ...agents.coordinator_agent import CoordinatorAgent
from .base_workflow import CreationWorkflow, CreationState


class GuidedModeCoordinator:
    """引导模式下的协调智能体，提供结构化引导和进度跟踪"""
    
    def select_appropriate_stage(self, state: CreationState) -> str:
        """
        选择合适的创作阶段
        
        参数:
            state: CreationState - 当前创作状态
            
        返回:
            str - 选择的阶段名称
        """
        # 获取当前状态信息
        metadata = state.get("metadata", {})
        completed_stages = metadata.get("completed_stages", [])
        current_stage = state.get("current_stage", "")
        
        # 标准引导式创作阶段顺序
        stage_sequence = ["concept", "outline", "character", "scene", "draft", "revision"]
        
        # 如果没有当前阶段或当前阶段已完成，选择下一个阶段
        if not current_stage or current_stage in completed_stages:
            for stage in stage_sequence:
                if stage not in completed_stages:
                    return stage
        
        # 如果已经完成所有阶段或存在未知状态，返回最后阶段
        return current_stage or "concept"
    
    def generate_stage_guidance(self, stage: str, state: CreationState) -> Dict[str, Any]:
        """
        生成阶段引导
        
        参数:
            stage: str - 创作阶段
            state: CreationState - 当前创作状态
            
        返回:
            Dict[str, Any] - 阶段引导信息
        """
        # 根据阶段生成相应的引导内容
        guidance = {
            "stage": stage,
            "description": self._get_stage_description(stage),
            "objectives": self._get_stage_objectives(stage),
            "tips": self._get_stage_tips(stage),
            "examples": self._get_stage_examples(stage, state),
            "questions": self._get_stage_questions(stage),
            "next_steps": self._get_stage_next_steps(stage)
        }
        
        return {"guidance": guidance}
    
    def evaluate_stage_progress(self, stage: str, state: CreationState) -> float:
        """
        评估阶段进度
        
        参数:
            stage: str - 创作阶段
            state: CreationState - 当前创作状态
            
        返回:
            float - 进度百分比 (0.0-1.0)
        """
        # 获取阶段内容和完成标准
        content = state.get("content", {})
        stage_content = content.get(f"{stage}_content", {})
        
        if not stage_content:
            return 0.0
        
        # 根据不同阶段的完成标准计算进度
        if stage == "concept":
            # 概念阶段: 检查是否有主题、设定和中心思想
            required_elements = ["theme", "setting", "central_idea"]
            completed = sum(1 for elem in required_elements if elem in stage_content)
            return min(1.0, completed / len(required_elements))
        
        elif stage == "outline":
            # 大纲阶段: 检查是否有足够的章节或段落
            sections = stage_content.get("sections", [])
            return min(1.0, len(sections) / 5)  # 假设至少需要5个段落
        
        elif stage == "character":
            # 角色阶段: 检查是否有主要角色及其详细信息
            characters = stage_content.get("characters", [])
            if not characters:
                return 0.0
                
            # 检查每个角色的完整度
            completeness_values = []
            for character in characters:
                required_traits = ["name", "background", "motivation", "personality"]
                trait_completeness = sum(1 for trait in required_traits if trait in character)
                completeness_values.append(trait_completeness / len(required_traits))
            
            return min(1.0, sum(completeness_values) / max(1, len(characters)))
        
        elif stage == "scene":
            # 场景阶段: 检查是否有足够的关键场景
            scenes = stage_content.get("scenes", [])
            return min(1.0, len(scenes) / 3)  # 假设至少需要3个关键场景
        
        elif stage == "draft":
            # 草稿阶段: 检查字数或段落数
            draft_text = stage_content.get("text", "")
            if isinstance(draft_text, str):
                word_count = len(draft_text.split())
                return min(1.0, word_count / 1000)  # 假设目标是1000字
            return 0.5  # 无法准确计算时的默认值
        
        elif stage == "revision":
            # 修订阶段: 检查修订完成的部分
            revisions = stage_content.get("revisions", [])
            revision_count = len(revisions)
            return min(1.0, revision_count / 5)  # 假设需要5次修订
        
        return 0.5  # 默认值
    
    def recommend_next_actions(self, stage: str, progress: float) -> List[Dict[str, Any]]:
        """
        推荐下一步行动
        
        参数:
            stage: str - 创作阶段
            progress: float - 阶段进度
            
        返回:
            List[Dict[str, Any]] - 推荐行动列表
        """
        # 根据阶段和进度推荐适当的后续行动
        recommendations = []
        
        # 进度分段处理
        if progress < 0.3:
            # 刚开始阶段
            recommendations.append({
                "action": "explore",
                "description": f"探索{self._get_stage_description(stage)}的更多可能性",
                "importance": "high"
            })
            recommendations.append({
                "action": "study_examples",
                "description": f"研究相关例子，获取{stage}阶段的灵感",
                "importance": "medium"
            })
            
        elif progress < 0.7:
            # 中期阶段
            recommendations.append({
                "action": "refine",
                "description": f"完善已有的{stage}内容",
                "importance": "high"
            })
            recommendations.append({
                "action": "check_coherence",
                "description": "检查各元素之间的一致性和连贯性",
                "importance": "medium"
            })
            
        else:
            # 后期阶段
            recommendations.append({
                "action": "review",
                "description": f"全面审查{stage}阶段的成果",
                "importance": "high"
            })
            recommendations.append({
                "action": "prepare_next_stage",
                "description": "为下一阶段做准备",
                "importance": "medium"
            })
        
        # 添加通用推荐
        recommendations.append({
            "action": "seek_feedback",
            "description": "获取反馈以改进内容",
            "importance": "medium"
        })
        
        return recommendations
    
    def _get_stage_description(self, stage: str) -> str:
        """获取阶段描述"""
        descriptions = {
            "concept": "构思创作的核心概念和主题",
            "outline": "规划作品的整体结构和情节发展",
            "character": "设计和发展作品中的角色",
            "scene": "创建具体场景和重要序列",
            "draft": "完成初稿写作",
            "revision": "修订和完善作品"
        }
        return descriptions.get(stage, "创作阶段")
    
    def _get_stage_objectives(self, stage: str) -> List[str]:
        """获取阶段目标"""
        objectives = {
            "concept": [
                "确定作品的核心主题和信息",
                "建立作品的基本设定和背景",
                "明确作品的目标受众"
            ],
            "outline": [
                "规划作品的整体结构",
                "确定主要情节点",
                "安排情节发展节奏"
            ],
            "character": [
                "创建主要和次要角色",
                "设计角色背景、动机和性格",
                "建立角色之间的关系"
            ],
            "scene": [
                "设计关键场景",
                "确定场景的情感基调",
                "构造场景之间的过渡"
            ],
            "draft": [
                "完成作品的初稿",
                "保持内容与大纲的一致性",
                "注意细节和描述的生动性"
            ],
            "revision": [
                "检查内容的连贯性和一致性",
                "提升语言表达的质量",
                "完善情节和角色发展"
            ]
        }
        return objectives.get(stage, ["完成当前阶段的创作任务"])
    
    def _get_stage_tips(self, stage: str) -> List[str]:
        """获取阶段提示"""
        tips = {
            "concept": [
                "尝试从不同角度思考你的主题",
                "考虑作品可能引起的情感反应",
                "确保概念足够独特或有新颖的表达方式"
            ],
            "outline": [
                "使用三幕结构或其他经典结构作为参考",
                "确保每个主要情节点都有明确的目的",
                "考虑起承转合的节奏变化"
            ],
            "character": [
                "为每个主要角色创建详细的背景故事",
                "考虑角色的成长弧线",
                "确保角色行为与其性格一致"
            ],
            "scene": [
                "关注场景的感官细节",
                "每个场景都应推动情节或角色发展",
                "注意场景的节奏和紧张感"
            ],
            "draft": [
                "不要过于追求完美，重点是完成初稿",
                "保持写作的连续性和动力",
                "记录遇到的问题，留待修订阶段解决"
            ],
            "revision": [
                "客观审视你的作品",
                "考虑寻求外部反馈",
                "注意情节漏洞和逻辑不一致"
            ]
        }
        return tips.get(stage, ["专注当前任务，保持创造力"])
    
    def _get_stage_examples(self, stage: str, state: CreationState) -> List[Dict[str, Any]]:
        """获取阶段示例"""
        # 根据作品类型和主题提供相关示例
        metadata = state.get("metadata", {})
        work_type = metadata.get("work_type", "story")
        theme = metadata.get("theme", "")
        
        # 示例库（实际应用中应从知识库或数据库中检索）
        examples = []
        
        # 简化实现，返回空示例
        return examples
    
    def _get_stage_questions(self, stage: str) -> List[str]:
        """获取引导性问题"""
        questions = {
            "concept": [
                "你希望通过这个作品表达什么?",
                "作品的核心冲突或问题是什么?",
                "读者/观众从中获得什么?"
            ],
            "outline": [
                "故事的主要转折点有哪些?",
                "结局如何体现主题?",
                "情节发展是否有足够的起伏?"
            ],
            "character": [
                "主角面临什么内在和外在冲突?",
                "角色之间的关系如何推动情节?",
                "角色的行为动机是否合理且一致?"
            ],
            "scene": [
                "这个场景如何推动情节或角色发展?",
                "场景的情感基调是什么?",
                "场景中的冲突和解决方式是什么?"
            ],
            "draft": [
                "内容是否与大纲保持一致?",
                "叙事视角是否恰当且一致?",
                "语言风格是否符合作品基调?"
            ],
            "revision": [
                "有哪些内容可以删减或合并?",
                "是否有不一致或不明确的部分?",
                "结构和节奏需要调整吗?"
            ]
        }
        return questions.get(stage, ["如何更好地完成当前阶段?"])
    
    def _get_stage_next_steps(self, stage: str) -> List[str]:
        """获取下一步建议"""
        next_steps = {
            "concept": [
                "确定作品的核心主题和信息",
                "构思基本的故事背景和设定",
                "考虑可能的情节方向"
            ],
            "outline": [
                "确定作品的开始、中间和结束",
                "规划主要情节点和转折",
                "思考次要情节线"
            ],
            "character": [
                "创建主要角色的详细资料",
                "设计角色之间的关系网络",
                "考虑角色的成长轨迹"
            ],
            "scene": [
                "列出关键场景清单",
                "为每个场景确定目的和情感基调",
                "设计场景之间的过渡"
            ],
            "draft": [
                "按照大纲开始写作",
                "专注于内容而非完美表达",
                "保持写作动力和连续性"
            ],
            "revision": [
                "审查内容的整体结构和流畅度",
                "细化人物对话和描述",
                "检查并解决逻辑问题和情节漏洞"
            ]
        }
        return next_steps.get(stage, ["继续当前阶段的工作"])


class GuidedCreationWorkflow(CreationWorkflow):
    """实现引导式创作模式的工作流，为用户提供更多结构化支持"""
    
    def __init__(
        self,
        *args,
        coordinator_agent: Optional[CoordinatorAgent] = None,
        **kwargs
    ):
        """
        初始化引导式创作工作流
        
        参数:
            coordinator_agent: Optional[CoordinatorAgent] - 协调智能体
        """
        # 设置工作流类型为"guided"
        kwargs["workflow_type"] = "guided"
        kwargs["coordinator_agent"] = coordinator_agent
        super().__init__(*args, **kwargs)
        
        # 引导式创作特有属性
        self.guidance_templates = self._load_guidance_templates()
        self.current_stage = ""
        self.stage_completion_criteria = self._define_stage_completion_criteria()
        self.guided_coordinator = GuidedModeCoordinator()
    
    def _load_guidance_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        加载引导模板集合
        
        返回:
            Dict[str, Dict[str, Any]] - 模板集合
        """
        # 实际应用中应从配置或数据库加载
        # 这里提供简化的模板示例
        templates = {
            "story": {
                "stages": ["concept", "outline", "character", "scene", "draft", "revision"],
                "descriptions": {
                    "concept": "故事的核心概念和主题构思",
                    "outline": "故事的结构规划和情节发展",
                    "character": "人物设计和发展",
                    "scene": "场景创建和安排",
                    "draft": "故事初稿写作",
                    "revision": "故事的修订和完善"
                }
            },
            "article": {
                "stages": ["topic", "research", "outline", "draft", "revision"],
                "descriptions": {
                    "topic": "文章主题和焦点确定",
                    "research": "资料收集和研究",
                    "outline": "文章结构和论点规划",
                    "draft": "文章初稿写作",
                    "revision": "文章的修订和完善"
                }
            },
            "poem": {
                "stages": ["theme", "form", "draft", "revision"],
                "descriptions": {
                    "theme": "诗歌的主题和意象构思",
                    "form": "诗歌形式和结构选择",
                    "draft": "诗歌初稿创作",
                    "revision": "诗歌的修订和完善"
                }
            }
        }
        return templates
    
    def _define_stage_completion_criteria(self) -> Dict[str, Callable]:
        """
        定义阶段完成标准
        
        返回:
            Dict[str, Callable] - 阶段完成标准函数字典
        """
        criteria = {}
        
        def concept_complete(state: CreationState) -> bool:
            content = state.get("content", {})
            concept_content = content.get("concept_content", {})
            required = ["theme", "central_idea", "target_audience"]
            return all(key in concept_content for key in required)
        
        def outline_complete(state: CreationState) -> bool:
            content = state.get("content", {})
            outline_content = content.get("outline_content", {})
            sections = outline_content.get("sections", [])
            # 至少需要3个部分且每部分需要有描述
            return len(sections) >= 3 and all("description" in section for section in sections)
        
        def character_complete(state: CreationState) -> bool:
            content = state.get("content", {})
            character_content = content.get("character_content", {})
            characters = character_content.get("characters", [])
            # 至少需要1个主要角色，且每个角色需要基本信息
            required_traits = ["name", "role", "personality"]
            has_main = any(char.get("is_main", False) for char in characters)
            return has_main and all(all(trait in char for trait in required_traits) for char in characters)
        
        def scene_complete(state: CreationState) -> bool:
            content = state.get("content", {})
            scene_content = content.get("scene_content", {})
            scenes = scene_content.get("scenes", [])
            # 至少需要3个场景，且每个场景需要基本信息
            required_fields = ["title", "description", "purpose"]
            return len(scenes) >= 3 and all(all(field in scene for field in required_fields) for scene in scenes)
        
        def draft_complete(state: CreationState) -> bool:
            content = state.get("content", {})
            draft_content = content.get("draft_content", {})
            text = draft_content.get("text", "")
            # 至少500字
            if isinstance(text, str):
                return len(text.split()) >= 500
            return False
        
        def revision_complete(state: CreationState) -> bool:
            content = state.get("content", {})
            revision_content = content.get("revision_content", {})
            revisions = revision_content.get("revisions", [])
            # 至少1次修订
            return len(revisions) >= 1
        
        criteria["concept"] = concept_complete
        criteria["outline"] = outline_complete
        criteria["character"] = character_complete
        criteria["scene"] = scene_complete
        criteria["draft"] = draft_complete
        criteria["revision"] = revision_complete
        
        return criteria
    
    def _build_graph(self) -> StateGraph:
        """
        构建引导式创作工作流图
        
        返回:
            StateGraph - 工作流状态图
        """
        # 创建StateGraph构建器
        builder = StateGraph(self.creation_state_schema)
        
        # 添加通用节点
        common_nodes = self._build_common_nodes()
        for name, node_func in common_nodes.items():
            builder.add_node(name, node_func)
        
        # 添加引导式模式特有节点
        guided_nodes = self._define_nodes()
        for name, node_func in guided_nodes.items():
            builder.add_node(name, node_func)
        
        # 定义边和条件
        builder = self._define_edges(builder)
        
        # 设置状态聚合器
        builder = self._setup_state_reducers(builder)
        
        return builder
    
    def _define_nodes(self) -> Dict[str, Callable]:
        """
        定义引导式创作特有节点
        
        返回:
            Dict[str, Callable] - 节点名称到节点函数的映射
        """
        nodes = {}
        
        def stage_selection_node(state: CreationState) -> Dict[str, Any]:
            """阶段选择节点"""
            try:
                # 调用协调器选择合适的阶段
                selected_stage = self.guided_coordinator.select_appropriate_stage(state)
                
                # 更新当前阶段
                self.current_stage = selected_stage
                
                return {
                    "status": "stage_selected",
                    "current_stage": selected_stage,
                    "progress": 0.2,
                    "metadata": {
                        **state.get("metadata", {}),
                        "current_stage": selected_stage
                    },
                    "updated_at": datetime.utcnow().isoformat(),
                    "creation_logs": state.get("creation_logs", []) + [{
                        "type": "stage_selection",
                        "selected_stage": selected_stage,
                        "timestamp": datetime.utcnow().isoformat()
                    }]
                }
            except Exception as e:
                return {
                    "error": {
                        "type": "stage_selection_error",
                        "message": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    "status": "error"
                }
        
        def generate_guidance_node(state: CreationState) -> Dict[str, Any]:
            """生成引导节点"""
            try:
                # 获取当前阶段
                current_stage = state.get("current_stage", "concept")
                
                # 调用协调器生成阶段引导
                guidance = self.guided_coordinator.generate_stage_guidance(current_stage, state)
                
                return {
                    "status": "guidance_generated",
                    "progress": 0.3,
                    "metadata": {
                        **state.get("metadata", {}),
                        "guidance": guidance.get("guidance")
                    },
                    "updated_at": datetime.utcnow().isoformat(),
                    "creation_logs": state.get("creation_logs", []) + [{
                        "type": "guidance",
                        "stage": current_stage,
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
        
        def guided_creation_node(state: CreationState) -> Dict[str, Any]:
            """引导式创作节点"""
            try:
                # 获取当前阶段和引导
                current_stage = state.get("current_stage", "concept")
                guidance = state.get("metadata", {}).get("guidance", {})
                
                # 模拟智能体根据引导进行创作的过程
                # 在实际实现中，这里应该调用相关智能体执行创作任务
                
                # 示例创作内容（简化实现）
                created_content = {
                    f"{current_stage}_content": {
                        "timestamp": datetime.utcnow().isoformat(),
                        "guided_by": guidance.get("description", ""),
                        "elements": [
                            {"type": "text", "content": f"示例{current_stage}创作内容1"},
                            {"type": "text", "content": f"示例{current_stage}创作内容2"}
                        ]
                    }
                }
                
                # 评估阶段进度
                progress = self.guided_coordinator.evaluate_stage_progress(current_stage, {
                    **state,
                    "content": {**state.get("content", {}), **created_content}
                })
                
                # 获取下一步推荐
                recommendations = self.guided_coordinator.recommend_next_actions(current_stage, progress)
                
                return {
                    "status": "creation_in_progress",
                    "progress": 0.5,
                    "content": {
                        **state.get("content", {}),
                        **created_content
                    },
                    "metadata": {
                        **state.get("metadata", {}),
                        "stage_progress": progress,
                        "recommendations": recommendations
                    },
                    "updated_at": datetime.utcnow().isoformat(),
                    "creation_logs": state.get("creation_logs", []) + [{
                        "type": "guided_creation",
                        "stage": current_stage,
                        "progress": progress,
                        "timestamp": datetime.utcnow().isoformat()
                    }]
                }
            except Exception as e:
                return {
                    "error": {
                        "type": "guided_creation_error",
                        "message": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    "status": "error"
                }
        
        nodes["stage_selection"] = stage_selection_node
        nodes["generate_guidance"] = generate_guidance_node
        nodes["guided_creation"] = guided_creation_node
        
        return nodes
    
    def _define_edges(self, builder: StateGraph) -> StateGraph:
        """
        定义引导式创作流程边
        
        参数:
            builder: StateGraph - 状态图构建器
            
        返回:
            StateGraph - 添加了边的状态图构建器
        """
        # 定义主流程
        builder.add_edge(START, "initialization")
        builder.add_edge("initialization", "stage_selection")
        builder.add_edge("stage_selection", "generate_guidance")
        builder.add_edge("generate_guidance", "guided_creation")
        
        # 在创作后检查阶段完成情况
        builder.add_conditional_edges(
            "guided_creation",
            self._check_stage_completion,
            {
                "stage_complete": "result_aggregation",
                "stage_in_progress": "create_stage_transition_intervention"
            }
        )
        
        # 结果聚合后进入审查
        builder.add_edge("result_aggregation", "review")
        builder.add_edge("review", "finalization")
        builder.add_edge("finalization", END)
        
        # 错误处理
        builder.add_edge(self._handle_error, END)
        
        return builder
    
    def _check_stage_completion(self, state: CreationState) -> str:
        """
        检查阶段完成情况
        
        参数:
            state: CreationState - 当前创作状态
            
        返回:
            str - 决策结果: "stage_complete" 或 "stage_in_progress"
        """
        current_stage = state.get("current_stage", "")
        stage_progress = state.get("metadata", {}).get("stage_progress", 0.0)
        
        # 获取阶段完成标准函数
        completion_check = self.stage_completion_criteria.get(current_stage)
        
        # 如果没有完成标准函数，使用进度阈值
        if not completion_check:
            return "stage_complete" if stage_progress >= 0.8 else "stage_in_progress"
        
        # 使用完成标准函数检查
        is_complete = completion_check(state)
        return "stage_complete" if is_complete else "stage_in_progress"
    
    def _create_stage_transition_intervention(self, state: CreationState) -> Dict[str, Any]:
        """
        创建阶段转换干预点
        
        参数:
            state: CreationState - 当前创作状态
            
        返回:
            Dict[str, Any] - 干预结果
        """
        current_stage = state.get("current_stage", "")
        progress = state.get("metadata", {}).get("stage_progress", 0.0)
        guidance = state.get("metadata", {}).get("guidance", {})
        
        # 使用interrupt函数创建干预点
        intervention_info = {
            "type": "stage_transition",
            "question": f"当前{current_stage}阶段进度为{int(progress*100)}%，您希望如何继续？",
            "options": [
                {"id": "continue", "text": f"继续完善{current_stage}阶段内容"},
                {"id": "complete", "text": f"将{current_stage}阶段标记为完成并进入下一阶段"},
                {"id": "guidance", "text": "获取更多创作引导"}
            ],
            "context": {
                "current_stage": current_stage,
                "progress": progress,
                "guidance": guidance,
                "stage_description": self.guided_coordinator._get_stage_description(current_stage)
            }
        }
        
        # 更新状态为等待干预
        intervention_updates = self.create_intervention_point(state, intervention_info)
        
        # 添加状态记录
        intervention_updates["status_before_intervention"] = state.get("status")
        intervention_updates["creation_logs"] = state.get("creation_logs", []) + [{
            "type": "intervention_needed",
            "reason": "stage_transition",
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
