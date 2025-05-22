"""
工具使用模式智能体

为智能体提供工具使用能力
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from app.agents.base_agent import BaseAgent
from app.agents.tools import BaseTool
from app.services.interfaces.llm_service import LLMService
from app.models.domain.llm_types import LLMMessage

logger = logging.getLogger(__name__)


class ToolUsingAgent(BaseAgent):
    """
    工具使用模式智能体
    
    能够使用工具完成任务的智能体，支持工具选择、参数提取和结果处理
    """
    
    def __init__(
        self,
        id: str,
        name: str,
        agent_type: str,
        llm_service: LLMService,
        tools: List[BaseTool] = None,
        max_tool_calls: int = 5,
        config: Dict[str, Any] = None
    ):
        """
        初始化工具使用智能体
        
        参数:
            id: 智能体唯一标识符
            name: 智能体名称
            agent_type: 智能体类型
            llm_service: LLM服务实例
            tools: 可用工具列表
            max_tool_calls: 单次任务最大工具调用次数
            config: 智能体配置信息
        """
        super().__init__(id, name, agent_type, llm_service, config)
        
        self.tools = tools or []
        self.tool_by_name = {tool.name: tool for tool in self.tools}
        self.max_tool_calls = max_tool_calls
        
        # 工具调用模式
        self.tool_call_template = config.get("tool_call_template", """
你现在需要完成一项任务，可以使用以下工具来辅助：

{tools_description}

任务描述：
{task_description}

{context}

请按以下格式使用工具：
```
思考: <你对如何解决任务的思考过程>
工具: <选择的工具名称>
参数: <工具所需参数，以JSON格式提供>
```

如果任务已完成，请以以下格式返回：
```
思考: <你的思考过程>
回答: <最终答案或结论>
```

