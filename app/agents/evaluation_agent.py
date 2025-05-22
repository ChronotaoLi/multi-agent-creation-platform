"""
评估智能体实现

负责评估内容质量和智能体性能的智能体
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from app.agents.base_agent import BaseAgent
from app.services.interfaces.llm_service import LLMService
from app.models.domain.llm_types import LLMMessage

logger = logging.getLogger(__name__)


class EvaluationAgent(BaseAgent):
    """
    评估智能体
    
    负责评估内容质量和智能体性能的智能体
    """
    
    def __init__(
        self,
        id: str,
        name: str,
        llm_service: LLMService,
        config: Dict[str, Any] = None
    ):
        """
        初始化评估智能体
        
        参数:
            id: 智能体唯一标识符
            name: 智能体名称
            llm_service: LLM服务实例
            config: 智能体配置信息
        """
        super().__init__(id, name, "evaluation", llm_service, config or {})
        
        # 评估标准
        self.evaluation_criteria = config.get("evaluation_criteria", {
            "content": {
                "coherence": {
                    "description": "内容的连贯性和逻辑性",
                    "weight": 0.8,
                },
                "creativity": {
                    "description": "内容的创新性和独特性",
                    "weight": 0.7,
                },
                "relevance": {
                    "description": "内容与主题的相关性",
                    "weight": 0.9,
                },
                "correctness": {
                    "description": "内容的事实正确性",
                    "weight": 0.9,
                },
                "engagement": {
                    "description": "内容的吸引力和参与度",
                    "weight": 0.6,
                },
                "clarity": {
                    "description": "表达的清晰度和易理解性",
                    "weight": 0.7,
                },
            },
            "agent_performance": {
                "task_completion": {
                    "description": "智能体完成任务的程度",
                    "weight": 0.9,
                },
                "efficiency": {
                    "description": "智能体执行任务的效率",
                    "weight": 0.7,
                },
                "responsiveness": {
                    "description": "智能体响应指令的准确度",
                    "weight": 0.8,
                },
                "robustness": {
                    "description": "智能体处理异常情况的能力",
                    "weight": 0.7,
                },
                "coordination": {
                    "description": "智能体与其他智能体的协作能力",
                    "weight": 0.6,
                },
            }
        })
        
        # 评估历史
        self.evaluation_history = []
        
        # 系统提示模板
        self.system_prompt_template = config.get("system_prompt_template", """
你是一个专业的评估专家，负责客观、公正地评估内容质量和智能体性能。

在评估时，你应该：
1. 基于明确的标准进行评估
2. 提供具体的证据支持你的评分
3. 指出具体的优点和不足
4. 提出有针对性的改进建议
5. 保持中立、客观的态度

请提供全面、深入、具有建设性的评估，帮助提高内容质量和智能体性能。
""")
    
    async def evaluate_content(self, content: Dict[str, Any], criteria: List[str] = None) -> Dict[str, Any]:
        """
        评估内容质量
        
        参数:
            content: 要评估的内容
            criteria: 评估标准列表，如果为空则使用所有内容评估标准
            
        返回:
            Dict[str, Any]: 评估结果
        """
        try:
            # 提取内容信息
            content_text = content.get("content", "")
            content_type = content.get("type", "text")
            content_metadata = content.get("metadata", {})
            
            # 确定评估标准
            eval_criteria = {}
            if criteria:
                for criterion in criteria:
                    if criterion in self.evaluation_criteria["content"]:
                        eval_criteria[criterion] = self.evaluation_criteria["content"][criterion]
            else:
                eval_criteria = self.evaluation_criteria["content"]
            
            # 构建标准描述
            criteria_text = ""
            for criterion_name, criterion_info in eval_criteria.items():
                criteria_text += f"- {criterion_name}: {criterion_info['description']}\n"
            
            # 构建提示
            prompt = f"""
请评估以下{content_type}类型内容的质量：

内容:
{content_text}

请根据以下标准进行评估:
{criteria_text}

对每个标准，请给出1-10的评分，并提供具体的理由和证据。然后提供整体评价和具体改进建议。

