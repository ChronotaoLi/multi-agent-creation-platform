"""
知识源管理与集成增强版

管理多种知识来源并实现高级集成功能
"""

import logging
import asyncio
import json
import uuid
from typing import Dict, List, Optional, Any, Union, Callable, Tuple, Set
from datetime import datetime

from app.knowledge_management.hybrid_knowledge import HybridKnowledgeManager
from app.data_access.vector_store.embeddings import EmbeddingService
from app.data_access.event_bus.redis_streams import RedisStreamsEventBus
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class SchemaRegistry:
    """
    模式注册表
    
    负责管理和验证知识源模式
    """
    
    def __init__(self):
        """
        初始化模式注册表
        """
        self.schemas = {}
        
    def register_schema(self, schema: Dict[str, Any], namespace: str = "default") -> None:
        """
        注册知识模式
        
        参数:
            schema: Dict[str, Any] - 模式定义
            namespace: str - 模式命名空间
        """
        self.schemas[namespace] = schema
        logger.info(f"已注册模式: {namespace}")
    
    def get_schema(self, namespace: str = "default") -> Optional[Dict[str, Any]]:
        """
        获取知识模式
        
        参数:
            namespace: str - 模式命名空间
            
        返回:
            Optional[Dict[str, Any]] - 模式定义或None
        """
        return self.schemas.get(namespace)
    
    def validate(self, data: Dict[str, Any], namespace: str = "default") -> Tuple[bool, List[str]]:
        """
        验证数据是否符合模式
        
        参数:
            data: Dict[str, Any] - 要验证的数据
            namespace: str - 模式命名空间
            
        返回:
            Tuple[bool, List[str]] - (是否有效, 错误消息列表)
        """
        schema = self.get_schema(namespace)
        if not schema:
            return False, [f"未找到模式: {namespace}"]
        
        errors = []
        
        # 简单的模式验证实现
        # 在实际应用中可能需要使用JSON Schema验证库
        if "required_fields" in schema:
            for field in schema["required_fields"]:
                if field not in data:
                    errors.append(f"缺少必填字段: {field}")
        
        if "field_types" in schema:
            for field, expected_type in schema["field_types"].items():
                if field in data:
                    # 简单类型检查
                    if expected_type == "string" and not isinstance(data[field], str):
                        errors.append(f"字段 {field} 应为字符串类型")
                    elif expected_type == "number" and not isinstance(data[field], (int, float)):
                        errors.append(f"字段 {field} 应为数字类型")
                    elif expected_type == "array" and not isinstance(data[field], list):
                        errors.append(f"字段 {field} 应为数组类型")
                    elif expected_type == "object" and not isinstance(data[field], dict):
                        errors.append(f"字段 {field} 应为对象类型")
        
        return len(errors) == 0, errors

