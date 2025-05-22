"""
OpenAI LLM提供者实现

处理OpenAI API的调用和响应转换
"""
import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Union, Any, AsyncGenerator, cast

from openai import AsyncOpenAI, AsyncAzureOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionChunk
from openai.types import CreateEmbeddingResponse

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
    ProviderType
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


class OpenAIProvider(LLMProvider):
    """OpenAI LLM提供者
    
    处理OpenAI API的调用和响应转换
    """
    
    def __init__(self, config: ProviderConfig):
        """初始化OpenAI提供者
        
        Args:
            config: 提供者配置
        """
        super().__init__(config)
        self.client = None
    
    async def initialize(self) -> None:
        """初始化OpenAI客户端"""
        try:
            if self.config.type == ProviderType.OPENAI:
                self.client = AsyncOpenAI(
                    api_key=self.config.api_key,
                    base_url=self.config.api_base,
                    organization=self.config.organization_id,
                    timeout=60.0  # 默认超时时间
                )
            elif self.config.type == ProviderType.AZURE_OPENAI:
                self.client = AsyncAzureOpenAI(
                    api_key=self.config.api_key,
                    api_version="2023-05-15",  # 使用适当的API版本
                    azure_endpoint=self.config.api_base
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
            functions: 可调用的函数列表
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
            openai_messages = [
                {
                    "role": msg.role,
                    "content": msg.content,
                    **({"name": msg.name} if msg.name else {}),
                    **({"function_call": msg.function_call} if msg.function_call else {})
                }
                for msg in messages
            ]
            
            # 准备请求参数
            request_params = {
                "model": model,
                "messages": openai_messages,
                "temperature": temperature,
            }
            
            if max_tokens is not None:
                request_params["max_tokens"] = max_tokens
            
            if stop is not None:
                request_params["stop"] = stop
            
            # 处理函数调用
            if functions:
                tools = []
                for func in functions:
                    tool = {
                        "type": "function",
                        "function": {
                            "name": func.name,
                            "description": func.description,
                            "parameters": func.parameters
                        }
                    }
                    if func.required:
                        tool["function"]["required"] = func.required
                    tools.append(tool)
                
                if tools:
                    request_params["tools"] = tools
            
            # 添加其他参数
            for key, value in kwargs.items():
                if key not in request_params:
                    request_params[key] = value
            
            # 发送请求
            start_time = time.time()
            completion: ChatCompletion = await self.client.chat.completions.create(**request_params)
            end_time = time.time()
            
            logger.debug(f"OpenAI请求耗时: {end_time - start_time:.2f}秒")
            
            # 转换响应
            return self._convert_chat_completion(completion)
            
        except Exception as e:
            self._handle_openai_exception(e)
    
    async def get_embeddings(
        self, 
        texts: Union[str, List[str]], 
        model: str
    ) -> Union[LLMEmbedding, List[LLMEmbedding]]:
        """获取文本嵌入向量
        
        Args:
            texts: 单个文本或文本列表
            model: 嵌入模型名称
            
        Returns:
            Union[LLMEmbedding, List[LLMEmbedding]]: 嵌入结果
            
        Raises:
            LLMServiceError: LLM服务调用失败
        """
        if not self.client:
            await self.initialize()
        
        try:
            # 统一处理为列表
            text_list = texts if isinstance(texts, list) else [texts]
            
            # 发送请求
            start_time = time.time()
            response: CreateEmbeddingResponse = await self.client.embeddings.create(
                model=model,
                input=text_list
            )
            end_time = time.time()
            
            logger.debug(f"OpenAI嵌入请求耗时: {end_time - start_time:.2f}秒")
            
            # 转换响应
            embeddings = [
                LLMEmbedding(
                    embedding=data.embedding,
                    index=data.index,
                    object=data.object
                )
                for data in response.data
            ]
            
            # 如果输入是单个文本，返回单个结果
            if isinstance(texts, str):
                return embeddings[0]
            return embeddings
            
        except Exception as e:
            self._handle_openai_exception(e)
    
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
            openai_messages = [
                {
                    "role": msg.role,
                    "content": msg.content,
                    **({"name": msg.name} if msg.name else {}),
                    **({"function_call": msg.function_call} if msg.function_call else {})
                }
                for msg in messages
            ]
            
            # 准备请求参数
            request_params = {
                "model": model,
                "messages": openai_messages,
                "temperature": temperature,
                "stream": True
            }
            
            if max_tokens is not None:
                request_params["max_tokens"] = max_tokens
            
            if stop is not None:
                request_params["stop"] = stop
            
            # 处理函数调用
            if functions:
                tools = []
                for func in functions:
                    tool = {
                        "type": "function",
                        "function": {
                            "name": func.name,
                            "description": func.description,
                            "parameters": func.parameters
                        }
                    }
                    if func.required:
                        tool["function"]["required"] = func.required
                    tools.append(tool)
                
                if tools:
                    request_params["tools"] = tools
            
            # 添加其他参数
            for key, value in kwargs.items():
                if key not in request_params:
                    request_params[key] = value
            
            # 发送流式请求
            start_time = time.time()
            stream = await self.client.chat.completions.create(**request_params)
            
            # 处理流式响应
            async for chunk in stream:
                chunk_dict = self._convert_streaming_chunk(chunk)
                yield chunk_dict
                
            end_time = time.time()
            logger.debug(f"OpenAI流式请求总耗时: {end_time - start_time:.2f}秒")
            
        except Exception as e:
            self._handle_openai_exception(e)
    
    def _convert_chat_completion(self, completion: ChatCompletion) -> LLMResponse:
        """转换OpenAI聊天补全响应到统一格式
        
        Args:
            completion: OpenAI聊天补全响应
            
        Returns:
            LLMResponse: 统一格式的LLM响应
        """
        choices = []
        for choice in completion.choices:
            # 转换消息
            message_dict = {
                "role": choice.message.role,
                "content": choice.message.content or ""
            }
            
            # 处理函数调用
            if hasattr(choice.message, 'tool_calls') and choice.message.tool_calls:
                for tool_call in choice.message.tool_calls:
                    if tool_call.type == 'function':
                        func_call = {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments
                        }
                        message_dict["function_call"] = func_call
                        break
            
            # 构建响应选项
            choice_obj = LLMResponseChoice(
                index=choice.index,
                message=LLMMessage(**message_dict),
                finish_reason=choice.finish_reason
            )
            choices.append(choice_obj)
        
        # 构建使用量统计
        usage = None
        if completion.usage:
            usage = LLMUsage(
                prompt_tokens=completion.usage.prompt_tokens,
                completion_tokens=completion.usage.completion_tokens,
                total_tokens=completion.usage.total_tokens
            )
        
        # 构建完整响应
        response = LLMResponse(
            id=completion.id,
            object=completion.object,
            created=completion.created,
            model=completion.model,
            choices=choices,
            usage=usage
        )
        
        return response
    
    def _convert_streaming_chunk(self, chunk: ChatCompletionChunk) -> Dict[str, Any]:
        """转换流式响应块为统一格式
        
        Args:
            chunk: OpenAI流式响应块
            
        Returns:
            Dict[str, Any]: 转换后的块数据
        """
        result = {
            "id": chunk.id,
            "object": chunk.object,
            "created": chunk.created,
            "model": chunk.model,
            "choices": []
        }
        
        for choice in chunk.choices:
            choice_data = {
                "index": choice.index,
                "finish_reason": choice.finish_reason
            }
            
            # 处理增量内容
            if hasattr(choice, 'delta') and choice.delta:
                delta = {}
                
                if hasattr(choice.delta, 'role') and choice.delta.role:
                    delta["role"] = choice.delta.role
                
                if hasattr(choice.delta, 'content') and choice.delta.content is not None:
                    delta["content"] = choice.delta.content
                
                # 处理函数调用
                if hasattr(choice.delta, 'tool_calls') and choice.delta.tool_calls:
                    for tool_call in choice.delta.tool_calls:
                        if tool_call.type == 'function':
                            func_name = None
                            if hasattr(tool_call.function, 'name'):
                                func_name = tool_call.function.name
                            
                            func_args = None
                            if hasattr(tool_call.function, 'arguments'):
                                func_args = tool_call.function.arguments
                            
                            if func_name or func_args:
                                delta["function_call"] = {
                                    "name": func_name,
                                    "arguments": func_args
                                }
                                break
                
                choice_data["delta"] = delta
            
            result["choices"].append(choice_data)
        
        return result
    
    def _handle_openai_exception(self, exception: Exception) -> None:
        """处理OpenAI异常
        
        Args:
            exception: 异常对象
            
        Raises:
            LLMServiceError: 转换后的LLM服务异常
        """
        error_message = str(exception)
        
        # 解析OpenAI错误
        if "rate limit" in error_message.lower():
            raise LLMRateLimitError(f"OpenAI请求频率超限: {error_message}")
        elif "authentication" in error_message.lower() or "api key" in error_message.lower():
            raise LLMAuthenticationError(f"OpenAI认证失败: {error_message}")
        elif "context length" in error_message.lower() or "token limit" in error_message.lower():
            raise LLMContextLengthError(f"OpenAI上下文长度超限: {error_message}")
        elif "invalid" in error_message.lower() and "argument" in error_message.lower():
            raise LLMInvalidArgumentError(f"OpenAI参数错误: {error_message}")
        elif "timeout" in error_message.lower():
            raise LLMTimeoutError(f"OpenAI请求超时: {error_message}")
        else:
            raise LLMServiceError(f"OpenAI服务错误: {error_message}")