请以JSON格式返回评估结果:
```json
{{
  "scores": {{
    "标准1": {{
      "score": 1-10,
      "justification": "评分理由",
      "evidence": ["支持证据1", "支持证据2", ...]
    }},
    ...
  }},
  "overall_score": 总体评分(1-10),
  "strengths": ["优点1", "优点2", ...],
  "weaknesses": ["缺点1", "缺点2", ...],
  "improvement_suggestions": [
    {{
      "issue": "问题描述",
      "suggestion": "改进建议",
      "expected_impact": "高/中/低"
    }},
    ...
  ],
  "summary": "总体评价"
}}
```
"""
            
            # 调用LLM进行评估
            messages = [
                LLMMessage(role="system", content=self.system_prompt_template),
                LLMMessage(role="user", content=prompt)
            ]
            
            response = await self.llm_service.chat_completion(
                messages=messages,
                temperature=0.3  # 使用较低的温度以获得一致的评估结果
            )
            
            content_response = response.content
            # 提取JSON部分
            import re
            
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content_response)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = content_response
                
            # 解析评估结果
            evaluation_result = json.loads(json_str)
            
            # 计算加权总分(如果没有提供)
            if "overall_score" not in evaluation_result:
                total_score = 0
                total_weight = 0
                
                for criterion_name, score_info in evaluation_result["scores"].items():
                    if criterion_name in eval_criteria:
                        weight = eval_criteria[criterion_name].get("weight", 1.0)
                        total_score += score_info["score"] * weight
                        total_weight += weight
                
                if total_weight > 0:
                    evaluation_result["overall_score"] = round(total_score / total_weight, 2)
                else:
                    evaluation_result["overall_score"] = 5.0  # 默认分数
            
            # 添加元数据
            evaluation_result["content_type"] = content_type
            evaluation_result["content_id"] = content.get("id", "")
            evaluation_result["evaluation_timestamp"] = datetime.now().isoformat()
            evaluation_result["criteria_used"] = list(eval_criteria.keys())
            
            # 保存到评估历史
            self.evaluation_history.append({
                "type": "content",
                "content_id": content.get("id", ""),
                "content_type": content_type,
                "overall_score": evaluation_result["overall_score"],
                "timestamp": evaluation_result["evaluation_timestamp"]
            })
            
            logger.info(f"评估了{content_type}类型内容，总分: {evaluation_result['overall_score']}")
            return evaluation_result
            
        except Exception as e:
            error_msg = f"内容评估失败: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg, "content_id": content.get("id", "")}
    
    async def evaluate_agent_performance(self, agent_id: str, task_records: List[Dict[str, Any]], criteria: List[str] = None) -> Dict[str, Any]:
        """
        评估智能体性能
        
        参数:
            agent_id: 智能体ID
            task_records: 任务记录列表
            criteria: 评估标准列表，如果为空则使用所有智能体性能评估标准
            
        返回:
            Dict[str, Any]: 评估结果
        """
        try:
            # 确定评估标准
            eval_criteria = {}
            if criteria:
                for criterion in criteria:
                    if criterion in self.evaluation_criteria["agent_performance"]:
                        eval_criteria[criterion] = self.evaluation_criteria["agent_performance"][criterion]
            else:
                eval_criteria = self.evaluation_criteria["agent_performance"]
            
            # 构建标准描述
            criteria_text = ""
            for criterion_name, criterion_info in eval_criteria.items():
                criteria_text += f"- {criterion_name}: {criterion_info['description']}\n"
            
            # 格式化任务记录
            tasks_text = ""
            for i, record in enumerate(task_records, 1):
                tasks_text += f"任务 {i}:\n"
                tasks_text += f"- 描述: {record.get('description', '无描述')}\n"
                tasks_text += f"- 状态: {record.get('status', '未知')}\n"
                tasks_text += f"- 开始时间: {record.get('start_time', '未知')}\n"
                tasks_text += f"- 结束时间: {record.get('end_time', '未知')}\n"
                
                if "result" in record:
                    result = record["result"]
                    if isinstance(result, dict):
                        tasks_text += f"- 结果摘要: {json.dumps(result, ensure_ascii=False)[:200]}...\n"
                    else:
                        tasks_text += f"- 结果摘要: {str(result)[:200]}...\n"
                
                if "error" in record:
                    tasks_text += f"- 错误: {record.get('error', '未知错误')}\n"
                
                tasks_text += "\n"
            
            # 构建提示
            prompt = f"""