class EnhancedSourceManager:
    """
    增强版知识源管理器
    
    管理多种知识来源并实现高级集成功能
    """
    
    def __init__(
        self,
        hybrid_knowledge: HybridKnowledgeManager,
        embedding_service: EmbeddingService,
        event_producer: Optional[RedisStreamsEventBus] = None,
        batch_size: int = 100
    ):
        """
        初始化增强版知识源管理器
        
        参数:
            hybrid_knowledge: HybridKnowledgeManager - 混合知识模型
            embedding_service: EmbeddingService - 嵌入服务
            event_producer: Optional[RedisStreamsEventBus] - 事件生产者
            batch_size: int - 批处理大小
        """
        self.hybrid_knowledge = hybrid_knowledge
        self.embedding_service = embedding_service
        self.event_producer = event_producer
        self.batch_size = batch_size
        
        # 内容处理器字典
        self.processors = {}
        
        # 模式注册表
        self.schema_registry = SchemaRegistry()
        
        # 提取管道
        self.extraction_pipelines = {}
        
        # 源跟踪
        self.source_tracking = {}
        
    def register_processor(self, content_type: str, processor: Callable) -> None:
        """
        注册内容处理器
        
        参数:
            content_type: str - 内容类型
            processor: Callable - 处理器函数
        """
        self.processors[content_type] = processor
        logger.info(f"已注册处理器: {content_type}")
    
    def register_schema(self, schema: Dict[str, Any], namespace: str = "default") -> None:
        """
        注册知识模式
        
        参数:
            schema: Dict[str, Any] - 模式定义
            namespace: str - 模式命名空间
        """
        self.schema_registry.register_schema(schema, namespace)
    
    def register_pipeline(self, pipeline_type: str, pipeline: Callable) -> None:
        """
        注册提取管道
        
        参数:
            pipeline_type: str - 管道类型
            pipeline: Callable - 管道函数
        """
        self.extraction_pipelines[pipeline_type] = pipeline
        logger.info(f"已注册提取管道: {pipeline_type}")
    
    async def add_source(self, source_data: Dict[str, Any], schema_namespace: str = "default") -> str:
        """
        添加知识来源
        
        参数:
            source_data: Dict[str, Any] - 源数据
            schema_namespace: str - 模式命名空间
            
        返回:
            str - 源ID
        """
        # 验证源数据
        is_valid, errors = self.validate_source_against_schema(source_data, schema_namespace)
        if not is_valid:
            error_msg = f"源数据验证失败: {', '.join(errors)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # 确保源有唯一ID
        if "id" not in source_data:
            source_data["id"] = str(uuid.uuid4())
        source_id = source_data["id"]
        
        # 提取内容和元数据
        content = source_data.get("content", "")
        metadata = source_data.get("metadata", {})
        
        # 添加时间戳
        if "created_at" not in metadata:
            metadata["created_at"] = datetime.now().isoformat()
        metadata["updated_at"] = datetime.now().isoformat()
        
        # 设置处理状态
        metadata["processing_status"] = "pending"
        source_data["metadata"] = metadata
        
        # 存储源数据
        await self.hybrid_knowledge.add_knowledge(
            content=content,
            metadata=metadata,
            id=source_id
        )
        
        # 更新源跟踪
        self.source_tracking[source_id] = {
            "status": "added",
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata
        }
        
        # 发布事件
        if self.event_producer:
            event_data = {
                "event_type": "source_added",
                "source_id": source_id,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata
            }
            await self.event_producer.publish("source_events", event_data)
        
        return source_id
    
    async def process_source(self, source_id: str, pipeline_type: str = None) -> List[str]:
        """
        处理知识来源
        
        参数:
            source_id: str - 源ID
            pipeline_type: str - 管道类型
            
        返回:
            List[str] - 生成的实体ID列表
        """
        # 获取源数据
        source_data = await self.hybrid_knowledge.get_by_id(source_id)
        if not source_data:
            logger.error(f"未找到源: {source_id}")
            return []
        
        # 选择管道
        if pipeline_type and pipeline_type in self.extraction_pipelines:
            pipeline = self.extraction_pipelines[pipeline_type]
        elif self.extraction_pipelines:
            # 使用默认管道（第一个注册的）
            pipeline_type = next(iter(self.extraction_pipelines))
            pipeline = self.extraction_pipelines[pipeline_type]
        else:
            logger.error("未注册提取管道")
            return []
        
        # 更新处理状态
        await self._update_source_metadata(source_id, {"processing_status": "processing"})
        
        # 创建处理任务
        task_id = self._create_processing_task(source_id, pipeline_type)
        
        generated_entities = []
        errors = []
        
        try:
            # 执行管道
            content = source_data.get("content", "")
            metadata = source_data.get("metadata", {})
            
            pipeline_result = await pipeline(content, metadata)
            
            # 处理提取的实体
            if isinstance(pipeline_result, list):
                for entity in pipeline_result:
                    entity_id = entity.get("id", str(uuid.uuid4()))
                    
                    # 添加实体源信息
                    if "metadata" not in entity:
                        entity["metadata"] = {}
                    
                    entity["metadata"]["source_id"] = source_id
                    entity["metadata"]["extraction_pipeline"] = pipeline_type
                    entity["metadata"]["extracted_at"] = datetime.now().isoformat()
                    
                    # 将提取的实体添加到知识库
                    await self.hybrid_knowledge.add_knowledge(
                        content=entity.get("content", ""),
                        metadata=entity.get("metadata", {}),
                        id=entity_id
                    )
                    
                    generated_entities.append(entity_id)
            
            # 更新源处理状态
            await self._update_source_metadata(
                source_id,
                {
                    "processing_status": "completed",
                    "processed_at": datetime.now().isoformat(),
                    "pipeline_type": pipeline_type,
                    "generated_entities": generated_entities
                }
            )
            
        except Exception as e:
            error_msg = f"处理源 {source_id} 时出错: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
            
            # 更新错误状态
            await self._update_source_metadata(
                source_id,
                {
                    "processing_status": "error",
                    "error_message": str(e),
                    "error_timestamp": datetime.now().isoformat()
                }
            )
        
        # 更新任务状态
        task_status = "completed" if not errors else "failed"
        task_update = {
            "status": task_status,
            "completion_time": datetime.now().isoformat(),
            "generated_entities": generated_entities,
            "errors": errors
        }
        
        # 在实际应用中，这里可能需要更新任务存储
        logger.info(f"任务 {task_id} {task_status}: 生成了 {len(generated_entities)} 个实体")
        
        return generated_entities
    
    async def update_source(self, source_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新知识来源
        
        参数:
            source_id: str - 源ID
            updates: Dict[str, Any] - 更新内容
            
        返回:
            Dict[str, Any] - 更新后的源数据
        """
        # 获取源数据
        source_data = await self.hybrid_knowledge.get_by_id(source_id)
        if not source_data:
            logger.error(f"未找到源: {source_id}")
            raise ValueError(f"未找到源: {source_id}")
        
        # 更新元数据
        metadata = source_data.get("metadata", {})
        if "metadata" in updates:
            metadata.update(updates["metadata"])
            updates["metadata"] = metadata
        
        # 更新更新时间
        if "metadata" not in updates:
            updates["metadata"] = {}
        updates["metadata"]["updated_at"] = datetime.now().isoformat()
        
        # 更新内容（如果有）
        if "content" in updates:
            content = updates["content"]
            
            # 如果内容类型有变化且有对应的处理器，预处理内容
            if "content_type" in updates.get("metadata", {}) and updates["metadata"]["content_type"] in self.processors:
                processor = self.processors[updates["metadata"]["content_type"]]
                content = await processor(content)
            
            updates["content"] = content
        
        # 更新源数据
        updated_data = await self.hybrid_knowledge.update_knowledge(source_id, updates)
        
        # 更新源跟踪
        self.source_tracking[source_id] = {
            "status": "updated",
            "timestamp": datetime.now().isoformat(),
            "metadata": updated_data.get("metadata", {})
        }
        
        # 发布事件
        if self.event_producer:
            event_data = {
                "event_type": "source_updated",
                "source_id": source_id,
                "timestamp": datetime.now().isoformat(),
                "metadata": updated_data.get("metadata", {})
            }
            await self.event_producer.publish("source_events", event_data)
        
        return updated_data
    
    async def delete_source(self, source_id: str) -> None:
        """
        删除知识来源
        
        参数:
            source_id: str - 源ID
        """
        # 获取源数据
        source_data = await self.hybrid_knowledge.get_by_id(source_id)
        if not source_data:
            logger.error(f"未找到源: {source_id}")
            return
        
        # 删除源
        await self.hybrid_knowledge.delete_knowledge(source_id)
        
        # 更新源跟踪
        if source_id in self.source_tracking:
            self.source_tracking[source_id] = {
                "status": "deleted",
                "timestamp": datetime.now().isoformat()
            }
        
        # 发布事件
        if self.event_producer:
            event_data = {
                "event_type": "source_deleted",
                "source_id": source_id,
                "timestamp": datetime.now().isoformat()
            }
            await self.event_producer.publish("source_events", event_data)
        
        logger.info(f"已删除源: {source_id}")
    
    async def get_source_status(self, source_id: str) -> Dict[str, Any]:
        """
        获取源状态
        
        参数:
            source_id: str - 源ID
            
        返回:
            Dict[str, Any] - 源状态
        """
        # 获取源数据
        source_data = await self.hybrid_knowledge.get_by_id(source_id)
        if not source_data:
            logger.error(f"未找到源: {source_id}")
            return {"status": "not_found", "source_id": source_id}
        
        # 获取元数据
        metadata = source_data.get("metadata", {})
        
        # 构建状态信息
        status_info = {
            "source_id": source_id,
            "status": metadata.get("processing_status", "unknown"),
            "created_at": metadata.get("created_at"),
            "updated_at": metadata.get("updated_at"),
            "processed_at": metadata.get("processed_at"),
            "pipeline_type": metadata.get("pipeline_type"),
            "error_message": metadata.get("error_message"),
            "generated_entities_count": len(metadata.get("generated_entities", [])),
            "content_type": metadata.get("content_type")
        }
        
        # 添加跟踪信息
        if source_id in self.source_tracking:
            status_info["tracking"] = self.source_tracking[source_id]
        
        return status_info
    
    async def get_source_lineage(self, entity_id: str) -> List[Dict[str, Any]]:
        """
        获取实体血统
        
        参数:
            entity_id: str - 实体ID
            
        返回:
            List[Dict[str, Any]] - 血统信息
        """
        # 获取实体数据
        entity_data = await self.hybrid_knowledge.get_by_id(entity_id)
        if not entity_data:
            logger.error(f"未找到实体: {entity_id}")
            return []
        
        lineage = []
        metadata = entity_data.get("metadata", {})
        
        # 如果有源ID，查找源
        source_id = metadata.get("source_id")
        if source_id:
            # 获取源数据
            source_data = await self.hybrid_knowledge.get_by_id(source_id)
            if source_data:
                source_metadata = source_data.get("metadata", {})
                
                # 添加源信息
                lineage.append({
                    "id": source_id,
                    "type": "source",
                    "content_type": source_metadata.get("content_type"),
                    "created_at": source_metadata.get("created_at"),
                    "title": source_metadata.get("title"),
                    "relation": "derived_from"
                })
                
                # 如果有上游血统，递归查找
                if "source_id" in source_metadata:
                    upstream_lineage = await self.get_source_lineage(source_id)
                    lineage.extend(upstream_lineage)
        
        # 查找从此实体派生的实体
        derived_entities = await self.hybrid_knowledge.search(
            filters={"metadata.source_id": entity_id},
            limit=100
        )
        
        for derived in derived_entities:
            derived_id = derived.get("id")
            derived_metadata = derived.get("metadata", {})
            
            lineage.append({
                "id": derived_id,
                "type": "entity",
                "content_type": derived_metadata.get("content_type"),
                "created_at": derived_metadata.get("created_at"),
                "title": derived_metadata.get("title"),
                "relation": "derives"
            })
        
        return lineage
    
    async def reprocess_sources(self, source_ids: List[str] = None, pipeline_type: str = None) -> Dict[str, Any]:
        """
        重新处理源
        
        参数:
            source_ids: List[str] - 源ID列表
            pipeline_type: str - 管道类型
            
        返回:
            Dict[str, Any] - 处理结果
        """
        if not source_ids:
            # 如果未提供源ID，获取所有未处理或处理失败的源
            all_sources = await self.hybrid_knowledge.search(
                filters={"metadata.processing_status": {"$in": ["pending", "error"]}},
                limit=1000
            )
            source_ids = [source.get("id") for source in all_sources]
        
        # 批量处理
        return await self.batch_process_sources(source_ids, pipeline_type)
    
    async def batch_process_sources(self, source_ids: List[str], pipeline_type: str = None) -> Dict[str, Any]:
        """
        批量处理源
        
        参数:
            source_ids: List[str] - 源ID列表
            pipeline_type: str - 管道类型
            
        返回:
            Dict[str, Any] - 处理结果
        """
        results = {
            "total": len(source_ids),
            "succeeded": 0,
            "failed": 0,
            "errors": {},
            "generated_entities": []
        }
        
        # 分批处理
        for i in range(0, len(source_ids), self.batch_size):
            batch = source_ids[i:i+self.batch_size]
            tasks = []
            
            # 创建任务
            for source_id in batch:
                task = asyncio.create_task(self.process_source(source_id, pipeline_type))
                tasks.append((source_id, task))
            
            # 等待所有任务完成
            for source_id, task in tasks:
                try:
                    entities = await task
                    results["succeeded"] += 1
                    results["generated_entities"].extend(entities)
                except Exception as e:
                    results["failed"] += 1
                    results["errors"][source_id] = str(e)
                    logger.error(f"处理源 {source_id} 时出错: {str(e)}")
        
        return results
    
    async def validate_source_against_schema(self, source_data: Dict[str, Any], schema_namespace: str) -> Tuple[bool, List[str]]:
        """
        根据模式验证源
        
        参数:
            source_data: Dict[str, Any] - 源数据
            schema_namespace: str - 模式命名空间
            
        返回:
            Tuple[bool, List[str]] - (是否有效, 错误消息列表)
        """
        # 使用模式注册表验证
        return self.schema_registry.validate(source_data, schema_namespace)
    
    def _create_processing_task(self, source_id: str, pipeline_type: str) -> str:
        """
        创建处理任务
        
        参数:
            source_id: str - 源ID
            pipeline_type: str - 管道类型
            
        返回:
            str - 任务ID
        """
        task_id = f"task_{uuid.uuid4()}"
        
        # 在实际应用中，这里可能需要将任务信息存储到数据库或状态存储中
        logger.info(f"创建处理任务: {task_id} 用于源 {source_id} 使用管道 {pipeline_type}")
        
        return task_id
    
    async def _update_source_metadata(self, source_id: str, metadata_updates: Dict[str, Any]) -> None:
        """
        更新源元数据
        
        参数:
            source_id: str - 源ID
            metadata_updates: Dict[str, Any] - 元数据更新
        """
        # 获取当前元数据
        source_data = await self.hybrid_knowledge.get_by_id(source_id)
        if not source_data:
            logger.error(f"未找到源: {source_id}")
            return
        
        current_metadata = source_data.get("metadata", {})
        
        # 更新元数据
        updated_metadata = {**current_metadata, **metadata_updates}
        
        # 更新源
        await self.hybrid_knowledge.update_knowledge(source_id, {"metadata": updated_metadata})

# 将KnowledgeSourceManager定义为EnhancedSourceManager的别名
KnowledgeSourceManager = EnhancedSourceManager
