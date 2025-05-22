"""
技能专家智能体模块 - 提供特定技能领域的专业支持
"""

from typing import Any, Dict, List, Optional
from ..base_agent import BaseAgent
from ...data_access.llm_adapter.base_llm_provider import LLMService
from ...knowledge_management.hybrid_knowledge import HybridKnowledge


class SkillLibrary:
    """
    技能库，管理和检索特定领域的技能知识
    """
    
    def __init__(self, 
                 skill_domain: str, 
                 library_sources: List[Dict[str, Any]], 
                 hybrid_knowledge: Optional[HybridKnowledge] = None,
                 config: Dict[str, Any] = None):
        """
        初始化技能库
        
        Args:
            skill_domain: 技能领域
            library_sources: 技能知识源
            hybrid_knowledge: 混合知识实例（可选）
            config: 配置参数
        """
        self.skill_domain = skill_domain
        self.library_sources = library_sources
        self.hybrid_knowledge = hybrid_knowledge
        
        config = config or {}
        self.skill_taxonomy = config.get("skill_taxonomy", {})
        self.technique_catalog = config.get("technique_catalog", {})
        self.practice_examples = config.get("practice_examples", {})
        
    def search_techniques(self, 
                          query: str, 
                          difficulty: str = "all", 
                          limit: int = 5) -> List[Dict[str, Any]]:
        """
        搜索特定技能的技术
        
        Args:
            query: 搜索查询
            difficulty: 技术难度 ("beginner", "intermediate", "advanced", "all")
            limit: 返回结果数量限制
            
        Returns:
            技术列表
        """
        # 使用混合知识模型搜索（如果可用）
        if self.hybrid_knowledge:
            search_params = {
                "query": query,
                "limit": limit,
                "filters": {
                    "domain": self.skill_domain,
                    "type": "technique"
                }
            }
            
            if difficulty != "all":
                search_params["filters"]["difficulty"] = difficulty
                
            return self.hybrid_knowledge.search(**search_params)
            
        # 回退到简单搜索
        # 在实际实现中，这会使用结构化数据源
        results = []
        difficulty_levels = [difficulty] if difficulty != "all" else ["beginner", "intermediate", "advanced"]
        
        # 模拟从技术目录中检索
        for i in range(min(limit, 5)):
            for diff in difficulty_levels:
                results.append({
                    "id": f"technique-{i}-{diff}",
                    "name": f"示例技术 {i} ({diff}级)",
                    "description": f"关于'{query}'的{diff}级{self.skill_domain}技术",
                    "difficulty": diff,
                    "application_context": "示例应用上下文",
                    "key_steps": [f"步骤 {j+1}" for j in range(3)],
                    "common_pitfalls": ["常见错误1", "常见错误2"],
                    "source": "技能库",
                })
        
        return results[:limit]
        
    def get_practice_examples(self, 
                             technique_id: str, 
                             count: int = 3) -> List[Dict[str, Any]]:
        """
        获取技术实践示例
        
        Args:
            technique_id: 技术ID
            count: 返回示例数量
            
        Returns:
            实践示例列表
        """
        # 在真实实现中，这会从实践示例库中检索
        examples = []
        
        for i in range(count):
            examples.append({
                "id": f"{technique_id}-example-{i}",
                "title": f"实践示例 {i+1}",
                "content": f"这是{technique_id}技术的实践示例内容",
                "difficulty": "intermediate",
                "author": "示例作者",
                "tags": ["示例", "实践", self.skill_domain],
                "rating": 4.5,
                "comments": []
            })
            
        return examples
        
    def get_skill_progression(self, 
                             starting_level: str = "beginner", 
                             target_level: str = "advanced") -> Dict[str, Any]:
        """
        获取技能进阶路径
        
        Args:
            starting_level: 起始级别
            target_level: 目标级别
            
        Returns:
            进阶路径信息
        """
        # 技能级别顺序
        levels = ["beginner", "intermediate", "advanced", "expert"]
        
        # 验证输入级别
        if starting_level not in levels:
            starting_level = "beginner"
        if target_level not in levels:
            target_level = "advanced"
            
        # 计算需要的阶段
        start_idx = levels.index(starting_level)
        target_idx = levels.index(target_level)
        
        if start_idx >= target_idx:
            return {"error": "起始级别不能高于或等于目标级别"}
            
        # 构建进阶路径
        stages = []
        for i in range(start_idx, target_idx + 1):
            stage_level = levels[i]
            
            # 在真实实现中，这会从技能分类中获取相关技能和技术
            techniques = self.search_techniques(
                query=self.skill_domain, 
                difficulty=stage_level, 
                limit=3
            )
            
            stages.append({
                "level": stage_level,
                "name": f"{stage_level.capitalize()} {self.skill_domain}",
                "description": f"{stage_level.capitalize()}级{self.skill_domain}技能水平描述",
                "key_techniques": techniques,
                "estimated_practice_time": f"{(i-start_idx+1)*3}个月",
                "prerequisites": [] if i == start_idx else [levels[i-1]],
            })
            
        return {
            "skill_domain": self.skill_domain,
            "starting_level": starting_level,
            "target_level": target_level,
            "stages": stages,
            "total_estimated_time": f"{(target_idx-start_idx+1)*3}个月"
        }
        
    def evaluate_skill_application(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估内容中的技能应用
        
        Args:
            content: 要评估的内容
            
        Returns:
            评估结果
        """
        content_text = content.get("description", "")
        if "details" in content:
            details = content["details"]
            if isinstance(details, list):
                content_text += "\n\n" + "\n".join(details)
            elif isinstance(details, str):
                content_text += "\n\n" + details
                
        # 在真实实现中，这可能会使用NLP或LLM提取技能应用点
        # 示例评估逻辑
        techniques_used = []
        for i in range(3):
            techniques_used.append({
                "id": f"technique-{i}",
                "name": f"示例技术 {i}",
                "application_quality": 0.7 + (i * 0.1),
                "context": f"在内容第{i+1}段中应用",
                "improvement_potential": 0.3 - (i * 0.1)
            })
            
        return {
            "content_id": content.get("id", ""),
            "skill_domain": self.skill_domain,
            "overall_skill_level": "intermediate",
            "techniques_used": techniques_used,
            "strengths": ["技能应用优势1", "技能应用优势2"],
            "areas_for_improvement": ["改进领域1", "改进领域2"],
            "recommended_techniques": self.search_techniques(
                query=self.skill_domain, 
                difficulty="intermediate", 
                limit=2
            )
        }


class SkillExpertAgent(BaseAgent):
    """
    技能专家智能体：提供特定技能领域的专业支持，指导技能应用和改进
    """
    
    def __init__(self, 
                 id: str, 
                 name: str, 
                 skill_domain: str,
                 llm_service: LLMService,
                 hybrid_knowledge: Optional[HybridKnowledge] = None,
                 config: Dict[str, Any] = None):
        """
        初始化技能专家智能体
        
        Args:
            id: 智能体唯一标识
            name: 智能体名称
            skill_domain: 技能领域标识
            llm_service: LLM服务实例
            hybrid_knowledge: 混合知识实例（可选）
            config: 配置参数
        """
        super().__init__(id, name, llm_service)
        
        # 设置技能领域
        self.skill_domain = skill_domain
        
        # 初始化配置
        config = config or {}
        self.expertise_level = config.get("expertise_level", 0.9)  # 专业水平，影响建议质量
        
        # 初始化技能库
        library_sources = config.get("library_sources", [])
        self.skill_library = SkillLibrary(
            skill_domain=skill_domain,
            library_sources=library_sources,
            hybrid_knowledge=hybrid_knowledge,
            config=config.get("skill_library_config", {})
        )
        
        # 初始化指导模板
        self.guidance_templates = config.get("guidance_templates", {})
        if not self.guidance_templates:
            self._setup_default_templates()
            
    def _setup_default_templates(self) -> None:
        """设置默认指导模板"""
        self.guidance_templates = {
            "technique_explanation": """
                作为{skill_domain}领域的专家，请详细解释以下技术:
                
                技术: {technique}
                
                请包括:
                - 技术概述和应用场景
                - 关键步骤和原则
                - 常见错误和避免方法
                - 提升应用效果的建议
            """,
            "skill_feedback": """
                作为{skill_domain}领域的专家，请评估以下内容的技能应用:
                
                {content}
                
                请提供具体的技能应用反馈，包括优点和可改进之处。
            """,
            "skill_improvement": """
                作为{skill_domain}领域的专家，请为以下内容提供技能改进建议:
                
                {content}
                
                目标是提升内容中{skill_domain}技能的应用质量。
            """
        }
        
    def explain_technique(self, 
                         technique_id: str, 
                         detail_level: str = "standard") -> Dict[str, Any]:
        """
        解释特定技术
        
        Args:
            technique_id: 技术ID或名称
            detail_level: 详细程度 ("basic", "standard", "advanced")
            
        Returns:
            技术解释
        """
        # 搜索技术信息
        technique_info = None
        search_results = self.skill_library.search_techniques(
            query=technique_id,
            limit=1
        )
        
        if search_results:
            technique_info = search_results[0]
            
        # 如果找不到技术信息，使用ID/名称作为查询
        if not technique_info:
            technique_info = {"name": technique_id, "description": f"技术: {technique_id}"}
            
        # 获取实践示例
        examples = self.skill_library.get_practice_examples(technique_id)
        
        # 构建说明提示
        template = self.guidance_templates.get("technique_explanation")
        prompt = template.format(
            skill_domain=self.skill_domain,
            technique=technique_info["name"]
        )
        
        # 根据详细程度调整提示
        if detail_level == "basic":
            prompt += "\n请提供简洁的基础解释，适合初学者。"
        elif detail_level == "advanced":
            prompt += "\n请提供深入详细的解释，包括高级技巧和实践经验。"
            
        # 添加技术描述
        if "description" in technique_info:
            prompt += f"\n\n技术描述:\n{technique_info['description']}"
            
        # 添加实践示例
        if examples:
            examples_text = "\n\n".join([
                f"示例 {i+1}: {example.get('title', '')}\n{example.get('content', '')}" 
                for i, example in enumerate(examples)
            ])
            prompt += f"\n\n实践示例:\n{examples_text}"
            
        # 使用LLM生成技术解释
        explanation_text = ""
        if self.llm_service:
            explanation_text = self.llm_service.generate_text(prompt)
        else:
            explanation_text = f"关于{technique_info['name']}技术的{detail_level}级别解释"
            
        # 构建响应结构
        explanation = {
            "technique_id": technique_id,
            "technique_name": technique_info.get("name", technique_id),
            "explanation": explanation_text,
            "detail_level": detail_level,
            "examples": examples,
            "skill_domain": self.skill_domain,
            "provided_by": self.name,
            "expertise_level": self.expertise_level
        }
        
        return explanation
        
    def provide_skill_feedback(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        提供技能应用反馈
        
        Args:
            content: 要评估的内容
            
        Returns:
            技能应用反馈
        """
        content_text = content.get("description", "")
        if "details" in content:
            details = content["details"]
            if isinstance(details, list):
                content_text += "\n\n" + "\n".join(details)
            elif isinstance(details, str):
                content_text += "\n\n" + details
                
        # 评估技能应用
        skill_evaluation = self.skill_library.evaluate_skill_application(content)
        
        # 构建反馈提示
        template = self.guidance_templates.get("skill_feedback")
        prompt = template.format(
            skill_domain=self.skill_domain,
            content=content_text
        )
        
        # 添加技能评估信息
        if skill_evaluation.get("techniques_used"):
            techniques_text = "\n".join([
                f"- {t.get('name', 'Unknown')} (应用质量: {t.get('application_quality', 0)*100:.0f}%)"
                for t in skill_evaluation.get("techniques_used", [])
            ])
            prompt += f"\n\n检测到的技术应用:\n{techniques_text}"
            
        # 使用LLM生成反馈
        feedback_text = ""
        if self.llm_service:
            feedback_text = self.llm_service.generate_text(prompt)
        else:
            feedback_text = f"关于{self.skill_domain}技能应用的反馈示例"
            
        # 构建反馈结构
        feedback = {
            "content_id": content.get("id", ""),
            "skill_domain": self.skill_domain,
            "feedback": feedback_text,
            "techniques_assessment": skill_evaluation.get("techniques_used", []),
            "overall_skill_level": skill_evaluation.get("overall_skill_level", "intermediate"),
            "strengths": skill_evaluation.get("strengths", []),
            "areas_for_improvement": skill_evaluation.get("areas_for_improvement", []),
            "recommended_techniques": skill_evaluation.get("recommended_techniques", []),
            "provided_by": self.name,
            "expertise_level": self.expertise_level
        }
        
        return feedback
        
    def suggest_skill_improvements(self, content: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        提供技能改进建议
        
        Args:
            content: 要改进的内容
            
        Returns:
            技能改进建议列表
        """
        content_text = content.get("description", "")
        if "details" in content:
            details = content["details"]
            if isinstance(details, list):
                content_text += "\n\n" + "\n".join(details)
            elif isinstance(details, str):
                content_text += "\n\n" + details
                
        # 评估技能应用
        skill_evaluation = self.skill_library.evaluate_skill_application(content)
        
        # 构建改进建议提示
        template = self.guidance_templates.get("skill_improvement")
        prompt = template.format(
            skill_domain=self.skill_domain,
            content=content_text
        )
        
        # 添加当前技能评估
        if skill_evaluation:
            prompt += f"\n\n当前技能水平评估: {skill_evaluation.get('overall_skill_level', 'intermediate')}"
            
            if skill_evaluation.get("areas_for_improvement"):
                areas_text = "\n".join([
                    f"- {area}" for area in skill_evaluation.get("areas_for_improvement", [])
                ])
                prompt += f"\n\n需要改进的领域:\n{areas_text}"
            
            if skill_evaluation.get("recommended_techniques"):
                tech_text = "\n".join([
                    f"- {tech.get('name', 'Unknown')}" 
                    for tech in skill_evaluation.get("recommended_techniques", [])
                ])
                prompt += f"\n\n推荐技术:\n{tech_text}"
                
        prompt += "\n\n请提供3-5个具体的技能改进建议，每个建议包括:\n1. 要改进的方面\n2. 改进原因\n3. 如何实施改进\n4. 技能层面的提升效果"
        
        # 使用LLM生成改进建议
        improvements_text = ""
        if self.llm_service:
            improvements_text = self.llm_service.generate_text(prompt)
        else:
            # 示例技能改进建议
            improvements_text = """
            建议1: 应用高级叙述技巧
            原因: 当前内容叙述风格较为直接，缺乏深度和层次
            实施: 增加多视角叙事、悬念设置和情感层次
            效果: 显著增强内容吸引力和读者参与度
            
            建议2: 优化角色对话结构
            原因: 对话缺乏自然流畅性和个性特征
            实施: 增加对话节奏变化，强化角色语言特征
            效果: 提高角色真实感和对话生动性
            
            建议3: 强化场景描写技巧
            原因: 场景描述平淡，缺乏感官细节
            实施: 加入多感官描述元素，注重细节与整体平衡
            效果: 创造更沉浸式的阅读体验
            """
            
        # 解析改进建议
        improvements = []
        current_improvement = {}
        for line in improvements_text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
                
            if line.startswith("建议"):
                if current_improvement and "aspect" in current_improvement:
                    improvements.append(current_improvement)
                current_improvement = {"aspect": line}
            elif line.startswith("原因"):
                current_improvement["rationale"] = line.replace("原因:", "").strip()
            elif line.startswith("实施"):
                current_improvement["implementation"] = line.replace("实施:", "").strip()
            elif line.startswith("效果"):
                current_improvement["impact"] = line.replace("效果:", "").strip()
                
        if current_improvement and "aspect" in current_improvement:
            improvements.append(current_improvement)
            
        # 添加元数据
        for i, imp in enumerate(improvements):
            imp["id"] = f"skill-improvement-{i+1}"
            imp["skill_domain"] = self.skill_domain
            imp["suggested_by"] = self.name
            imp["expertise_level"] = self.expertise_level
            imp["difficulty"] = "intermediate"  # 在实际中可能因建议而异
            
        return improvements
        
    def create_skill_development_plan(self, 
                                     current_level: str, 
                                     target_level: str, 
                                     timeframe: str = "3 months") -> Dict[str, Any]:
        """
        创建技能发展计划
        
        Args:
            current_level: 当前技能水平
            target_level: 目标技能水平
            timeframe: 时间框架
            
        Returns:
            技能发展计划
        """
        # 获取技能进阶路径
        progression = self.skill_library.get_skill_progression(
            starting_level=current_level,
            target_level=target_level
        )
        
        if "error" in progression:
            return {"error": progression["error"]}
            
        # 根据时间框架调整计划
        # 在实际实现中，这可能会使用更复杂的时间估算逻辑
        
        # 使用LLM创建定制计划
        stages = progression.get("stages", [])
        stages_text = "\n\n".join([
            f"阶段 {i+1}: {stage.get('name', '')}\n{stage.get('description', '')}" 
            for i, stage in enumerate(stages)
        ])
        
        prompt = f"""
        作为{self.skill_domain}领域的技能专家，请创建一个从{current_level}水平到{target_level}水平的技能发展计划。
        
        时间框架: {timeframe}
        
        参考技能阶段:
        {stages_text}
        
        请创建一个详细的发展计划，包括:
        1. 每个阶段的具体学习目标和里程碑
        2. 推荐的学习资源和实践活动
        3. 进度跟踪和自我评估方法
        4. 根据{timeframe}时间框架的进度安排
        
        计划应该实用、可行且结构清晰。
        """
        
        plan_text = ""
        if self.llm_service:
            plan_text = self.llm_service.generate_text(prompt)
        else:
            plan_text = f"从{current_level}到{target_level}的{self.skill_domain}技能发展计划示例"
            
        # 构建计划结构
        plan = {
            "skill_domain": self.skill_domain,
            "current_level": current_level,
            "target_level": target_level,
            "timeframe": timeframe,
            "plan_text": plan_text,
            "stages": stages,
            "created_by": self.name,
            "expertise_level": self.expertise_level,
            "creation_date": None  # 在实际实现中设置为当前日期
        }
        
        return plan
        
    def analyze_skill_gap(self, 
                         content: Dict[str, Any], 
                         target_level: str = "advanced") -> Dict[str, Any]:
        """
        分析内容与目标技能水平之间的差距
        
        Args:
            content: 要分析的内容
            target_level: 目标技能水平
            
        Returns:
            技能差距分析
        """
        content_text = content.get("description", "")
        if "details" in content:
            details = content["details"]
            if isinstance(details, list):
                content_text += "\n\n" + "\n".join(details)
            elif isinstance(details, str):
                content_text += "\n\n" + details
                
        # 评估当前技能应用
        skill_evaluation = self.skill_library.evaluate_skill_application(content)
        current_level = skill_evaluation.get("overall_skill_level", "beginner")
        
        # 构建差距分析提示
        prompt = f"""
        作为{self.skill_domain}领域的技能专家，请分析以下内容与{target_level}级水平之间的差距:
        
        {content_text}
        
        当前评估的技能水平: {current_level}
        目标技能水平: {target_level}
        
        请详细分析:
        1. 当前内容展现的技能强项
        2. 与{target_level}级技能水平的主要差距
        3. 需要掌握的关键技术和方法
        4. 弥补差距的具体建议
        """
        
        # 使用LLM生成差距分析
        gap_analysis_text = ""
        if self.llm_service:
            gap_analysis_text = self.llm_service.generate_text(prompt)
        else:
            gap_analysis_text = f"{current_level}级与{target_level}级{self.skill_domain}技能的差距分析示例"
            
        # 构建差距分析结构
        gap_analysis = {
            "content_id": content.get("id", ""),
            "skill_domain": self.skill_domain,
            "current_level": current_level,
            "target_level": target_level,
            "gap_analysis": gap_analysis_text,
            "key_gaps": [],  # 在实际实现中，这将从LLM输出中提取
            "required_techniques": [],  # 同上
            "improvement_recommendations": [],  # 同上
            "analyzed_by": self.name,
            "expertise_level": self.expertise_level
        }
        
        return gap_analysis
        
    def demonstrate_technique(self, 
                             technique_id: str, 
                             context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        展示特定技术的应用示例
        
        Args:
            technique_id: 技术ID或名称
            context: 应用上下文（可选）
            
        Returns:
            技术应用示例
        """
        # 搜索技术信息
        technique_info = None
        search_results = self.skill_library.search_techniques(
            query=technique_id,
            limit=1
        )
        
        if search_results:
            technique_info = search_results[0]
            
        # 如果找不到技术信息，使用ID/名称作为查询
        if not technique_info:
            technique_info = {"name": technique_id, "description": f"技术: {technique_id}"}
            
        # 获取实践示例
        examples = self.skill_library.get_practice_examples(technique_id)
        
        # 构建示范提示
        prompt = f"""
        作为{self.skill_domain}领域的技能专家，请展示如何应用"{technique_info['name']}"技术。
        
        请提供:
        1. 技术应用的逐步指南
        2. 一个详细的具体示例
        3. 常见错误和避免方法
        4. 应用技术的最佳实践
        """
        
        # 添加技术描述
        if "description" in technique_info:
            prompt += f"\n\n技术描述:\n{technique_info['description']}"
            
        # 添加上下文（如果有）
        if context:
            context_text = context.get("context_text", "")
            if context_text:
                prompt += f"\n\n应用上下文:\n{context_text}"
                
        # 添加实践示例（如果有）
        if examples:
            example = examples[0]  # 使用第一个示例作为参考
            prompt += f"\n\n参考示例:\n{example.get('content', '')}"
            
        # 使用LLM生成技术示范
        demonstration_text = ""
        if self.llm_service:
            demonstration_text = self.llm_service.generate_text(prompt)
        else:
            demonstration_text = f"{technique_info['name']}技术应用示范示例"
            
        # 构建示范结构
        demonstration = {
            "technique_id": technique_id,
            "technique_name": technique_info.get("name", technique_id),
            "demonstration": demonstration_text,
            "examples_referenced": len(examples),
            "skill_domain": self.skill_domain,
            "context_used": bool(context),
            "demonstrated_by": self.name,
            "expertise_level": self.expertise_level
        }
        
        return demonstration