请评估智能体 {agent_id} 在以下任务中的表现：

任务记录：
{tasks_text}

请根据以下标准进行评估:
{criteria_text}

对每个标准，请给出1-10的评分，并提供具体的理由和证据。然后提供整体评价和具体改进建议。

请以JSON格式返回评估结果:
```json
{{
  "scores": {{
    "标准1": {{
      "score": 1-10,
      "justification": "评分理由",
      "evidence": ["支持证据1", "支持证据2", ...]
    }},
    ...
  }},
  "overall_score": 总体评分(1-10),
  "strengths": ["优点1", "优点2", ...],
  "weaknesses": ["缺点1", "缺点2", ...],
  "improvement_suggestions": [
    {{
      "issue": "问题描述",
      "suggestion": "改进建议",
      "priority": "高/中/低"
    }},
    ...
  ],
  "summary": "总体评价"
}}
```
"""
            
            # 调用LLM进行评估
            messages = [
                LLMMessage(role="system", content=self.system_prompt_template),
                LLMMessage(role="user", content=prompt)
            ]
            
            response = await self.llm_service.chat_completion(
                messages=messages,
                temperature=0.3
            )
            
            content_response = response.content
            # 提取JSON部分
            import re
            
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content_response)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = content_response
                
            # 解析评估结果
            evaluation_result = json.loads(json_str)
            
            # 计算加权总分(如果没有提供)
            if "overall_score" not in evaluation_result:
                total_score = 0
                total_weight = 0
                
                for criterion_name, score_info in evaluation_result["scores"].items():
                    if criterion_name in eval_criteria:
                        weight = eval_criteria[criterion_name].get("weight", 1.0)
                        total_score += score_info["score"] * weight
                        total_weight += weight
                
                if total_weight > 0:
                    evaluation_result["overall_score"] = round(total_score / total_weight, 2)
                else:
                    evaluation_result["overall_score"] = 5.0  # 默认分数
            
            # 添加元数据
            evaluation_result["agent_id"] = agent_id
            evaluation_result["task_count"] = len(task_records)
            evaluation_result["evaluation_timestamp"] = datetime.now().isoformat()
            evaluation_result["criteria_used"] = list(eval_criteria.keys())
            
            # 保存到评估历史
            self.evaluation_history.append({
                "type": "agent_performance",
                "agent_id": agent_id,
                "task_count": len(task_records),
                "overall_score": evaluation_result["overall_score"],
                "timestamp": evaluation_result["evaluation_timestamp"]
            })
            
            logger.info(f"评估了智能体 {agent_id} 的性能，总分: {evaluation_result['overall_score']}")
            return evaluation_result
            
        except Exception as e:
            error_msg = f"智能体性能评估失败: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg, "agent_id": agent_id}
    
    async def compare_outputs(self, outputs: List[Dict[str, Any]], reference: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        比较多个输出结果
        
        参数:
            outputs: 输出结果列表
            reference: 可选的参考输出
            
        返回:
            Dict[str, Any]: 比较结果
        """
        try:
            if len(outputs) < 2 and not reference:
                return {"error": "需要至少两个输出进行比较，或者一个输出和一个参考"}
            
            # 格式化输出内容
            outputs_text = ""
            for i, output in enumerate(outputs, 1):
                content = output.get("content", "")
                if isinstance(content, dict):
                    content = json.dumps(content, ensure_ascii=False, indent=2)
                
                outputs_text += f"输出 {i}:\n{content}\n\n"
            
            # 格式化参考内容
            reference_text = ""
            if reference:
                content = reference.get("content", "")
                if isinstance(content, dict):
                    content = json.dumps(content, ensure_ascii=False, indent=2)
                
                reference_text = f"参考输出:\n{content}\n\n"
            
            # 构建提示
            prompt = f"""
请比较以下输出{f"与参考输出" if reference else ""}：

{outputs_text}
{reference_text}

请进行详细的比较分析，包括：
1. 每个输出的主要优缺点
2. 输出之间的关键差异
3. 在准确性、完整性、清晰度和有用性方面的比较
4. {"与参考输出的相似度和偏差" if reference else "排名和推荐的最佳输出"}

请以JSON格式返回比较结果:
```json
{{
  "analysis": [
    {{
      "output_id": 1,
      "strengths": ["优点1", "优点2", ...],
      "weaknesses": ["缺点1", "缺点2", ...],
      "similarity_to_reference": 0-1的相似度评分(如果有参考),
      "score": 1-10的整体评分
    }},
    ...
  ],
  "key_differences": [
    {{
      "aspect": "差异方面",
      "description": "差异描述",
      "significance": "高/中/低"
    }},
    ...
  ],
  "recommendation": "最佳输出ID和理由"
}}
```
"""
            
            # 调用LLM进行比较
            messages = [
                LLMMessage(role="system", content=self.system_prompt_template),
                LLMMessage(role="user", content=prompt)
            ]
            
            response = await self.llm_service.chat_completion(
                messages=messages,
                temperature=0.4
            )
            
            content_response = response.content
            # 提取JSON部分
            import re
            
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content_response)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = content_response
                
            # 解析比较结果
            comparison_result = json.loads(json_str)
            
            # 添加元数据
            comparison_result["output_count"] = len(outputs)
            comparison_result["has_reference"] = reference is not None
            comparison_result["comparison_timestamp"] = datetime.now().isoformat()
            
            # 提取输出ID（如果有）
            output_ids = []
            for i, output in enumerate(outputs):
                output_ids.append(output.get("id", f"output_{i+1}"))
            comparison_result["output_ids"] = output_ids
            
            logger.info(f"比较了 {len(outputs)} 个输出{' 与参考输出' if reference else ''}")
            return comparison_result
            
        except Exception as e:
            error_msg = f"输出比较失败: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
    
    async def evaluate_consistency(self, content_series: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        评估一系列内容的一致性
        
        参数:
            content_series: 内容序列
            
        返回:
            Dict[str, Any]: 一致性评估结果
        """
        try:
            if len(content_series) < 2:
                return {"error": "需要至少两个内容项来评估一致性"}
            
            # 格式化内容序列
            contents_text = ""
            for i, content_item in enumerate(content_series, 1):
                content = content_item.get("content", "")
                if isinstance(content, dict):
                    content = json.dumps(content, ensure_ascii=False, indent=2)
                
                # 限制内容长度
                if len(content) > 500:
                    content = content[:500] + "...(已截断)"
                
                contents_text += f"内容 {i} ({content_item.get('type', '未知类型')}):\n{content}\n\n"
            
            # 构建提示
            prompt = f"""
请评估以下内容序列的一致性：

{contents_text}

请检查这些内容在以下方面的一致性：
1. 叙事一致性：情节、事件和时间线是否前后一致
2. 角色一致性：角色特征、行为和动机是否一致
3. 世界设定一致性：背景、规则和环境描述是否一致
4. 风格一致性：语言风格、语气和表达方式是否一致
5. 主题一致性：核心主题和信息是否一致

请以JSON格式返回一致性评估：
```json
{{
  "consistency_scores": {{
    "narrative_consistency": 1-10,
    "character_consistency": 1-10,
    "world_building_consistency": 1-10,
    "style_consistency": 1-10,
    "thematic_consistency": 1-10
  }},
  "overall_consistency": 1-10,
  "inconsistencies": [
    {{
      "type": "不一致类型",
      "description": "具体描述",
      "affected_contents": [内容编号列表],
      "severity": "高/中/低"
    }},
    ...
  ],
  "improvement_suggestions": [
    {{
      "issue": "问题",
      "suggestion": "建议",
      "priority": "高/中/低"
    }},
    ...
  ],
  "summary": "总体评价"
}}
```
"""
            
            # 调用LLM评估一致性
            messages = [
                LLMMessage(role="system", content=self.system_prompt_template),
                LLMMessage(role="user", content=prompt)
            ]
            
            response = await self.llm_service.chat_completion(
                messages=messages,
                temperature=0.3
            )
            
            content_response = response.content
            # 提取JSON部分
            import re
            
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content_response)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = content_response
                
            # 解析一致性评估结果
            consistency_result = json.loads(json_str)
            
            # 添加元数据
            consistency_result["content_count"] = len(content_series)
            consistency_result["evaluation_timestamp"] = datetime.now().isoformat()
            
            # 提取内容ID（如果有）
            content_ids = []
            for i, content_item in enumerate(content_series):
                content_ids.append(content_item.get("id", f"content_{i+1}"))
            consistency_result["content_ids"] = content_ids
            
            logger.info(f"评估了 {len(content_series)} 个内容项的一致性，总分: {consistency_result.get('overall_consistency', 0)}")
            return consistency_result
            
        except Exception as e:
            error_msg = f"一致性评估失败: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
    
    async def evaluate_workflow(self, workflow: Dict[str, Any], execution_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        评估工作流执行
        
        参数:
            workflow: 工作流定义
            execution_records: 执行记录列表
            
        返回:
            Dict[str, Any]: 工作流评估结果
        """
        try:
            # 提取工作流信息
            workflow_name = workflow.get("name", "未命名工作流")
            workflow_description = workflow.get("description", "无描述")
            workflow_steps = workflow.get("steps", [])
            
            # 格式化工作流定义
            workflow_text = f"工作流名称: {workflow_name}\n"
            workflow_text += f"描述: {workflow_description}\n"
            workflow_text += f"步骤数: {len(workflow_steps)}\n\n"
            
            for i, step in enumerate(workflow_steps, 1):
                workflow_text += f"步骤 {i}: {step.get('name', f'步骤{i}')}\n"
                workflow_text += f"- 描述: {step.get('description', '无描述')}\n"
                workflow_text += f"- 预期输出: {step.get('expected_output', '未指定')}\n"
                workflow_text += "\n"
            
            # 格式化执行记录
            execution_text = ""
            for i, record in enumerate(execution_records, 1):
                execution_text += f"执行记录 {i}:\n"
                execution_text += f"- 开始时间: {record.get('start_time', '未知')}\n"
                execution_text += f"- 结束时间: {record.get('end_time', '未知')}\n"
                execution_text += f"- 总体状态: {record.get('status', '未知')}\n"
                
                steps = record.get("steps", [])
                execution_text += f"- 完成步骤数: {len(steps)}/{len(workflow_steps)}\n"
                
                for j, step in enumerate(steps, 1):
                    execution_text += f"  步骤 {j}: {step.get('name', f'步骤{j}')}\n"
                    execution_text += f"  - 状态: {step.get('status', '未知')}\n"
                    
                    if "error" in step:
                        execution_text += f"  - 错误: {step['error']}\n"
                    
                    if "duration" in step:
                        execution_text += f"  - 耗时: {step['duration']}秒\n"
                    
                execution_text += "\n"
            
            # 构建提示
            prompt = f"""
请评估以下工作流的执行情况：

工作流定义：
{workflow_text}

执行记录：
{execution_text}

请从以下方面进行评估：
1. 完成度：工作流整体完成情况
2. 效率：执行时间和资源使用
3. 正确性：执行结果是否符合预期
4. 稳定性：执行过程是否稳定，是否有错误或异常
5. 可优化点：工作流设计和执行中可以改进的地方

请以JSON格式返回评估结果：
```json
{{
  "scores": {{
    "completion": 1-10,
    "efficiency": 1-10,
    "correctness": 1-10,
    "stability": 1-10
  }},
  "overall_score": 1-10,
  "bottlenecks": [
    {{
      "step": "步骤名称或编号",
      "issue": "问题描述",
      "impact": "高/中/低"
    }},
    ...
  ],
  "optimization_suggestions": [
    {{
      "type": "优化类型(流程/资源/并行化等)",
      "description": "具体建议",
      "expected_improvement": "预期改进效果"
    }},
    ...
  ],
  "summary": "总体评价"
}}
```
"""
            
            # 调用LLM评估工作流
            messages = [
                LLMMessage(role="system", content=self.system_prompt_template),
                LLMMessage(role="user", content=prompt)
            ]
            
            response = await self.llm_service.chat_completion(
                messages=messages,
                temperature=0.3
            )
            
            content_response = response.content
            # 提取JSON部分
            import re
            
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content_response)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = content_response
                
            # 解析工作流评估结果
            evaluation_result = json.loads(json_str)
            
            # 添加元数据
            evaluation_result["workflow_name"] = workflow_name
            evaluation_result["workflow_id"] = workflow.get("id", "")
            evaluation_result["execution_count"] = len(execution_records)
            evaluation_result["step_count"] = len(workflow_steps)
            evaluation_result["evaluation_timestamp"] = datetime.now().isoformat()
            
            # 保存到评估历史
            self.evaluation_history.append({
                "type": "workflow",
                "workflow_id": workflow.get("id", ""),
                "workflow_name": workflow_name,
                "overall_score": evaluation_result["overall_score"],
                "timestamp": evaluation_result["evaluation_timestamp"]
            })
            
            logger.info(f"评估了工作流 '{workflow_name}' 的执行情况，总分: {evaluation_result['overall_score']}")
            return evaluation_result
            
        except Exception as e:
            error_msg = f"工作流评估失败: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg, "workflow_name": workflow.get("name", "未命名工作流")}
    
    async def provide_actionable_feedback(self, evaluation_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        基于评估结果提供可操作的反馈
        
        参数:
            evaluation_result: 评估结果
            
        返回:
            Dict[str, Any]: 可操作的反馈
        """
        try:
            # 提取评估类型和基本信息
            eval_type = ""
            if "content_type" in evaluation_result:
                eval_type = "content"
            elif "agent_id" in evaluation_result:
                eval_type = "agent_performance"
            elif "workflow_name" in evaluation_result:
                eval_type = "workflow"
            elif "output_count" in evaluation_result:
                eval_type = "comparison"
            elif "consistency_scores" in evaluation_result:
                eval_type = "consistency"
            else:
                eval_type = "unknown"
            
            # 格式化评估结果
            eval_text = json.dumps(evaluation_result, ensure_ascii=False, indent=2)
            if len(eval_text) > 2000:
                eval_text = eval_text[:2000] + "...(已截断)"
            
            # 构建提示
            prompt = f"""
请基于以下{eval_type}类型的评估结果，提供具体的、可操作的改进建议：

评估结果：
{eval_text}

请提供以下格式的反馈：
1. 明确、具体的行动建议
2. 每个建议的优先级和预期效果
3. 实施建议的步骤或方法
4. 如何衡量改进效果

请以JSON格式返回可操作的反馈：
```json
{{
  "prioritized_actions": [
    {{
      "action": "具体行动建议",
      "priority": "高/中/低",
      "reasoning": "为什么这是重要的",
      "implementation": ["步骤1", "步骤2", ...],
      "expected_outcome": "预期效果",
      "measurement": "衡量改进的方法"
    }},
    ...
  ],
  "quick_wins": ["可以立即实施的小改进1", "可以立即实施的小改进2", ...],
  "long_term_improvements": ["需要长期规划的改进1", "需要长期规划的改进2", ...],
  "summary": "反馈总结"
}}
```
"""
            
            # 调用LLM提供反馈
            messages = [
                LLMMessage(role="system", content=self.system_prompt_template),
                LLMMessage(role="user", content=prompt)
            ]
            
            response = await self.llm_service.chat_completion(
                messages=messages,
                temperature=0.4
            )
            
            content_response = response.content
            # 提取JSON部分
            import re
            
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content_response)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = content_response
                
            # 解析反馈结果
            feedback = json.loads(json_str)
            
            # 添加元数据
            feedback["evaluation_type"] = eval_type
            feedback["feedback_timestamp"] = datetime.now().isoformat()
            
            if eval_type == "content":
                feedback["content_id"] = evaluation_result.get("content_id", "")
                feedback["content_type"] = evaluation_result.get("content_type", "")
            elif eval_type == "agent_performance":
                feedback["agent_id"] = evaluation_result.get("agent_id", "")
            elif eval_type == "workflow":
                feedback["workflow_id"] = evaluation_result.get("workflow_id", "")
                feedback["workflow_name"] = evaluation_result.get("workflow_name", "")
            
            logger.info(f"基于{eval_type}类型评估结果提供了可操作反馈，包含 {len(feedback.get('prioritized_actions', []))} 个优先行动建议")
            return feedback
            
        except Exception as e:
            error_msg = f"提供可操作反馈失败: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg, "evaluation_type": eval_type}
    
    def get_evaluation_history(self, type_filter: str = None, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取评估历史记录
        
        参数:
            type_filter: 可选的类型过滤器
            limit: 返回记录的数量限制
            
        返回:
            List[Dict[str, Any]]: 评估历史记录
        """
        if type_filter:
            filtered_history = [record for record in self.evaluation_history if record.get("type") == type_filter]
            return filtered_history[-limit:]
        else:
            return self.evaluation_history[-limit:]