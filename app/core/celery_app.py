"""
Celery应用配置模块

本模块配置Celery应用实例，包括任务路由、队列、调度和中间件配置。
"""

import os
from datetime import timedelta
from pathlib import Path
from typing import Dict, List, Optional

from celery import Celery
from celery.schedules import crontab
from celery.signals import task_failure, task_postrun, task_prerun, worker_ready

from app.core.config import get_settings
from .logging_config import get_logger

# 获取应用配置和日志器
settings = get_settings()
logger = get_logger(__name__)

# 创建Celery应用实例
celery_app = Celery(
    "multi_agent_creation_platform",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# 配置任务模块自动发现
celery_app.autodiscover_tasks(
    [
        "app.tasks.content_tasks",
        "app.tasks.analysis_tasks",
        "app.tasks.notification_tasks",
        "app.tasks.maintenance_tasks",
    ]
)

# 基本配置
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.TIMEZONE,
    enable_utc=True,
    worker_prefetch_multiplier=1,  # 减少预取任务数，避免任务分配不均
)

# 任务过期时间
celery_app.conf.task_acks_late = True  # 任务完成后才确认（对于重要任务）
celery_app.conf.task_time_limit = settings.CELERY_TASK_TIME_LIMIT  # 任务超时时间（秒）
celery_app.conf.task_soft_time_limit = settings.CELERY_TASK_SOFT_TIME_LIMIT  # 软超时（发送信号）

# 任务重试设置
celery_app.conf.task_acks_on_failure_or_timeout = False  # 任务失败或超时不自动确认
celery_app.conf.task_reject_on_worker_lost = True  # 如果worker挂了，任务自动放回队列

# 结果存储设置
celery_app.conf.result_expires = 60 * 60 * 24 * 7  # 结果保存7天

# 定义任务队列
task_queues = {
    "default": {"exchange": "default", "routing_key": "default"},
    "content": {"exchange": "content", "routing_key": "content.#"},
    "analysis": {"exchange": "analysis", "routing_key": "analysis.#"},
    "notifications": {"exchange": "notifications", "routing_key": "notifications.#"},
    "maintenance": {"exchange": "maintenance", "routing_key": "maintenance.#"},
}

# 配置队列
celery_app.conf.task_queues = list(task_queues.values())

# 任务路由配置
celery_app.conf.task_routes = {
    # 内容生成任务
    "app.tasks.content_tasks.*": {"queue": "content"},
    # 分析任务
    "app.tasks.analysis_tasks.*": {"queue": "analysis"},
    # 通知任务
    "app.tasks.notification_tasks.*": {"queue": "notifications"},
    # 维护任务
    "app.tasks.maintenance_tasks.*": {"queue": "maintenance"},
}

# 配置定时任务
celery_app.conf.beat_schedule = {
    "cleanup_expired_sessions": {
        "task": "app.tasks.maintenance_tasks.cleanup_expired_sessions",
        "schedule": timedelta(hours=6),
        "options": {"queue": "maintenance"},
    },
    "health_check": {
        "task": "app.tasks.maintenance_tasks.system_health_check",
        "schedule": timedelta(minutes=30),
        "options": {"queue": "maintenance"},
    },
    "process_pending_content_index": {
        "task": "app.tasks.content_tasks.process_pending_content_index",
        "schedule": timedelta(minutes=10),
        "options": {"queue": "content"},
    },
    "cleanup_temporary_files": {
        "task": "app.tasks.maintenance_tasks.cleanup_temporary_files",
        "schedule": crontab(hour="3", minute="0"),  # 每天凌晨3点执行
        "options": {"queue": "maintenance"},
    },
}


@task_prerun.connect
def task_prerun_handler(task_id, task, *args, **kwargs):
    """任务开始前的处理"""
    task.logger.info(f"Task {task.name}[{task_id}] started")


@task_postrun.connect
def task_postrun_handler(task_id, task, retval, state, *args, **kwargs):
    """任务结束后的处理"""
    task.logger.info(f"Task {task.name}[{task_id}] finished with state {state}")


@task_failure.connect
def task_failure_handler(task_id, exception, traceback, einfo, *args, **kwargs):
    """任务失败的处理"""
    # 可以在这里添加监控告警逻辑
    task = kwargs.get("sender")
    task_name = task.name if task else "Unknown"
    print(f"Task {task_name}[{task_id}] failed: {exception}")


@worker_ready.connect
def worker_ready_handler(sender, **kwargs):
    """Worker 启动时的处理"""
    print(f"Worker {sender.hostname} is ready.")


@celery_app.task(bind=True)
def debug_task(self):
    """用于调试的Celery任务"""
    logger.info(f"Request: {self.request!r}")
    return {"status": "success", "task_id": self.request.id}
