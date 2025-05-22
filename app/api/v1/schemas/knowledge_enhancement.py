"""
知识管理增强层API模型

定义知识管理增强层API所需的Pydantic模型
"""

from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, root_validator, model_validator

# 枚举类型
class RetrievalStrategy(str, Enum):
    """检索策略类型"""
    VECTOR = "vector"  # 向量检索
    GRAPH = "graph"    # 图检索
    HYBRID = "hybrid"  # 混合检索
    DEFAULT = "default"  # 默认策略

class ContentType(str, Enum):
    """内容类型"""
    TEXT = "text"
    MARKDOWN = "markdown"
    HTML = "html"
    CODE = "code"
    JSON = "json"
    XML = "xml"
    CSV = "csv"

class RelationType(str, Enum):
    """关系类型"""
    RELATED_TO = "related_to"
    REFERENCES = "references"
    CONTAINS = "contains"
    DESCRIBES = "describes"
    RESPONDS_TO = "responds_to"
    ELABORATES = "elaborates"
    CONTRADICTS = "contradicts"
    SUPPORTS = "supports"

# 基础请求模型
class KnowledgeQueryBase(BaseModel):
    """知识查询基础模型"""
    query: str = Field(..., description="查询文本")
    limit: int = Field(10, description="结果数量限制")
    filters: Optional[Dict[str, Any]] = Field(None, description="查询过滤条件")

# 增强查询请求
class EnhancedQueryRequest(KnowledgeQueryBase):
    """增强查询请求模型"""
    strategy: RetrievalStrategy = Field(RetrievalStrategy.DEFAULT, description="检索策略")
    use_agentic_rag: bool = Field(True, description="是否使用智能体RAG")
    use_hybrid_search: bool = Field(True, description="是否使用混合搜索")
    max_iterations: Optional[int] = Field(None, description="最大迭代次数")
    include_reasoning: bool = Field(False, description="是否包含推理过程")
    include_context: bool = Field(False, description="是否包含检索上下文")
    session_id: Optional[str] = Field(None, description="会话ID")
    
    class Config:
        use_enum_values = True

# 智能查询规划请求
class QueryPlanningRequest(KnowledgeQueryBase):
    """查询规划请求模型"""
    max_sub_queries: int = Field(5, description="最大子查询数量")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")

# 子查询定义
class SubQuery(BaseModel):
    """子查询模型"""
    query: str = Field(..., description="子查询文本")
    strategy: RetrievalStrategy = Field(RetrievalStrategy.DEFAULT, description="检索策略")
    params: Dict[str, Any] = Field(default_factory=dict, description="查询参数")
    explanation: Optional[str] = Field(None, description="解释说明")
    
    class Config:
        use_enum_values = True

# 查询规划结果
class QueryPlan(BaseModel):
    """查询规划结果模型"""
    sub_queries: List[SubQuery] = Field(..., description="子查询列表")
    reasoning: Optional[str] = Field(None, description="规划推理过程")

# 知识反馈请求
class KnowledgeFeedbackRequest(BaseModel):
    """知识反馈请求模型"""
    query_id: str = Field(..., description="查询ID")
    is_relevant: bool = Field(..., description="结果是否相关")
    feedback_text: Optional[str] = Field(None, description="用户反馈文本")
    rating: Optional[int] = Field(None, description="评分(1-5)", ge=1, le=5)
    selected_items: Optional[List[str]] = Field(None, description="选择的相关知识项ID列表")
    
    @model_validator(mode='after')
    def check_feedback(self) -> 'KnowledgeFeedbackRequest':
        """验证反馈信息"""
        if not self.is_relevant and not self.feedback_text:
            raise ValueError("当结果不相关时，需要提供反馈文本")
        return self

# 知识创建请求
class RelationDefinition(BaseModel):
    """关系定义模型"""
    type: RelationType = Field(..., description="关系类型")
    target_id: str = Field(..., description="目标ID")
    
    class Config:
        use_enum_values = True

class SourceMetadataCreate(BaseModel):
    """创建信息源元数据模型"""
    source_type: str = Field(..., description="信息源类型")
    content_type: ContentType = Field(..., description="内容类型")
    title: Optional[str] = Field(None, description="标题")
    description: Optional[str] = Field(None, description="描述")
    authors: Optional[List[str]] = Field(None, description="作者列表")
    version: Optional[str] = Field(None, description="版本")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    language: Optional[str] = Field(None, description="语言")
    license: Optional[str] = Field(None, description="许可证")
    url: Optional[str] = Field(None, description="URL")
    additional_metadata: Optional[Dict[str, Any]] = Field(None, description="附加元数据")
    
    class Config:
        use_enum_values = True

