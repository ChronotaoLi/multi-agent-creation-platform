"""
应用入口模块

配置FastAPI应用，注册路由、中间件、事件处理器和异常处理器。
"""
import logging
from typing import Callable

from fastapi import FastAPI, Request, Response, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.core.events import startup_event_handler, shutdown_event_handler
from app.core.logging_config import get_logger
from app.utils.idempotency import setup_idempotency_middleware
from app.utils.common_utils import generate_uuid
from app.api.v1.api import api_router as v1_router
from app.api.websockets import register_websocket_routes

# 获取应用配置和日志器
settings = get_settings()
logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求

        Args:
            request: 请求
            call_next: 下一个处理函数

        Returns:
            Response: 响应
        """
        # 生成请求ID
        request_id = request.headers.get("X-Request-ID") or generate_uuid()
        request.state.request_id = request_id
        
        # 记录请求日志
        logger.info(
            f"收到请求: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "client_ip": request.client.host,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
            },
        )
        
        # 处理请求
        response = await call_next(request)
        
        # 记录响应日志
        logger.info(
            f"发送响应: {response.status_code}",
            extra={
                "request_id": request_id,
                "status_code": response.status_code,
            },
        )
        
        # 添加请求ID到响应头
        response.headers["X-Request-ID"] = request_id
        
        return response


def create_app() -> FastAPI:
    """创建FastAPI应用实例

    Returns:
        FastAPI: FastAPI应用实例
    """
    app = FastAPI(
        title=settings.project_name,
        description="多智能体AI创作平台API",
        version="0.3.2",
        docs_url="/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )
    
    # 注册路由
    register_routers(app)
    
    # 注册中间件
    register_middleware(app)
    
    # 注册事件处理器
    register_event_handlers(app)
    
    # 注册异常处理器
    register_exception_handlers(app)
    
    return app


def register_routers(app: FastAPI) -> None:
    """注册API路由

    Args:
        app: FastAPI应用实例
    """
    # 注册 API v1 路由
    app.include_router(v1_router, prefix=settings.api_prefix)
    
    # 注册 WebSocket 路由
    register_websocket_routes(app)
    
    # 注册健康检查路由
    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}


def register_middleware(app: FastAPI) -> None:
    """注册中间件

    Args:
        app: FastAPI应用实例
    """
    # 注册CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 注册请求日志中间件
    app.add_middleware(RequestLoggingMiddleware)
    
    # 注册幂等性中间件
    if settings.redis_url:
        setup_idempotency_middleware(app, settings.redis_url)


def register_event_handlers(app: FastAPI) -> None:
    """注册事件处理器

    Args:
        app: FastAPI应用实例
    """
    app.add_event_handler("startup", startup_event_handler(app))
    app.add_event_handler("shutdown", shutdown_event_handler(app))


def register_exception_handlers(app: FastAPI) -> None:
    """注册异常处理器

    Args:
        app: FastAPI应用实例
    """
    from app.utils.error_handlers import setup_exception_handlers
    setup_exception_handlers(app)


app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    # 配置uvicorn日志级别
    log_level = "debug" if settings.debug else "info"
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=log_level,
    )
