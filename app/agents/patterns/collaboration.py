"""
协作模式智能体

实现多智能体协作系统，支持层次化和点对点协作
"""

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from app.agents.base_agent import BaseAgent
from app.agents.communication.command import EnhancedCommand, CommandFactory
from app.agents.communication.message_bus import MessageBus
from app.services.interfaces.llm_service import LLMService
from app.models.domain.llm_types import LLMMessage

logger = logging.getLogger(__name__)


class CollaborationAgent(BaseAgent):
    """
    协作智能体
    
    能够与其他智能体协作完成任务的智能体
    """
    
    def __init__(
        self,
        id: str,
        name: str,
        agent_type: str,
        llm_service: LLMService,
        message_bus: MessageBus,
        team_members: Dict[str, str] = None,  # id -> name
        max_collaboration_rounds: int = 10,
        config: Dict[str, Any] = None
    ):
        """
        初始化协作智能体
        
        参数:
            id: 智能体唯一标识符
            name: 智能体名称
            agent_type: 智能体类型
            llm_service: LLM服务实例
            message_bus: 消息总线实例
            team_members: 团队成员映射表，id -> name
            max_collaboration_rounds: 最大协作轮次
            config: 智能体配置信息
        """
        super().__init__(id, name, agent_type, llm_service, config)
        self.message_bus = message_bus
        self.team_members = team_members or {}
        self.max_collaboration_rounds = max_collaboration_rounds
        
        # 任务会话
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        # 等待响应的Future
        self.waiting_responses: Dict[str, asyncio.Future] = {}
        
        # 设置消息处理器
        self._setup_message_handlers()


