"""
工具智能体实现

负责调用外部工具和API的智能体
"""

import json
import logging
import aiohttp
import os
import base64
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from app.agents.base_agent import BaseAgent
from app.services.interfaces.llm_service import LLMService
from app.models.domain.llm_types import LLMMessage
from app.agents.tools.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


class ToolAgent(BaseAgent):
    """
    工具智能体
    
    负责管理和调用外部工具和API，扩展其他智能体的能力
    """
    
    def __init__(
        self,
        id: str,
        name: str,
        llm_service: LLMService,
        tool_registry: ToolRegistry,
        config: Dict[str, Any] = None
    ):
        """
        初始化工具智能体
        
        参数:
            id: 智能体唯一标识符
            name: 智能体名称
            llm_service: LLM服务实例
            tool_registry: 工具注册表实例
            config: 智能体配置信息
        """
        super().__init__(id, name, "tool", llm_service, config or {})
        
        # 工具注册表
        self.tool_registry = tool_registry
        
        # 工具使用历史
        self.tool_usage_history = []
        
        # 最大历史记录条数
        self.max_history_items = config.get("max_history_items", 100)
        
        # API密钥（安全存储）
        self.api_keys = config.get("api_keys", {})
        
        # 系统提示模板
        self.system_prompt_template = config.get("system_prompt_template", """
你是一个专业的工具调用智能体，负责理解任务需求并调用合适的外部工具和API来完成任务。

你应该：
1. 理解请求的意图和要求
2. 选择最合适的工具来满足需求
3. 正确设置工具参数
4. 解析和格式化工具返回的结果
5. 处理可能的错误和异常

请保持专业、高效，并确保你的工具调用是安全和合规的。
""")
        
        # HTTP会话
        self._http_session = None
    
    async def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用工具
        
        参数:
            tool_name: 工具名称
            parameters: 工具参数
            
        返回:
            Dict[str, Any]: 工具执行结果
        """
        try:
            # 检查工具是否存在
            if not self.tool_registry.has_tool(tool_name):
                error_msg = f"工具 '{tool_name}' 不存在"
                logger.error(error_msg)
                return {"error": error_msg, "status": "failed"}
            
            # 获取工具
            tool = self.tool_registry.get_tool(tool_name)
            
            # 记录工具调用
            call_record = {
                "tool_name": tool_name,
                "parameters": self._sanitize_parameters(parameters),
                "timestamp": datetime.now().isoformat(),
                "status": "pending"
            }
            self.tool_usage_history.append(call_record)
            self._trim_history()
            
            # 调用工具
            start_time = datetime.now()
            result = await tool.execute(parameters)
            end_time = datetime.now()
            
            # 更新调用记录
            call_record["status"] = "success" if "error" not in result else "failed"
            call_record["duration"] = (end_time - start_time).total_seconds()
            call_record["result_summary"] = self._summarize_result(result)
            
            logger.info(f"工具 '{tool_name}' 调用成功，耗时: {call_record['duration']:.2f}秒")
            return result
            
        except Exception as e:
            error_msg = f"调用工具 '{tool_name}' 失败: {str(e)}"
            logger.error(error_msg)
            
            # 更新调用记录
            if self.tool_usage_history and self.tool_usage_history[-1]["tool_name"] == tool_name:
                self.tool_usage_history[-1]["status"] = "failed"
                self.tool_usage_history[-1]["error"] = str(e)
            
            return {"error": error_msg, "status": "failed"}
    
    async def find_suitable_tool(self, task_description: str) -> Dict[str, Any]:
        """
        查找适合任务的工具
        
        参数:
            task_description: 任务描述
            
        返回:
            Dict[str, Any]: 推荐的工具信息
        """
        try:
            # 获取所有可用工具
            available_tools = self.tool_registry.list_tools()
            
            # 构建工具描述
            tools_description = ""
            for tool in available_tools:
                tools_description += f"- {tool['name']}: {tool['description']}\n"
                tools_description += f"  参数: {json.dumps(tool['parameters'], ensure_ascii=False)}\n\n"
            
            # 构建提示
            prompt = f"""
请帮我找出最适合完成以下任务的工具：

任务: {task_description}

