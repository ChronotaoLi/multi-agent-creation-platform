"""
错误处理模块

定义应用异常体系和处理器
"""
from typing import Dict, Any, Callable, Type

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError


class AppError(Exception):
    """应用基础异常
    
    所有应用异常的基类
    """
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "app_error"
    
    def __init__(self, message: str = "应用发生错误", details: Dict[str, Any] = None):
        """初始化应用异常
        
        Args:
            message: 错误消息
            details: 错误详情
        """
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class BusinessError(AppError):
    """业务逻辑异常基类
    
    业务相关的错误，通常不影响系统稳定性
    """
    status_code: int = status.HTTP_400_BAD_REQUEST
    error_code: str = "business_error"


class TechnicalError(AppError):
    """技术相关异常基类
    
    系统级错误，通常表示某个技术组件出问题
    """
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "technical_error"


# 业务异常
class InvalidInputError(BusinessError):
    """输入验证失败异常"""
    status_code: int = status.HTTP_400_BAD_REQUEST
    error_code: str = "invalid_input"


class ResourceNotFoundError(BusinessError):
    """资源未找到异常"""
    status_code: int = status.HTTP_404_NOT_FOUND
    error_code: str = "resource_not_found"


class PermissionDeniedError(BusinessError):
    """权限不足异常"""
    status_code: int = status.HTTP_403_FORBIDDEN
    error_code: str = "permission_denied"


class ResourceConflictError(BusinessError):
    """资源冲突异常"""
    status_code: int = status.HTTP_409_CONFLICT
    error_code: str = "resource_conflict"


class AuthenticationError(BusinessError):
    """认证失败异常"""
    status_code: int = status.HTTP_401_UNAUTHORIZED
    error_code: str = "authentication_error"


# 技术异常
class DatabaseConnectionError(TechnicalError):
    """数据库连接错误"""
    error_code: str = "database_connection_error"


class LLMServiceError(TechnicalError):
    """LLM服务错误"""
    error_code: str = "llm_service_error"


class VectorStoreError(TechnicalError):
    """向量存储错误"""
    error_code: str = "vector_store_error"


class GraphStoreError(TechnicalError):
    """图存储错误"""
    error_code: str = "graph_store_error"


class CacheError(TechnicalError):
    """缓存错误"""
    error_code: str = "cache_error"


class ConfigurationError(TechnicalError):
    """配置错误"""
    error_code: str = "configuration_error"


# 异常处理器
def setup_exception_handlers(app: FastAPI) -> None:
    """配置FastAPI异常处理器
    
    Args:
        app: FastAPI应用实例
    """
    app.add_exception_handler(BusinessError, handle_business_error)
    app.add_exception_handler(TechnicalError, handle_technical_error)
    app.add_exception_handler(ValidationError, handle_validation_error)
    app.add_exception_handler(Exception, handle_generic_error)


async def handle_business_error(request: Request, exc: BusinessError) -> JSONResponse:
    """处理业务异常
    
    Args:
        request: 请求对象
        exc: 业务异常
        
    Returns:
        JSONResponse: 格式化的错误响应
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details
            }
        }
    )


async def handle_technical_error(request: Request, exc: TechnicalError) -> JSONResponse:
    """处理技术异常
    
    Args:
        request: 请求对象
        exc: 技术异常
        
    Returns:
        JSONResponse: 格式化的错误响应
    """
    # 这里可以添加日志记录、告警等处理
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details
            }
        }
    )


async def handle_validation_error(request: Request, exc: ValidationError) -> JSONResponse:
    """处理验证异常
    
    Args:
        request: 请求对象
        exc: 验证异常
        
    Returns:
        JSONResponse: 格式化的错误响应
    """
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "validation_error",
                "message": "输入数据验证失败",
                "details": {
                    "errors": exc.errors()
                }
            }
        }
    )


async def handle_generic_error(request: Request, exc: Exception) -> JSONResponse:
    """处理通用异常
    
    Args:
        request: 请求对象
        exc: 通用异常
        
    Returns:
        JSONResponse: 格式化的错误响应
    """
    # 这里可以添加日志记录、告警等处理
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "internal_server_error",
                "message": "服务器内部错误",
                "details": {
                    "type": type(exc).__name__,
                    "message": str(exc)
                }
            }
        }
    )
