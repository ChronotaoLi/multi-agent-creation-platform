"""
分析相关的异步任务模块

本模块实现内容分析、文本分析、相似度分析等异步任务。
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from celery import Task

from app.core.celery_app import celery_app
from app.data_access.event_bus.producers import EventProducer
from app.utils.common_utils import get_utc_now

logger = logging.getLogger(__name__)


class AnalysisTaskBase(Task):
    """分析任务基类，包含通用的任务处理逻辑"""
    
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
        logger.error(f"分析任务 {task_id} 失败: {exc}")
        
        # 获取分析ID和类型（如果可用）
        analysis_id = kwargs.get("analysis_id", None)
        analysis_type = kwargs.get("analysis_type", None)
        content_id = kwargs.get("content_id", None)
        
        # 如果有内容ID，发布内容更新事件（分析状态为失败）
        if content_id and self.event_producer:
            # 构建更新数据
            update_data = {
                f"{analysis_type}_analysis_status": "failed",
                f"{analysis_type}_analysis_error": str(exc),
                "updated_at": get_utc_now().isoformat(),
            }
            
            # 发布内容更新事件
            self.event_producer.publish_content_updated_event(
                content_id=content_id,
                content_type="any",  # 实际类型在服务层处理
                changes=update_data,
            )
            
        super().on_failure(exc, task_id, args, kwargs, einfo)


@celery_app.task(
    bind=True,
    base=AnalysisTaskBase,
    name="app.tasks.analysis_tasks.analyze_text_sentiment",
    max_retries=2,
    default_retry_delay=30,
)
def analyze_text_sentiment(
    self, 
    content_id: str, 
    text: str,
    analysis_id: str,
    project_id: str = None,
    language: str = "zh",
) -> Dict[str, Any]:
    """
    分析文本情感的异步任务
    
    参数:
        content_id: 内容ID
        text: 要分析的文本内容
        analysis_id: 分析任务ID
        project_id: 项目ID
        language: 文本语言
        
    返回:
        情感分析结果
    """
    try:
        logger.info(f"开始情感分析: content_id={content_id}, analysis_id={analysis_id}")
        
        # 记录任务开始
        self.event_producer.publish_content_updated_event(
            content_id=content_id,
            content_type="text",
            changes={"sentiment_analysis_status": "processing", "analysis_started_at": get_utc_now().isoformat()},
            source="analysis_tasks.analyze_text_sentiment",
        )
        
        # 延迟导入，避免循环依赖
        from app.services.analysis_service import TextAnalysisService
        
        # 创建文本分析服务
        analysis_service = TextAnalysisService()
        
        # 进行情感分析
        sentiment_result = analysis_service.analyze_sentiment(
            text=text,
            language=language,
        )
        
        # 准备分析结果
        result = {
            "content_id": content_id,
            "analysis_id": analysis_id,
            "analysis_type": "sentiment",
            "result": sentiment_result,
            "language": language,
            "status": "completed",
            "completed_at": get_utc_now().isoformat(),
        }
        
        # 发布分析结果更新事件
        self.event_producer.publish_content_updated_event(
            content_id=content_id,
            content_type="text",
            changes={
                "sentiment_analysis": sentiment_result,
                "sentiment_analysis_status": "completed",
            },
            source="analysis_tasks.analyze_text_sentiment",
            project_id=project_id,
        )
        
        logger.info(f"情感分析完成: content_id={content_id}, analysis_id={analysis_id}")
        return result
    
    except Exception as e:
        logger.exception(f"情感分析时出错: {str(e)}")
        # 重试任务
        self.retry(exc=e)


@celery_app.task(
    bind=True,
    base=AnalysisTaskBase,
    name="app.tasks.analysis_tasks.extract_text_keywords",
    max_retries=2,
    default_retry_delay=30,
)
def extract_text_keywords(
    self, 
    content_id: str, 
    text: str,
    analysis_id: str,
    project_id: str = None,
    language: str = "zh",
    max_keywords: int = 10,
) -> Dict[str, Any]:
    """
    提取文本关键词的异步任务
    
    参数:
        content_id: 内容ID
        text: 要分析的文本内容
        analysis_id: 分析任务ID
        project_id: 项目ID
        language: 文本语言
        max_keywords: 最大关键词数量
        
    返回:
        关键词提取结果
    """
    try:
        logger.info(f"开始关键词提取: content_id={content_id}, analysis_id={analysis_id}")
        
        # 记录任务开始
        self.event_producer.publish_content_updated_event(
            content_id=content_id,
            content_type="text",
            changes={"keywords_extraction_status": "processing", "analysis_started_at": get_utc_now().isoformat()},
            source="analysis_tasks.extract_text_keywords",
        )
        
        # 延迟导入，避免循环依赖
        from app.services.analysis_service import TextAnalysisService
        
        # 创建文本分析服务
        analysis_service = TextAnalysisService()
        
        # 提取关键词
        keywords = analysis_service.extract_keywords(
            text=text,
            language=language,
            max_keywords=max_keywords,
        )
        
        # 准备分析结果
        result = {
            "content_id": content_id,
            "analysis_id": analysis_id,
            "analysis_type": "keywords",
            "keywords": keywords,
            "language": language,
            "status": "completed",
            "completed_at": get_utc_now().isoformat(),
        }
        
        # 发布分析结果更新事件
        self.event_producer.publish_content_updated_event(
            content_id=content_id,
            content_type="text",
            changes={
                "keywords": keywords,
                "keywords_extraction_status": "completed",
            },
            source="analysis_tasks.extract_text_keywords",
            project_id=project_id,
        )
        
        logger.info(f"关键词提取完成: content_id={content_id}, analysis_id={analysis_id}, keywords_count={len(keywords)}")
        return result
    
    except Exception as e:
        logger.exception(f"关键词提取时出错: {str(e)}")
        # 重试任务
        self.retry(exc=e)


@celery_app.task(
    bind=True,
    base=AnalysisTaskBase,
    name="app.tasks.analysis_tasks.analyze_text_similarity",
    max_retries=2,
    default_retry_delay=30,
)
def analyze_text_similarity(
    self, 
    content_id: str, 
    text1: str,
    text2: str,
    analysis_id: str,
    project_id: str = None,
) -> Dict[str, Any]:
    """
    分析文本相似度的异步任务
    
    参数:
        content_id: 内容ID
        text1: 第一个文本
        text2: 第二个文本
        analysis_id: 分析任务ID
        project_id: 项目ID
        
    返回:
        文本相似度分析结果
    """
    try:
        logger.info(f"开始文本相似度分析: content_id={content_id}, analysis_id={analysis_id}")
        
        # 记录任务开始
        self.event_producer.publish_content_updated_event(
            content_id=content_id,
            content_type="text",
            changes={"similarity_analysis_status": "processing", "analysis_started_at": get_utc_now().isoformat()},
            source="analysis_tasks.analyze_text_similarity",
        )
        
        # 延迟导入，避免循环依赖
        from app.services.analysis_service import TextAnalysisService
        
        # 创建文本分析服务
        analysis_service = TextAnalysisService()
        
        # 计算文本相似度
        similarity_result = analysis_service.compute_similarity(
            text1=text1,
            text2=text2,
        )
        
        # 准备分析结果
        result = {
            "content_id": content_id,
            "analysis_id": analysis_id,
            "analysis_type": "similarity",
            "similarity_score": similarity_result["score"],
            "similarity_details": similarity_result.get("details", {}),
            "status": "completed",
            "completed_at": get_utc_now().isoformat(),
        }
        
        # 发布分析结果更新事件
        self.event_producer.publish_content_updated_event(
            content_id=content_id,
            content_type="text",
            changes={
                "similarity_analysis": result,
                "similarity_analysis_status": "completed",
            },
            source="analysis_tasks.analyze_text_similarity",
            project_id=project_id,
        )
        
        logger.info(f"文本相似度分析完成: content_id={content_id}, analysis_id={analysis_id}, score={similarity_result['score']}")
        return result
    
    except Exception as e:
        logger.exception(f"文本相似度分析时出错: {str(e)}")
        # 重试任务
        self.retry(exc=e)


@celery_app.task(
    bind=True,
    base=AnalysisTaskBase,
    name="app.tasks.analysis_tasks.analyze_content_quality",
    max_retries=2,
    default_retry_delay=30,
)
def analyze_content_quality(
    self, 
    content_id: str, 
    text: str,
    content_type: str,
    analysis_id: str,
    project_id: str = None,
    quality_criteria: List[str] = None,
) -> Dict[str, Any]:
    """
    分析内容质量的异步任务
    
    参数:
        content_id: 内容ID
        text: 要分析的文本内容
        content_type: 内容类型
        analysis_id: 分析任务ID
        project_id: 项目ID
        quality_criteria: 质量评价标准列表
        
    返回:
        内容质量分析结果
    """
    try:
        logger.info(f"开始内容质量分析: content_id={content_id}, analysis_id={analysis_id}, content_type={content_type}")
        
        # 设置默认质量评价标准
        if quality_criteria is None:
            quality_criteria = [
                "grammar_correctness",  # 语法正确性
                "coherence",            # 连贯性
                "readability",          # 可读性
                "originality",          # 原创性
                "logical_flow",         # 逻辑流畅度
            ]
            
            # 根据内容类型添加特定标准
            if content_type == "article":
                quality_criteria.extend([
                    "argument_strength",    # 论证力度
                    "fact_accuracy",        # 事实准确性
                ])
            elif content_type == "creative_writing":
                quality_criteria.extend([
                    "creativity",           # 创造性
                    "character_development", # 角色发展
                    "narrative_structure",  # 叙事结构
                ])
        
        # 记录任务开始
        self.event_producer.publish_content_updated_event(
            content_id=content_id,
            content_type=content_type,
            changes={"quality_analysis_status": "processing", "analysis_started_at": get_utc_now().isoformat()},
            source="analysis_tasks.analyze_content_quality",
        )
        
        # 延迟导入，避免循环依赖
        from app.services.analysis_service import ContentQualityAnalyzer
        
        # 创建内容质量分析器
        analyzer = ContentQualityAnalyzer()
        
        # 分析内容质量
        quality_result = analyzer.analyze_quality(
            text=text,
            content_type=content_type,
            criteria=quality_criteria,
        )
        
        # 准备分析结果
        result = {
            "content_id": content_id,
            "analysis_id": analysis_id,
            "analysis_type": "quality",
            "content_type": content_type,
            "scores": quality_result["scores"],
            "overall_score": quality_result["overall_score"],
            "suggestions": quality_result.get("suggestions", []),
            "status": "completed",
            "completed_at": get_utc_now().isoformat(),
        }
        
        # 发布分析结果更新事件
        self.event_producer.publish_content_updated_event(
            content_id=content_id,
            content_type=content_type,
            changes={
                "quality_analysis": result,
                "quality_analysis_status": "completed",
            },
            source="analysis_tasks.analyze_content_quality",
            project_id=project_id,
        )
        
        logger.info(f"内容质量分析完成: content_id={content_id}, analysis_id={analysis_id}, overall_score={quality_result['overall_score']}")
        return result
    
    except Exception as e:
        logger.exception(f"内容质量分析时出错: {str(e)}")
        # 重试任务
        self.retry(exc=e)


@celery_app.task(
    bind=True,
    base=AnalysisTaskBase,
    name="app.tasks.analysis_tasks.find_similar_content",
    max_retries=2,
    default_retry_delay=30,
)
def find_similar_content(
    self, 
    content_id: str, 
    text: str,
    project_id: str,
    top_k: int = 5,
    min_similarity: float = 0.7,
) -> Dict[str, Any]:
    """
    查找相似内容的异步任务
    
    参数:
        content_id: 内容ID
        text: 要查找相似内容的文本
        project_id: 项目ID
        top_k: 返回最相似的结果数量
        min_similarity: 最小相似度阈值
        
    返回:
        相似内容查找结果
    """
    try:
        logger.info(f"开始查找相似内容: content_id={content_id}, project_id={project_id}")
        
        # 延迟导入，避免循环依赖
        from app.data_access.vector_store.content_index import ContentIndexService
        
        # 创建索引服务
        index_service = ContentIndexService()
        
        # 查找相似内容
        similar_results = index_service.search_similar(
            text=text,
            project_id=project_id,
            limit=top_k,
            min_score=min_similarity,
            exclude_ids=[content_id]  # 排除自身
        )
        
        # 准备结果数据
        result = {
            "content_id": content_id,
            "project_id": project_id,
            "similar_content": similar_results,
            "count": len(similar_results),
            "completed_at": get_utc_now().isoformat(),
        }
        
        # 发布分析结果更新事件（可选）
        if similar_results:
            self.event_producer.publish_content_updated_event(
                content_id=content_id,
                content_type="any",
                changes={
                    "similar_content": similar_results,
                    "similar_content_found_at": get_utc_now().isoformat(),
                },
                source="analysis_tasks.find_similar_content",
                project_id=project_id,
            )
        
        logger.info(f"相似内容查找完成: content_id={content_id}, found={len(similar_results)}")
        return result
    
    except Exception as e:
        logger.exception(f"查找相似内容时出错: {str(e)}")
        # 重试任务
        self.retry(exc=e)
