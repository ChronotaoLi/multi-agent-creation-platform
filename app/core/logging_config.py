"""
日志配置模块

配置应用日志系统，支持控制台和文件输出，以及JSON格式日志。
"""
import json
import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from typing import Dict, Optional, Any, List

from .config import get_settings

# 获取应用配置
settings = get_settings()


class JsonFormatter(logging.Formatter):
    """JSON格式日志格式化器"""
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # 添加请求ID（如果存在）
        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id
        
        # 添加额外字段
        if hasattr(record, "extras") and record.extras:
            log_record.update(record.extras)
        
        # 添加异常信息（如果存在）
        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)
        
        return json.dumps(log_record)


class RequestIdFilter(logging.Filter):
    """请求ID过滤器，用于添加请求ID到日志记录"""
    
    def __init__(self, request_id: Optional[str] = None):
        super().__init__()
        self.request_id = request_id
    
    def filter(self, record: logging.LogRecord) -> bool:
        """过滤日志记录，添加请求ID"""
        if not hasattr(record, "request_id") and self.request_id:
            record.request_id = self.request_id
        return True


def get_log_level(level_name: str) -> int:
    """获取日志级别"""
    return getattr(logging, level_name.upper(), logging.INFO)


def configure_logging() -> None:
    """配置应用日志系统"""
    log_level = get_log_level(settings.log_level)
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # 清除现有的处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 定义格式化器
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    simple_formatter = logging.Formatter(log_format)
    json_formatter = JsonFormatter()
    
    # 添加控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # 添加文件处理器（如果指定了日志目录）
    log_dir = os.environ.get("LOG_DIR", "logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # 按大小轮转的日志文件处理器
    log_file = os.path.join(log_dir, f"{settings.app_env}.log")
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10*1024*1024, backupCount=5
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(simple_formatter)
    root_logger.addHandler(file_handler)
    
    # 添加JSON格式日志文件处理器
    json_log_file = os.path.join(log_dir, f"{settings.app_env}_json.log")
    json_file_handler = TimedRotatingFileHandler(
        json_log_file, when="midnight", interval=1, backupCount=30
    )
    json_file_handler.setLevel(log_level)
    json_file_handler.setFormatter(json_formatter)
    json_file_handler.suffix = "%Y-%m-%d"
    root_logger.addHandler(json_file_handler)
    
    # 设置第三方库的日志级别
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    
    # 配置应用日志
    logger = logging.getLogger("app")
    logger.setLevel(log_level)
    
    # 记录启动日志
    logger.info(
        f"日志系统已配置，级别: {settings.log_level}, 环境: {settings.app_env}"
    )


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的日志器"""
    return logging.getLogger(name)


class LoggingMixin:
    """日志混入类，为类添加日志功能"""
    
    @property
    def logger(self) -> logging.Logger:
        """获取当前类的日志器"""
        return logging.getLogger(f"{self.__module__}.{self.__class__.__name__}")


def log_with_extras(
    logger: logging.Logger, level: str, message: str, extras: Dict[str, Any] = None
) -> None:
    """使用额外信息记录日志"""
    record_kwargs = {"extras": extras} if extras else {}
    level_no = getattr(logging, level.upper())
    logger.log(level_no, message, extra=record_kwargs)
