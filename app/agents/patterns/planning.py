"""
规划模式智能体

实现具有任务分解和规划能力的智能体
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from app.agents.base_agent import BaseAgent
from app.services.interfaces.llm_service import LLMService
from app.models.domain.llm_types import LLMMessage

logger = logging.getLogger(__name__)


class PlanningAgent(BaseAgent):
    """
    规划模式智能体
    
    具有任务分解和规划能力的智能体，可以制定执行计划并按步骤执行
    """
    
    def __init__(
        self,
        id: str,
        name: str,
        agent_type: str,
        llm_service: LLMService,
        max_planning_attempts: int = 3,
        max_execution_steps: int = 10,
        config: Dict[str, Any] = None
    ):
        """
        初始化规划智能体
        
        参数:
            id: 智能体唯一标识符
            name: 智能体名称
            agent_type: 智能体类型
            llm_service: LLM服务实例
            max_planning_attempts: 最大规划尝试次数
            max_execution_steps: 最大执行步骤数
            config: 智能体配置信息
        """
        super().__init__(id, name, agent_type, llm_service, config)
        
        self.max_planning_attempts = max_planning_attempts
        self.max_execution_steps = max_execution_steps
        
        # 规划提示模板
        self.planning_prompt_template = config.get("planning_prompt_template", """
你需要为以下任务制定一个详细的执行计划：

任务：{task}

{context}

请将任务分解为一系列具体、可执行的步骤。你的计划应该：
1. 从当前状态到目标状态提供清晰的路径
2. 包含足够的细节，使每个步骤都可以独立执行
3. 考虑可能的障碍和备选方案
4. 保持步骤之间的逻辑连贯性

请以下面的JSON格式返回你的规划结果：
```json
{
  "plan_name": "计划名称",
  "description": "计划的简短描述",
  "steps": [
    {
      "id": "1",
      "name": "步骤名称",
      "description": "步骤详细描述",
      "expected_outcome": "预期结果",
      "dependencies": []
    },
    {
      "id": "2",
      "name": "步骤名称",
      "description": "步骤详细描述",
      "expected_outcome": "预期结果",
      "dependencies": ["1"]
    },
    ...
  ]
}
```

请确保每个步骤都是具体和可执行的，并且明确标识步骤之间的依赖关系。
""")
        
        # 步骤执行提示模板
        self.step_execution_template = config.get("step_execution_template", """
你正在执行一项任务的计划。以下是当前的任务步骤：

步骤名称：{step_name}
步骤描述：{step_description}
预期结果：{expected_outcome}

完整的任务计划：
{plan_summary}

当前进度：已完成 {completed_steps_count}/{total_steps_count} 个步骤
已完成的步骤：{completed_steps}

任务背景：
{context}

请执行当前步骤，并提供详细的执行结果。你的回答应该：
1. 解释你如何执行这个步骤
2. 提供执行过程中的关键决策和考虑因素
3. 明确说明执行结果是否达到预期
4. 如果遇到问题，提出可能的解决方案

请以JSON格式返回结果：
```json
{
  "execution": "步骤的执行过程和决策",
  "result": "执行结果",
  "success": true/false,
  "issues": ["遇到的问题"],
  "next_actions": ["建议的后续行动"]
}
```
""")
        
        # 计划评估提示模板
        self.plan_evaluation_template = config.get("plan_evaluation_template", """
请评估以下执行计划是否足够完整和有效：

计划名称：{plan_name}
计划描述：{plan_description}

计划步骤：
{plan_steps}

任务：{task}

请分析这个计划的优缺点，特别是：
1. 计划是否足够完整，覆盖了完成任务的所有必要步骤？
2. 步骤之间的依赖关系是否合理？
3. 计划是否有效率，没有多余或重复的步骤？
4. 是否考虑了可能的问题和风险？
5. 每个步骤是否足够具体和可执行？

请以JSON格式返回评估结果：
```json
{
  "score": 0-10的评分,
  "complete": true/false,
  "strengths": ["计划的优点"],
  "weaknesses": ["计划的缺点"],
  "missing_steps": ["缺失的步骤"],
  "improvement_suggestions": ["改进建议"],
  "should_replan": true/false
}
```
""")
        
        # 结果整合提示模板
        self.results_integration_template = config.get("results_integration_template", """
以下是任务"{task}"的计划和执行结果的总结：