请确保准确使用工具，并仅在必要时使用。
""")
        
        self.tools_description_template = config.get("tools_description_template", """
{name}: {description}
""")
    
    async def process_with_tools(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用工具处理输入
        
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
            
        # 初始化工具调用历史
        tool_calls_history = []
        
        # 准备工具描述
        tools_description = self._prepare_tools_description()
        
        # 构造初始提示
        initial_prompt = self.tool_call_template.format(
            tools_description=tools_description,
            task_description=task,
            context=self._format_context(context)
        )
        
        messages = [
            LLMMessage(role="system", content=f"你是一个能够使用工具解决问题的AI助手。你的名字是{self.name}。"),
            LLMMessage(role="user", content=initial_prompt)
        ]
        
        try:
            # 工具调用循环
            for i in range(self.max_tool_calls):
                # 获取LLM响应
                response = await self.llm_service.chat_completion(
                    messages=messages,
                    temperature=0.3  # 使用较低的温度以获得更确定性的工具使用
                )
                
                content = response.content
                
                # 检查是否包含最终答案
                if "回答:" in content:
                    # 提取答案
                    answer_match = re.search(r"回答:(.*?)($|```)", content, re.DOTALL)
                    if answer_match:
                        answer = answer_match.group(1).strip()
                        # 返回最终结果
                        return {
                            "status": "success",
                            "output": answer,
                            "tool_calls": tool_calls_history
                        }
                    else:
                        # 如果发现"回答:"标记但无法提取，可能是格式问题
                        return {
                            "status": "success", 
                            "output": content,
                            "tool_calls": tool_calls_history
                        }
                        
                # 尝试解析工具调用
                tool_call = self._parse_tool_call(content)
                if tool_call:
                    tool_name, tool_params, thinking = tool_call
                    
                    # 记录思考过程
                    if thinking:
                        self.context.add_memory(f"thinking_{i}", thinking)
                    
                    # 执行工具调用
                    if tool_name in self.tool_by_name:
                        tool = self.tool_by_name[tool_name]
                        try:
                            # 执行工具调用
                            tool_result = await self._call_tool_async(tool, tool_params)
                            
                            # 记录工具调用
                            call_record = {
                                "tool": tool_name,
                                "params": tool_params,
                                "result": tool_result,
                                "success": True
                            }
                            tool_calls_history.append(call_record)
                            
                            # 添加工具调用结果到消息历史
                            tool_message = f"工具调用结果 [{tool_name}]:\n```\n{tool_result}\n```"
                            messages.append(LLMMessage(role="user", content=tool_message))
                            
                        except Exception as e:
                            # 工具调用失败
                            error_message = f"工具 {tool_name} 调用失败: {str(e)}"
                            logger.error(error_message)
                            
                            # 记录失败的调用
                            call_record = {
                                "tool": tool_name,
                                "params": tool_params,
                                "error": str(e),
                                "success": False
                            }
                            tool_calls_history.append(call_record)
                            
                            # 添加错误消息到历史
                            messages.append(LLMMessage(role="user", content=f"错误: {error_message}"))
                    else:
                        # 工具不存在
                        error_message = f"工具 {tool_name} 不存在，可用工具: {', '.join(self.tool_by_name.keys())}"
                        messages.append(LLMMessage(role="user", content=f"错误: {error_message}"))
                else:
                    # 无法解析工具调用
                    logger.warning(f"无法解析工具调用: {content}")
                    messages.append(LLMMessage(role="user", content="无法解析你的工具调用请求。请使用正确的格式指定工具和参数。"))
            
            # 如果达到最大调用次数，生成最终总结
            messages.append(LLMMessage(role="user", content="你已达到最大工具调用次数。请提供当前任务的最终答案或结论。"))
            
            final_response = await self.llm_service.chat_completion(
                messages=messages,
                temperature=0.7  # 最终总结可以稍微提高创造性
            )
            
            # 返回结果
            return {
                "status": "success",
                "output": final_response.content,
                "tool_calls": tool_calls_history,
                "note": "达到最大工具调用次数"
            }
            
        except Exception as e:
            logger.error(f"工具使用过程出错: {str(e)}")
            return {
                "status": "error",
                "message": f"处理失败: {str(e)}",
                "tool_calls": tool_calls_history
            }
    
    def _prepare_tools_description(self) -> str:
        """
        准备工具描述文本
        
        返回:
            str: 工具描述文本
        """
        descriptions = []
        for tool in self.tools:
            desc = self.tools_description_template.format(
                name=tool.name,
                description=tool.description
            )
            descriptions.append(desc)
            
        return "\n".join(descriptions)
    
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
            
        context_lines = ["上下文信息:"]
        for key, value in context.items():
            if isinstance(value, dict):
                value_str = json.dumps(value, ensure_ascii=False, indent=2)
                context_lines.append(f"{key}:\n```\n{value_str}\n```")
            elif isinstance(value, list):
                if all(isinstance(item, dict) for item in value):
                    value_str = json.dumps(value, ensure_ascii=False, indent=2)
                    context_lines.append(f"{key}:\n```\n{value_str}\n```")
                else:
                    value_str = "\n".join(f"- {item}" for item in value)
                    context_lines.append(f"{key}:\n{value_str}")
            else:
                context_lines.append(f"{key}: {value}")
                
        return "\n".join(context_lines)
    
    def _parse_tool_call(self, text: str) -> Optional[Tuple[str, Dict[str, Any], Optional[str]]]:
        """
        解析工具调用文本
        
        参数:
            text: 包含工具调用的文本
            
        返回:
            Optional[Tuple[str, Dict[str, Any], Optional[str]]]: 工具名称、参数和思考过程，解析失败则返回None
        """
        # 提取思考部分
        thinking_match = re.search(r"思考:(.*?)(?=工具:|$)", text, re.DOTALL)
        thinking = thinking_match.group(1).strip() if thinking_match else None
        
        # 提取工具名称
        tool_match = re.search(r"工具:(.*?)(?=参数:|$)", text, re.DOTALL)
        if not tool_match:
            return None
            
        tool_name = tool_match.group(1).strip()
        
        # 提取参数
        params_match = re.search(r"参数:(.*?)($|```)", text, re.DOTALL)
        if not params_match:
            return None
            
        params_text = params_match.group(1).strip()
        
        # 尝试解析JSON参数
        try:
            # 首先检查是否包含在JSON代码块中
            json_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", params_text)
            if json_block_match:
                params_json = json_block_match.group(1)
                return tool_name, json.loads(params_json), thinking
                
            # 如果没有代码块，直接尝试解析
            return tool_name, json.loads(params_text), thinking
                
        except json.JSONDecodeError:
            logger.warning(f"无法解析工具参数JSON: {params_text}")
            # 尝试简单参数提取
            simple_params = {}
            param_lines = params_text.split("\n")
            for line in param_lines:
                if ":" in line:
                    key, value = line.split(":", 1)
                    simple_params[key.strip()] = value.strip()
            
            if simple_params:
                return tool_name, simple_params, thinking
                
            return None
    
    async def _call_tool_async(self, tool: BaseTool, params: Dict[str, Any]) -> Any:
        """
        异步调用工具
        
        参数:
            tool: 工具实例
            params: 工具参数
            
        返回:
            Any: 工具调用结果
        """
        # 如果是同步工具，在事件循环中执行
        result = tool(**params)
        return result


class ToolNode:
    """
    工具节点
    
    LangGraph工作流中使用的工具节点
    """
    
    def __init__(
        self,
        llm_service: LLMService,
        tools: List[BaseTool],
        max_tool_calls: int = 3,
        stop_on_error: bool = False
    ):
        """
        初始化工具节点
        
        参数:
            llm_service: LLM服务实例
            tools: 可用工具列表
            max_tool_calls: 最大工具调用次数
            stop_on_error: 错误时是否停止
        """
        self.llm_service = llm_service
        self.tools = tools
        self.tool_by_name = {tool.name: tool for tool in tools}
        self.max_tool_calls = max_tool_calls
        self.stop_on_error = stop_on_error
        
        self.tool_selection_template = """
