"""
内容生成相关的异步任务模块

本模块实现与内容生成、转换、索引相关的异步任务。
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from celery import shared_task, Task
from pydantic import ValidationError

from app.core.celery_app import celery_app
from app.data_access.event_bus.event_models import ContentCreatedEvent, ContentUpdatedEvent
from app.data_access.event_bus.producers import EventProducer
from app.utils.common_utils import get_utc_now

logger = logging.getLogger(__name__)


class ContentTaskBase(Task):
    """内容任务基类，包含通用的任务处理逻辑"""
    
    _event_producer = None
    
    @property
    def event_producer(self):
        """懒加载事件生产者"""
        if self._event_producer is None:
            # 延迟导入，避免循环导入
            from app.data_access.cache.redis_client import get_redis_client
            from app.data_access.event_bus.redis_streams import RedisStreamsEventBus
            from app.data_access.event_bus.producers import ContentEventProducer
            
            # 创建事件总线
            redis_client = get_redis_client()
            event_bus = RedisStreamsEventBus(redis_client=redis_client)
            
            # 创建事件生产者
            self._event_producer = ContentEventProducer(event_bus=event_bus)
            
        return self._event_producer
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """任务失败处理"""
        logger.error(f"内容任务 {task_id} 失败: {exc}")
        
        # 获取内容ID和类型（如果可用）
        content_id = kwargs.get("content_id", None)
        content_type = kwargs.get("content_type", None)
        
        # 如果有内容ID，发布内容更新事件（状态为失败）
        if content_id and self.event_producer:
            # 构建更新数据
            update_data = {
                "status": "failed",
                "error_message": str(exc),
                "updated_at": get_utc_now().isoformat(),
            }
            
            # 发布内容更新事件
            self.event_producer.publish_content_updated_event(
                content_id=content_id,
                content_type=content_type,
                changes=update_data,
            )
            
        super().on_failure(exc, task_id, args, kwargs, einfo)


@celery_app.task(
    bind=True,
    base=ContentTaskBase,
    name="app.tasks.content_tasks.generate_text_content",
    max_retries=2,
    default_retry_delay=30,
)
def generate_text_content(
    self, 
    content_id: str, 
    content_type: str,
    prompt: str,
    project_id: str,
    parameters: Dict[str, Any] = None,
    max_tokens: int = 2000,
) -> Dict[str, Any]:
    """
    生成文本内容的异步任务
    
    参数:
        content_id: 内容ID
        content_type: 内容类型（如 article, script, caption等）
        prompt: 生成提示词
        project_id: 项目ID
        parameters: 生成参数（如温度、top_p等）
        max_tokens: 最大生成令牌数
        
    返回:
        生成的内容数据
    """
    try:
        logger.info(f"开始生成文本: content_id={content_id}, content_type={content_type}")
        
        # 准备默认参数
        if parameters is None:
            parameters = {
                "temperature": 0.7,
                "top_p": 0.9,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0,
            }
        
        # 记录任务开始
        self.event_producer.publish_content_updated_event(
            content_id=content_id,
            content_type=content_type,
            changes={"status": "generating", "started_at": get_utc_now().isoformat()},
            source="content_tasks.generate_text_content",
        )
        
        # 导入LLM适配器（延迟导入避免循环依赖）
        from app.data_access.llm_adapter.text_generator import TextGenerator
        
        # 创建文本生成器
        text_generator = TextGenerator()
        
        # 调用生成器生成文本
        generated_text = text_generator.generate_text(
            prompt=prompt,
            max_tokens=max_tokens,
            **parameters
        )
        
        # 准备结果数据
        result = {
            "content_id": content_id,
            "content_type": content_type,
            "text": generated_text,
            "metadata": {
                "prompt": prompt,
                "parameters": parameters,
                "generated_at": get_utc_now().isoformat(),
                "token_count": len(generated_text.split()),  # 简单估算
            },
            "status": "completed",
        }
        
        # 发布内容更新事件
        self.event_producer.publish_content_updated_event(
            content_id=content_id,
            content_type=content_type,
            changes=result,
            source="content_tasks.generate_text_content",
            project_id=project_id,
        )
        
        logger.info(f"文本生成完成: content_id={content_id}")
        return result
    
    except Exception as e:
        logger.exception(f"生成文本内容时出错: {str(e)}")
        # 重试任务
        self.retry(exc=e)


@celery_app.task(
    bind=True,
    base=ContentTaskBase,
    name="app.tasks.content_tasks.index_content",
    max_retries=3,
    default_retry_delay=60,
)
def index_content(
    self, 
    content_id: str, 
    content_type: str,
    text: str,
    metadata: Dict[str, Any],
    project_id: str,
) -> Dict[str, Any]:
    """
    索引内容的异步任务
    
    参数:
        content_id: 内容ID
        content_type: 内容类型
        text: 需要索引的文本内容
        metadata: 内容元数据
        project_id: 项目ID
        
    返回:
        索引结果
    """
    try:
        logger.info(f"开始索引内容: content_id={content_id}, content_type={content_type}")
        
        # 记录任务开始
        self.event_producer.publish_content_updated_event(
            content_id=content_id,
            content_type=content_type,
            changes={"index_status": "processing", "index_started_at": get_utc_now().isoformat()},
            source="content_tasks.index_content",
        )
        
        # 延迟导入，避免循环依赖
        from app.data_access.vector_store.content_index import ContentIndexService
        
        # 创建索引服务
        index_service = ContentIndexService()
        
        # 索引文本内容
        vector_id = index_service.index_text(
            text=text,
            content_id=content_id,
            content_type=content_type,
            metadata=metadata,
            project_id=project_id,
        )
        
        # 准备结果数据
        result = {
            "content_id": content_id,
            "vector_id": vector_id,
            "index_status": "completed",
            "index_completed_at": get_utc_now().isoformat(),
        }
        
        # 发布内容更新事件
        self.event_producer.publish_content_updated_event(
            content_id=content_id,
            content_type=content_type,
            changes=result,
            source="content_tasks.index_content",
            project_id=project_id,
        )
        
        logger.info(f"内容索引完成: content_id={content_id}, vector_id={vector_id}")
        return result
    
    except Exception as e:
        logger.exception(f"索引内容时出错: {str(e)}")
        # 更新索引状态
        self.event_producer.publish_content_updated_event(
            content_id=content_id,
            content_type=content_type,
            changes={"index_status": "failed", "index_error": str(e)},
            source="content_tasks.index_content",
        )
        # 重试任务
        self.retry(exc=e)


@celery_app.task(
    bind=True,
    base=ContentTaskBase,
    name="app.tasks.content_tasks.convert_content_format",
    max_retries=2,
)
def convert_content_format(
    self, 
    content_id: str, 
    source_format: str,
    target_format: str,
    content: str,
    metadata: Dict[str, Any] = None,
    project_id: str = None,
) -> Dict[str, Any]:
    """
    转换内容格式的异步任务
    
    参数:
        content_id: 内容ID
        source_format: 源格式（如 markdown, html, text）
        target_format: 目标格式
        content: 要转换的内容
        metadata: 内容元数据
        project_id: 项目ID
        
    返回:
        转换后的内容数据
    """
    try:
        logger.info(f"开始转换内容格式: content_id={content_id}, {source_format} -> {target_format}")
        
        if metadata is None:
            metadata = {}
        
        # 记录任务开始
        self.event_producer.publish_content_updated_event(
            content_id=content_id,
            content_type=f"{target_format}_content",
            changes={"conversion_status": "processing", "started_at": get_utc_now().isoformat()},
            source="content_tasks.convert_content_format",
        )
        
        # 延迟导入，避免循环依赖
        from app.services.content_service import ContentFormatConverter
        
        # 创建格式转换器
        converter = ContentFormatConverter()
        
        # 执行格式转换
        converted_content = converter.convert(
            content=content,
            source_format=source_format,
            target_format=target_format,
            metadata=metadata,
        )
        
        # 准备结果数据
        result = {
            "content_id": content_id,
            "source_format": source_format,
            "target_format": target_format,
            "converted_content": converted_content,
            "status": "completed",
            "completed_at": get_utc_now().isoformat(),
        }
        
        # 发布内容更新事件
        self.event_producer.publish_content_updated_event(
            content_id=content_id,
            content_type=f"{target_format}_content",
            changes=result,
            source="content_tasks.convert_content_format",
            project_id=project_id,
        )
        
        logger.info(f"内容格式转换完成: content_id={content_id}")
        return result
    
    except Exception as e:
        logger.exception(f"转换内容格式时出错: {str(e)}")
        # 更新转换状态
        self.event_producer.publish_content_updated_event(
            content_id=content_id,
            content_type=f"{target_format}_content",
            changes={"conversion_status": "failed", "error": str(e)},
            source="content_tasks.convert_content_format",
        )
        # 重试任务
        self.retry(exc=e)


@celery_app.task(
    bind=True,
    name="app.tasks.content_tasks.process_pending_content_index",
)
def process_pending_content_index(self) -> Dict[str, Any]:
    """
    处理待索引内容的定时任务
    
    此任务定期检查待索引的内容，并为其创建索引任务
    
    返回:
        处理结果
    """
    try:
        logger.info("开始处理待索引内容")
        
        # 延迟导入，避免循环依赖
        from app.services.content_service import ContentService
        
        # 创建内容服务
        content_service = ContentService()
        
        # 获取待索引内容
        pending_content = content_service.get_pending_index_content(limit=50)
        
        # 处理结果统计
        result = {
            "processed_count": 0,
            "error_count": 0,
            "skipped_count": 0,
            "details": [],
        }
        
        # 为每个内容创建索引任务
        for content_item in pending_content:
            try:
                content_id = content_item.get("id")
                content_type = content_item.get("type")
                text = content_item.get("text")
                metadata = content_item.get("metadata", {})
                project_id = content_item.get("project_id")
                
                if not all([content_id, content_type, text, project_id]):
                    logger.warning(f"跳过内容索引，缺少必要信息: {content_item}")
                    result["skipped_count"] += 1
                    result["details"].append({
                        "content_id": content_id,
                        "status": "skipped",
                        "reason": "缺少必要信息",
                    })
                    continue
                
                # 创建索引任务
                index_content.delay(
                    content_id=content_id,
                    content_type=content_type,
                    text=text,
                    metadata=metadata,
                    project_id=project_id,
                )
                
                # 更新内容索引状态
                content_service.update_content_status(
                    content_id=content_id,
                    updates={"index_status": "queued"}
                )
                
                result["processed_count"] += 1
                result["details"].append({
                    "content_id": content_id,
                    "status": "queued",
                })
                
            except Exception as e:
                logger.exception(f"处理内容索引时出错: {str(e)}")
                result["error_count"] += 1
                result["details"].append({
                    "content_id": content_item.get("id"),
                    "status": "error",
                    "error": str(e),
                })
        
        logger.info(f"待索引内容处理完成: {result['processed_count']} 已处理, {result['error_count']} 错误, {result['skipped_count']} 跳过")
        return result
    
    except Exception as e:
        logger.exception(f"处理待索引内容任务出错: {str(e)}")
        raise
