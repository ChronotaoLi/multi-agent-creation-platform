"""
LLM服务实现

实现与大语言模型的交互功能
"""
import json
import logging
import os
from typing import Dict, List, Optional, Any, Union, AsyncGenerator

from app.models.domain.llm_types import (
    LLMConfig, 
    LLMMessage, 
    LLMResponse, 
    LLMProvider, 
    LLMEmbedding,
    LLMFunction,
    ProviderType,
    ProviderConfig,
    ModelConfig,
    ModelType
)
from app.utils.llm_exceptions import (
    LLMConfigError,
    LLMProviderNotFoundError,
    LLMServiceError
)
from app.data_access.llm_adapter.base_llm_provider import llm_provider_factory

logger = logging.getLogger(__name__)


class LLMServiceImpl:
    """LLM服务实现
    
    实现与大语言模型的交互功能
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化LLM服务
        
        Args:
            config_path: LLM配置文件路径，如果为None则使用默认配置
        """
        self.config = self._load_config(config_path)
    
    def _load_config(self, config_path: Optional[str] = None) -> LLMConfig:
        """加载LLM配置
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            LLMConfig: LLM配置
            
        Raises:
            LLMConfigError: 配置加载错误
        """
        # 如果提供了配置文件路径，尝试加载
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_dict = json.load(f)
                return LLMConfig(**config_dict)
            except Exception as e:
                logger.error(f"加载LLM配置文件失败: {str(e)}", exc_info=True)
                raise LLMConfigError(f"加载LLM配置文件失败: {str(e)}")
        
        # 使用默认配置
        try:
            # 加载环境变量
            openai_api_key = os.environ.get("OPENAI_API_KEY")
            anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
            
            # 准备默认的提供者配置
            providers = []
            
            # 添加OpenAI提供者（如果有API密钥）
            if openai_api_key:
                openai_provider = ProviderConfig(
                    type=ProviderType.OPENAI,
                    api_key=openai_api_key,
                    api_base="https://api.openai.com/v1",
                    models=[
                        ModelConfig(
                            name="gpt-4o",
                            provider=ProviderType.OPENAI,
                            context_window=128000,
                            supports_functions=True,
                            supports_vision=True,
                            default_max_tokens=1024
                        ),
                        ModelConfig(
                            name="gpt-3.5-turbo",
                            provider=ProviderType.OPENAI,
                            context_window=16385,
                            supports_functions=True,
                            default_max_tokens=1024
                        ),
                        ModelConfig(
                            name="text-embedding-3-large",
                            provider=ProviderType.OPENAI,
                            type=ModelType.EMBEDDING
                        )
                    ],
                    default_model="gpt-3.5-turbo",
                    default_embedding_model="text-embedding-3-large"
                )
                providers.append(openai_provider)
            
            # 添加Anthropic提供者（如果有API密钥）
            if anthropic_api_key:
                anthropic_provider = ProviderConfig(
                    type=ProviderType.ANTHROPIC,
                    api_key=anthropic_api_key,
                    models=[
                        ModelConfig(
                            name="claude-3-opus-20240229",
                            provider=ProviderType.ANTHROPIC,
                            context_window=180000,
                            supports_functions=True,
                            supports_vision=True,
                            default_max_tokens=4096
                        ),
                        ModelConfig(
                            name="claude-3-sonnet-20240229",
                            provider=ProviderType.ANTHROPIC,
                            context_window=180000,
                            supports_functions=True,
                            supports_vision=True,
                            default_max_tokens=4096
                        ),
                        ModelConfig(
                            name="claude-3-haiku-20240307",
                            provider=ProviderType.ANTHROPIC,
                            context_window=180000,
                            supports_functions=True,
                            supports_vision=True,
                            default_max_tokens=4096
                        )
                    ],
                    default_model="claude-3-sonnet-20240229"
                )
                providers.append(anthropic_provider)
            
            # 创建LLM配置
            default_provider = ProviderType.OPENAI if openai_api_key else (
                ProviderType.ANTHROPIC if anthropic_api_key else None
            )
            
            config = LLMConfig(
                providers=providers,
                default_provider=default_provider
            )
            
            # 验证配置
            if not providers:
                logger.warning("未找到任何LLM提供者配置，请确保设置了相关环境变量或提供配置文件")
            
            return config
            
        except Exception as e:
            logger.error(f"创建默认LLM配置失败: {str(e)}", exc_info=True)
            raise LLMConfigError(f"创建默认LLM配置失败: {str(e)}")
    
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
        try:
            # 获取适合的提供者
            provider = await self.select_provider(model)
            
            # 如果未指定模型，使用提供者的默认模型
            if not model:
                model = self._get_default_model_for_provider(provider)
            
            # 调用提供者的聊天补全方法
            return await provider.chat_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                functions=functions,
                stop=stop,
                **kwargs
            )
            
        except Exception as e:
            logger.error(f"聊天补全请求失败: {str(e)}", exc_info=True)
            raise LLMServiceError(f"聊天补全请求失败: {str(e)}")
    
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
        try:
            # 查找提供者和嵌入模型
            embedding_model, provider = self._get_embedding_model_and_provider(model)
            
            # 调用提供者的嵌入方法
            return await provider.get_embeddings(texts=texts, model=embedding_model)
            
        except Exception as e:
            logger.error(f"获取嵌入向量失败: {str(e)}", exc_info=True)
            raise LLMServiceError(f"获取嵌入向量失败: {str(e)}")
    
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
        return llm_provider_factory.get_provider_for_model(self.config, model)
    
    def set_api_key(self, provider: str, api_key: str) -> None:
        """设置API密钥
        
        Args:
            provider: 提供者名称
            api_key: API密钥
        """
        try:
            provider_type = ProviderType(provider)
            
            # 更新配置中的API密钥
            for provider_config in self.config.providers:
                if provider_config.type == provider_type:
                    provider_config.api_key = api_key
                    break
            else:
                # 如果找不到该提供者，添加一个新的配置
                if provider_type == ProviderType.OPENAI:
                    new_provider = ProviderConfig(
                        type=provider_type,
                        api_key=api_key,
                        api_base="https://api.openai.com/v1",
                        models=[
                            ModelConfig(
                                name="gpt-4o",
                                provider=provider_type,
                                context_window=128000,
                                supports_functions=True,
                                supports_vision=True
                            ),
                            ModelConfig(
                                name="gpt-3.5-turbo",
                                provider=provider_type
                            ),
                            ModelConfig(
                                name="text-embedding-3-large",
                                provider=provider_type,
                                type=ModelType.EMBEDDING
                            )
                        ],
                        default_model="gpt-3.5-turbo",
                        default_embedding_model="text-embedding-3-large"
                    )
                elif provider_type == ProviderType.ANTHROPIC:
                    new_provider = ProviderConfig(
                        type=provider_type,
                        api_key=api_key,
                        models=[
                            ModelConfig(
                                name="claude-3-opus-20240229",
                                provider=provider_type,
                                context_window=180000,
                                supports_functions=True,
                                supports_vision=True
                            ),
                            ModelConfig(
                                name="claude-3-sonnet-20240229",
                                provider=provider_type,
                                context_window=180000,
                                supports_functions=True
                            )
                        ],
                        default_model="claude-3-sonnet-20240229"
                    )
                else:
                    new_provider = ProviderConfig(
                        type=provider_type,
                        api_key=api_key
                    )
                
                self.config.providers.append(new_provider)
                
                # 如果这是第一个提供者，设置为默认提供者
                if len(self.config.providers) == 1:
                    self.config.default_provider = provider_type
            
            # 重置提供者实例缓存
            llm_provider_factory.reset_providers()
            
        except Exception as e:
            logger.error(f"设置API密钥失败: {str(e)}", exc_info=True)
            raise LLMConfigError(f"设置API密钥失败: {str(e)}")
    
    def get_config(self) -> LLMConfig:
        """获取LLM配置
        
        Returns:
            LLMConfig: 当前LLM配置
        """
        return self.config
    
    def update_config(self, config: LLMConfig) -> None:
        """更新LLM配置
        
        Args:
            config: 新的LLM配置
        """
        self.config = config
        
        # 重置提供者实例缓存
        llm_provider_factory.reset_providers()
    
    async def streaming_chat_completion(
        self, 
        messages: List[LLMMessage], 
        model: str = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        functions: Optional[List[LLMFunction]] = None,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """流式获取聊天补全响应
        
        Args:
            messages: 聊天上下文消息列表
            model: 模型名称，默认使用配置中的默认模型
            temperature: 温度参数，控制随机性
            max_tokens: 最大生成token数
            functions: 可调用的函数列表
            stop: 停止生成的标记列表
            **kwargs: 其他参数
            
        Yields:
            Dict[str, Any]: 包含部分响应的字典
            
        Raises:
            LLMServiceError: LLM服务调用失败
        """
        try:
            # 获取适合的提供者
            provider = await self.select_provider(model)
            
            # 如果未指定模型，使用提供者的默认模型
            if not model:
                model = self._get_default_model_for_provider(provider)
            
            # 验证模型是否支持流式输出
            for provider_config in self.config.providers:
                if provider_config.type == provider.config.type:
                    for model_config in provider_config.models:
                        if model_config.name == model and not model_config.supports_streaming:
                            raise LLMServiceError(f"模型 {model} 不支持流式输出")
            
            # 调用提供者的流式聊天补全方法
            async for chunk in provider.streaming_chat_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                functions=functions,
                stop=stop,
                **kwargs
            ):
                yield chunk
                
        except LLMServiceError:
            # 直接传递LLM服务错误
            raise
        except Exception as e:
            logger.error(f"流式聊天补全请求失败: {str(e)}", exc_info=True)
            raise LLMServiceError(f"流式聊天补全请求失败: {str(e)}")
    
    def _get_default_model_for_provider(self, provider: LLMProvider) -> str:
        """获取提供者的默认模型名称
        
        Args:
            provider: LLM提供者
            
        Returns:
            str: 默认模型名称
            
        Raises:
            LLMConfigError: 配置错误
        """
        # 从提供者配置中获取默认模型
        if provider.config.default_model:
            return provider.config.default_model
        
        # 如果提供者配置中没有默认模型，但有模型列表，使用第一个
        if provider.config.models:
            # 优先使用聊天模型
            for model in provider.config.models:
                if model.type == ModelType.CHAT:
                    return model.name
            
            # 如果没有聊天模型，使用第一个模型
            return provider.config.models[0].name
        
        # 如果没有模型列表，根据提供者类型猜测一个默认模型
        if provider.config.type == ProviderType.OPENAI:
            return "gpt-3.5-turbo"
        elif provider.config.type == ProviderType.ANTHROPIC:
            return "claude-3-sonnet-20240229"
        
        raise LLMConfigError(f"无法确定提供者 {provider.config.type} 的默认模型")
    
    def _get_embedding_model_and_provider(self, model: Optional[str] = None) -> tuple[str, LLMProvider]:
        """获取嵌入模型和对应的提供者
        
        Args:
            model: 嵌入模型名称，如果为None则使用默认嵌入模型
            
        Returns:
            tuple[str, LLMProvider]: 嵌入模型名称和提供者
            
        Raises:
            LLMConfigError: 配置错误
            LLMProviderNotFoundError: 找不到支持嵌入的提供者
        """
        # 如果指定了模型，查找支持该模型的提供者
        if model:
            for provider_config in self.config.providers:
                for model_config in provider_config.models:
                    if model_config.name == model and model_config.type == ModelType.EMBEDDING:
                        provider = llm_provider_factory.create_provider(provider_config)
                        return model, provider
            
            # 如果找不到指定的嵌入模型，尝试使用该名称和默认提供者
            if self.config.default_provider:
                for provider_config in self.config.providers:
                    if provider_config.type == self.config.default_provider:
                        provider = llm_provider_factory.create_provider(provider_config)
                        return model, provider
            
            # 如果仍然找不到，抛出异常
            raise LLMProviderNotFoundError(f"找不到支持嵌入模型 {model} 的提供者")
        
        # 如果未指定模型，查找配置中的默认嵌入模型
        for provider_config in self.config.providers:
            if provider_config.default_embedding_model:
                provider = llm_provider_factory.create_provider(provider_config)
                return provider_config.default_embedding_model, provider
        
        # 如果没有配置默认嵌入模型，查找任何嵌入类型的模型
        for provider_config in self.config.providers:
            for model_config in provider_config.models:
                if model_config.type == ModelType.EMBEDDING:
                    provider = llm_provider_factory.create_provider(provider_config)
                    return model_config.name, provider
        
        # 如果找不到任何嵌入模型，但存在OpenAI提供者，使用其默认嵌入模型
        for provider_config in self.config.providers:
            if provider_config.type == ProviderType.OPENAI:
                provider = llm_provider_factory.create_provider(provider_config)
                return "text-embedding-3-large", provider
        
        # 如果实在找不到，抛出异常
        raise LLMProviderNotFoundError("找不到支持嵌入功能的提供者") 