可用工具:
{tools_description}

请根据任务需求和工具功能，选择最合适的工具。如果有多个合适的工具，请按优先级排序。
请以JSON格式返回结果：
```json
{{
  "recommended_tools": [
    {{
      "name": "工具名称",
      "reason": "推荐理由",
      "suggested_parameters": {{
        "参数1": "建议值",
        "参数2": "建议值"
      }}
    }},
    ...
  ],
  "task_analysis": "任务需求分析"
}}
```
"""
            
            # 调用LLM查找适合的工具
            messages = [
                LLMMessage(role="system", content=self.system_prompt_template),
                LLMMessage(role="user", content=prompt)
            ]
            
            response = await self.llm_service.chat_completion(
                messages=messages,
                temperature=0.2
            )
            
            content = response.content
            # 提取JSON部分
            import re
            
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = content
                
            # 解析推荐结果
            recommendations = json.loads(json_str)
            
            logger.info(f"为任务 '{task_description}' 找到 {len(recommendations.get('recommended_tools', []))} 个推荐工具")
            return recommendations
            
        except Exception as e:
            error_msg = f"查找工具失败: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg, "status": "failed"}
    
    async def format_tool_input(self, tool_name: str, user_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化工具输入参数
        
        参数:
            tool_name: 工具名称
            user_input: 用户提供的输入
            
        返回:
            Dict[str, Any]: 格式化后的工具参数
        """
        try:
            # 检查工具是否存在
            if not self.tool_registry.has_tool(tool_name):
                error_msg = f"工具 '{tool_name}' 不存在"
                logger.error(error_msg)
                return {"error": error_msg, "status": "failed"}
            
            # 获取工具
            tool = self.tool_registry.get_tool(tool_name)
            tool_spec = tool.get_spec()
            
            # 获取参数规范
            required_params = []
            optional_params = []
            
            for param_name, param_spec in tool_spec.get("parameters", {}).items():
                if param_spec.get("required", False):
                    required_params.append({
                        "name": param_name,
                        "type": param_spec.get("type", "string"),
                        "description": param_spec.get("description", "")
                    })
                else:
                    optional_params.append({
                        "name": param_name,
                        "type": param_spec.get("type", "string"),
                        "description": param_spec.get("description", ""),
                        "default": param_spec.get("default", None)
                    })
            
            # 构建提示
            input_text = json.dumps(user_input, ensure_ascii=False, indent=2)
            
            prompt = f"""
请将以下用户输入格式化为工具 '{tool_name}' 的标准参数：

工具描述: {tool_spec.get('description', '')}

必需参数:
{json.dumps(required_params, ensure_ascii=False, indent=2)}

可选参数:
{json.dumps(optional_params, ensure_ascii=False, indent=2)}

用户输入:
{input_text}

请提取和格式化参数，确保满足所有必需参数，并尽可能利用可选参数。对于用户未提供的必需参数，请给出合理的缺失提示。
请以JSON格式返回格式化的参数：
```json
{{
  "formatted_parameters": {{
    "参数1": "值1",
    "参数2": "值2",
    ...
  }},
  "missing_required": ["缺失的必需参数1", ...],
  "invalid_values": [
    {{
      "param": "参数名",
      "reason": "无效原因"
    }},
    ...
  ]
}}
```
"""
            
            # 调用LLM格式化参数
            messages = [
                LLMMessage(role="system", content=self.system_prompt_template),
                LLMMessage(role="user", content=prompt)
            ]
            
            response = await self.llm_service.chat_completion(
                messages=messages,
                temperature=0.1
            )
            
            content = response.content
            # 提取JSON部分
            import re
            
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = content
                
            # 解析格式化结果
            formatted_result = json.loads(json_str)
            
            # 检查是否有缺失的必需参数
            if formatted_result.get("missing_required"):
                logger.warning(f"工具 '{tool_name}' 调用缺少必需参数: {', '.join(formatted_result['missing_required'])}")
            
            logger.info(f"已格式化工具 '{tool_name}' 的输入参数")
            return formatted_result
            
        except Exception as e:
            error_msg = f"格式化工具输入失败: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg, "status": "failed"}
    
    async def interpret_tool_result(self, tool_name: str, result: Dict[str, Any], format_type: str = "default") -> Dict[str, Any]:
        """
        解释工具执行结果
        
        参数:
            tool_name: 工具名称
            result: 工具执行结果
            format_type: 结果格式类型（default, summary, detailed）
            
        返回:
            Dict[str, Any]: 解释后的结果
        """
        try:
            # 如果结果中包含错误，直接返回错误信息
            if "error" in result:
                return {
                    "status": "failed",
                    "error": result["error"],
                    "interpretation": f"工具 '{tool_name}' 执行失败: {result['error']}"
                }
            
            # 根据格式类型选择提示模板
            format_prompts = {
                "summary": "请提供一个简短摘要，突出最重要的信息",
                "detailed": "请提供详细解释，包括所有重要细节和上下文",
                "default": "请提供一个平衡的解释，包含关键信息和适当的详细程度"
            }
            
            format_instruction = format_prompts.get(format_type, format_prompts["default"])
            
            # 构建提示
            result_text = json.dumps(result, ensure_ascii=False, indent=2)
            
            prompt = f"""
请解释以下工具执行结果：

工具: {tool_name}
执行结果:
{result_text}

{format_instruction}

请以用户友好的方式解释这些结果，突出关键信息，并指出任何可能需要注意的问题。
"""
            
            # 调用LLM解释结果
            messages = [
                LLMMessage(role="system", content=self.system_prompt_template),
                LLMMessage(role="user", content=prompt)
            ]
            
            response = await self.llm_service.chat_completion(
                messages=messages,
                temperature=0.4
            )
            
            interpretation = response.content
            
            logger.info(f"已解释工具 '{tool_name}' 的执行结果，格式: {format_type}")
            return {
                "status": "success",
                "interpretation": interpretation,
                "original_result": result,
                "format_type": format_type
            }
            
        except Exception as e:
            error_msg = f"解释工具结果失败: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "failed",
                "error": error_msg,
                "original_result": result
            }
    
    async def chain_tools(self, workflow: List[Dict[str, Any]], initial_input: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        链式调用多个工具
        
        参数:
            workflow: 工具调用工作流
            initial_input: 初始输入
            
        返回:
            Dict[str, Any]: 链式调用结果
        """
        try:
            results = []
            current_input = initial_input or {}
            
            for i, step in enumerate(workflow):
                tool_name = step.get("tool")
                
                if not tool_name:
                    error_msg = f"工作流步骤 {i+1} 未指定工具名称"
                    logger.error(error_msg)
                    return {
                        "status": "failed",
                        "error": error_msg,
                        "step": i+1,
                        "results": results
                    }
                
                # 获取当前步骤的参数
                parameters = step.get("parameters", {})
                
                # 替换参数中的引用
                parameters = self._resolve_references(parameters, results, current_input)
                
                # 调用工具
                logger.info(f"工作流步骤 {i+1}: 调用工具 '{tool_name}'")
                result = await self.call_tool(tool_name, parameters)
                
                # 记录结果
                step_result = {
                    "step": i+1,
                    "tool": tool_name,
                    "parameters": self._sanitize_parameters(parameters),
                    "result": result,
                    "status": "success" if "error" not in result else "failed"
                }
                results.append(step_result)
                
                # 如果步骤失败且不允许继续，则中断工作流
                if "error" in result and not step.get("continue_on_error", False):
                    logger.warning(f"工作流在步骤 {i+1} 中断: {result['error']}")
                    break
                
                # 更新当前输入为上一步的结果
                if "error" not in result:
                    current_input = result
            
            # 返回最终结果
            return {
                "status": "completed" if len(results) == len(workflow) else "partial",
                "steps_completed": len(results),
                "total_steps": len(workflow),
                "results": results,
                "final_result": results[-1]["result"] if results else None
            }
            
        except Exception as e:
            error_msg = f"链式调用工具失败: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "failed",
                "error": error_msg,
                "steps_completed": len(results),
                "total_steps": len(workflow),
                "results": results
            }
    
    async def make_api_request(self, api_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        发起API请求
        
        参数:
            api_config: API配置信息
            
        返回:
            Dict[str, Any]: API响应结果
        """
        try:
            # 提取API配置
            url = api_config.get("url")
            if not url:
                error_msg = "API请求未指定URL"
                logger.error(error_msg)
                return {"error": error_msg, "status": "failed"}
            
            method = api_config.get("method", "GET").upper()
            headers = api_config.get("headers", {})
            params = api_config.get("params", {})
            data = api_config.get("data")
            json_data = api_config.get("json")
            timeout = api_config.get("timeout", 30)
            
            # 处理认证
            auth = api_config.get("auth", {})
            auth_type = auth.get("type")
            
            if auth_type == "bearer":
                token = auth.get("token")
                if token:
                    headers["Authorization"] = f"Bearer {token}"
            elif auth_type == "basic":
                username = auth.get("username")
                password = auth.get("password")
                if username and password:
                    auth_string = base64.b64encode(f"{username}:{password}".encode()).decode()
                    headers["Authorization"] = f"Basic {auth_string}"
            elif auth_type == "api_key":
                key_name = auth.get("key_name")
                key_value = auth.get("key_value")
                key_in = auth.get("in", "header")
                
                if key_name and key_value:
                    if key_in == "header":
                        headers[key_name] = key_value
                    elif key_in == "query":
                        params[key_name] = key_value
            
            # 创建HTTP会话（如果需要）
            if not self._http_session:
                self._http_session = aiohttp.ClientSession()
            
            # 发起请求
            async with self._http_session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                data=data,
                json=json_data,
                timeout=timeout
            ) as response:
                # 读取响应
                response_data = None
                content_type = response.headers.get("Content-Type", "")
                
                if "application/json" in content_type:
                    response_data = await response.json()
                else:
                    response_data = await response.text()
                
                # 构建结果
                result = {
                    "status": "success" if response.status < 400 else "failed",
                    "status_code": response.status,
                    "headers": dict(response.headers),
                    "data": response_data
                }
                
                if response.status >= 400:
                    result["error"] = f"API请求失败，状态码: {response.status}"
                
                logger.info(f"API请求 {method} {url} 完成，状态码: {response.status}")
                return result
                
        except aiohttp.ClientError as e:
            error_msg = f"API请求网络错误: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg, "status": "failed"}
            
        except Exception as e:
            error_msg = f"API请求失败: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg, "status": "failed"}
    
    async def register_new_tool(self, tool_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        注册新工具
        
        参数:
            tool_spec: 工具规范
            
        返回:
            Dict[str, Any]: 注册结果
        """
        try:
            # 检查必要的字段
            required_fields = ["name", "description", "method", "parameters"]
            missing_fields = [field for field in required_fields if field not in tool_spec]
            
            if missing_fields:
                error_msg = f"工具规范缺少必要字段: {', '.join(missing_fields)}"
                logger.error(error_msg)
                return {"error": error_msg, "status": "failed"}
            
            # 检查工具是否已存在
            tool_name = tool_spec["name"]
            if self.tool_registry.has_tool(tool_name):
                error_msg = f"工具 '{tool_name}' 已存在"
                logger.error(error_msg)
                return {"error": error_msg, "status": "failed"}
            
            # 注册工具
            result = await self.tool_registry.register_tool(tool_spec)
            
            logger.info(f"注册了新工具 '{tool_name}'")
            return {
                "status": "success",
                "tool_name": tool_name,
                "result": result
            }
            
        except Exception as e:
            error_msg = f"注册工具失败: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg, "status": "failed"}
    
    def get_tool_usage_stats(self) -> Dict[str, Any]:
        """
        获取工具使用统计
        
        返回:
            Dict[str, Any]: 工具使用统计信息
        """
        try:
            # 按工具名称分组统计
            stats = {}
            
            for record in self.tool_usage_history:
                tool_name = record.get("tool_name", "unknown")
                status = record.get("status", "unknown")
                
                if tool_name not in stats:
                    stats[tool_name] = {
                        "total_calls": 0,
                        "successful_calls": 0,
                        "failed_calls": 0,
                        "average_duration": 0
                    }
                
                stats[tool_name]["total_calls"] += 1
                
                if status == "success":
                    stats[tool_name]["successful_calls"] += 1
                elif status == "failed":
                    stats[tool_name]["failed_calls"] += 1
                
                # 计算平均持续时间
                if "duration" in record:
                    current_avg = stats[tool_name]["average_duration"]
                    total_calls = stats[tool_name]["total_calls"]
                    
                    # 更新平均值
                    stats[tool_name]["average_duration"] = (current_avg * (total_calls - 1) + record["duration"]) / total_calls
            
            # 构建结果
            result = {
                "overall": {
                    "total_calls": len(self.tool_usage_history),
                    "unique_tools": len(stats)
                },
                "tools": stats
            }
            
            return result
            
        except Exception as e:
            error_msg = f"获取工具使用统计失败: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
    
    async def shutdown(self) -> None:
        """
        关闭智能体和释放资源
        """
        try:
            # 关闭HTTP会话
            if self._http_session:
                await self._http_session.close()
                self._http_session = None
            
            logger.info("工具智能体已关闭")
            
        except Exception as e:
            logger.error(f"关闭工具智能体失败: {str(e)}")
    
    def _sanitize_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        清理敏感参数信息
        
        参数:
            parameters: 参数字典
            
        返回:
            Dict[str, Any]: 清理后的参数
        """
        # 复制参数
        sanitized = {}
        
        # 敏感参数名列表
        sensitive_params = ["password", "token", "api_key", "secret", "credential", "auth", "key"]
        
        for key, value in parameters.items():
            # 检查是否是敏感参数
            is_sensitive = any(sensitive in key.lower() for sensitive in sensitive_params)
            
            if is_sensitive:
                sanitized[key] = "********"  # 屏蔽敏感值
            else:
                sanitized[key] = value
                
        return sanitized
    
    def _summarize_result(self, result: Dict[str, Any]) -> str:
        """
        总结工具结果
        
        参数:
            result: 工具结果
            
        返回:
            str: 结果总结
        """
        if "error" in result:
            return f"错误: {result['error']}"
        
        # 尝试获取结果的关键信息
        summary = []
        
        if "status" in result:
            summary.append(f"状态: {result['status']}")
        
        if "data" in result and isinstance(result["data"], dict):
            data_keys = list(result["data"].keys())
            summary.append(f"数据字段: {', '.join(data_keys[:5])}")
            if len(data_keys) > 5:
                summary.append(f"等 {len(data_keys)} 个字段")
        
        if not summary:
            return "执行完成，无法总结结果"
        
        return ", ".join(summary)
    
    def _trim_history(self) -> None:
        """
        修剪历史记录，保持在最大条数限制内
        """
        if len(self.tool_usage_history) > self.max_history_items:
            self.tool_usage_history = self.tool_usage_history[-self.max_history_items:]
    
    def _resolve_references(self, parameters: Dict[str, Any], previous_results: List[Dict[str, Any]], current_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析参数中的引用
        
        参数:
            parameters: 参数字典
            previous_results: 之前的结果列表
            current_input: 当前输入
            
        返回:
            Dict[str, Any]: 解析后的参数
        """
        resolved = {}
        
        for key, value in parameters.items():
            if isinstance(value, str) and value.startswith("$result."):
                # 解析结果引用，格式: $result.step_number.path.to.value
                parts = value[8:].split(".")
                if parts and parts[0].isdigit():
                    step_index = int(parts[0]) - 1
                    if 0 <= step_index < len(previous_results):
                        # 获取指定步骤的结果
                        step_result = previous_results[step_index]["result"]
                        
                        # 解析路径
                        result_value = step_result
                        for part in parts[1:]:
                            if isinstance(result_value, dict) and part in result_value:
                                result_value = result_value[part]
                            else:
                                result_value = None
                                break
                                
                        resolved[key] = result_value
                        continue
            
            elif isinstance(value, str) and value.startswith("$input."):
                # 解析输入引用，格式: $input.path.to.value
                path = value[7:].split(".")
                input_value = current_input
                for part in path:
                    if isinstance(input_value, dict) and part in input_value:
                        input_value = input_value[part]
                    else:
                        input_value = None
                        break
                
                resolved[key] = input_value
                continue
                
            # 默认情况，保持原值
            resolved[key] = value
            
        return resolved