"""
知识模型定义 (Pydantic Models)

包含知识项的数据模型及相关定义，用于API交互和数据验证
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field

class KnowledgeItem(BaseModel):
    """
    知识项模型
    
    表示从知识库中检索的单个知识片段
    """
    
    id: str = Field(..., description="知识项唯一标识符")
    content: str = Field(..., description="知识项内容")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="知识项元数据")
    
    @property
    def score(self) -> float:
        """获取知识项的相关性分数"""
        return self.metadata.get("score", 0.0)
    
    @property
    def source(self) -> str:
        """获取知识项的来源"""
        return self.metadata.get("source", "unknown")
    
    @property
    def content_type(self) -> str:
        """获取知识项的内容类型"""
        return self.metadata.get("content_type", "text")
    
    @property
    def created_at(self) -> Optional[datetime]:
        """获取知识项的创建时间"""
        created_at = self.metadata.get("created_at")
        if isinstance(created_at, str):
            try:
                return datetime.fromisoformat(created_at)
            except ValueError:
                return None
        return created_at if isinstance(created_at, datetime) else None

class KnowledgeQuery(BaseModel):
    """
    知识查询模型
    
    表示对知识库的查询请求
    """
    
    query: str = Field(..., description="查询文本")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="过滤条件")
    limit: int = Field(default=10, description="结果数量限制")
    strategy: Optional[str] = Field(default=None, description="检索策略名称")
    use_rag: bool = Field(default=True, description="是否使用RAG增强")
    
class KnowledgeResponse(BaseModel):
    """
    知识响应模型
    
    表示知识查询的响应结果
    """
    
    items: List[KnowledgeItem] = Field(default_factory=list, description="知识项列表")
    total: int = Field(default=0, description="总结果数量")
    query: str = Field(..., description="原始查询文本")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="响应元数据")
    
class EnhancedKnowledgeResponse(KnowledgeResponse):
    """
    增强知识响应模型
    
    表示使用高级RAG技术的知识查询响应
    """
    
    answer: Optional[str] = Field(default=None, description="生成的回答")
    confidence: float = Field(default=0.0, description="回答置信度")
    reasoning: Optional[str] = Field(default=None, description="推理过程")
    context_items: List[KnowledgeItem] = Field(default_factory=list, description="用于生成回答的上下文知识项")
    quality_metrics: Optional[Dict[str, Any]] = Field(default=None, description="质量评估指标")
    
class KnowledgeFeedback(BaseModel):
    """
    知识反馈模型
    
    表示用户对知识查询结果的反馈
    """
    
    query_id: str = Field(..., description="查询ID")
    is_relevant: bool = Field(..., description="结果是否相关")
    feedback_text: Optional[str] = Field(default=None, description="文本反馈")
    rating: Optional[int] = Field(default=None, description="评分(1-5)")
    selected_items: Optional[List[str]] = Field(default=None, description="用户选择的有用知识项ID列表")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="反馈元数据")
    created_at: datetime = Field(default_factory=datetime.now, description="反馈创建时间") 