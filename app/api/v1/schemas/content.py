"""
内容相关的请求/响应Pydantic模型

定义内容（故事、角色、场景等）相关的API请求和响应数据结构
"""
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union

from pydantic import BaseModel, Field, ConfigDict


class ContentType(str, Enum):
    """内容类型枚举"""
    STORY = "story"
    CHARACTER = "character"
    SCENE = "scene"
    PLOT = "plot"
    DIALOGUE = "dialogue"
    SETTING = "setting"
    CUSTOM = "custom"


class ContentBase(BaseModel):
    """内容基础模型
    
    包含内容的基本信息字段
    """
    title: str = Field(..., description="内容标题", min_length=1, max_length=200)
    content_type: ContentType = Field(..., description="内容类型")


class ContentCreate(ContentBase):
    """内容创建请求模型
    
    用于创建新内容项的请求数据
    """
    content_data: Dict[str, Any] = Field(..., description="内容数据，结构根据内容类型不同而变化")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="内容元数据")


class ContentUpdate(BaseModel):
    """内容更新请求模型
    
    用于更新内容的请求数据
    """
    title: Optional[str] = Field(None, description="内容标题", min_length=1, max_length=200)
    content_data: Optional[Dict[str, Any]] = Field(None, description="内容数据")
    metadata: Optional[Dict[str, Any]] = Field(None, description="内容元数据")


class ContentResponse(ContentBase):
    """内容响应模型
    
    API返回的内容基本信息
    """
    id: int = Field(..., description="内容ID")
    project_id: int = Field(..., description="所属项目ID")
    content_data: Dict[str, Any] = Field(..., description="内容数据")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="内容元数据")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    created_by: int = Field(..., description="创建者ID")
    updated_by: Optional[int] = Field(None, description="最后更新者ID")

    model_config = ConfigDict(from_attributes=True)


class ContentListItem(BaseModel):
    """内容列表项模型
    
    用于列表展示的简化内容模型
    """
    id: int = Field(..., description="内容ID")
    title: str = Field(..., description="内容标题")
    content_type: ContentType = Field(..., description="内容类型")
    project_id: int = Field(..., description="所属项目ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    excerpt: Optional[str] = Field(None, description="内容摘要")
    
    model_config = ConfigDict(from_attributes=True)
    
    @classmethod
    def model_validate(cls, obj):
        """处理内容摘要
        
        从内容数据中提取简短摘要
        """
        data = {
            "id": obj.id,
            "title": obj.title,
            "content_type": obj.content_type,
            "project_id": obj.project_id,
            "created_at": obj.created_at,
            "updated_at": obj.updated_at
        }
        
        # 根据不同内容类型生成摘要
        if hasattr(obj, 'content_data') and isinstance(obj.content_data, dict):
            if obj.content_type == ContentType.STORY:
                data["excerpt"] = obj.content_data.get("summary", "")[:100] + "..." if obj.content_data.get("summary") else None
            elif obj.content_type == ContentType.CHARACTER:
                data["excerpt"] = obj.content_data.get("description", "")[:100] + "..." if obj.content_data.get("description") else None
            elif obj.content_type == ContentType.SCENE:
                data["excerpt"] = obj.content_data.get("description", "")[:100] + "..." if obj.content_data.get("description") else None
        
        return cls(**data)


class ContentDetail(ContentResponse):
    """内容详细信息模型
    
    扩展内容响应模型，包含更多详细信息
    """
    version_count: int = Field(0, description="版本数量")
    latest_version_at: Optional[datetime] = Field(None, description="最近版本创建时间")
    # 可以添加更多和内容相关的详细字段
    
    model_config = ConfigDict(from_attributes=True)


class ContentVersionResponse(BaseModel):
    """内容版本响应模型
    
    内容历史版本信息
    """
    id: int = Field(..., description="版本ID")
    content_id: int = Field(..., description="内容ID")
    version_number: int = Field(..., description="版本号")
    version_data: Dict[str, Any] = Field(..., description="版本内容数据")
    created_at: datetime = Field(..., description="版本创建时间")
    created_by: int = Field(..., description="版本创建者ID")
    change_description: Optional[str] = Field(None, description="变更说明")
    
    model_config = ConfigDict(from_attributes=True)