你需要使用工具来完成任务。可用的工具有：

{tools_description}

任务：{task}

上下文：
{context}

请选择最适合当前任务的工具，并提供调用参数：

工具名：<工具名称>
参数：
{
  // 工具参数，JSON格式
}
思考过程：<解释为什么选择此工具以及如何使用它>
"""
    
    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行工具节点
        
        参数:
            state: 工作流状态
            
        返回:
            Dict[str, Any]: 更新后的状态
        """
        # 从状态中提取必要信息
        task = state.get("task", "")
        context = state.get("context", {})
        tool_history = state.get("tool_history", [])
        
        # 如果没有任务，直接返回
        if not task:
            return state
            
        # 如果已经达到最大工具调用次数，直接返回
        if len(tool_history) >= self.max_tool_calls:
            new_state = state.copy()
            new_state["tool_status"] = "max_calls_reached"
            return new_state
        
        try:
            # 选择工具
            tool_name, params, thinking = await self._select_tool(task, context, tool_history)
            
            # 执行工具调用
            if tool_name in self.tool_by_name:
                tool = self.tool_by_name[tool_name]
                
                try:
                    # 调用工具
                    result = tool(**params)
                    
                    # 更新工具历史
                    tool_call = {
                        "tool": tool_name,
                        "params": params,
                        "thinking": thinking,
                        "result": result,
                        "success": True
                    }
                    
                    # 更新状态
                    new_state = state.copy()
                    new_state["tool_history"] = tool_history + [tool_call]
                    new_state["last_tool_result"] = result
                    new_state["current_tool_thinking"] = thinking
                    new_state["tool_status"] = "success"
                    
                    return new_state
                    
                except Exception as e:
                    # 工具调用失败
                    error_message = f"工具 {tool_name} 调用失败: {str(e)}"
                    logger.error(error_message)
                    
                    # 更新工具历史
                    tool_call = {
                        "tool": tool_name,
                        "params": params,
                        "thinking": thinking,
                        "error": str(e),
                        "success": False
                    }
                    
                    # 更新状态
                    new_state = state.copy()
                    new_state["tool_history"] = tool_history + [tool_call]
                    new_state["last_tool_error"] = error_message
                    new_state["tool_status"] = "error"
                    
                    return new_state
            else:
                # 工具不存在
                error_message = f"工具 {tool_name} 不存在，可用工具: {', '.join(self.tool_by_name.keys())}"
                
                # 更新工具历史
                tool_call = {
                    "tool": tool_name,
                    "params": params,
                    "thinking": thinking,
                    "error": error_message,
                    "success": False
                }
                
                # 更新状态
                new_state = state.copy()
                new_state["tool_history"] = tool_history + [tool_call]
                new_state["last_tool_error"] = error_message
                new_state["tool_status"] = "error"
                
                return new_state
                
        except Exception as e:
            logger.error(f"工具节点执行失败: {str(e)}")
            
            # 更新状态
            new_state = state.copy()
            new_state["tool_status"] = "error"
            new_state["last_tool_error"] = f"工具节点执行失败: {str(e)}"
            
            return new_state
    
    async def _select_tool(
        self, 
        task: str, 
        context: Dict[str, Any], 
        tool_history: List[Dict[str, Any]]
    ) -> Tuple[str, Dict[str, Any], str]:
        """
        选择要使用的工具
        
        参数:
            task: 任务描述
            context: 上下文信息
            tool_history: 工具使用历史
            
        返回:
            Tuple[str, Dict[str, Any], str]: 工具名称、参数和思考过程
        """
        # 准备工具描述
        tools_description = "\n".join([
            f"{tool.name}: {tool.description}" for tool in self.tools
        ])
        
        # 格式化上下文
        context_str = "\n".join([f"{k}: {v}" for k, v in context.items()]) if context else "无"
        
        # 添加工具使用历史
        history_str = ""
        if tool_history:
            history_entries = []
            for entry in tool_history:
                tool = entry["tool"]
                success = entry.get("success", False)
                result = entry.get("result", "无结果")
                error = entry.get("error", "")
                
                if success:
                    history_entries.append(f"工具: {tool}\n结果: {result}")
                else:
                    history_entries.append(f"工具: {tool}\n错误: {error}")
                    
            history_str = "工具使用历史:\n" + "\n\n".join(history_entries)
            context_str = context_str + "\n\n" + history_str
        
        # 构造选择工具的提示
        prompt = self.tool_selection_template.format(
            tools_description=tools_description,
            task=task,
            context=context_str
        )
        
        try:
            # 调用LLM选择工具
            messages = [
                LLMMessage(role="system", content="你是一个工具选择助手，你需要为给定任务选择最适合的工具。"),
                LLMMessage(role="user", content=prompt)
            ]
            
            response = await self.llm_service.chat_completion(
                messages=messages,
                temperature=0.2
            )
            
            content = response.content
            
            # 解析工具名
            tool_name_match = re.search(r"工具名：?\s*(.*?)$", content, re.MULTILINE)
            tool_name = tool_name_match.group(1).strip() if tool_name_match else None
            
            # 解析JSON参数
            params = {}
            json_match = re.search(r"(?:参数：?|```json)\s*([\s\S]*?)(?:```|思考过程)", content)
            if json_match:
                try:
                    params_text = json_match.group(1).strip()
                    params = json.loads(params_text)
                except json.JSONDecodeError:
                    logger.warning(f"无法解析工具参数JSON: {params_text}")
            
            # 解析思考过程
            thinking_match = re.search(r"思考过程：?\s*([\s\S]*?)$", content)
            thinking = thinking_match.group(1).strip() if thinking_match else ""
            
            if not tool_name:
                raise ValueError("未能从响应中提取工具名")
                
            return tool_name, params, thinking
            
        except Exception as e:
            logger.error(f"选择工具失败: {str(e)}")
            # 默认返回第一个工具（如果有）
            if self.tools:
                return self.tools[0].name, {}, f"工具选择失败，默认使用第一个工具: {str(e)}"
            else:
                raise ValueError(f"无可用工具且工具选择失败: {str(e)}")
