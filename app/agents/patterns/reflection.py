"""
反思模式智能体

实现具有自我反思与评估能力的智能体
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from app.agents.base_agent import BaseAgent
from app.services.interfaces.llm_service import LLMService
from app.models.domain.llm_types import LLMMessage

logger = logging.getLogger(__name__)


class ReflectionAgent(BaseAgent):
    """
    反思模式智能体
    
    实现自我反思和评估能力的智能体，能够对自己的输出进行批评和改进
    """
    
    def __init__(
        self,
        id: str,
        name: str,
        agent_type: str,
        llm_service: LLMService,
        reflection_criteria: List[str] = None,
        max_reflection_attempts: int = 3,
        config: Dict[str, Any] = None
    ):
        """
        初始化反思智能体
        
        参数:
            id: 智能体唯一标识符
            name: 智能体名称
            agent_type: 智能体类型
            llm_service: LLM服务实例
            reflection_criteria: 反思评估标准列表
            max_reflection_attempts: 最大反思次数
            config: 智能体配置信息
        """
        super().__init__(id, name, agent_type, llm_service, config)
        
        self.reflection_criteria = reflection_criteria or [
            "准确性 - 内容是否客观准确",
            "相关性 - 内容是否与任务相关",
            "完整性 - 内容是否完整全面",
            "逻辑性 - 内容是否逻辑连贯",
            "创造性 - 内容是否有创意和独特性"
        ]
        
        self.reflection_prompt_template = config.get("reflection_prompt_template", """
请对以下输出内容进行批判性思考和评估，考虑以下评估标准：

{criteria}

请分析该输出在以下方面的问题：
1. 有哪些具体的缺陷或错误？
2. 有哪些可以改进的地方？
3. 整体质量评分（1-10分）

输出内容：
```
{output}
```

背景上下文：
{context}

请以JSON格式返回评估结果，包含以下字段：
- issues: 发现的问题列表
- improvements: 改进建议列表
- score: 整体评分（1-10）
- reasoning: 评分理由
""")
        
        self.improvement_prompt_template = config.get("improvement_prompt_template", """
原始输出：
```
{original_output}
```

评估发现的问题：
{issues}

改进建议：
{improvements}

请根据上述问题和建议，重新生成一个改进后的版本。改进后的内容应该：
1. 解决评估中指出的所有问题
2. 采纳所有有价值的改进建议
3. 保持原内容的核心信息和目的
4. 提高整体质量和有效性

