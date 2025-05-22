"""
基础LLM提供者工厂

负责创建和管理不同类型的LLM提供者
"""
import logging
from typing import Dict, Optional, Type, Union

from app.models.domain.llm_types import (
    LLMProvider, 
    ProviderConfig, 
    ProviderType,
    LLMConfig
)
from app.utils.llm_exceptions import (
    LLMConfigError,
    LLMProviderNotFoundError
)
from app.data_access.llm_adapter.openai_provider import OpenAIProvider
from app.data_access.llm_adapter.anthropic_provider import AnthropicProvider

logger = logging.getLogger(__name__)


class LLMProviderFactory:
    """LLM提供者工厂
    
    负责根据配置创建和管理不同类型的LLM提供者
    """
    
    # 提供者类型映射
    _provider_classes: Dict[ProviderType, Type[LLMProvider]] = {
        ProviderType.OPENAI: OpenAIProvider,
        ProviderType.AZURE_OPENAI: OpenAIProvider,
        ProviderType.ANTHROPIC: AnthropicProvider,
    }
    
    # 缓存已创建的提供者实例
    _provider_instances: Dict[str, LLMProvider] = {}
    
    @classmethod
    def create_provider(cls, config: ProviderConfig) -> LLMProvider:
        """创建LLM提供者
        
        Args:
            config: 提供者配置
            
        Returns:
            LLMProvider: LLM提供者实例
            
        Raises:
            LLMProviderNotFoundError: 找不到支持该提供者类型的实现
        """
        provider_type = config.type
        provider_key = f"{provider_type}_{config.api_key}"
        
        # 如果已有缓存实例，则返回
        if provider_key in cls._provider_instances:
            return cls._provider_instances[provider_key]
        
        # 检查是否支持该提供者类型
        if provider_type not in cls._provider_classes:
            # 处理其他类型或特定情况
            if provider_type == ProviderType.OTHER:
                # 根据API基础URL判断使用哪个提供者
                if config.api_base and "bedrock" in config.api_base.lower():
                    provider_class = AnthropicProvider
                else:
                    raise LLMProviderNotFoundError(f"不支持的提供者类型: {provider_type}")
            else:
                raise LLMProviderNotFoundError(f"不支持的提供者类型: {provider_type}")
        else:
            provider_class = cls._provider_classes[provider_type]
        
        # 创建提供者实例
        provider = provider_class(config)
        
        # 缓存实例
        cls._provider_instances[provider_key] = provider
        
        return provider
    
    @classmethod
    def get_provider_for_model(cls, config: LLMConfig, model_name: Optional[str] = None) -> LLMProvider:
        """根据模型名称获取适合的提供者
        
        Args:
            config: LLM配置
            model_name: 模型名称，如果为None则使用默认模型
            
        Returns:
            LLMProvider: 适合的LLM提供者实例
            
        Raises:
            LLMConfigError: 配置错误
            LLMProviderNotFoundError: 找不到支持该模型的提供者
        """
        if not config.providers:
            raise LLMConfigError("未配置任何LLM提供者")
        
        # 如果未指定模型，使用默认提供者的默认模型
        if not model_name:
            # 使用默认提供者
            if config.default_provider:
                for provider_config in config.providers:
                    if provider_config.type == config.default_provider:
                        return cls.create_provider(provider_config)
                
                # 如果找不到默认提供者，则使用第一个配置的提供者
                logger.warning(f"未找到默认提供者 {config.default_provider}，使用第一个配置的提供者")
            
            # 使用第一个提供者
            return cls.create_provider(config.providers[0])
        
        # 如果指定了模型，查找支持该模型的提供者
        for provider_config in config.providers:
            model_names = [model.name for model in provider_config.models]
            if model_name in model_names:
                return cls.create_provider(provider_config)
        
        # 如果找不到支持该模型的提供者，尝试根据模型名称前缀猜测
        if model_name.startswith(("gpt-", "text-davinci")):
            for provider_config in config.providers:
                if provider_config.type in [ProviderType.OPENAI, ProviderType.AZURE_OPENAI]:
                    logger.warning(f"基于名称猜测模型 {model_name} 由OpenAI提供")
                    return cls.create_provider(provider_config)
        elif model_name.startswith(("claude-")):
            for provider_config in config.providers:
                if provider_config.type == ProviderType.ANTHROPIC:
                    logger.warning(f"基于名称猜测模型 {model_name} 由Anthropic提供")
                    return cls.create_provider(provider_config)
        
        # 如果无法猜测，则使用默认提供者
        if config.default_provider:
            for provider_config in config.providers:
                if provider_config.type == config.default_provider:
                    logger.warning(f"未找到支持模型 {model_name} 的提供者，使用默认提供者")
                    return cls.create_provider(provider_config)
        
        # 如果实在找不到适合的提供者，则抛出异常
        raise LLMProviderNotFoundError(f"找不到支持模型 {model_name} 的提供者")
    
    @classmethod
    def reset_providers(cls) -> None:
        """重置所有提供者实例缓存
        
        用于在配置更改后刷新提供者实例
        """
        cls._provider_instances.clear()


# 为简便使用提供单例工厂实例
llm_provider_factory = LLMProviderFactory()
