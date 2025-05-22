"""
结果合成器实现

分析多个子查询的结果，生成综合性的回答
"""

import logging
import json
from typing import Dict, List, Optional, Any, Union

from app.data_access.llm_adapter.base_llm_provider import LLMProvider
from app.core.config import get_settings

logger = logging.getLogger(__name__)

# 获取应用配置
settings = get_settings()

class ResultSynthesizer:
    """
    结果合成器
    
    分析多个检索结果和子查询回答，合成一个连贯、全面的最终回答
    """
    
    def __init__(
        self,
        llm_service: LLMProvider,
        template: Optional[str] = None,
        max_context_length: int = 8000,
        enable_reasoning: bool = True
    ):
        """
        初始化结果合成器
        
        参数:
            llm_service: LLMProvider - LLM服务实例
            template: Optional[str] - 自定义合成模板
            max_context_length: int - 最大上下文长度
            enable_reasoning: bool - 是否启用推理过程
        """
        self.llm_service = llm_service
        self.max_context_length = max_context_length
        self.enable_reasoning = enable_reasoning
        
        # 默认合成提示模板
        self.default_template = """
        你是一个精确、全面的回答合成专家。你的任务是基于以下子查询及其结果，为用户的原始问题生成一个综合的、连贯的回答。

        原始问题: "{original_query}"

        子查询结果:
        {results}

        请遵循以下指导原则:
        1. 综合所有相关信息，但避免重复或冗余
        2. 保持答案的连贯性和流畅性
        3. 清晰标明信息的来源(如果可知)
        4. 解决可能存在的信息冲突，并说明你的推理过程
        5. 如果缺乏足够信息，坦率地表明这一点
        6. 按重要性和相关性组织信息

        {reasoning_instruction}

        请提供你的综合回答:
        """
        
        self.reasoning_instruction = """
        在生成最终回答前，请简要说明你的推理过程，解释你如何整合不同来源的信息以及如何解决潜在的信息冲突。
        """
        
        self.no_reasoning_instruction = """
        直接提供最终回答，无需解释推理过程。
        """
        
        # 使用提供的模板或默认模板
        self.template = template or self.default_template
    
    async def synthesize(
        self, 
        original_query: str, 
        sub_query_results: List[Dict[str, Any]], 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        综合多个查询结果，生成最终回答
        
        参数:
            original_query: str - 原始查询
            sub_query_results: List[Dict[str, Any]] - 子查询结果列表
            context: Optional[Dict[str, Any]] - 上下文信息
            
        返回:
            Dict[str, Any] - 合成结果，包含回答和可选的推理过程
        """
        context = context or {}
        
        # 格式化子查询结果
        formatted_results = []
        
        for i, result_item in enumerate(sub_query_results):
            sub_query = result_item.get("sub_query", {})
            result = result_item.get("result", {})
            
            query_text = sub_query.get("query", f"子查询 {i+1}")
            answer = result.get("answer", "无答案")
            quality_score = result.get("quality_score", 0.0)
            strategy = result.get("strategy", "unknown")
            
            # 只包含少量上下文示例，而不是全部
            context_examples = []
            if "context" in result and result["context"]:
                for j, ctx in enumerate(result["context"][:3]):  # 只取前3个上下文项
                    content = ctx.get("content", "")
                    if content:
                        # 截断长内容
                        if len(content) > 200:
                            content = content[:200] + "..."
                        context_examples.append(f"- 上下文 {j+1}: {content}")
            
            context_text = "\n".join(context_examples) if context_examples else "无上下文"
            
            formatted_result = f"""
            子查询 {i+1}: "{query_text}"
            策略: {strategy}
            质量分数: {quality_score}
            回答: {answer}
            
            上下文摘要:
            {context_text}
            """
            
            formatted_results.append(formatted_result)
        
        # 合并所有格式化结果
        all_results = "\n\n".join(formatted_results)
        
        # 选择是否包含推理指导
        reasoning_instruction = self.reasoning_instruction if self.enable_reasoning else self.no_reasoning_instruction
        
        # 构建合成提示
        synthesis_prompt = self.template.format(
            original_query=original_query,
            results=all_results,
            reasoning_instruction=reasoning_instruction
        )
        
        # 截断提示以适应模型限制
        if len(synthesis_prompt) > self.max_context_length:
            logger.warning(f"合成提示超过最大长度 ({len(synthesis_prompt)} > {self.max_context_length})，将进行截断")
            # 简单截断策略（在实际系统中可能需要更复杂的处理）
            synthesis_prompt = synthesis_prompt[:self.max_context_length]
        
        # 调用LLM生成合成回答
        synthesis_response = await self.llm_service.generate_text(synthesis_prompt)
        
        # 处理回答，分离推理和最终回答（如果启用推理）
        final_answer, reasoning = self._process_synthesis_response(synthesis_response)
        
        # 返回结果
        result = {
            "answer": final_answer,
            "original_query": original_query,
            "sub_queries_count": len(sub_query_results)
        }
        
        # 如果启用推理，添加推理过程
        if self.enable_reasoning and reasoning:
            result["reasoning"] = reasoning
        
        return result
    
    def _process_synthesis_response(self, response: str) -> tuple[str, Optional[str]]:
        """
        处理合成响应，分离推理和最终回答
        
        参数:
            response: str - LLM生成的合成响应
            
        返回:
            Tuple[str, Optional[str]] - (最终回答, 推理过程(可选))
        """
        # 如果未启用推理，直接返回完整响应作为答案
        if not self.enable_reasoning:
            return response.strip(), None
        
        # 尝试分离推理和最终回答
        # 查找常见的分隔标记
        separators = [
            "最终回答:", "综合回答:", "回答:", "答案:", 
            "Final Answer:", "Synthesized Answer:", "Answer:"
        ]
        
        # 尝试使用分隔符分割
        reasoning = None
        answer = response.strip()
        
        for separator in separators:
            if separator in response:
                parts = response.split(separator, 1)
                reasoning = parts[0].strip()
                answer = parts[1].strip()
                break
        
        # 如果没有找到明确的分隔符，尝试启发式方法
        # 假设前几段是推理，最后一段是回答
        if reasoning is None and "\n\n" in response:
            paragraphs = response.split("\n\n")
            if len(paragraphs) > 1:
                answer = paragraphs[-1].strip()
                reasoning = "\n\n".join(paragraphs[:-1]).strip()
        
        return answer, reasoning 