class MultiAgentCollaborationSystem:
    """
    多智能体协作系统
    
    管理多个智能体之间的协作，包括任务分配、结果聚合等
    """
    
    def __init__(
        self, 
        message_bus: MessageBus,
        collaboration_strategy: str = "hierarchical"
    ):
        """
        初始化协作系统
        
        参数:
            message_bus: 消息总线实例
            collaboration_strategy: 协作策略，如"hierarchical", "peer_to_peer"等
        """
        self.agents: Dict[str, BaseAgent] = {}
        self.collaboration_strategy = collaboration_strategy
        self.message_bus = message_bus
        self.coordinator_agent_id: Optional[str] = None
        
        # 任务跟踪
        self.tasks: Dict[str, Dict[str, Any]] = {}
        
        # 订阅ID
        self.subscription_id: Optional[str] = None
    
    async def initialize(self) -> None:
        """初始化协作系统，设置消息订阅"""
        # 订阅系统消息
        self.subscription_id = await self.message_bus.subscribe(
            topics=["agent_messages", "agent_broadcasts"],
            handler=self._handle_message,
            group_name="collaboration_system",
            consumer_name=f"collab_system_{uuid.uuid4().hex[:8]}"
        )
        
        # 启动消费
        await self.message_bus.start_consuming(self.subscription_id)
        logger.info(f"多智能体协作系统初始化完成，订阅ID: {self.subscription_id}")
    
    async def shutdown(self) -> None:
        """关闭协作系统，取消订阅"""
        if self.subscription_id:
            await self.message_bus.unsubscribe(self.subscription_id)
            logger.info("多智能体协作系统已关闭")
    
    async def _handle_message(self, topic: str, command: EnhancedCommand) -> None:
        """处理智能体消息"""
        # 如果是任务相关消息，更新任务状态
        if command.command_type == "response" and "task_id" in command.metadata:
            task_id = command.metadata["task_id"]
            if task_id in self.tasks:
                source_id = command.source_id
                self.tasks[task_id]["agent_responses"][source_id] = command
                
                # 检查任务是否完成
                if self._check_task_completion(task_id):
                    await self._finalize_task(task_id)
    
    def _check_task_completion(self, task_id: str) -> bool:
        """检查任务是否完成"""
        if task_id not in self.tasks:
            return False
            
        task = self.tasks[task_id]
        assigned_agents = set(task["assigned_agents"])
        responded_agents = set(task["agent_responses"].keys())
        
        # 所有分配的智能体都已响应
        return assigned_agents.issubset(responded_agents)
    
    async def _finalize_task(self, task_id: str) -> None:
        """完成任务，聚合结果"""
        if task_id not in self.tasks:
            return
            
        task = self.tasks[task_id]
        
        # 聚合结果
        results = {}
        for agent_id, response in task["agent_responses"].items():
            results[agent_id] = response.content
            
        # 更新任务状态
        task["status"] = "completed"
        task["results"] = results
        
        # 通知请求者
        if task["requester_id"]:
            response_command = CommandFactory.create_response_command(
                source_id="collaboration_system",
                response_to=task["request_id"],
                content={
                    "status": "success",
                    "task_id": task_id,
                    "results": results
                },
                target_ids=[task["requester_id"]]
            )
            
            # 添加任务ID到元数据
            response_command.metadata["task_id"] = task_id
            
            await self.message_bus.publish_message("agent_messages", response_command)
    
    def add_agent(self, agent: BaseAgent) -> None:
        """
        添加智能体到系统
        
        参数:
            agent: 智能体实例
        """
        self.agents[agent.id] = agent
        # 设置消息总线
        agent.set_message_bus(self.message_bus)
        logger.info(f"添加智能体到协作系统: {agent.id} ({agent.name})")
    
    def remove_agent(self, agent_id: str) -> None:
        """
        从系统移除智能体
        
        参数:
            agent_id: 智能体ID
        """
        if agent_id in self.agents:
            del self.agents[agent_id]
            logger.info(f"从协作系统移除智能体: {agent_id}")
    
    def set_coordinator(self, agent_id: str) -> None:
        """
        设置协调者智能体
        
        参数:
            agent_id: 协调者智能体ID
        """
        if agent_id not in self.agents:
            raise ValueError(f"智能体 {agent_id} 不存在")
            
        self.coordinator_agent_id = agent_id
        logger.info(f"设置协调者智能体: {agent_id}")
    
    async def assign_task(self, task: Dict[str, Any], target_agent_ids: List[str] = None) -> str:
        """
        分配任务
        
        参数:
            task: 任务内容
            target_agent_ids: 目标智能体ID列表，为None则根据策略选择
            
        返回:
            str: 任务ID
        """
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 如果没有指定目标智能体，根据策略选择
        if not target_agent_ids:
            if self.collaboration_strategy == "hierarchical" and self.coordinator_agent_id:
                # 层次协作，分配给协调者
                target_agent_ids = [self.coordinator_agent_id]
            else:
                # 点对点协作，分配给所有智能体
                target_agent_ids = list(self.agents.keys())
        
        # 创建任务命令
        command = CommandFactory.create_action_command(
            source_id="collaboration_system",
            action="process_task",
            parameters=task,
            target_ids=target_agent_ids
        )
        
        # 添加任务ID到元数据
        command.metadata["task_id"] = task_id
        
        # 记录任务信息
        self.tasks[task_id] = {
            "id": task_id,
            "task": task,
            "assigned_agents": target_agent_ids,
            "agent_responses": {},
            "status": "assigned",
            "request_id": command.id,
            "requester_id": task.get("requester_id")
        }
        
        # 发布任务命令
        for agent_id in target_agent_ids:
            if agent_id in self.agents:
                await self.message_bus.publish_message("agent_messages", command)
                logger.info(f"分配任务 {task_id} 给智能体 {agent_id}")
            else:
                logger.warning(f"智能体 {agent_id} 不存在，无法分配任务")
        
        return task_id
    
    async def collect_results(self, task_id: str, timeout: float = 30.0) -> Dict[str, Any]:
        """
        收集任务结果
        
        参数:
            task_id: 任务ID
            timeout: 超时时间（秒）
            
        返回:
            Dict[str, Any]: 任务结果
        """
        if task_id not in self.tasks:
            return {"status": "error", "message": f"任务 {task_id} 不存在"}
            
        task = self.tasks[task_id]
        
        # 如果任务已完成，直接返回结果
        if task["status"] == "completed":
            return {
                "status": "success",
                "task_id": task_id,
                "results": task["results"]
            }
            
        # 等待任务完成
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < timeout:
            # 检查任务是否完成
            if self._check_task_completion(task_id):
                await self._finalize_task(task_id)
                return {
                    "status": "success",
                    "task_id": task_id,
                    "results": task["results"]
                }
                
            # 等待一小段时间
            await asyncio.sleep(0.1)
            
        # 超时
        partial_results = {}
        for agent_id, response in task["agent_responses"].items():
            partial_results[agent_id] = response.content
            
        return {
            "status": "timeout",
            "task_id": task_id,
            "partial_results": partial_results,
            "missing_agents": list(set(task["assigned_agents"]) - set(task["agent_responses"].keys()))
        }
    
    async def create_collaboration_graph(self, agents: List[str] = None) -> Dict[str, Any]:
        """
        创建协作工作流图
        
        参数:
            agents: 参与协作的智能体ID列表，为None则使用所有智能体
            
        返回:
            Dict[str, Any]: 协作图结构
        """
        if not agents:
            agents = list(self.agents.keys())
            
        # 根据协作策略创建不同的图结构
        if self.collaboration_strategy == "hierarchical":
            return self._create_hierarchical_graph(agents)
        elif self.collaboration_strategy == "peer_to_peer":
            return self._create_peer_graph(agents)
        else:
            return self._create_default_graph(agents)
    
    def _create_hierarchical_graph(self, agent_ids: List[str]) -> Dict[str, Any]:
        """创建层次协作图"""
        # 确保有协调者
        if not self.coordinator_agent_id or self.coordinator_agent_id not in agent_ids:
            # 选择第一个智能体作为协调者
            if agent_ids:
                self.coordinator_agent_id = agent_ids[0]
            else:
                return {"nodes": [], "edges": []}
        
        # 创建节点
        nodes = []
        for agent_id in agent_ids:
            agent = self.agents.get(agent_id)
            if agent:
                node_type = "coordinator" if agent_id == self.coordinator_agent_id else "worker"
                nodes.append({
                    "id": agent_id,
                    "name": agent.name,
                    "type": node_type
                })
        
        # 创建边（协调者连接到所有其他智能体）
        edges = []
        for agent_id in agent_ids:
            if agent_id != self.coordinator_agent_id:
                edges.append({
                    "source": self.coordinator_agent_id,
                    "target": agent_id,
                    "type": "coordination"
                })
        
        return {"nodes": nodes, "edges": edges}
    
    def _create_peer_graph(self, agent_ids: List[str]) -> Dict[str, Any]:
        """创建点对点协作图"""
        # 创建节点
        nodes = []
        for agent_id in agent_ids:
            agent = self.agents.get(agent_id)
            if agent:
                nodes.append({
                    "id": agent_id,
                    "name": agent.name,
                    "type": "peer"
                })
        
        # 创建边（全连接网络）
        edges = []
        for i, source_id in enumerate(agent_ids):
            for target_id in agent_ids[i+1:]:
                edges.append({
                    "source": source_id,
                    "target": target_id,
                    "type": "peer"
                })
        
        return {"nodes": nodes, "edges": edges}
    
    def _create_default_graph(self, agent_ids: List[str]) -> Dict[str, Any]:
        """创建默认协作图"""
        # 创建节点
        nodes = []
        for agent_id in agent_ids:
            agent = self.agents.get(agent_id)
            if agent:
                nodes.append({
                    "id": agent_id,
                    "name": agent.name,
                    "type": "default"
                })
        
        # 创建边（环形拓扑）
        edges = []
        for i in range(len(agent_ids)):
            source_id = agent_ids[i]
            target_id = agent_ids[(i+1) % len(agent_ids)]
            edges.append({
                "source": source_id,
                "target": target_id,
                "type": "default"
            })
        
        return {"nodes": nodes, "edges": edges}
    
    async def start_collaboration(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        启动协作流程
        
        参数:
            task: 任务内容
            
        返回:
            Dict[str, Any]: 协作结果
        """
        # 检查任务格式
        if "type" not in task or "content" not in task:
            return {"status": "error", "message": "任务格式不正确"}
            
        # 获取协作智能体
        if self.collaboration_strategy == "hierarchical" and self.coordinator_agent_id:
            # 分配给协调者，由协调者进一步分配
            target_agents = [self.coordinator_agent_id]
        else:
            # 分配给所有智能体
            target_agents = list(self.agents.keys())
            
        if not target_agents:
            return {"status": "error", "message": "没有可用的智能体"}
            
        # 分配任务
        task_id = await self.assign_task(task, target_agents)
        
        # 收集结果
        timeout = task.get("timeout", 30.0)
        results = await self.collect_results(task_id, timeout)
        
        return results


class CollaborationNode:
    """
    协作节点
    
    LangGraph图中用于智能体间协作的节点
    """
    
    def __init__(self, agent_system: MultiAgentCollaborationSystem):
        """
        初始化协作节点
        
        参数:
            agent_system: 多智能体协作系统实例
        """
        self.agent_system = agent_system
        
        self.routing_template = """
请分析以下消息，并确定应该将其发送给哪些团队成员。

消息内容：
{message}

团队成员列表：
{team_members}

任务背景：
{context}

请返回应该接收此消息的团队成员ID列表，以JSON格式：
```json
{
  "target_ids": ["id1", "id2", ...]
}
```

如果消息应该发送给所有人，请返回空列表[]。
"""
    
    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行协作逻辑
        
        参数:
            state: 工作流状态
            
        返回:
            Dict[str, Any]: 更新后的状态
        """
        # 从状态中提取必要信息
        message = state.get("message", "")
        context = state.get("context", {})
        
        if not message:
            # 如果没有消息，直接返回原始状态
            return state
            
        # 路由消息
        routing_result = await self.route_message(message, state)
        
        # 如果有目标智能体，发送消息
        if routing_result.get("target_ids"):
            # 创建任务
            task = {
                "type": "collaboration",
                "content": message,
                "context": context,
                "requester_id": state.get("current_agent_id", "system")
            }
            
            # 分配任务给目标智能体
            task_id = await self.agent_system.assign_task(
                task=task,
                target_agent_ids=routing_result["target_ids"]
            )
            
            # 等待结果
            timeout = state.get("timeout", 30.0)
            results = await self.agent_system.collect_results(task_id, timeout)
            
            # 更新状态
            new_state = state.copy()
            new_state["collaboration_results"] = results
            
            # 如果有响应，聚合它们
            if results.get("status") == "success":
                aggregated = await self.aggregate_responses(
                    [r for r in results.get("results", {}).values()]
                )
                new_state["aggregated_response"] = aggregated
                
            return new_state
            
        # 没有目标智能体，直接返回原始状态
        return state
    
    async def route_message(self, message: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        """
        路由消息
        
        参数:
            message: 消息内容
            state: 工作流状态
            
        返回:
            Dict[str, Any]: 路由结果，包含target_ids
        """
        # 获取LLM服务
        llm_service = state.get("llm_service")
        if not llm_service:
            logger.warning("协作节点未提供LLM服务，无法智能路由")
            # 默认路由给所有智能体
            return {"target_ids": []}
            
        # 格式化团队成员
        team_members_text = "\n".join([
            f"- ID: {agent_id}, 名称: {agent.name}, 类型: {agent.agent_type}"
            for agent_id, agent in self.agent_system.agents.items()
        ])
        
        # 生成路由提示
        prompt = self.routing_template.format(
            message=json.dumps(message, ensure_ascii=False, indent=2),
            team_members=team_members_text,
            context=json.dumps(state.get("context", {}), ensure_ascii=False, indent=2)
        )
        
        try:
            # 调用LLM确定路由
            from app.models.domain.llm_types import LLMMessage
            
            messages = [
                LLMMessage(role="system", content="你是一个负责在团队中路由消息的助手。你需要决定哪些团队成员应该接收特定消息。"),
                LLMMessage(role="user", content=prompt)
            ]
            
            response = await llm_service.chat_completion(
                messages=messages,
                temperature=0.2
            )
            
            content = response.content
            
            # 提取JSON
            import re
            json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
            
            if json_match:
                try:
                    routing_result = json.loads(json_match.group(1))
                    return routing_result
                except json.JSONDecodeError:
                    logger.warning(f"解析路由结果失败: {content}")
            
            # 默认路由给所有智能体
            return {"target_ids": []}
            
        except Exception as e:
            logger.error(f"路由消息失败: {str(e)}")
            return {"target_ids": []}
    
    async def aggregate_responses(self, responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        聚合响应
        
        参数:
            responses: 响应列表
            
        返回:
            Dict[str, Any]: 聚合后的响应
        """
        # 简单聚合，收集所有响应
        aggregated = {
            "responses": responses,
            "summary": f"收到 {len(responses)} 个响应"
        }
        
        return aggregated