原始计划：
{original_plan}

执行结果摘要：
{execution_summary}

请根据原计划和执行结果，提供一个全面的任务执行总结。你的总结应该：
1. 概述最初的计划和目标
2. 回顾执行过程中的主要步骤和关键决策
3. 分析达成的成果与最初目标的符合度
4. 指出遇到的挑战及如何解决的
5. 提供对未来类似任务的建议

请以一个结构化的报告形式呈现总结。
""")
    
    async def create_plan(self, task: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        为任务创建执行计划
        
        参数:
            task: 任务描述
            context: 上下文信息
            
        返回:
            Dict[str, Any]: 计划内容
        """
        context = context or {}
        context_str = self._format_context(context)
        
        # 构造规划提示
        prompt = self.planning_prompt_template.format(
            task=task,
            context=context_str
        )
        
        try:
            # 调用LLM生成计划
            messages = [
                LLMMessage(role="system", content=f"你是{self.name}，一个专注于任务规划的智能体。你擅长将复杂任务分解为可执行的步骤。"),
                LLMMessage(role="user", content=prompt)
            ]
            
            response = await self.llm_service.chat_completion(
                messages=messages,
                temperature=0.3 # 使用低温度以获得更一致的规划
            )
            
            content = response.content
            
            # 提取JSON格式的计划
            plan = self._extract_json(content)
            
            if not plan:
                logger.warning("无法从LLM响应中提取有效的计划JSON")
                return {
                    "status": "error",
                    "message": "无法生成有效的计划"
                }
            
            # 验证计划格式
            if not self._validate_plan(plan):
                logger.warning(f"计划格式验证失败: {plan}")
                return {
                    "status": "error",
                    "message": "生成的计划格式不正确"
                }
                
            # 添加额外的计划元数据
            plan["task"] = task
            plan["context"] = context
            
            return {
                "status": "success",
                "plan": plan
            }
            
        except Exception as e:
            logger.error(f"创建计划失败: {str(e)}")
            return {
                "status": "error",
                "message": f"创建计划时出错: {str(e)}"
            }
    
    async def evaluate_plan(self, plan: Dict[str, Any], task: str) -> Dict[str, Any]:
        """
        评估计划的质量和完整性
        
        参数:
            plan: 要评估的计划
            task: 原始任务描述
            
        返回:
            Dict[str, Any]: 评估结果
        """
        # 格式化计划步骤
        steps_text = "\n".join([
            f"步骤 {step['id']}: {step['name']} - {step['description']} "
            f"(依赖: {', '.join(step.get('dependencies', []))})"
            for step in plan.get("steps", [])
        ])
        
        # 构造评估提示
        prompt = self.plan_evaluation_template.format(
            plan_name=plan.get("plan_name", "未命名计划"),
            plan_description=plan.get("description", "无描述"),
            plan_steps=steps_text,
            task=task
        )
        
        try:
            # 调用LLM评估计划
            messages = [
                LLMMessage(role="system", content="你是一个专注于评估计划质量的分析师。你擅长识别计划中的优点和不足。"),
                LLMMessage(role="user", content=prompt)
            ]
            
            response = await self.llm_service.chat_completion(
                messages=messages,
                temperature=0.2
            )
            
            content = response.content
            
            # 提取JSON格式的评估
            evaluation = self._extract_json(content)
            
            if not evaluation:
                logger.warning("无法从LLM响应中提取有效的评估JSON")
                return {
                    "status": "error",
                    "message": "无法生成有效的评估"
                }
                
            # 确保评估包含必要的字段
            if "score" not in evaluation:
                evaluation["score"] = 5.0
            if "complete" not in evaluation:
                evaluation["complete"] = False
            if "should_replan" not in evaluation:
                evaluation["should_replan"] = evaluation["score"] < 7.0
                
            return {
                "status": "success",
                "evaluation": evaluation
            }
            
        except Exception as e:
            logger.error(f"评估计划失败: {str(e)}")
            return {
                "status": "error",
                "message": f"评估计划时出错: {str(e)}",
                "evaluation": {
                    "score": 0.0,
                    "complete": False,
                    "strengths": [],
                    "weaknesses": ["评估过程中出错"],
                    "should_replan": True
                }
            }
    
    async def execute_step(self, step: Dict[str, Any], plan: Dict[str, Any], context: Dict[str, Any] = None, completed_steps: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        执行计划中的单个步骤
        
        参数:
            step: 要执行的步骤
            plan: 完整计划
            context: 上下文信息
            completed_steps: 已完成的步骤
            
        返回:
            Dict[str, Any]: 执行结果
        """
        context = context or {}
        completed_steps = completed_steps or []
        
        # 计划摘要
        plan_summary = f"{plan.get('plan_name', '未命名计划')}: {plan.get('description', '无描述')}"
        
        # 格式化已完成步骤
        completed_steps_text = "\n".join([
            f"- {cs['name']}: {cs.get('result', '已完成')}" for cs in completed_steps
        ]) if completed_steps else "无"
        
        # 构造步骤执行提示
        prompt = self.step_execution_template.format(
            step_name=step.get("name", "未命名步骤"),
            step_description=step.get("description", "无描述"),
            expected_outcome=step.get("expected_outcome", "无预期结果"),
            plan_summary=plan_summary,
            completed_steps_count=len(completed_steps),
            total_steps_count=len(plan.get("steps", [])),
            completed_steps=completed_steps_text,
            context=self._format_context(context)
        )
        
        try:
            # 调用LLM执行步骤
            messages = [
                LLMMessage(role="system", content=f"你是{self.name}，一个执行计划步骤的智能体。你现在正在执行任务计划中的一个步骤。"),
                LLMMessage(role="user", content=prompt)
            ]
            
            response = await self.llm_service.chat_completion(
                messages=messages,
                temperature=0.5
            )
            
            content = response.content
            
            # 提取JSON格式的执行结果
            execution_result = self._extract_json(content)
            
            if not execution_result:
                logger.warning("无法从LLM响应中提取有效的执行结果JSON")
                # 尝试从文本中构造一个基本结果
                return {
                    "status": "partial",
                    "execution": {
                        "execution": "无法解析执行结果",
                        "result": content,
                        "success": False,
                        "issues": ["结果格式不正确"],
                        "next_actions": []
                    },
                    "raw_response": content
                }
            
            # 添加步骤信息到结果中
            execution_result["step_id"] = step.get("id")
            execution_result["step_name"] = step.get("name")
            
            return {
                "status": "success",
                "execution": execution_result
            }
            
        except Exception as e:
            logger.error(f"执行步骤失败: {str(e)}")
            return {
                "status": "error",
                "message": f"执行步骤时出错: {str(e)}",
                "execution": {
                    "step_id": step.get("id"),
                    "step_name": step.get("name"),
                    "execution": "执行过程出错",
                    "result": f"错误: {str(e)}",
                    "success": False,
                    "issues": [str(e)],
                    "next_actions": ["重试或跳过此步骤"]
                }
            }
    
    async def integrate_results(self, plan: Dict[str, Any], executions: List[Dict[str, Any]], task: str) -> Dict[str, Any]:
        """
        整合计划执行结果
        
        参数:
            plan: 原始计划
            executions: 所有步骤的执行结果
            task: 任务描述
            
        返回:
            Dict[str, Any]: 整合后的结果
        """
        # 格式化原始计划
        plan_steps = "\n".join([
            f"步骤 {step['id']}: {step['name']} - {step['description']}"
            for step in plan.get("steps", [])
        ])
        original_plan = f"计划名称: {plan.get('plan_name', '未命名计划')}\n" \
                       f"计划描述: {plan.get('description', '无描述')}\n" \
                       f"步骤:\n{plan_steps}"
        
        # 格式化执行摘要
        execution_entries = []
        for exe in executions:
            execution = exe.get("execution", {})
            step_id = execution.get("step_id", "未知")
            step_name = execution.get("step_name", "未知步骤")
            result = execution.get("result", "无结果")
            success = "成功" if execution.get("success", False) else "失败"
            issues = ", ".join(execution.get("issues", [])) or "无"
            
            execution_entries.append(f"步骤 {step_id} ({step_name}) - {success}\n结果: {result}\n问题: {issues}")
            
        execution_summary = "\n\n".join(execution_entries)
        
        # 构造整合结果提示
        prompt = self.results_integration_template.format(
            task=task,
            original_plan=original_plan,
            execution_summary=execution_summary
        )
        
        try:
            # 调用LLM整合结果
            messages = [
                LLMMessage(role="system", content=f"你是{self.name}，一个专注于整合和总结任务执行结果的智能体。"),
                LLMMessage(role="user", content=prompt)
            ]
            
            response = await self.llm_service.chat_completion(
                messages=messages,
                temperature=0.7
            )
            
            # 返回整合结果
            return {
                "status": "success",
                "summary": response.content,
                "plan": plan,
                "executions": executions
            }
            
        except Exception as e:
            logger.error(f"整合结果失败: {str(e)}")
            return {
                "status": "error",
                "message": f"整合结果时出错: {str(e)}",
                "plan": plan,
                "executions": executions
            }
    
    async def process_with_planning(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用规划模式处理输入
        
        参数:
            input_data: 输入数据，包含task和context
            
        返回:
            Dict[str, Any]: 处理结果
        """
        # 从输入数据中提取必要信息
        task = input_data.get("task", "")
        context = input_data.get("context", {})
        
        if not task:
            return {"status": "error", "message": "未提供有效的任务"}
        
        try:
            # 1. 创建计划
            planning_result = None
            plan = None
            
            # 尝试创建计划，最多尝试max_planning_attempts次
            for attempt in range(self.max_planning_attempts):
                planning_result = await self.create_plan(task, context)
                
                if planning_result.get("status") == "success":
                    plan = planning_result.get("plan")
                    
                    # 评估计划质量
                    evaluation_result = await self.evaluate_plan(plan, task)
                    
                    if evaluation_result.get("status") == "success":
                        evaluation = evaluation_result.get("evaluation", {})
                        
                        # 如果计划评分足够高且不需要重新规划，则接受此计划
                        if not evaluation.get("should_replan", False):
                            logger.info(f"计划被接受，评分: {evaluation.get('score')}")
                            break
                        else:
                            # 更新上下文，添加改进建议
                            context["plan_feedback"] = evaluation
                            logger.info(f"计划需要改进，尝试重新规划 (尝试 {attempt+1}/{self.max_planning_attempts})")
                    else:
                        logger.warning("计划评估失败")
                        # 继续使用当前计划
                        break
                else:
                    logger.error(f"创建计划失败: {planning_result.get('message')}")
                    return planning_result
            
            if not plan:
                return {"status": "error", "message": "无法创建有效的计划"}
                
            # 记录最终计划
            self.context.add_memory("final_plan", plan)
            
            # 2. 按照计划执行步骤
            all_steps = plan.get("steps", [])
            completed_steps = []
            execution_results = []
            
            # 按照依赖关系顺序执行步骤
            remaining_steps = all_steps.copy()
            step_counter = 0
            
            while remaining_steps and step_counter < self.max_execution_steps:
                # 找出当前可以执行的步骤（所有依赖都已完成）
                executable_steps = []
                
                for step in remaining_steps:
                    dependencies = step.get("dependencies", [])
                    all_dependencies_met = True
                    
                    for dep in dependencies:
                        dependency_completed = any(cs.get("id") == dep for cs in completed_steps)
                        if not dependency_completed:
                            all_dependencies_met = False
                            break
                    
                    if all_dependencies_met:
                        executable_steps.append(step)
                
                if not executable_steps:
                    # 没有可执行的步骤，可能存在循环依赖
                    logger.warning("没有可执行的步骤，可能存在循环依赖")
                    break
                
                # 选择第一个可执行的步骤
                current_step = executable_steps[0]
                
                # 执行步骤
                execution_result = await self.execute_step(
                    current_step, 
                    plan, 
                    context, 
                    completed_steps
                )
                
                # 记录执行结果
                execution_results.append(execution_result)
                
                if execution_result.get("status") in ["success", "partial"]:
                    execution = execution_result.get("execution", {})
                    
                    # 添加执行结果到已完成步骤
                    completed_step = {**current_step, "execution": execution}
                    completed_steps.append(completed_step)
                    
                    # 从剩余步骤中移除
                    remaining_steps.remove(current_step)
                else:
                    logger.warning(f"步骤执行失败: {execution_result.get('message')}")
                    # 尽管失败，仍记录此步骤为已完成以避免循环
                    completed_steps.append(current_step)
                    remaining_steps.remove(current_step)
                
                step_counter += 1
            
            # 记录执行结果
            self.context.add_memory("execution_results", execution_results)
            
            # 3. 整合结果
            integration_result = await self.integrate_results(plan, execution_results, task)
            
            # 返回最终结果
            return {
                "status": "success",
                "plan": plan,
                "executions": execution_results,
                "summary": integration_result.get("summary"),
                "completed_steps_count": len(completed_steps),
                "total_steps_count": len(all_steps)
            }
            
        except Exception as e:
            logger.error(f"规划过程出错: {str(e)}")
            return {
                "status": "error",
                "message": f"处理失败: {str(e)}"
            }
    
    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """
        从文本中提取JSON对象
        
        参数:
            text: 包含JSON的文本
            
        返回:
            Optional[Dict[str, Any]]: 提取的JSON对象，如果提取失败则返回None
        """
        try:
            # 尝试从整个文本解析JSON
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
            
            # 尝试从代码块中提取JSON
            import re
            json_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
            match = re.search(json_pattern, text)
            if match:
                json_str = match.group(1)
                return json.loads(json_str)
                
            return None
        except Exception:
            return None
    
    def _validate_plan(self, plan: Dict[str, Any]) -> bool:
        """
        验证计划格式是否正确
        
        参数:
            plan: 要验证的计划
            
        返回:
            bool: 验证是否通过
        """
        # 检查必要字段
        if not isinstance(plan, dict):
            return False
            
        if "plan_name" not in plan or "steps" not in plan:
            return False
            
        # 检查步骤格式
        steps = plan.get("steps", [])
        if not isinstance(steps, list) or not steps:
            return False
            
        # 检查每个步骤的格式
        for step in steps:
            if not isinstance(step, dict):
                return False
                
            if "id" not in step or "name" not in step or "description" not in step:
                return False
                
        return True
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """
        格式化上下文信息
        
        参数:
            context: 上下文信息
            
        返回:
            str: 格式化的上下文文本
        """
        if not context:
            return ""
            
        context_parts = []
        
        for key, value in context.items():
            if isinstance(value, dict):
                # 对于字典类型，使用JSON格式
                value_str = json.dumps(value, ensure_ascii=False, indent=2)
                context_parts.append(f"{key}:\n```json\n{value_str}\n```")
            elif isinstance(value, list):
                # 对于列表类型，如果是字典列表则使用JSON，否则使用列表格式
                if value and isinstance(value[0], dict):
                    value_str = json.dumps(value, ensure_ascii=False, indent=2)
                    context_parts.append(f"{key}:\n```json\n{value_str}\n```")
                else:
                    items = "\n".join([f"- {item}" for item in value])
                    context_parts.append(f"{key}:\n{items}")
            else:
                # 对于其他类型，直接使用字符串表示
                context_parts.append(f"{key}: {value}")
                
        return "\n\n".join(context_parts)


class PlanNode:
    """
    规划节点
    
    LangGraph工作流中用于规划的节点
    """
    
    def __init__(self, llm_service: LLMService):
        """
        初始化规划节点
        
        参数:
            llm_service: LLM服务实例
        """
        self.llm_service = llm_service
        
        self.planning_template = """
请为以下任务制定一个详细的执行计划：

任务：{task}

上下文：
{context}

请将任务分解为清晰、具体的步骤，并以JSON格式返回：
```json
{
  "plan_name": "计划名称",
  "steps": [
    {
      "id": "1",
      "name": "步骤名称",
      "description": "详细描述",
      "expected_outcome": "预期结果"
    },
    ...
  ]
}
```
"""
    
    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行规划过程
        
        参数:
            state: 工作流状态
            
        返回:
            Dict[str, Any]: 更新后的状态
        """
        # 从状态中提取必要信息
        task = state.get("task", "")
        context = state.get("context", {})
        
        if not task:
            # 如果没有任务，直接返回原始状态
            return state
            
        # 格式化上下文
        context_str = "\n".join([f"{k}: {v}" for k, v in context.items()]) if context else "无"
        
        # 构造规划提示
        prompt = self.planning_template.format(
            task=task,
            context=context_str
        )
        
        try:
            # 调用LLM创建计划
            messages = [
                LLMMessage(role="system", content="你是一个专注于任务规划的智能体。你的任务是将复杂任务分解为可执行的步骤。"),
                LLMMessage(role="user", content=prompt)
            ]
            
            response = await self.llm_service.chat_completion(
                messages=messages,
                temperature=0.3
            )
            
            content = response.content
            
            # 提取JSON格式的计划
            import re
            import json
            
            json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
            if json_match:
                try:
                    plan = json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    plan = {"plan_name": "解析失败", "steps": []}
            else:
                plan = {"plan_name": "无法提取计划", "steps": []}
                
            # 更新状态
            new_state = state.copy()
            new_state["plan"] = plan
            new_state["current_step_index"] = 0
            
            return new_state
            
        except Exception as e:
            logger.error(f"规划节点执行失败: {str(e)}")
            
            # 更新状态，添加错误信息
            new_state = state.copy()
            new_state["error"] = f"规划失败: {str(e)}"
            
            return new_state


class ExecutionNode:
    """
    执行节点
    
    LangGraph工作流中用于执行计划步骤的节点
    """
    
    def __init__(self, llm_service: LLMService):
        """
        初始化执行节点
        
        参数:
            llm_service: LLM服务实例
        """
        self.llm_service = llm_service
        
        self.execution_template = """
你正在执行一个任务计划中的步骤：

当前步骤：{step_name}
步骤描述：{step_description}
预期结果：{expected_outcome}

任务：{task}

请执行这个步骤，并以JSON格式返回结果：
```json
{
  "result": "执行结果",
  "success": true/false,
  "observations": ["执行过程中的观察"]
}
```
"""
    
    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行计划步骤
        
        参数:
            state: 工作流状态
            
        返回:
            Dict[str, Any]: 更新后的状态
        """
        # 从状态中提取必要信息
        plan = state.get("plan", {})
        current_step_index = state.get("current_step_index", 0)
        task = state.get("task", "")
        
        # 检查是否有计划和步骤
        steps = plan.get("steps", [])
        if not steps or current_step_index >= len(steps):
            # 如果没有更多步骤，直接返回
            new_state = state.copy()
            new_state["plan_completed"] = True
            return new_state
            
        # 获取当前步骤
        current_step = steps[current_step_index]
        
        # 构造执行提示
        prompt = self.execution_template.format(
            step_name=current_step.get("name", "未命名步骤"),
            step_description=current_step.get("description", "无描述"),
            expected_outcome=current_step.get("expected_outcome", "无预期结果"),
            task=task
        )
        
        try:
            # 调用LLM执行步骤
            messages = [
                LLMMessage(role="system", content="你是一个专注于执行任务的智能体。你需要执行给定的计划步骤。"),
                LLMMessage(role="user", content=prompt)
            ]
            
            response = await self.llm_service.chat_completion(
                messages=messages,
                temperature=0.5
            )
            
            content = response.content
            
            # 提取JSON格式的执行结果
            import re
            import json
            
            json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
            if json_match:
                try:
                    execution = json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    execution = {
                        "result": "解析执行结果失败",
                        "success": False,
                        "observations": ["JSON解析错误"]
                    }
            else:
                # 如果没有找到JSON，使用整个响应作为结果
                execution = {
                    "result": content,
                    "success": True,
                    "observations": ["无结构化结果"]
                }
                
            # 更新状态
            new_state = state.copy()
            
            # 如果这是第一个执行结果，创建执行历史列表
            if "executions" not in new_state:
                new_state["executions"] = []
                
            # 添加执行结果到历史
            new_state["executions"].append({
                "step_index": current_step_index,
                "step": current_step,
                "execution": execution
            })
            
            # 更新到下一个步骤
            new_state["current_step_index"] = current_step_index + 1
            
            # 检查是否完成所有步骤
            if new_state["current_step_index"] >= len(steps):
                new_state["plan_completed"] = True
                
            return new_state
            
        except Exception as e:
            logger.error(f"执行节点失败: {str(e)}")
            
            # 更新状态，添加错误信息
            new_state = state.copy()
            
            # 如果这是第一个执行结果，创建执行历史列表
            if "executions" not in new_state:
                new_state["executions"] = []
                
            # 添加失败的执行结果
            new_state["executions"].append({
                "step_index": current_step_index,
                "step": current_step,
                "execution": {
                    "result": f"执行出错: {str(e)}",
                    "success": False,
                    "observations": [f"错误: {str(e)}"]
                }
            })
            
            # 移动到下一个步骤
            new_state["current_step_index"] = current_step_index + 1
            
            return new_state
