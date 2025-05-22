"""
LLM服务异常模块

定义LLM服务相关的异常类
"""
from typing import Dict, Any, Optional

from app.utils.error_handlers import TechnicalError


class LLMBaseError(TechnicalError):
    """LLM基础异常"""
    error_code = "llm_error"
    
    def __init__(self, message: str = "LLM服务错误", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)


class LLMConfigError(LLMBaseError):
    """LLM配置错误"""
    error_code = "llm_config_error"
    
    def __init__(self, message: str = "LLM配置错误", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)


class LLMProviderNotFoundError(LLMBaseError):
    """找不到LLM提供者"""
    error_code = "llm_provider_not_found"
    
    def __init__(self, message: str = "找不到LLM提供者", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)


class LLMServiceError(LLMBaseError):
    """LLM服务调用错误"""
    error_code = "llm_service_error"
    
    def __init__(self, message: str = "LLM服务调用错误", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)


class LLMRateLimitError(LLMServiceError):
    """LLM服务请求限制错误"""
    error_code = "llm_rate_limit"
    
    def __init__(self, message: str = "LLM服务请求频率超限", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)


class LLMAuthenticationError(LLMServiceError):
    """LLM服务认证错误"""
    error_code = "llm_authentication_error"
    
    def __init__(self, message: str = "LLM服务认证错误", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)


class LLMContextLengthError(LLMServiceError):
    """LLM上下文长度错误"""
    error_code = "llm_context_length_error"
    
    def __init__(self, message: str = "LLM上下文长度超限", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)


class LLMInvalidArgumentError(LLMServiceError):
    """LLM参数错误"""
    error_code = "llm_invalid_argument"
    
    def __init__(self, message: str = "LLM参数错误", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)


class LLMTimeoutError(LLMServiceError):
    """LLM服务超时错误"""
    error_code = "llm_timeout"
    
    def __init__(self, message: str = "LLM服务请求超时", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details) 