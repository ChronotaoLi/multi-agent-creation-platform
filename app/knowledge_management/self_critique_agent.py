"""
自我批评代理实现

评估生成回答的质量并提供改进建议
"""

import logging
import json
from typing import Dict, List, Optional, Any, Tuple, Union

from app.data_access.llm_adapter.base_llm_provider import LLMProvider
from app.core.config import get_settings

logger = logging.getLogger(__name__)

# 获取应用配置
settings = get_settings()

class SelfCritiqueAgent:
    """
    自我批评代理
    
    评估生成的回答质量，找出问题和不足，提供改进建议
    """
    
    def __init__(
        self,
        llm_service: LLMProvider,
        template: Optional[str] = None,
        detailed_analysis: bool = True,
        criteria: Optional[Dict[str, float]] = None
    ):
        """
        初始化自我批评代理
        
        参数:
            llm_service: LLMProvider - LLM服务实例
            template: Optional[str] - 自定义批评模板
            detailed_analysis: bool - 是否提供详细分析
            criteria: Optional[Dict[str, float]] - 评估标准及权重
        """
        self.llm_service = llm_service
        self.detailed_analysis = detailed_analysis
        
        # 默认评估标准及权重
        self.default_criteria = {
            "relevance": 0.25,          # 相关性
            "coherence": 0.15,          # 连贯性
            "information_accuracy": 0.2, # 信息准确性
            "completeness": 0.2,        # 完整性
            "objectivity": 0.1,         # 客观性
            "clarity": 0.1              # 清晰度
        }
        
        # 使用提供的标准或默认标准
        self.criteria = criteria or self.default_criteria
        
        # 默认批评提示模板
        self.default_template = """
        你是一个专业的回答质量评估专家。你的任务是评估以下回答的质量，找出问题和不足，并提供改进建议。

        原始问题: "{original_query}"

        当前回答:
        "{current_answer}"

        参考信息（来自检索结果）:
        {context_summary}

        请按照以下评估标准进行评估:
        1. 相关性 (权重: {relevance_weight}): 回答是否直接解答了原始问题？
        2. 连贯性 (权重: {coherence_weight}): 回答是否结构清晰、逻辑连贯？
        3. 信息准确性 (权重: {accuracy_weight}): 回答中的信息是否与参考信息一致？
        4. 完整性 (权重: {completeness_weight}): 回答是否涵盖了问题的所有重要方面？
        5. 客观性 (权重: {objectivity_weight}): 回答是否避免了主观判断或无根据的推测？
        6. 清晰度 (权重: {clarity_weight}): 回答是否表述清晰、易于理解？

        按照以下JSON格式输出你的评估结果:
        {{
            "scores": {{
                "relevance": 0-10的分数,
                "coherence": 0-10的分数,
                "information_accuracy": 0-10的分数,
                "completeness": 0-10的分数,
                "objectivity": 0-10的分数,
                "clarity": 0-10的分数
            }},
            "overall_score": 0-10的总体分数,
            "confidence": 0-1之间的置信度,
            "issues": [
                "发现的问题1",
                "发现的问题2",
                ...
            ],
            "suggestions": [
                "改进建议1",
                "改进建议2",
                ...
            ],
            {detailed_analysis_field}
        }}

        请确保你的评估是客观的，基于提供的参考信息，并给出具体的改进建议。
        """
        
        self.detailed_analysis_field = """
            "analysis": "详细的分析说明，包括每个评分标准的具体分析和总体评价"
        """
        
        # 使用提供的模板或默认模板
        self.template = template or self.default_template
    
    async def critique(
        self, 
        original_query: str, 
        current_answer: str, 
        sub_query_results: List[Dict[str, Any]], 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        评估当前回答并提供批评意见
        
        参数:
            original_query: str - 原始查询
            current_answer: str - 当前生成的回答
            sub_query_results: List[Dict[str, Any]] - 子查询结果列表
            context: Optional[Dict[str, Any]] - 上下文信息
            
        返回:
            Dict[str, Any] - 批评结果
        """
        context = context or {}
        
        # 准备上下文摘要
        context_summary = self._prepare_context_summary(sub_query_results)
        
        # 格式化评估标准权重
        format_args = {
            "original_query": original_query,
            "current_answer": current_answer,
            "context_summary": context_summary,
            "relevance_weight": self.criteria.get("relevance", 0.25),
            "coherence_weight": self.criteria.get("coherence", 0.15),
            "accuracy_weight": self.criteria.get("information_accuracy", 0.2),
            "completeness_weight": self.criteria.get("completeness", 0.2),
            "objectivity_weight": self.criteria.get("objectivity", 0.1),
            "clarity_weight": self.criteria.get("clarity", 0.1),
            "detailed_analysis_field": self.detailed_analysis_field if self.detailed_analysis else ""
        }
        
        # 构建批评提示
        critique_prompt = self.template.format(**format_args)
        
        # 调用LLM生成批评
        critique_response = await self.llm_service.generate_text(critique_prompt)
        
        # 解析JSON响应
        try:
            # 尝试直接解析
            critique = json.loads(critique_response)
        except json.JSONDecodeError:
            # 如果失败，尝试从响应中提取JSON部分
            try:
                # 找到第一个{和最后一个}之间的内容
                json_start = critique_response.find('{')
                json_end = critique_response.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = critique_response[json_start:json_end]
                    critique = json.loads(json_str)
                else:
                    # 无法提取JSON，返回默认批评
                    logger.warning(f"无法从批评响应中提取JSON: {critique_response}")
                    critique = self._create_default_critique()
            except Exception as e:
                logger.error(f"解析批评响应失败: {str(e)}")
                critique = self._create_default_critique()
        
        # 验证和清理批评
        critique = self._validate_and_clean_critique(critique)
        
        return critique
    
    def _prepare_context_summary(self, sub_query_results: List[Dict[str, Any]]) -> str:
        """
        准备上下文摘要
        
        参数:
            sub_query_results: List[Dict[str, Any]] - 子查询结果列表
            
        返回:
            str - 格式化的上下文摘要
        """
        summary_items = []
        
        for i, result_item in enumerate(sub_query_results):
            sub_query = result_item.get("sub_query", {})
            result = result_item.get("result", {})
            
            query_text = sub_query.get("query", f"子查询 {i+1}")
            answer = result.get("answer", "无答案")
            
            # 添加摘要项
            summary_item = f"""
            子查询 {i+1}: "{query_text}"
            回答: {answer}
            """
            
            # 添加一些上下文片段
            if "context" in result and result["context"]:
                context_snippets = []
                for j, ctx in enumerate(result["context"][:2]):  # 只取前2个上下文项
                    content = ctx.get("content", "")
                    if content:
                        # 截断长内容
                        if len(content) > 150:
                            content = content[:150] + "..."
                        context_snippets.append(f"- 参考 {j+1}: {content}")
                
                if context_snippets:
                    summary_item += "\n关键参考资料:\n" + "\n".join(context_snippets)
            
            summary_items.append(summary_item)
        
        # 合并所有摘要项
        return "\n\n".join(summary_items)
    
    def _create_default_critique(self) -> Dict[str, Any]:
        """
        创建默认的批评结果
        
        返回:
            Dict[str, Any] - 默认批评结果
        """
        return {
            "scores": {
                "relevance": 7,
                "coherence": 7,
                "information_accuracy": 7,
                "completeness": 7,
                "objectivity": 7,
                "clarity": 7
            },
            "overall_score": 7.0,
            "confidence": 0.7,
            "issues": ["无法对回答进行详细评估"],
            "suggestions": ["建议核实回答中的关键信息"],
            "analysis": "系统无法生成详细分析" if self.detailed_analysis else None
        }
    
    def _validate_and_clean_critique(self, critique: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证和清理批评结果
        
        参数:
            critique: Dict[str, Any] - 原始批评结果
            
        返回:
            Dict[str, Any] - 清理后的批评结果
        """
        # 确保包含所需的字段
        if "scores" not in critique or not isinstance(critique["scores"], dict):
            critique["scores"] = self._create_default_critique()["scores"]
        
        # 验证分数字段
        score_fields = ["relevance", "coherence", "information_accuracy", "completeness", "objectivity", "clarity"]
        for field in score_fields:
            if field not in critique["scores"] or not isinstance(critique["scores"][field], (int, float)):
                critique["scores"][field] = 7  # 默认分数
            else:
                # 确保分数在0-10范围内
                critique["scores"][field] = max(0, min(10, critique["scores"][field]))
        
        # 验证总体分数
        if "overall_score" not in critique or not isinstance(critique["overall_score"], (int, float)):
            # 计算加权平均分数
            overall_score = 0
            for field, weight in self.criteria.items():
                if field in critique["scores"]:
                    overall_score += critique["scores"][field] * weight
            critique["overall_score"] = overall_score
        else:
            # 确保总体分数在0-10范围内
            critique["overall_score"] = max(0, min(10, critique["overall_score"]))
        
        # 验证置信度
        if "confidence" not in critique or not isinstance(critique["confidence"], (int, float)):
            # 默认置信度
            critique["confidence"] = 0.7
        else:
            # 确保置信度在0-1范围内
            critique["confidence"] = max(0, min(1, critique["confidence"]))
        
        # 验证问题列表
        if "issues" not in critique or not isinstance(critique["issues"], list):
            critique["issues"] = ["无法识别具体问题"]
        
        # 验证建议列表
        if "suggestions" not in critique or not isinstance(critique["suggestions"], list):
            critique["suggestions"] = ["建议重新审视回答"]
        
        # 验证分析字段（如果启用）
        if self.detailed_analysis:
            if "analysis" not in critique or not isinstance(critique["analysis"], str):
                critique["analysis"] = "无法生成详细分析"
        elif "analysis" in critique:
            # 如果未启用详细分析，移除分析字段
            critique.pop("analysis")
        
        return critique 