"""
知识库相关的请求/响应Pydantic模型

定义知识库相关的API请求和响应数据结构
"""
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union

from pydantic import BaseModel, Field, HttpUrl, ConfigDict


class ContentType(str, Enum):
    """内容类型枚举"""
    TEXT = "text"
    CODE = "code"
    IMAGE = "image"
    STRUCTURED = "structured"
    DOCUMENT = "document"
    URL = "url"


class SourceType(str, Enum):
    """来源类型枚举"""
    SYSTEM = "system"
    USER = "user"
    PROJECT = "project"
    EXTERNAL = "external"
    INFERENCE = "inference"


class KnowledgeBase(BaseModel):
    """知识基础模型
    
    包含知识项的基本字段
    """
    content: str = Field(..., description="知识内容")
    content_type: ContentType = Field(ContentType.TEXT, description="内容类型")
    source: Dict[str, Any] = Field(default_factory=dict, description="内容来源信息")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class KnowledgeCreate(KnowledgeBase):
    """知识创建请求模型
    
    用于创建新知识项的请求数据
    """
    project_id: Optional[int] = Field(None, description="关联的项目ID")
    embedding_model: Optional[str] = Field(None, description="使用的嵌入模型")


class KnowledgeUpdate(BaseModel):
    """知识更新请求模型
    
    用于更新知识项的请求数据
    """
    content: Optional[str] = Field(None, description="更新的知识内容")
    metadata: Optional[Dict[str, Any]] = Field(None, description="更新的元数据")


class KnowledgeItemResponse(KnowledgeBase):
    """知识响应模型
    
    API返回的知识项信息
    """
    id: int = Field(..., description="知识ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    created_by: int = Field(..., description="创建者ID")
    
    model_config = ConfigDict(from_attributes=True)


class KnowledgeItemDetail(KnowledgeItemResponse):
    """知识详细信息模型
    
    包含知识项的详细信息
    """
    relation_count: int = Field(0, description="关系数量")
    related_items_preview: List["KnowledgeItemResponse"] = Field(default_factory=list, description="相关知识项预览")
    vector_embedding: Optional[List[float]] = Field(None, description="向量嵌入（如果请求时需要）")
    usage_count: Optional[int] = Field(None, description="使用次数")
    
    model_config = ConfigDict(from_attributes=True)


class KnowledgeRelationCreate(BaseModel):
    """知识关系创建请求模型
    
    用于创建知识项之间关系的请求数据
    """
    source_id: int = Field(..., description="源知识ID")
    target_id: int = Field(..., description="目标知识ID")
    relation_type: str = Field(..., description="关系类型")
    properties: Optional[Dict[str, Any]] = Field(None, description="关系属性")


class KnowledgeRelationResponse(BaseModel):
    """知识关系响应模型
    
    API返回的知识关系信息
    """
    id: int = Field(..., description="关系ID")
    source_id: int = Field(..., description="源知识ID")
    target_id: int = Field(..., description="目标知识ID")
    relation_type: str = Field(..., description="关系类型")
    properties: Dict[str, Any] = Field(default_factory=dict, description="关系属性")
    created_at: datetime = Field(..., description="创建时间")
    
    model_config = ConfigDict(from_attributes=True)


class KnowledgeSearchResponse(BaseModel):
    """知识搜索响应模型
    
    知识搜索结果
    """
    query: str = Field(..., description="搜索查询")
    items: List[KnowledgeItemResponse] = Field(..., description="搜索结果")
    total: int = Field(..., description="总结果数")
    
    model_config = ConfigDict(from_attributes=True)


class RelatedEntitiesResponse(BaseModel):
    """相关实体响应模型
    
    与特定实体相关的其他实体
    """
    entity_id: int = Field(..., description="实体ID")
    related_items: List[KnowledgeItemResponse] = Field(..., description="相关知识项")
    relations: List[KnowledgeRelationResponse] = Field(..., description="关系")
    
    model_config = ConfigDict(from_attributes=True)


class GraphSearchParams(BaseModel):
    """图搜索参数模型
    
    用于图结构搜索的参数
    """
    query: str = Field(..., description="搜索查询")
    relation_types: Optional[List[str]] = Field(None, description="关系类型过滤")
    filters: Optional[str] = Field(None, description="过滤条件（JSON字符串）")
    limit: int = Field(10, description="结果数量限制", ge=1, le=100)
    depth: int = Field(1, description="遍历深度", ge=1, le=3)


class KnowledgeExtractionParams(BaseModel):
    """知识提取参数模型
    
    用于从文本中提取知识的参数
    """
    text: str = Field(..., description="要提取知识的文本内容")
    extract_relations: bool = Field(True, description="是否提取实体间关系")
    project_id: Optional[int] = Field(None, description="关联的项目ID")


class KnowledgeGraphQuery(BaseModel):
    """知识图谱查询模型
    
    用于知识图谱查询的参数
    """
    query: str = Field(..., description="查询文本")
    context_ids: Optional[List[int]] = Field(None, description="上下文知识项ID列表")
    use_rag: bool = Field(True, description="是否使用检索增强生成")
    max_tokens: Optional[int] = Field(None, description="生成答案的最大token数") 