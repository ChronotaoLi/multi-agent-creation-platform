"""
分析智能体模块

实现分析智能体，负责内容分析和洞察，以及评估一致性和质量。
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple, Callable, Set, Union
from datetime import datetime

from app.agents.base_agent import BaseAgent
from app.services.interfaces.llm_service import LLMService

logger = logging.getLogger(__name__)


class ContentStructureAnalyzer:
    """
    内容结构分析器
    
    分析内容结构，识别组织模式和逻辑流程
    """
    
    def __init__(
        self,
        llm_service: LLMService,
        structure_patterns: Dict[str, Dict[str, Any]] = None
    ):
        """
        初始化内容结构分析器
        
        参数:
            llm_service: LLMService - LLM服务实例
            structure_patterns: Dict[str, Dict[str, Any]] - 结构模式定义
        """
        self.llm_service = llm_service
        self.structure_patterns = structure_patterns or {
            "three_act": {
                "description": "三幕结构，包含设置、对抗和结局",
                "parts": ["开端", "发展", "高潮", "结局"],
                "expected_ratio": [0.25, 0.5, 0.2, 0.05]
            },
            "hero_journey": {
                "description": "英雄之旅结构，跟随坎贝尔的英雄模onomyth",
                "parts": ["平凡世界", "冒险召唤", "拒绝召唤", "遇见导师", "跨越第一道门槛", 
                          "考验、盟友与敌人", "接近内窟", "严峻考验", "获得报偿", 
                          "返回之路", "复活", "带着灵药回归"],
                "expected_ratio": [0.1, 0.05, 0.05, 0.05, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.05]
            },
            "problem_solution": {
                "description": "问题-解决方案结构，适合说明性或教育性内容",
                "parts": ["问题陈述", "背景信息", "解决方案", "实施", "结论"],
                "expected_ratio": [0.2, 0.2, 0.3, 0.2, 0.1]
            },
            "compare_contrast": {
                "description": "比较对比结构，比较多个主题的异同",
                "parts": ["引言", "主题A", "主题B", "比较分析", "结论"],
                "expected_ratio": [0.1, 0.3, 0.3, 0.2, 0.1]
            },
            "chronological": {
                "description": "时间顺序结构，按时间顺序组织内容",
                "parts": ["开端", "早期发展", "中期事件", "后期事件", "结论"],
                "expected_ratio": [0.1, 0.25, 0.3, 0.25, 0.1]
            }
        }
        
        # 结构识别提示模板
        self.structure_identification_prompt = """
        你是一个专业的内容结构分析专家。请分析以下内容的结构类型和组织方式。

        内容:
        {content}

        可能的结构类型包括：
        {structure_types}

        请分析这段内容最符合哪种结构模式，并详细说明理由。注意分析内容的节奏、转折点和整体流程。

        请按以下JSON格式回答:
        {{
            "structure_type": "识别出的结构类型名称",
            "confidence": 0-100之间的数字，表示确信度,
            "reasoning": "简短的分析理由",
            "alternative_structure": "可能的替代结构类型（如有）",
            "key_elements": ["识别到的结构关键元素1", "元素2", "..."]
        }}
        """
        
        # 章节提取提示模板
        self.section_extraction_prompt = """
        你是一个专业的内容分析专家。请将以下内容划分为逻辑章节，并提取每个章节的关键信息。

        内容:
        {content}

        请执行以下任务:
        1. 将内容划分为明确的逻辑章节
        2. 为每个章节提供简洁的标题
        3. 捕捉每个章节的关键信息和要点
        4. 识别章节之间的逻辑关系

        请按以下JSON格式回答:
        {{
            "sections": [
                {{
                    "title": "章节标题",
                    "content_summary": "章节内容概要",
                    "key_points": ["要点1", "要点2", "..."],
                    "approximate_position": "开始/中间/结尾或百分比位置",
                    "function": "这个章节在整体中的作用"
                }},
                ...
            ],
            "overall_structure": "内容的整体结构描述",
            "logical_flow": "章节之间的逻辑流程描述"
        }}
        """
        
        # 章节流程分析提示模板
        self.section_flow_prompt = """
        你是一个专业的内容分析专家。请分析以下内容章节之间的逻辑流程和转换质量。

        章节信息:
        {sections_info}

        请分析以下方面:
        1. 章节之间的逻辑连接性和流畅度
        2. 转换是否自然，是否有突兀转折
        3. 是否有逻辑跳跃或信息缺失
        4. 内容的节奏和节奏变化
        5. 是否有冗余或重复部分

        请按以下JSON格式回答:
        {{
            "flow_quality": 1-10之间的数字，表示流程质量,
            "transition_analysis": [
                {{
                    "from_section": "章节A",
                    "to_section": "章节B",
                    "quality": 1-10的评分,
                    "issues": ["问题1", "问题2"]或[],
                    "strengths": ["优点1", "优点2"]或[]
                }},
                ...
            ],
            "overall_assessment": "整体流程评估",
            "improvement_suggestions": ["建议1", "建议2", "..."]
        }}
        """
        
        # 重构建议提示模板
        self.restructure_prompt = """
        你是一个专业的内容编辑专家。请分析以下内容，并提供如何将其重构为{target_structure}结构的具体建议。

        内容:
        {content}

        目标结构 ({target_structure}) 的特点:
        {structure_description}

        请提供详细的重构计划，包括:
        1. 如何重新组织现有内容
        2. 哪些部分需要扩展或压缩
        3. 需要添加哪些元素使内容符合目标结构
        4. 如何改进转换和连贯性

        请按以下JSON格式回答:
        {{
            "restructure_plan": {{
                "current_assessment": "当前内容结构评估",
                "gap_analysis": "当前结构与目标结构的差距分析",
                "major_changes": ["主要变更1", "主要变更2", "..."],
                "sections": [
                    {{
                        "title": "新章节标题",
                        "purpose": "章节目的",
                        "content_sources": ["从原内容的哪些部分获取或改编"],
                        "new_elements": ["需要新增的元素"]
                    }},
                    ...
                ]
            }},
            "effort_assessment": "改动工作量评估 (小/中/大)",
            "expected_benefits": ["预期改进1", "预期改进2", "..."]
        }}
        """
    
    async def identify_structure(self, content: Dict[str, Any]) -> str:
        """
        识别内容结构
        
        参数:
            content: Dict[str, Any] - 内容数据
            
        返回:
            str - 识别出的结构类型
        """
        if not content or "content" not in content:
            raise ValueError("内容数据无效或为空")
        
        text = content["content"]
        if not text:
            return "unknown"
        
        # 准备结构类型描述
        structure_types_desc = []
        for struct_type, details in self.structure_patterns.items():
            parts_str = ", ".join(details["parts"])
            structure_types_desc.append(f"{struct_type}: {details['description']} (包含: {parts_str})")
        
        structure_types_text = "\n".join(structure_types_desc)
        
        # 构建提示
        prompt = self.structure_identification_prompt.format(
            content=text[:10000],  # 限制长度避免超出上下文窗口
            structure_types=structure_types_text
        )
        
        try:
            # 使用LLM进行结构识别
            response = await self.llm_service.chat_complete_json(
                [{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            # 解析结果
            analysis = json.loads(response)
            
            # 获取识别的结构类型
            structure_type = analysis.get("structure_type", "unknown")
            confidence = analysis.get("confidence", 0)
            
            logger.debug(f"内容结构识别: {structure_type} (置信度: {confidence})")
            
            # 如果识别的类型不在预定义模式中，但有替代结构，且替代结构在预定义模式中，则使用替代结构
            if (structure_type not in self.structure_patterns and 
                "alternative_structure" in analysis and 
                analysis["alternative_structure"] in self.structure_patterns):
                structure_type = analysis["alternative_structure"]
                logger.debug(f"使用替代结构类型: {structure_type}")
            
            return structure_type
        
        except Exception as e:
            logger.error(f"内容结构识别失败: {str(e)}")
            return "unknown"
    
    async def extract_sections(self, content: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        提取内容章节
        
        参数:
            content: Dict[str, Any] - 内容数据
            
        返回:
            List[Dict[str, Any]] - 提取的章节列表
        """
        if not content or "content" not in content:
            raise ValueError("内容数据无效或为空")
        
        text = content["content"]
        if not text:
            return []
        
        # 构建提示
        prompt = self.section_extraction_prompt.format(
            content=text[:10000]  # 限制长度避免超出上下文窗口
        )
        
        try:
            # 使用LLM提取章节
            response = await self.llm_service.chat_complete_json(
                [{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            # 解析结果
            extraction = json.loads(response)
            
            # 获取章节列表
            sections = extraction.get("sections", [])
            
            # 添加额外信息
            for i, section in enumerate(sections):
                section["index"] = i
                section["id"] = f"section_{i}"
                
                # 如果有整体结构和逻辑流程，添加到最后一个章节
                if i == len(sections) - 1:
                    section["overall_structure"] = extraction.get("overall_structure", "")
                    section["logical_flow"] = extraction.get("logical_flow", "")
            
            logger.debug(f"已提取 {len(sections)} 个章节")
            return sections
        
        except Exception as e:
            logger.error(f"章节提取失败: {str(e)}")
            return []
    
    async def analyze_section_flow(self, sections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析章节流程
        
        参数:
            sections: List[Dict[str, Any]] - 章节列表
            
        返回:
            Dict[str, Any] - 流程分析结果
        """
        if not sections:
            return {
                "flow_quality": 0,
                "transition_analysis": [],
                "overall_assessment": "没有章节可供分析",
                "improvement_suggestions": ["添加内容章节"]
            }
        
        # 准备章节信息
        sections_info = []
        for i, section in enumerate(sections):
            section_info = (
                f"章节 {i+1}: {section.get('title', f'未命名章节 {i+1}')}\n"
                f"内容概要: {section.get('content_summary', '无概要')}\n"
                f"关键点: {', '.join(section.get('key_points', ['无关键点']))}\n"
                f"位置: {section.get('approximate_position', '未知')}\n"
                f"功能: {section.get('function', '未指定')}\n"
            )
            sections_info.append(section_info)
        
        sections_text = "\n\n".join(sections_info)
        
        # 构建提示
        prompt = self.section_flow_prompt.format(
            sections_info=sections_text
        )
        
        try:
            # 使用LLM分析流程
            response = await self.llm_service.chat_complete_json(
                [{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            # 解析结果
            flow_analysis = json.loads(response)
            
            logger.debug(f"章节流程分析完成，质量评分: {flow_analysis.get('flow_quality', 0)}")
            return flow_analysis
        
        except Exception as e:
            logger.error(f"章节流程分析失败: {str(e)}")
            return {
                "flow_quality": 0,
                "transition_analysis": [],
                "overall_assessment": f"分析失败: {str(e)}",
                "improvement_suggestions": ["重新尝试分析"]
            }
    
    async def suggest_restructure(
        self,
        content: Dict[str, Any],
        target_structure: str
    ) -> Dict[str, Any]:
        """
        提出重构建议
        
        参数:
            content: Dict[str, Any] - 内容数据
            target_structure: str - 目标结构类型
            
        返回:
            Dict[str, Any] - 重构建议
        """
        if not content or "content" not in content:
            raise ValueError("内容数据无效或为空")
            
        text = content["content"]
        if not text:
            return {
                "error": "内容为空，无法提供重构建议"
            }
            
        # 验证目标结构是否存在
        if target_structure not in self.structure_patterns:
            valid_structures = ", ".join(self.structure_patterns.keys())
            return {
                "error": f"无效的目标结构: {target_structure}。有效结构: {valid_structures}"
            }
            
        # 获取目标结构描述
        structure_details = self.structure_patterns[target_structure]
        parts_str = ", ".join(structure_details["parts"])
        structure_description = f"{structure_details['description']} (包含: {parts_str})"
            
        # 构建提示
        prompt = self.restructure_prompt.format(
            content=text[:10000],  # 限制长度避免超出上下文窗口
            target_structure=target_structure,
            structure_description=structure_description
        )
            
        try:
            # 使用LLM提供重构建议
            response = await self.llm_service.chat_complete_json(
                [{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
                
            # 解析结果
            restructure_plan = json.loads(response)
                
            logger.debug(f"已生成重构建议，目标结构: {target_structure}")
            return restructure_plan
        
        except Exception as e:
            logger.error(f"生成重构建议失败: {str(e)}")
            return {
                "error": f"生成重构建议失败: {str(e)}",
                "target_structure": target_structure
            }

class AnalysisAgent(BaseAgent):
    """
    分析智能体
    
    分析内容、生成见解和优化建议，以及评估一致性和质量
    """
    
    def __init__(
        self,
        id: str,
        name: str,
        llm_service: LLMService,
        config: Dict[str, Any] = None
    ):
        """
        初始化分析智能体
        
        参数:
            id: str - 智能体唯一标识符
            name: str - 智能体名称
            llm_service: LLMService - LLM服务实例
            config: Dict[str, Any] - 智能体配置信息
        """
        super().__init__(id, name, "analysis", llm_service, config)
        
        # 初始化分析模型
        self.analysis_models = {
            "structure": ContentStructureAnalyzer(llm_service),
            "sentiment": self._create_sentiment_analyzer(),
            "readability": self._create_readability_analyzer(),
            "coherence": self._create_coherence_analyzer(),
            "engagement": self._create_engagement_analyzer()
        }
        
        # 初始化见解生成器
        self.insight_generators = {
            "structure": self._generate_structure_insights,
            "sentiment": self._generate_sentiment_insights,
            "readability": self._generate_readability_insights,
            "coherence": self._generate_coherence_insights,
            "engagement": self._generate_engagement_insights
        }
        
        # 初始化模式检测器
        self.pattern_detectors = [
            {
                "name": "重复模式",
                "description": "检测内容中的重复片段或模式",
                "detector": self._detect_repetition_patterns
            },
            {
                "name": "过渡模式",
                "description": "分析内容中的转换和过渡模式",
                "detector": self._detect_transition_patterns
            },
            {
                "name": "指称模式",
                "description": "分析实体指称模式和连贯性",
                "detector": self._detect_reference_patterns
            },
            {
                "name": "用词模式",
                "description": "分析用词、词汇多样性和语言风格",
                "detector": self._detect_vocabulary_patterns
            }
        ]
        
        # 分析提示模板
        self.analysis_prompts = {
            "sentiment": """
            你是一个专业的情感分析专家。请分析以下内容的情感基调、变化和细微差别。

            内容:
            {content}

            请按以下JSON格式回答:
            {{
                "overall_sentiment": "整体情感基调（积极/消极/中性等）",
                "sentiment_score": -1到1之间的分数，表示整体情感倾向,
                "emotional_journey": [
                    {{
                        "segment": "内容段落或部分的简要描述",
                        "emotion": "该段落的主要情感",
                        "intensity": 0-10的强度评分
                    }},
                    ...
                ],
                "emotional_balance": "情感平衡性评估",
                "key_emotional_triggers": ["情感触发点1", "情感触发点2", "..."],
                "tonal_consistency": 0-10的一致性评分,
                "dominant_emotions": ["主要情感1", "主要情感2", "..."]
            }}
            """,
            
            "readability": """
            你是一个专业的可读性分析专家。请分析以下内容的可读性、复杂性和易懂程度。

            内容:
            {content}

            请按以下JSON格式回答:
            {{
                "overall_readability": "整体可读性评估",
                "readability_score": 0-100的分数，表示整体可读性（越高越易读）,
                "complexity_factors": [
                    {{
                        "factor": "复杂因素（如句子长度、术语使用等）",
                        "impact": "该因素的影响评估",
                        "examples": ["示例1", "示例2"]
                    }},
                    ...
                ],
                "sentence_structure": "句子结构分析",
                "vocabulary_assessment": "词汇使用评估",
                "target_audience": "适合的目标读者群体",
                "improvement_suggestions": ["改进建议1", "改进建议2", "..."]
            }}
            """,
            
            "coherence": """
            你是一个专业的连贯性分析专家。请分析以下内容的内在连贯性、主题流动和逻辑结构。

            内容:
            {content}

            请按以下JSON格式回答:
            {{
                "overall_coherence": "整体连贯性评估",
                "coherence_score": 0-10的分数，表示整体连贯性,
                "thematic_flow": "主题流动评估",
                "logical_structure": "逻辑结构评估",
                "transition_quality": "转换和过渡质量",
                "consistency_issues": [
                    {{
                        "issue": "一致性问题描述",
                        "location": "问题位置描述",
                        "suggestion": "改进建议"
                    }},
                    ...
                ],
                "strengths": ["连贯性优势1", "连贯性优势2", "..."],
                "improvement_areas": ["需要改进的区域1", "区域2", "..."]
            }}
            """,
            
            "engagement": """
            你是一个专业的内容吸引力分析专家。请分析以下内容的吸引力、引人入胜程度和潜在读者参与度。

            内容:
            {content}

            请按以下JSON格式回答:
            {{
                "overall_engagement": "整体吸引力评估",
                "engagement_score": 0-10的分数，表示整体吸引力,
                "engagement_elements": [
                    {{
                        "element": "吸引力元素（如悬念、共鸣等）",
                        "effectiveness": 0-10的评分,
                        "examples": ["示例1", "示例2"]
                    }},
                    ...
                ],
                "pacing_assessment": "节奏和步调评估",
                "attention_curve": "可能的注意力曲线描述",
                "memorable_aspects": ["令人难忘的方面1", "方面2", "..."],
                "improvement_suggestions": ["提高吸引力的建议1", "建议2", "..."]
            }}
            """
        }
        
        # 比较提示模板
        self.comparison_prompt = """
        你是一个专业的内容比较分析专家。请详细比较以下两个版本的内容，分析它们的异同、优缺点及适用场景。

        版本A:
        {version_a}

        版本B:
        {version_b}

        请按以下JSON格式回答:
        {{
            "similarity_score": 0-100的百分比分数，表示整体相似度,
            "key_differences": [
                {{
                    "aspect": "不同方面（如结构、语调、细节等）",
                    "version_a": "版本A的特点",
                    "version_b": "版本B的特点",
                    "impact": "这一差异的潜在影响"
                }},
                ...
            ],
            "strengths_comparison": {{
                "version_a": ["版本A的优势1", "优势2", "..."],
                "version_b": ["版本B的优势1", "优势2", "..."]
            }},
            "weaknesses_comparison": {{
                "version_a": ["版本A的弱点1", "弱点2", "..."],
                "version_b": ["版本B的弱点1", "弱点2", "..."]
            }},
            "suitability": {{
                "version_a": "版本A更适合的场景",
                "version_b": "版本B更适合的场景"
            }},
            "recommendation": "基于比较的总体推荐",
            "potential_integration": "两个版本可能的整合方案"
        }}
        """
        
        # 关键概念提示模板
        self.key_concepts_prompt = """
        你是一个专业的内容分析专家。请从以下内容中提取和分析关键概念、实体和它们之间的关系。

        内容:
        {content}

        请按以下JSON格式回答:
        {{
            "key_concepts": [
                {{
                    "concept": "关键概念名称",
                    "description": "概念简要描述",
                    "importance": 0-10的重要性评分,
                    "occurrences": 概念出现的大致次数,
                    "related_concepts": ["相关概念1", "相关概念2", "..."]
                }},
                ...
            ],
            "concept_relationships": [
                {{
                    "source": "源概念",
                    "target": "目标概念",
                    "relationship_type": "关系类型（如'部分-整体'、'因果'等）",
                    "description": "关系描述"
                }},
                ...
            ],
            "concept_clusters": [
                {{
                    "cluster_name": "概念集群名称",
                    "concepts": ["概念1", "概念2", "..."],
                    "central_theme": "集群的中心主题"
                }},
                ...
            ],
            "conceptual_gaps": ["可能的概念缺口或发展机会1", "概念缺口2", "..."],
            "concept_map_description": "概念图的总体描述"
        }}
        """
        
    def _create_sentiment_analyzer(self) -> Callable:
        """创建情感分析器"""
        async def analyze_sentiment(content: Dict[str, Any]) -> Dict[str, Any]:
            if not content or "content" not in content:
                raise ValueError("内容数据无效或为空")
                
            text = content["content"]
            if not text:
                return {"error": "内容为空"}
                
            prompt = self.analysis_prompts["sentiment"].format(
                content=text[:10000]  # 限制长度避免超出上下文窗口
            )
            
            try:
                response = await self.llm_service.chat_complete_json(
                    [{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                
                analysis = json.loads(response)
                logger.debug("完成情感分析")
                return analysis
            except Exception as e:
                logger.error(f"情感分析失败: {str(e)}")
                return {"error": f"情感分析失败: {str(e)}"}
                
        return analyze_sentiment
        
    def _create_readability_analyzer(self) -> Callable:
        """创建可读性分析器"""
        async def analyze_readability(content: Dict[str, Any]) -> Dict[str, Any]:
            if not content or "content" not in content:
                raise ValueError("内容数据无效或为空")
                
            text = content["content"]
            if not text:
                return {"error": "内容为空"}
                
            prompt = self.analysis_prompts["readability"].format(
                content=text[:10000]  # 限制长度避免超出上下文窗口
            )
            
            try:
                response = await self.llm_service.chat_complete_json(
                    [{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                
                analysis = json.loads(response)
                logger.debug("完成可读性分析")
                return analysis
            except Exception as e:
                logger.error(f"可读性分析失败: {str(e)}")
                return {"error": f"可读性分析失败: {str(e)}"}
                
        return analyze_readability
        
    def _create_coherence_analyzer(self) -> Callable:
        """创建连贯性分析器"""
        async def analyze_coherence(content: Dict[str, Any]) -> Dict[str, Any]:
            if not content or "content" not in content:
                raise ValueError("内容数据无效或为空")
                
            text = content["content"]
            if not text:
                return {"error": "内容为空"}
                
            prompt = self.analysis_prompts["coherence"].format(
                content=text[:10000]  # 限制长度避免超出上下文窗口
            )
            
            try:
                response = await self.llm_service.chat_complete_json(
                    [{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                
                analysis = json.loads(response)
                logger.debug("完成连贯性分析")
                return analysis
            except Exception as e:
                logger.error(f"连贯性分析失败: {str(e)}")
                return {"error": f"连贯性分析失败: {str(e)}"}
                
        return analyze_coherence
        
    def _create_engagement_analyzer(self) -> Callable:
        """创建吸引力分析器"""
        async def analyze_engagement(content: Dict[str, Any]) -> Dict[str, Any]:
            if not content or "content" not in content:
                raise ValueError("内容数据无效或为空")
                
            text = content["content"]
            if not text:
                return {"error": "内容为空"}
                
            prompt = self.analysis_prompts["engagement"].format(
                content=text[:10000]  # 限制长度避免超出上下文窗口
            )
            
            try:
                response = await self.llm_service.chat_complete_json(
                    [{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                
                analysis = json.loads(response)
                logger.debug("完成吸引力分析")
                return analysis
            except Exception as e:
                logger.error(f"吸引力分析失败: {str(e)}")
                return {"error": f"吸引力分析失败: {str(e)}"}
                
        return analyze_engagement
