"""
协调智能体实现模块

负责任务分解、规划和分配的核心协调智能体
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from app.agents.base_agent import BaseAgent
from app.agents.communication.command import CommandFactory, EnhancedCommand
from app.models.domain.llm_types import LLMMessage
from app.services.interfaces.llm_service import LLMService

logger = logging.getLogger(__name__)


class CoordinatorAgent(BaseAgent):
    """
    协调智能体类
    
    作为整个智能体系统的核心协调者，负责任务解析、分解、分配和监控
    """
    
    def __init__(
        self,
        id: str,
        name: str,
        llm_service: LLMService,
        team_members: Dict[str, str],
        config: Dict[str, Any] = None
    ):
        """
        初始化协调智能体
        
        参数:
            id: 智能体唯一标识符
            name: 智能体名称
            llm_service: LLM服务实例
            team_members: 团队成员映射（ID到角色描述）
            config: 智能体配置信息
        """
        super().__init__(id, name, "coordinator", llm_service, config)
        
        # 协调者特有属性
        self.supervisor_prompt_template = self.config.get("supervisor_prompt_template", (
            "你是一个创作团队的协调者，负责管理和分配任务。"
            "你的团队由以下成员组成:\n{team_member_descriptions}\n\n"
            "你需要将主任务分解成适合各团队成员的子任务，并确保整体任务的完成。"
            "每个子任务应明确分配给最合适的团队成员。"
        ))
        
        self.team_members = team_members
        self.planning_strategy = self.config.get("planning_strategy", "hierarchical")
        self.escalation_policy = self.config.get("escalation_policy", {
            "retry_limit": 3,
            "escalation_threshold": 0.8
        })
        self.task_history: Dict[str, List[Dict[str, Any]]] = {}
        
        # 创建任务路由器
        self.task_router = TaskRouter(
            routing_rules=self.config.get("routing_rules", {}),
            agent_capabilities=self.config.get("agent_capabilities", {}),
            llm_service=llm_service
        )
        
        # 执行中的任务状态
        self._active_tasks: Dict[str, Dict[str, Any]] = {}
        self._task_locks: Dict[str, asyncio.Lock] = {}
        
        logger.info(f"协调智能体初始化完成: {id} ({name})")
    
    async def decompose_task(self, task: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        将主任务分解为子任务
        
        参数:
            task: 主任务详情
        
        返回:
            List[Dict[str, Any]]: 子任务列表
        """
        task_id = task.get("id", "unknown")
        logger.info(f"协调智能体正在分解任务: {task_id}")
        
        # 构建团队成员描述
        team_member_descriptions = "\n".join([
            f"- {member_id}: {description}" for member_id, description in self.team_members.items()
        ])
        
        # 准备提示
        prompt = self.supervisor_prompt_template.format(
            team_member_descriptions=team_member_descriptions
        )
        
        # 准备消息
        messages: List[LLMMessage] = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": (
                f"请将以下任务分解成适合团队成员的子任务:\n\n"
                f"任务标题: {task.get('title', '未命名任务')}\n"
                f"任务描述: {task.get('description', '无描述')}\n\n"
                f"根据任务性质和团队成员专长，将任务分解为适当数量的子任务。"
                f"请以JSON格式返回子任务列表，每个子任务包含id、title、description、assigned_to字段。"
            )}
        ]
        
        # 调用LLM服务
        try:
            response = await self.llm_service.chat_completion(
                messages=messages,
                temperature=0.2,
                functions=[{
                    "name": "provide_subtasks",
                    "description": "提供任务分解结果",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "subtasks": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "string"},
                                        "title": {"type": "string"},
                                        "description": {"type": "string"},
                                        "assigned_to": {"type": "string"},
                                        "dependencies": {
                                            "type": "array",
                                            "items": {"type": "string"}
                                        }
                                    },
                                    "required": ["id", "title", "description", "assigned_to"]
                                }
                            },
                            "reasoning": {"type": "string"}
                        },
                        "required": ["subtasks", "reasoning"]
                    }
                }]
            )
            
            # 解析结果
            result = response.function_call
            if result and result.get("arguments"):
                subtasks = result["arguments"].get("subtasks", [])
                
                # 记录任务分解历史
                self.task_history[task_id] = subtasks
                
                logger.info(f"任务 {task_id} 已分解为 {len(subtasks)} 个子任务")
                return subtasks
            else:
                logger.warning(f"任务分解失败，未返回有效结果: {response.content}")
                return []
                
        except Exception as e:
            logger.error(f"任务分解过程中出错: {str(e)}")
            return []
    
    async def assign_tasks(self, subtasks: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        将子任务分配给合适的团队成员
        
        参数:
            subtasks: 子任务列表
            
        返回:
            Dict[str, List[Dict[str, Any]]]: 按智能体ID分组的任务分配
        """
        task_assignment: Dict[str, List[Dict[str, Any]]] = {}
        
        for subtask in subtasks:
            agent_id = subtask.get("assigned_to")
            
            # 验证分配的智能体ID
            if agent_id not in self.team_members:
                # 使用路由器寻找合适的智能体
                agent_id = self.task_router.route_task(subtask)
                subtask["assigned_to"] = agent_id
            
            # 初始化任务列表（如果不存在）
            if agent_id not in task_assignment:
                task_assignment[agent_id] = []
            
            # 添加任务到分配中
            task_assignment[agent_id].append(subtask)
        
        logger.info(f"任务分配完成，共分配给 {len(task_assignment)} 个智能体")
        return task_assignment
    
    async def generate_execution_plan(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成任务执行计划
        
        参数:
            task: 主任务详情
            
        返回:
            Dict[str, Any]: 执行计划
        """
        # 首先分解任务
        subtasks = await self.decompose_task(task)
        
        # 分配任务
        assignments = await self.assign_tasks(subtasks)
        
        # 构建依赖图
        dependency_graph = self._build_dependency_graph(subtasks)
        
        # 构建执行计划
        execution_plan = {
            "task_id": task.get("id", "unknown"),
            "subtasks": subtasks,
            "assignments": assignments,
            "dependencies": dependency_graph,
            "execution_order": self._generate_execution_order(subtasks, dependency_graph),
            "status": "planned"
        }
        
        logger.info(f"已为任务 {task.get('id', 'unknown')} 生成执行计划")
        return execution_plan
    
    async def monitor_progress(self, task_id: str) -> Dict[str, Any]:
        """
        监控任务进度
        
        参数:
            task_id: 任务ID
            
        返回:
            Dict[str, Any]: 任务进度状态
        """
        if task_id not in self._active_tasks:
            return {"status": "unknown", "message": f"任务 {task_id} 不存在或未启动"}
        
        task_data = self._active_tasks[task_id]
        completed_subtasks = [
            subtask for subtask in task_data.get("subtasks", [])
            if subtask.get("status") == "completed"
        ]
        
        total_subtasks = len(task_data.get("subtasks", []))
        completed_count = len(completed_subtasks)
        
        progress = {
            "task_id": task_id,
            "total_subtasks": total_subtasks,
            "completed_subtasks": completed_count,
            "progress_percentage": (completed_count / total_subtasks * 100) if total_subtasks > 0 else 0,
            "status": task_data.get("status", "unknown"),
            "subtask_statuses": {
                subtask.get("id"): {
                    "status": subtask.get("status", "pending"),
                    "assigned_to": subtask.get("assigned_to"),
                    "last_update": subtask.get("last_update")
                }
                for subtask in task_data.get("subtasks", [])
            }
        }
        
        logger.info(f"任务 {task_id} 进度: {progress['progress_percentage']:.1f}% ({completed_count}/{total_subtasks})")
        return progress
    
    async def handle_exception(self, task_id: str, agent_id: str, error: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理任务执行异常
        
        参数:
            task_id: 任务ID
            agent_id: 报告异常的智能体ID
            error: 错误详情
            
        返回:
            Dict[str, Any]: 处理结果
        """
        if task_id not in self._active_tasks:
            return {"status": "error", "message": f"任务 {task_id} 不存在或未启动"}
        
        logger.warning(f"智能体 {agent_id} 报告任务 {task_id} 执行异常: {error.get('message', 'Unknown error')}")
        
        # 获取任务数据
        task_data = self._active_tasks[task_id]
        
        # 查找相关子任务
        subtask = next(
            (s for s in task_data.get("subtasks", []) 
             if s.get("assigned_to") == agent_id and s.get("status") != "completed"),
            None
        )
        
        if not subtask:
            return {"status": "error", "message": f"找不到智能体 {agent_id} 正在执行的子任务"}
        
        subtask_id = subtask.get("id")
        retry_count = subtask.get("retry_count", 0)
        
        # 检查是否超过重试限制
        if retry_count >= self.escalation_policy.get("retry_limit", 3):
            # 记录失败状态
            subtask["status"] = "failed"
            subtask["error"] = error
            
            # 检查是否需要上报
            severity = error.get("severity", 0.5)
            if severity >= self.escalation_policy.get("escalation_threshold", 0.8):
                # 发送上报通知（这里可以集成通知系统）
                await self._notify_escalation(task_id, subtask_id, agent_id, error)
                
                return {
                    "status": "escalated",
                    "message": f"子任务 {subtask_id} 执行失败并已上报",
                    "subtask_id": subtask_id
                }
            else:
                return {
                    "status": "failed",
                    "message": f"子任务 {subtask_id} 执行失败，超过重试次数限制",
                    "subtask_id": subtask_id
                }
        else:
            # 更新重试计数
            subtask["retry_count"] = retry_count + 1
            subtask["status"] = "retrying"
            subtask["last_error"] = error
            
            # 重新分配任务？
            reassign = error.get("recommend_reassign", False)
            if reassign:
                # 尝试重新分配给其他智能体
                new_agent_id = self.task_router.route_task(subtask, exclude_agents=[agent_id])
                if new_agent_id and new_agent_id != agent_id:
                    old_agent_id = subtask["assigned_to"]
                    subtask["assigned_to"] = new_agent_id
                    subtask["reassigned_from"] = old_agent_id
                    
                    logger.info(f"子任务 {subtask_id} 已从 {old_agent_id} 重新分配给 {new_agent_id}")
                    
                    # 从旧智能体的分配中移除
                    if old_agent_id in task_data["assignments"]:
                        task_data["assignments"][old_agent_id] = [
                            s for s in task_data["assignments"][old_agent_id] 
                            if s.get("id") != subtask_id
                        ]
                    
                    # 添加到新智能体的分配中
                    if new_agent_id not in task_data["assignments"]:
                        task_data["assignments"][new_agent_id] = []
                    task_data["assignments"][new_agent_id].append(subtask)
                    
                    return {
                        "status": "reassigned",
                        "message": f"子任务 {subtask_id} 已重新分配给 {new_agent_id}",
                        "subtask_id": subtask_id,
                        "new_agent_id": new_agent_id
                    }
            
            # 准备重试
            return {
                "status": "retry",
                "message": f"子任务 {subtask_id} 将进行第 {subtask['retry_count']} 次重试",
                "subtask_id": subtask_id
            }
    
    async def evaluate_results(self, task_id: str, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        评估任务执行结果
        
        参数:
            task_id: 任务ID
            results: 结果列表
            
        返回:
            Dict[str, Any]: 评估结果
        """
        if task_id not in self._active_tasks:
            return {"status": "error", "message": f"任务 {task_id} 不存在或未启动"}
        
        logger.info(f"评估任务 {task_id} 的结果")
        
        # 获取任务数据
        task_data = self._active_tasks[task_id]
        
        # 准备评估提示
        messages: List[LLMMessage] = [
            {"role": "system", "content": (
                "你是一个专业的创作评估者，负责评估智能体团队生成的内容质量。"
                "请基于一致性、完整性、创造性和内容质量等维度进行全面评估。"
            )},
            {"role": "user", "content": (
                f"请评估以下创作任务的结果:\n\n"
                f"任务标题: {task_data.get('title', '未命名任务')}\n"
                f"任务描述: {task_data.get('description', '无描述')}\n\n"
                f"结果内容:\n{self._format_results_for_evaluation(results)}\n\n"
                f"请提供详细评估并以JSON格式返回评分（1-10分）和具体反馈。"
            )}
        ]
        
        # 调用LLM服务
        try:
            response = await self.llm_service.chat_completion(
                messages=messages,
                temperature=0.3,
                functions=[{
                    "name": "provide_evaluation",
                    "description": "提供任务结果评估",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "overall_score": {"type": "number", "minimum": 1, "maximum": 10},
                            "consistency_score": {"type": "number", "minimum": 1, "maximum": 10},
                            "completeness_score": {"type": "number", "minimum": 1, "maximum": 10},
                            "creativity_score": {"type": "number", "minimum": 1, "maximum": 10},
                            "quality_score": {"type": "number", "minimum": 1, "maximum": 10},
                            "strengths": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "weaknesses": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "improvement_suggestions": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "detailed_feedback": {"type": "string"}
                        },
                        "required": ["overall_score", "consistency_score", "completeness_score", 
                                    "creativity_score", "quality_score", "strengths", 
                                    "weaknesses", "improvement_suggestions", "detailed_feedback"]
                    }
                }]
            )
            
            # 解析结果
            result = response.function_call
            if result and result.get("arguments"):
                evaluation = result["arguments"]
                
                # 更新任务状态
                task_data["evaluation"] = evaluation
                task_data["status"] = "evaluated"
                
                logger.info(f"任务 {task_id} 评估完成，总分: {evaluation.get('overall_score', 'N/A')}")
                return evaluation
            else:
                logger.warning(f"任务评估失败，未返回有效结果: {response.content}")
                return {"status": "error", "message": "评估失败，未能获取有效结果"}
                
        except Exception as e:
            logger.error(f"任务评估过程中出错: {str(e)}")
            return {"status": "error", "message": f"评估过程出错: {str(e)}"}
    
    async def synthesize_final_response(self, task_id: str, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        合成最终响应
        
        参数:
            task_id: 任务ID
            results: 结果列表
            
        返回:
            Dict[str, Any]: 合成的最终响应
        """
        if task_id not in self._active_tasks:
            return {"status": "error", "message": f"任务 {task_id} 不存在或未启动"}
        
        logger.info(f"合成任务 {task_id} 的最终响应")
        
        # 获取任务数据
        task_data = self._active_tasks[task_id]
        
        # 准备合成提示
        messages: List[LLMMessage] = [
            {"role": "system", "content": (
                "你是一个高级内容整合专家，负责将多个智能体的工作成果整合为连贯一致的最终作品。"
                "请确保最终内容连贯、统一且完整。"
            )},
            {"role": "user", "content": (
                f"请将以下创作任务的多个结果整合为最终成果:\n\n"
                f"任务标题: {task_data.get('title', '未命名任务')}\n"
                f"任务描述: {task_data.get('description', '无描述')}\n\n"
                f"各部分内容:\n{self._format_results_for_synthesis(results)}\n\n"
                f"请整合所有内容，确保最终作品的一致性、完整性和质量。"
            )}
        ]
        
        # 调用LLM服务
        try:
            response = await self.llm_service.chat_completion(
                messages=messages,
                temperature=0.2,
                max_tokens=4000
            )
            
            # 更新任务状态
            synthesis = {
                "content": response.content,
                "timestamp": response.created_at,
                "task_id": task_id
            }
            
            task_data["synthesis"] = synthesis
            task_data["status"] = "completed"
            
            logger.info(f"任务 {task_id} 最终内容合成完成")
            return synthesis
                
        except Exception as e:
            logger.error(f"内容合成过程中出错: {str(e)}")
            return {"status": "error", "message": f"合成过程出错: {str(e)}"}
    
    # 内部辅助方法
    def _build_dependency_graph(self, subtasks: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """构建子任务依赖图"""
        dependency_graph: Dict[str, List[str]] = {}
        
        for subtask in subtasks:
            subtask_id = subtask.get("id")
            dependencies = subtask.get("dependencies", [])
            dependency_graph[subtask_id] = dependencies
            
        return dependency_graph
    
    def _generate_execution_order(
        self, 
        subtasks: List[Dict[str, Any]], 
        dependency_graph: Dict[str, List[str]]
    ) -> List[str]:
        """生成考虑依赖关系的执行顺序"""
        # 拓扑排序实现
        result: List[str] = []
        visited: Set[str] = set()
        temp_visited: Set[str] = set()
        
        def visit(node: str) -> None:
            if node in temp_visited:
                # 检测到循环依赖
                logger.warning(f"检测到循环依赖，涉及节点: {node}")
                return
            
            if node not in visited:
                temp_visited.add(node)
                
                # 处理当前节点的所有依赖
                for dep in dependency_graph.get(node, []):
                    visit(dep)
                
                temp_visited.remove(node)
                visited.add(node)
                result.append(node)
        
        # 遍历所有子任务
        for subtask in subtasks:
            subtask_id = subtask.get("id")
            if subtask_id not in visited:
                visit(subtask_id)
        
        # 反转结果以获得正确的执行顺序（从无依赖到有依赖）
        return list(reversed(result))
    
    def _format_results_for_evaluation(self, results: List[Dict[str, Any]]) -> str:
        """格式化结果用于评估"""
        formatted = []
        for i, result in enumerate(results, 1):
            formatted.append(f"结果 {i}:")
            formatted.append(f"标题: {result.get('title', '无标题')}")
            formatted.append(f"内容: {result.get('content', '无内容')}")
            formatted.append(f"生成者: {result.get('agent_id', '未知智能体')}")
            formatted.append("")
        
        return "\n".join(formatted)
    
    def _format_results_for_synthesis(self, results: List[Dict[str, Any]]) -> str:
        """格式化结果用于合成"""
        formatted = []
        
        # 按任务顺序排序结果
        sorted_results = sorted(
            results, 
            key=lambda r: r.get("subtask_index", 999)
        )
        
        for result in sorted_results:
            formatted.append(f"# {result.get('title', '无标题')}")
            formatted.append(f"{result.get('content', '无内容')}")
            formatted.append("")
        
        return "\n".join(formatted)
    
    async def _notify_escalation(self, task_id: str, subtask_id: str, agent_id: str, error: Dict[str, Any]) -> None:
        """发送任务异常上报通知"""
        # 这里可以集成通知系统，如发送邮件、短信或调用其他API
        logger.warning(f"任务异常上报: 任务 {task_id}, 子任务 {subtask_id}, 智能体 {agent_id}")
        logger.warning(f"错误详情: {error.get('message', 'Unknown error')}")
        
        # 简单地记录到协调者的上下文中
        self.context.add_memory(
            f"escalation_{task_id}_{subtask_id}",
            {
                "timestamp": error.get("timestamp"),
                "task_id": task_id,
                "subtask_id": subtask_id,
                "agent_id": agent_id,
                "error": error
            }
        )


class TaskRouter:
    """
    任务路由器类
    
    根据任务类型和内容决定适当的处理智能体
    """
    
    def __init__(
        self,
        routing_rules: Dict[str, List[str]],
        agent_capabilities: Dict[str, List[str]],
        llm_service: LLMService
    ):
        """
        初始化路由器
        
        参数:
            routing_rules: 路由规则配置
            agent_capabilities: 智能体能力映射
            llm_service: LLM服务实例
        """
        self.routing_rules = routing_rules
        self.agent_capabilities = agent_capabilities
        self.llm_service = llm_service
        
        # 缓存已评分的任务
        self._task_scores_cache: Dict[str, Dict[str, float]] = {}
    
    def route_task(self, task: Dict[str, Any], exclude_agents: List[str] = None) -> str:
        """
        路由任务到最合适的智能体
        
        参数:
            task: 任务详情
            exclude_agents: 要排除的智能体ID列表
            
        返回:
            str: 选中的智能体ID
        """
        exclude_agents = exclude_agents or []
        task_id = task.get("id", "unknown")
        task_type = task.get("type", "general")
        
        # 1. 检查显式规则
        if task_type in self.routing_rules:
            candidates = self.routing_rules[task_type]
            # 过滤掉排除的智能体
            valid_candidates = [a for a in candidates if a not in exclude_agents]
            if valid_candidates:
                # 简单策略: 返回第一个有效候选
                return valid_candidates[0]
        
        # 2. 使用能力匹配
        agent_scores = self._score_agents_for_task(task, exclude_agents)
        
        if agent_scores:
            # 返回得分最高的智能体
            return max(agent_scores.items(), key=lambda x: x[1])[0]
        
        # 3. 如果没有找到合适的智能体，返回"fallback_agent"
        logger.warning(f"找不到任务 {task_id} 的合适智能体，使用默认智能体")
        return "fallback_agent"
    
    def update_routing_rules(self, new_rules: Dict[str, List[str]]) -> None:
        """
        更新路由规则
        
        参数:
            new_rules: 新的路由规则
        """
        self.routing_rules.update(new_rules)
    
    def _score_agents_for_task(self, task: Dict[str, Any], exclude_agents: List[str] = None) -> Dict[str, float]:
        """
        为任务评分各智能体的适合度
        
        参数:
            task: 任务详情
            exclude_agents: 要排除的智能体ID列表
            
        返回:
            Dict[str, float]: 智能体ID到得分的映射
        """
        exclude_agents = exclude_agents or []
        task_id = task.get("id", "unknown")
        
        # 检查缓存
        if task_id in self._task_scores_cache:
            scores = self._task_scores_cache[task_id]
            # 过滤掉排除的智能体
            return {a: s for a, s in scores.items() if a not in exclude_agents}
        
        # 基于能力匹配的简单评分
        scores: Dict[str, float] = {}
        task_keywords = self._extract_keywords(task)
        
        for agent_id, capabilities in self.agent_capabilities.items():
            if agent_id in exclude_agents:
                continue
                
            # 计算能力匹配分数
            match_score = self._calculate_match_score(task_keywords, capabilities)
            scores[agent_id] = match_score
        
        # 缓存结果
        self._task_scores_cache[task_id] = scores.copy()
        
        return scores
    
    def _extract_keywords(self, task: Dict[str, Any]) -> List[str]:
        """从任务中提取关键词"""
        keywords = []
        
        # 从任务类型中提取
        if "type" in task:
            keywords.append(task["type"])
        
        # 从任务标题中提取
        if "title" in task:
            title_words = task["title"].lower().split()
            keywords.extend([w for w in title_words if len(w) > 3])
        
        # 从任务标签中提取
        if "tags" in task and isinstance(task["tags"], list):
            keywords.extend(task["tags"])
        
        return list(set(keywords))  # 去重
    
    def _calculate_match_score(self, task_keywords: List[str], agent_capabilities: List[str]) -> float:
        """计算任务关键词与智能体能力的匹配分数"""
        if not task_keywords or not agent_capabilities:
            return 0.0
        
        matches = 0
        for keyword in task_keywords:
            for capability in agent_capabilities:
                if keyword.lower() in capability.lower():
                    matches += 1
                    break
        
        return matches / len(task_keywords) if task_keywords else 0.0
