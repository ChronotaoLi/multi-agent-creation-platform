"""
项目相关的请求/响应Pydantic模型

定义项目相关的API请求和响应数据结构
"""
from datetime import datetime
from typing import List, Optional, Dict, Any, Union

from pydantic import BaseModel, Field, EmailStr, field_validator, ConfigDict


class ProjectBase(BaseModel):
    """项目基础模型
    
    包含项目的基本信息字段
    """
    title: str = Field(..., description="项目标题", min_length=1, max_length=100)
    description: Optional[str] = Field(None, description="项目描述")
    project_type: str = Field(..., description="项目类型，如 'story', 'script', 'game' 等")


class ProjectCreate(ProjectBase):
    """项目创建请求模型
    
    用于创建新项目的请求数据
    """
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict, description="项目设置")


class ProjectUpdate(BaseModel):
    """项目更新请求模型
    
    用于更新项目的请求数据
    """
    title: Optional[str] = Field(None, description="项目标题", min_length=1, max_length=100)
    description: Optional[str] = Field(None, description="项目描述")
    status: Optional[str] = Field(None, description="项目状态，如 'active', 'archived', 'deleted'")
    settings: Optional[Dict[str, Any]] = Field(None, description="项目设置")
    
    @field_validator("*", "pre")
    def check_at_least_one_field(cls, values):
        """确保至少提供一个字段进行更新"""
        if all(v is None for v in values.values()):
            raise ValueError("至少需要提供一个字段进行更新")
        return values


class ProjectListItem(BaseModel):
    """项目列表项模型
    
    用于项目列表的简要信息
    """
    id: int = Field(..., description="项目ID")
    title: str = Field(..., description="项目标题")
    description: Optional[str] = Field(None, description="项目描述")
    project_type: str = Field(..., description="项目类型")
    status: str = Field(..., description="项目状态")
    updated_at: datetime = Field(..., description="更新时间")
    created_at: datetime = Field(..., description="创建时间")
    created_by: int = Field(..., description="创建者用户ID")
    
    model_config = ConfigDict(from_attributes=True)


class ProjectResponse(ProjectListItem):
    """项目响应模型
    
    API返回的完整项目信息
    """
    settings: Dict[str, Any] = Field(default_factory=dict, description="项目设置")
    access_level: Optional[str] = Field(None, description="当前用户的访问级别")


class ContentSummary(BaseModel):
    """内容项摘要模型
    
    用于项目详情中展示关联内容的简要信息
    """
    id: int = Field(..., description="内容项ID")
    title: str = Field(..., description="内容标题")
    content_type: str = Field(..., description="内容类型")
    updated_at: datetime = Field(..., description="更新时间")
    
    model_config = ConfigDict(from_attributes=True)


class AgentSummary(BaseModel):
    """智能体摘要模型
    
    用于项目详情中展示关联智能体的简要信息
    """
    id: int = Field(..., description="智能体ID")
    name: str = Field(..., description="智能体名称")
    agent_type: str = Field(..., description="智能体类型")
    status: str = Field(..., description="智能体状态")
    
    model_config = ConfigDict(from_attributes=True)


class ProjectDetail(ProjectResponse):
    """项目详情模型
    
    包含完整的项目详细信息，包括关联的内容项、智能体等
    """
    content_items: List[ContentSummary] = Field(default_factory=list, description="关联的内容项")
    agents: List[AgentSummary] = Field(default_factory=list, description="关联的智能体")
    member_count: int = Field(0, description="项目成员数量")


class ProjectMemberCreate(BaseModel):
    """项目成员添加请求模型
    
    用于向项目添加成员的请求数据
    """
    user_id: int = Field(..., description="用户ID")
    role: str = Field(..., description="用户在项目中的角色，如 'editor', 'viewer'")


class ProjectMemberResponse(BaseModel):
    """项目成员响应模型
    
    API返回的项目成员信息
    """
    project_id: int = Field(..., description="项目ID")
    user_id: int = Field(..., description="用户ID")
    username: Optional[str] = Field(None, description="用户名")
    display_name: Optional[str] = Field(None, description="显示名称")
    email: Optional[EmailStr] = Field(None, description="电子邮箱")
    role: str = Field(..., description="用户在项目中的角色")
    
    model_config = ConfigDict(from_attributes=True)


class ProjectStatsResponse(BaseModel):
    """项目统计响应模型
    
    项目统计信息
    """
    content_count: Dict[str, int] = Field(default_factory=dict, description="各类型内容项数量")
    agent_count: Dict[str, int] = Field(default_factory=dict, description="各类型智能体数量")
    member_count: int = Field(0, description="项目成员数量")
    last_activity: Optional[datetime] = Field(None, description="最后活动时间")
    completion_rate: Optional[float] = Field(None, description="项目完成度")