class KnowledgeSourceCreate(BaseModel):
    """创建知识源请求模型"""
    content: str = Field(..., description="知识内容")
    metadata: SourceMetadataCreate = Field(..., description="元数据")
    relations: Optional[List[RelationDefinition]] = Field(None, description="关系列表")
    chunks: Optional[List[Dict[str, Any]]] = Field(None, description="预处理的内容块")
    validate_content: bool = Field(True, description="是否验证内容")

# 知识编辑请求
class RelationUpdate(BaseModel):
    """关系更新模型"""
    relations_to_add: Optional[List[RelationDefinition]] = Field(None, description="要添加的关系")
    relations_to_remove: Optional[List[RelationDefinition]] = Field(None, description="要移除的关系")

# 信息源格式转换请求
class FormatConversionRequest(BaseModel):
    """格式转换请求模型"""
    source_id: str = Field(..., description="信息源ID")
    target_format: ContentType = Field(..., description="目标格式")
    conversion_params: Optional[Dict[str, Any]] = Field(None, description="转换参数")
    
    class Config:
        use_enum_values = True

# 响应模型
class QualityMetrics(BaseModel):
    """质量评估指标模型"""
    relevance: float = Field(..., description="相关性分数", ge=0, le=10)
    coherence: float = Field(..., description="连贯性分数", ge=0, le=10)
    information_accuracy: float = Field(..., description="信息准确性分数", ge=0, le=10)
    completeness: float = Field(..., description="完整性分数", ge=0, le=10)
    objectivity: float = Field(..., description="客观性分数", ge=0, le=10)
    clarity: float = Field(..., description="清晰度分数", ge=0, le=10)
    overall_score: float = Field(..., description="总体评分", ge=0, le=10)

class KnowledgeItem(BaseModel):
    """知识项模型"""
    id: str = Field(..., description="知识项ID")
    content: str = Field(..., description="知识内容")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")

class EnhancedKnowledgeResponse(BaseModel):
    """增强知识响应模型"""
    query_id: str = Field(..., description="查询ID")
    original_query: str = Field(..., description="原始查询")
    answer: str = Field(..., description="生成的回答")
    confidence: float = Field(..., description="置信度", ge=0, le=1)
    quality_metrics: Optional[QualityMetrics] = Field(None, description="质量评估指标")
    reasoning: Optional[str] = Field(None, description="推理过程")
    context_items: Optional[List[KnowledgeItem]] = Field(None, description="上下文知识项")
    retrieval_strategy: RetrievalStrategy = Field(RetrievalStrategy.DEFAULT, description="使用的检索策略")
    execution_time: float = Field(..., description="执行时间(秒)")
    iteration_count: Optional[int] = Field(None, description="迭代次数")
    session_id: Optional[str] = Field(None, description="会话ID")
    
    class Config:
        use_enum_values = True

class StandardKnowledgeResponse(BaseModel):
    """标准知识响应模型"""
    items: List[KnowledgeItem] = Field(..., description="知识项列表")
    total: int = Field(..., description="总结果数量")
    query: str = Field(..., description="原始查询")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="响应元数据")

class QueryPlanResponse(BaseModel):
    """查询规划响应模型"""
    query_id: str = Field(..., description="查询ID")
    original_query: str = Field(..., description="原始查询")
    plan: QueryPlan = Field(..., description="查询规划")

class KnowledgeSourceResponse(BaseModel):
    """知识源响应模型"""
    source_id: str = Field(..., description="信息源ID")
    content: str = Field(..., description="内容")
    metadata: Dict[str, Any] = Field(..., description="元数据")
    chunks: Optional[List[Dict[str, Any]]] = Field(None, description="内容块")
    relations_data: Optional[Dict[str, List[Any]]] = Field(None, description="关系数据")

class FormatConversionResponse(BaseModel):
    """格式转换响应模型"""
    source_id: str = Field(..., description="信息源ID")
    original_format: ContentType = Field(..., description="原始格式")
    target_format: ContentType = Field(..., description="目标格式")
    converted_content: str = Field(..., description="转换后的内容")
    metadata: Dict[str, Any] = Field(..., description="更新后的元数据")
    
    class Config:
        use_enum_values = True

class RelationUpdateResponse(BaseModel):
    """关系更新响应模型"""
    source_id: str = Field(..., description="信息源ID")
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="消息")
    updated_relations: Optional[Dict[str, List[str]]] = Field(None, description="更新后的关系") 