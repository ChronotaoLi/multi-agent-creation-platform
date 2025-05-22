"""
Anthropic LLM提供者实现

处理Anthropic API的调用和响应转换
"""
import asyncio
import json
import logging
import time
import uuid
from typing import Dict, List, Optional, Union, Any, AsyncGenerator, cast

from anthropic import AsyncAnthropic, AsyncAnthropicBedrock

from app.models.domain.llm_types import (
    LLMMessage, 
    LLMResponse, 
    LLMProvider, 
    ProviderConfig,
    LLMEmbedding,
    LLMFunction,
    LLMResponseChoice,
    LLMUsage,
    LLMFunctionCall,
    ProviderType,
    LLMRole
)
from app.utils.llm_exceptions import (
    LLMAuthenticationError,
    LLMContextLengthError,
    LLMInvalidArgumentError,
    LLMRateLimitError,
    LLMServiceError,
    LLMTimeoutError
)

logger = logging.getLogger(__name__)


class AnthropicProvider(LLMProvider):
    """Anthropic LLM提供者
    
    处理Anthropic API的调用和响应转换
    """
    
    def __init__(self, config: ProviderConfig):
        """初始化Anthropic提供者
        
        Args:
            config: 提供者配置
        """
        super().__init__(config)
        self.client = None
    
    async def initialize(self) -> None:
        """初始化Anthropic客户端"""
        try:
            if self.config.type == ProviderType.ANTHROPIC:
                self.client = AsyncAnthropic(
                    api_key=self.config.api_key,
                    base_url=self.config.api_base,
                    timeout=60.0  # 默认超时时间
                )
            elif self.config.type == ProviderType.OTHER and "bedrock" in self.config.api_base.lower():
                # Bedrock集成
                self.client = AsyncAnthropicBedrock(
                    aws_region=self.config.organization_id or "us-west-2",  # 使用organization_id存储AWS区域
                    api_key=self.config.api_key  # 可选的API密钥
                )
            else:
                raise ValueError(f"不支持的提供者类型: {self.config.type}")
            
            logger.info(f"已成功初始化 {self.config.type} 客户端")
        except Exception as e:
            logger.error(f"初始化 {self.config.type} 客户端时出错: {str(e)}", exc_info=True)
            raise LLMServiceError(f"初始化 {self.config.type} 客户端失败: {str(e)}")
    
    async def chat_completion(
        self, 
        messages: List[LLMMessage], 
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        functions: Optional[List[LLMFunction]] = None,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> LLMResponse:
        """获取聊天补全响应
        
        Args:
            messages: 聊天上下文消息列表
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大生成token数
            functions: 可调用的函数列表，Claude用tools实现
            stop: 停止生成的标记列表
            **kwargs: 其他参数
            
        Returns:
            LLMResponse: LLM响应内容
            
        Raises:
            LLMServiceError: LLM服务调用失败
        """
        if not self.client:
            await self.initialize()
        
        try:
            # 转换消息格式
            anthropic_messages = self._convert_messages_to_anthropic(messages)
            
            # 准备请求参数
            request_params = {
                "model": model,
                "messages": anthropic_messages,
                "temperature": temperature,
                "max_tokens": max_tokens or 1024,
            }
            
            if stop is not None:
                request_params["stop_sequences"] = stop
            
            # 处理工具（函数）调用
            if functions:
                tools = []
                for func in functions:
                    tool = {
                        "name": func.name,
                        "description": func.description,
                        "input_schema": func.parameters
                    }
                    tools.append(tool)
                
                if tools:
                    request_params["tools"] = tools
                    # 可选的工具选择参数
                    request_params["tool_choice"] = "auto"
            
            # 添加其他参数
            for key, value in kwargs.items():
                if key not in request_params:
                    request_params[key] = value
            
            # 发送请求
            start_time = time.time()
            completion = await self.client.messages.create(**request_params)
            end_time = time.time()
            
            logger.debug(f"Anthropic请求耗时: {end_time - start_time:.2f}秒")
            
            # 转换响应
            return self._convert_anthropic_response(completion)
            
        except Exception as e:
            self._handle_anthropic_exception(e)
    
    async def get_embeddings(
        self, 
        texts: Union[str, List[str]], 
        model: str
    ) -> Union[LLMEmbedding, List[LLMEmbedding]]:
        """获取文本嵌入向量
        
        Claude API暂不支持直接生成嵌入，这里提供一个错误处理
        
        Args:
            texts: 单个文本或文本列表
            model: 嵌入模型名称
            
        Raises:
            LLMServiceError: 不支持的功能
        """
        raise LLMServiceError("Anthropic API不支持直接获取嵌入向量功能")
    
    async def streaming_chat_completion(
        self, 
        messages: List[LLMMessage], 
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        functions: Optional[List[LLMFunction]] = None,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """流式获取聊天补全响应
        
        Args:
            messages: 聊天上下文消息列表
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大生成token数
            functions: 可调用的函数列表
            stop: 停止生成的标记列表
            **kwargs: 其他参数
            
        Yields:
            Dict[str, Any]: 包含部分响应的字典
            
        Raises:
            LLMServiceError: LLM服务调用失败
        """
        if not self.client:
            await self.initialize()
        
        try:
            # 转换消息格式
            anthropic_messages = self._convert_messages_to_anthropic(messages)
            
            # 准备请求参数
            request_params = {
                "model": model,
                "messages": anthropic_messages,
                "temperature": temperature,
                "max_tokens": max_tokens or 1024,
                "stream": True
            }
            
            if stop is not None:
                request_params["stop_sequences"] = stop
            
            # 处理工具（函数）调用
            if functions:
                tools = []
                for func in functions:
                    tool = {
                        "name": func.name,
                        "description": func.description,
                        "input_schema": func.parameters
                    }
                    tools.append(tool)
                
                if tools:
                    request_params["tools"] = tools
                    # 可选的工具选择参数
                    request_params["tool_choice"] = "auto"
            
            # 添加其他参数
            for key, value in kwargs.items():
                if key not in request_params:
                    request_params[key] = value
            
            # 发送流式请求
            start_time = time.time()
            stream = await self.client.messages.create(**request_params)
            
            # 用于累积最终的用量统计
            usage_stats = {"input_tokens": 0, "output_tokens": 0}
            
            # 处理流式响应
            async for event in stream:
                # 处理流式事件并转换为统一格式
                chunk_dict = self._convert_streaming_event(event)
                
                # 跟踪token使用量
                if hasattr(event, 'usage') and event.usage:
                    usage_stats["input_tokens"] = event.usage.input_tokens
                    usage_stats["output_tokens"] = event.usage.output_tokens
                
                yield chunk_dict
                
            # 流式请求完成
            end_time = time.time()
            logger.debug(f"Anthropic流式请求总耗时: {end_time - start_time:.2f}秒")
            
        except Exception as e:
            self._handle_anthropic_exception(e)
    
    def _convert_messages_to_anthropic(self, messages: List[LLMMessage]) -> List[Dict[str, Any]]:
        """转换消息格式为Anthropic格式
        
        Args:
            messages: 内部LLM消息格式
            
        Returns:
            List[Dict[str, Any]]: Anthropic格式的消息列表
        """
        anthropic_messages = []
        
        for msg in messages:
            # 处理角色映射（Anthropic只支持user/assistant）
            role = "user" if msg.role in [LLMRole.USER, LLMRole.SYSTEM] else "assistant"
            
            # 系统消息需要特殊处理
            if msg.role == LLMRole.SYSTEM:
                # 插入系统提示到用户消息内容
                content = f"<system>\n{msg.content}\n</system>"
                # 查找下一个用户消息并合并
                for next_idx, next_msg in enumerate(messages):
                    if next_idx > messages.index(msg) and next_msg.role == LLMRole.USER:
                        anthropic_messages.append({
                            "role": "user",
                            "content": f"{content}\n\n{next_msg.content}"
                        })
                        break
                else:
                    # 如果没有后续用户消息，直接添加系统消息作为用户消息
                    anthropic_messages.append({
                        "role": "user",
                        "content": content
                    })
                continue  # 跳过当前消息，因为已经处理
            
            # 跳过被系统消息合并的用户消息
            skip = False
            for prev_idx, prev_msg in enumerate(messages):
                if (prev_idx < messages.index(msg) and 
                    prev_msg.role == LLMRole.SYSTEM and 
                    msg.role == LLMRole.USER):
                    # 检查该用户消息是否紧跟在系统消息之后
                    if messages.index(msg) - prev_idx == 1:
                        skip = True
                        break
            
            if skip:
                continue
            
            # 处理函数调用结果消息
            if msg.role == LLMRole.FUNCTION:
                # Anthropic不支持function角色，需要转换为工具响应格式
                # 当前可通过assistant消息中添加tool_use字段来表示
                anthropic_messages.append({
                    "role": "assistant",
                    "content": "",
                    "tool_use": {
                        "name": msg.name or "unknown_function",
                        "input": msg.content  # 函数输入参数
                    }
                })
                continue
            
            # 处理常规消息
            message_dict = {
                "role": role,
                "content": msg.content
            }
            
            # 处理函数调用
            if msg.function_call:
                message_dict["tool_use"] = {
                    "name": msg.function_call.get("name", "unknown_function"),
                    "input": msg.function_call.get("arguments", "{}")
                }
            
            anthropic_messages.append(message_dict)
        
        return anthropic_messages
    
    def _convert_anthropic_response(self, response) -> LLMResponse:
        """转换Anthropic响应为标准格式
        
        Args:
            response: Anthropic响应对象
            
        Returns:
            LLMResponse: 统一格式的LLM响应
        """
        try:
            # 解析响应内容
            content = response.content[0].text if hasattr(response, 'content') and response.content else ""
            
            # 处理函数/工具调用
            function_call = None
            if hasattr(response, 'tool_use') and response.tool_use:
                function_call = {
                    "name": response.tool_use.name,
                    "arguments": response.tool_use.input
                }
            
            # 构建响应选项
            choice = LLMResponseChoice(
                index=0,
                message=LLMMessage(
                    role=LLMRole.ASSISTANT,
                    content=content,
                    function_call=function_call
                ),
                finish_reason=response.stop_reason if hasattr(response, 'stop_reason') else None
            )
            
            # 构建使用量统计
            usage = None
            if hasattr(response, 'usage') and response.usage:
                usage = LLMUsage(
                    prompt_tokens=response.usage.input_tokens,
                    completion_tokens=response.usage.output_tokens,
                    total_tokens=response.usage.input_tokens + response.usage.output_tokens
                )
            
            # 构建LLM响应
            llm_response = LLMResponse(
                id=response.id if hasattr(response, 'id') else f"anthropic-{uuid.uuid4()}",
                object="anthropic.message",
                created=int(time.time()),
                model=response.model if hasattr(response, 'model') else "unknown",
                choices=[choice],
                usage=usage
            )
            
            return llm_response
            
        except Exception as e:
            logger.error(f"转换Anthropic响应时出错: {str(e)}", exc_info=True)
            raise LLMServiceError(f"转换Anthropic响应失败: {str(e)}")
    
    def _convert_streaming_event(self, event) -> Dict[str, Any]:
        """转换Anthropic流式事件为统一格式
        
        Args:
            event: Anthropic流式事件
            
        Returns:
            Dict[str, Any]: 转换后的事件数据
        """
        try:
            # 创建基本结构
            result = {
                "id": str(uuid.uuid4()),  # Anthropic流式事件可能没有唯一ID
                "object": "anthropic.message.delta",
                "created": int(time.time()),
                "model": event.model if hasattr(event, 'model') else "unknown",
                "choices": []
            }
            
            # 处理不同类型的事件
            if event.type == "message_start":
                # 消息开始
                choice_data = {
                    "index": 0,
                    "finish_reason": None,
                    "delta": {"role": "assistant"}
                }
                result["choices"].append(choice_data)
                
            elif event.type == "content_block_start":
                # 内容块开始
                choice_data = {
                    "index": 0,
                    "finish_reason": None,
                    "delta": {"role": "assistant"}
                }
                result["choices"].append(choice_data)
                
            elif event.type == "content_block_delta":
                # 内容增量
                if hasattr(event, 'delta') and hasattr(event.delta, 'text'):
                    choice_data = {
                        "index": 0,
                        "finish_reason": None,
                        "delta": {"content": event.delta.text}
                    }
                    result["choices"].append(choice_data)
                
            elif event.type == "content_block_stop":
                # 内容块结束
                choice_data = {
                    "index": 0,
                    "finish_reason": None,
                }
                result["choices"].append(choice_data)
                
            elif event.type == "message_delta":
                # 消息增量（可能包含usage等信息）
                choice_data = {
                    "index": 0,
                    "finish_reason": None,
                }
                result["choices"].append(choice_data)
                
                # 添加使用量信息
                if hasattr(event, 'usage') and event.usage:
                    result["usage"] = {
                        "prompt_tokens": event.usage.input_tokens,
                        "completion_tokens": event.usage.output_tokens,
                        "total_tokens": event.usage.input_tokens + event.usage.output_tokens
                    }
                
            elif event.type == "message_stop":
                # 消息结束
                choice_data = {
                    "index": 0,
                    "finish_reason": event.stop_reason if hasattr(event, 'stop_reason') else "stop",
                }
                result["choices"].append(choice_data)
                
                # 添加最终使用量信息
                if hasattr(event, 'usage') and event.usage:
                    result["usage"] = {
                        "prompt_tokens": event.usage.input_tokens,
                        "completion_tokens": event.usage.output_tokens,
                        "total_tokens": event.usage.input_tokens + event.usage.output_tokens
                    }
                
            elif event.type == "tool_use":
                # 工具/函数调用
                choice_data = {
                    "index": 0,
                    "finish_reason": "tool_calls",
                    "delta": {
                        "function_call": {
                            "name": event.tool_use.name if hasattr(event.tool_use, 'name') else "",
                            "arguments": event.tool_use.input if hasattr(event.tool_use, 'input') else ""
                        }
                    }
                }
                result["choices"].append(choice_data)
            
            # 如果没有识别的事件类型，添加一个空的选择
            if not result["choices"]:
                result["choices"].append({"index": 0, "finish_reason": None})
            
            return result
            
        except Exception as e:
            logger.error(f"转换Anthropic流式事件时出错: {str(e)}", exc_info=True)
            # 返回错误事件，避免流中断
            return {
                "id": str(uuid.uuid4()),
                "object": "anthropic.message.delta.error",
                "created": int(time.time()),
                "model": "unknown",
                "choices": [{"index": 0, "finish_reason": "error"}],
                "error": str(e)
            }
    
    def _handle_anthropic_exception(self, exception: Exception) -> None:
        """处理Anthropic异常
        
        Args:
            exception: 异常对象
            
        Raises:
            LLMServiceError: 转换后的LLM服务异常
        """
        error_message = str(exception)
        
        # 解析Anthropic错误
        if "rate" in error_message.lower() and "limit" in error_message.lower():
            raise LLMRateLimitError(f"Anthropic请求频率超限: {error_message}")
        elif "auth" in error_message.lower() or "api key" in error_message.lower():
            raise LLMAuthenticationError(f"Anthropic认证失败: {error_message}")
        elif "context" in error_message.lower() and "length" in error_message.lower():
            raise LLMContextLengthError(f"Anthropic上下文长度超限: {error_message}")
        elif ("invalid" in error_message.lower() or "bad request" in error_message.lower()) and "param" in error_message.lower():
            raise LLMInvalidArgumentError(f"Anthropic参数错误: {error_message}")
        elif "timeout" in error_message.lower():
            raise LLMTimeoutError(f"Anthropic请求超时: {error_message}")
        else:
            raise LLMServiceError(f"Anthropic服务错误: {error_message}")
