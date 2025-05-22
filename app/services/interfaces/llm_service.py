"""
LLM服务接口

定义与大语言模型交互的服务接口
"""
from typing import Dict, List, Optional, Protocol, Any, Union

from app.models.domain.llm_types import (
    LLMConfig, 
    LLMMessage, 
    LLMResponse, 
    LLMProvider, 
    LLMEmbedding,
    LLMFunction
)


class LLMService(Protocol):
    """LLM服务接口
    
    定义与大语言模型交互的方法
    """
    
    async def chat_completion(
        self, 
        messages: List[LLMMessage], 
        model: str = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        functions: Optional[List[LLMFunction]] = None,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> LLMResponse:
        """获取聊天补全响应
        
        Args:
            messages: 聊天上下文消息列表
            model: 模型名称，默认使用配置中的默认模型
            temperature: 温度参数，控制随机性
            max_tokens: 最大生成token数
            functions: 可调用的函数列表
            stop: 停止生成的标记列表
            **kwargs: 其他参数
            
        Returns:
            LLMResponse: LLM响应内容
            
        Raises:
            LLMServiceError: LLM服务调用失败
        """
        ...
    
    async def get_embeddings(
        self, 
        texts: Union[str, List[str]], 
        model: str = None
    ) -> Union[LLMEmbedding, List[LLMEmbedding]]:
        """获取文本嵌入向量
        
        Args:
            texts: 单个文本或文本列表
            model: 嵌入模型名称，默认使用配置中的默认嵌入模型
            
        Returns:
            Union[LLMEmbedding, List[LLMEmbedding]]: 嵌入结果
            
        Raises:
            LLMServiceError: LLM服务调用失败
        """
        ...
    
    async def select_provider(self, model: str = None) -> LLMProvider:
        """选择合适的LLM提供者
        
        Args:
            model: 模型名称
            
        Returns:
            LLMProvider: 选中的LLM提供者
            
        Raises:
            LLMConfigError: 配置错误
            LLMProviderNotFoundError: 找不到支持该模型的提供者
        """
        ...
    
    def set_api_key(self, provider: str, api_key: str) -> None:
        """设置API密钥
        
        Args:
            provider: 提供者名称
            api_key: API密钥
        """
        ...
    
    def get_config(self) -> LLMConfig:
        """获取LLM配置
        
        Returns:
            LLMConfig: 当前LLM配置
        """
        ...
    
    def update_config(self, config: LLMConfig) -> None:
        """更新LLM配置
        
        Args:
            config: 新的LLM配置
        """
        ...
    
    async def streaming_chat_completion(
        self, 
        messages: List[LLMMessage], 
        model: str = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        functions: Optional[List[LLMFunction]] = None,
        stop: Optional[List[str]] = None,
        **kwargs
    ):
        """流式获取聊天补全响应
        
        Args:
            messages: 聊天上下文消息列表
            model: 模型名称，默认使用配置中的默认模型
            temperature: 温度参数，控制随机性
            max_tokens: 最大生成token数
            functions: 可调用的函数列表
            stop: 停止生成的标记列表
            **kwargs: 其他参数
            
        Returns:
            AsyncGenerator: 生成LLMResponse的异步生成器
            
        Raises:
            LLMServiceError: LLM服务调用失败
        """
        ... 