请直接给出改进后的内容，无需额外解释。
""")
        
        self.max_reflection_attempts = max_reflection_attempts
        
    async def reflect_on_output(self, output: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        对输出进行反思评估
        
        参数:
            output: 需要评估的输出文本
            context: 输出相关的上下文信息
            
        返回:
            Dict[str, Any]: 反思评估结果
        """
        # 生成反思提示
        reflection_prompt = self._generate_reflection_prompt(output, context)
        
        try:
            # 调用LLM进行反思评估
            messages = [
                LLMMessage(role="system", content="你是一个专注于批判性思考和评估的AI助手。你的任务是分析输出内容的质量并提出改进建议。"),
                LLMMessage(role="user", content=reflection_prompt)
            ]
            
            response = await self.llm_service.chat_completion(
                messages=messages,
                temperature=0.2  # 使用较低的温度以获得更一致的评估
            )
            
            content = response.content
            # 尝试解析JSON响应
            try:
                reflection = json.loads(content)
                # 标准化字段
                if "issues" not in reflection:
                    reflection["issues"] = []
                if "improvements" not in reflection:
                    reflection["improvements"] = []
                if "score" not in reflection:
                    reflection["score"] = 5.0
                if "reasoning" not in reflection:
                    reflection["reasoning"] = "未提供评分理由"
                
                # 确保score是数值
                try:
                    reflection["score"] = float(reflection["score"])
                except (ValueError, TypeError):
                    reflection["score"] = 5.0
                    
                return reflection
                
            except json.JSONDecodeError:
                # 如果返回的不是有效JSON，尝试提取关键信息
                logger.warning(f"反思评估未返回有效JSON: {content}")
                
                # 简单地构造一个结果
                return {
                    "issues": ["无法解析反思结果"],
                    "improvements": ["建议重新生成"],
                    "score": 5.0,
                    "reasoning": "解析错误"
                }
                
        except Exception as e:
            logger.error(f"反思评估失败: {str(e)}")
            return {
                "issues": ["反思过程出错"],
                "improvements": [],
                "score": 0.0,
                "reasoning": f"错误: {str(e)}"
            }
    
    async def improve_output(self, output: str, reflection: Dict[str, Any]) -> str:
        """
        基于反思结果改进输出
        
        参数:
            output: 原始输出
            reflection: 反思评估结果
            
        返回:
            str: 改进后的输出
        """
        # 如果评分较高，无需改进
        if reflection.get("score", 0) >= 9.0 and not reflection.get("issues"):
            return output
            
        # 构造改进提示
        issues_text = "\n".join(f"- {issue}" for issue in reflection.get("issues", []))
        improvements_text = "\n".join(f"- {imp}" for imp in reflection.get("improvements", []))
        
        improvement_prompt = self.improvement_prompt_template.format(
            original_output=output,
            issues=issues_text,
            improvements=improvements_text
        )
        
        try:
            # 调用LLM生成改进版本
            messages = [
                LLMMessage(role="system", content="你是一个专注于内容改进和优化的AI助手。你的任务是根据评估结果改进原始内容。"),
                LLMMessage(role="user", content=improvement_prompt)
            ]
            
            response = await self.llm_service.chat_completion(
                messages=messages,
                temperature=0.5  # 使用适中的温度以平衡创造性和连贯性
            )
            
            return response.content
            
        except Exception as e:
            logger.error(f"输出改进失败: {str(e)}")
            # 如果改进失败，返回原始输出
            return output
    
    async def process_with_reflection(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用反思模式处理输入
        
        参数:
            input_data: 输入数据，包含prompt和context
            
        返回:
            Dict[str, Any]: 处理结果
        """
        # 从输入数据中提取必要信息
        prompt = input_data.get("prompt", "")
        context = input_data.get("context", {})
        
        if not prompt:
            return {"status": "error", "message": "未提供有效的提示"}
            
        # 初始生成
        try:
            messages = [
                LLMMessage(role="system", content=input_data.get("system_prompt", "你是一个有用的AI助手。")),
                LLMMessage(role="user", content=prompt)
            ]
            
            response = await self.llm_service.chat_completion(
                messages=messages,
                temperature=input_data.get("temperature", 0.7),
                max_tokens=input_data.get("max_tokens")
            )
            
            output = response.content
            current_attempt = 1
            
            # 反思和改进循环
            while current_attempt <= self.max_reflection_attempts:
                # 反思评估
                reflection = await self.reflect_on_output(output, context)
                
                # 记录反思过程
                self.context.add_memory(f"reflection_{current_attempt}", {
                    "output": output,
                    "reflection": reflection
                })
                
                # 如果评分足够高，结束反思循环
                if reflection.get("score", 0) >= 8.0:
                    logger.info(f"反思评估得分达到阈值，结束反思过程")
                    break
                
                # 改进输出
                improved_output = await self.improve_output(output, reflection)
                
                # 如果改进后的输出与当前输出相同，结束反思循环
                if improved_output == output:
                    logger.info(f"输出未发生变化，结束反思过程")
                    break
                
                # 更新输出并继续下一轮反思
                output = improved_output
                current_attempt += 1
                
            # 返回最终输出和反思历史
            return {
                "status": "success",
                "output": output,
                "reflection_history": [
                    self.context.get_memory(f"reflection_{i}")
                    for i in range(1, current_attempt)
                ],
                "reflection_rounds": current_attempt - 1
            }
            
        except Exception as e:
            logger.error(f"使用反思模式处理输入时出错: {str(e)}")
            return {
                "status": "error",
                "message": f"处理失败: {str(e)}"
            }
    
    def _generate_reflection_prompt(self, output: str, context: Dict[str, Any]) -> str:
        """
        生成反思提示
        
        参数:
            output: 需要评估的输出
            context: 上下文信息
            
        返回:
            str: 反思提示
        """
        # 格式化评估标准
        formatted_criteria = "\n".join(f"- {criterion}" for criterion in self.reflection_criteria)
        
        # 格式化上下文
        context_str = "\n".join(f"{k}: {v}" for k, v in context.items()) if context else "无可用上下文"
        
        # 生成反思提示
        return self.reflection_prompt_template.format(
            criteria=formatted_criteria,
            output=output,
            context=context_str
        )


class ReflectionNode:
    """
    反思节点
    
    LangGraph图中用于反思的节点，可集成到工作流中
    """
    
    def __init__(self, llm_service: LLMService, reflection_criteria: List[str] = None):
        """
        初始化反思节点
        
        参数:
            llm_service: LLM服务实例
            reflection_criteria: 反思评估标准列表
        """
        self.llm_service = llm_service
        self.reflection_criteria = reflection_criteria or [
            "准确性 - 内容是否客观准确",
            "相关性 - 内容是否与任务相关",
            "完整性 - 内容是否完整全面",
            "逻辑性 - 内容是否逻辑连贯",
            "创造性 - 内容是否有创意和独特性"
        ]
        
        self.reflection_prompt_template = """
请评估以下输出的质量。考虑这些标准：

{criteria}

输出内容：
```
{output}
```

任务目标：
{goal}

以JSON格式返回评估结果，包含以下字段：
- score: 总体评分（1-10）
- issues: 问题列表
- strengths: 优点列表
- should_refine: 是否需要改进（true/false）
"""
    
    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行反思过程
        
        参数:
            state: 工作流状态
            
        返回:
            Dict[str, Any]: 更新后的状态
        """
        # 从状态中提取必要信息
        output = state.get("output", "")
        goal = state.get("goal", "完成任务")
        
        if not output:
            # 如果没有输出需要评估，直接返回
            return state
        
        # 评估输出
        evaluation = await self.evaluate_output(output, {"goal": goal})
        
        # 更新状态
        new_state = state.copy()
        new_state["evaluation"] = evaluation
        new_state["should_refine"] = self.should_refine(evaluation)
        
        return new_state
    
    async def evaluate_output(self, output: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估输出质量
        
        参数:
            output: 需要评估的输出
            context: 上下文信息
            
        返回:
            Dict[str, Any]: 评估结果
        """
        # 格式化评估标准
        formatted_criteria = "\n".join(f"- {criterion}" for criterion in self.reflection_criteria)
        
        # 构造评估提示
        prompt = self.reflection_prompt_template.format(
            criteria=formatted_criteria,
            output=output,
            goal=context.get("goal", "完成任务")
        )
        
        try:
            # 调用LLM进行评估
            messages = [
                LLMMessage(role="system", content="你是一个专注于内容质量评估的专家。你需要客观评估内容的质量。"),
                LLMMessage(role="user", content=prompt)
            ]
            
            response = await self.llm_service.chat_completion(
                messages=messages,
                temperature=0.2
            )
            
            content = response.content
            # 解析JSON响应
            try:
                evaluation = json.loads(content)
                # 标准化字段
                if "score" not in evaluation:
                    evaluation["score"] = 5.0
                if "issues" not in evaluation:
                    evaluation["issues"] = []
                if "strengths" not in evaluation:
                    evaluation["strengths"] = []
                if "should_refine" not in evaluation:
                    evaluation["should_refine"] = len(evaluation["issues"]) > 0
                
                # 确保score是数值
                try:
                    evaluation["score"] = float(evaluation["score"])
                except (ValueError, TypeError):
                    evaluation["score"] = 5.0
                    
                # 确保should_refine是布尔值
                if isinstance(evaluation["should_refine"], str):
                    evaluation["should_refine"] = evaluation["should_refine"].lower() == "true"
                
                return evaluation
                
            except json.JSONDecodeError:
                logger.warning(f"评估未返回有效JSON: {content}")
                # 构造默认评估结果
                return {
                    "score": 5.0,
                    "issues": ["解析评估结果失败"],
                    "strengths": [],
                    "should_refine": True
                }
                
        except Exception as e:
            logger.error(f"评估输出失败: {str(e)}")
            return {
                "score": 0.0,
                "issues": [f"评估过程出错: {str(e)}"],
                "strengths": [],
                "should_refine": True
            }
    
    def should_refine(self, evaluation: Dict[str, Any], threshold: float = 7.0) -> bool:
        """
        判断是否需要改进
        
        参数:
            evaluation: 评估结果
            threshold: 评分阈值
            
        返回:
            bool: 是否需要改进
        """
        # 如果评估明确指出需要改进
        if "should_refine" in evaluation:
            return evaluation["should_refine"]
            
        # 如果评分低于阈值或存在问题，需要改进
        return evaluation.get("score", 0) < threshold or len(evaluation.get("issues", [])) > 0
