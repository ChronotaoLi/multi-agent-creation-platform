"""
服务层内部使用的Pydantic模型

定义服务层和API接口使用的数据模型
"""
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union, Literal

from pydantic import BaseModel, Field, EmailStr, HttpUrl


# 基础用户模型
class UserBase(BaseModel):
    """用户基础模型"""
    username: str = Field(..., description="用户名")
    email: EmailStr = Field(..., description="电子邮箱")
    display_name: Optional[str] = Field(None, description="显示名称")


class UserCreate(UserBase):
    """用户创建模型"""
    password: str = Field(..., description="密码")


class UserUpdate(BaseModel):
    """用户更新模型"""
    username: Optional[str] = Field(None, description="用户名")
    email: Optional[EmailStr] = Field(None, description="电子邮箱")
    display_name: Optional[str] = Field(None, description="显示名称")
    is_active: Optional[bool] = Field(None, description="是否激活")


class User(UserBase):
    """用户返回模型"""
    id: int = Field(..., description="用户ID")
    is_active: bool = Field(..., description="是否激活")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class UserWithRole(User):
    """带角色的用户模型"""
    role: str = Field(..., description="用户在项目中的角色")

    class Config:
        from_attributes = True


class UserDB(UserBase):
    """用户数据库模型"""
    id: int = Field(..., description="用户ID")
    is_active: bool = Field(..., description="是否激活")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


# 角色模型
class RoleBase(BaseModel):
    """角色基础模型"""
    name: str = Field(..., description="角色名称")
    description: Optional[str] = Field(None, description="角色描述")


class RoleCreate(RoleBase):
    """角色创建模型"""
    pass


class RoleDB(RoleBase):
    """角色数据库模型"""
    id: int = Field(..., description="角色ID")

    class Config:
        from_attributes = True


# 项目模型
class ProjectBase(BaseModel):
    """项目基础模型"""
    title: str = Field(..., description="项目标题")
    description: Optional[str] = Field(None, description="项目描述")
    project_type: str = Field(..., description="项目类型")


class ProjectCreate(ProjectBase):
    """项目创建模型"""
    pass


class ProjectUpdate(BaseModel):
    """项目更新模型"""
    title: Optional[str] = Field(None, description="项目标题")
    description: Optional[str] = Field(None, description="项目描述")
    status: Optional[str] = Field(None, description="项目状态")


class Project(ProjectBase):
    """项目返回模型"""
    id: int = Field(..., description="项目ID")
    status: str = Field(..., description="项目状态")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    created_by: int = Field(..., description="创建者ID")

    class Config:
        from_attributes = True


class ProjectDB(ProjectBase):
    """项目数据库模型"""
    id: int = Field(..., description="项目ID")
    status: str = Field(..., description="项目状态")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    created_by: int = Field(..., description="创建者ID")

    class Config:
        from_attributes = True


# 内容模型
class ContentBase(BaseModel):
    """内容基础模型"""
    title: str = Field(..., description="内容标题")
    content_type: str = Field(..., description="内容类型")
    content_data: Dict[str, Any] = Field(..., description="内容数据")
    project_id: int = Field(..., description="项目ID")


class ContentCreate(ContentBase):
    """内容创建模型"""
    pass


class ContentUpdate(BaseModel):
    """内容更新模型"""
    title: Optional[str] = Field(None, description="内容标题")
    content_data: Optional[Dict[str, Any]] = Field(None, description="内容数据")


class ContentItem(ContentBase):
    """内容项返回模型"""
    id: int = Field(..., description="内容项ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    created_by: int = Field(..., description="创建者ID")

    class Config:
        from_attributes = True


class ContentVersion(BaseModel):
    """内容版本返回模型"""
    id: int = Field(..., description="版本ID")
    content_id: int = Field(..., description="内容项ID")
    data: Dict[str, Any] = Field(..., description="版本数据")
    created_at: datetime = Field(..., description="创建时间")
    created_by: int = Field(..., description="创建者ID")

    class Config:
        from_attributes = True


class ContentItemDB(ContentBase):
    """内容项数据库模型"""
    id: int = Field(..., description="内容项ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    created_by: int = Field(..., description="创建者ID")

    class Config:
        from_attributes = True


class ContentVersionDB(BaseModel):
    """内容版本数据库模型"""
    id: int = Field(..., description="版本ID")
    content_item_id: int = Field(..., description="内容项ID")
    version_data: Dict[str, Any] = Field(..., description="版本数据")
    created_at: datetime = Field(..., description="创建时间")
    created_by: int = Field(..., description="创建者ID")

    class Config:
        from_attributes = True


# 智能体模型
class AgentType(str, Enum):
    """智能体类型枚举"""
    COORDINATOR = "coordinator"
    CHARACTER = "character" 
    CONTENT = "content"
    REVIEW = "review"
    MEMORY = "memory"
    ANALYSIS = "analysis"
    INFORMATION = "information"


class AgentBase(BaseModel):
    """智能体基础模型"""
    name: str = Field(..., description="智能体名称")
    agent_type: AgentType = Field(..., description="智能体类型")
    config: Dict[str, Any] = Field(default_factory=dict, description="配置数据")
    project_id: int = Field(..., description="项目ID")


class AgentCreate(AgentBase):
    """智能体创建模型"""
    pass


class AgentUpdate(BaseModel):
    """智能体更新模型"""
    name: Optional[str] = Field(None, description="智能体名称")
    config: Optional[Dict[str, Any]] = Field(None, description="配置数据")


class Agent(AgentBase):
    """智能体返回模型"""
    id: int = Field(..., description="智能体ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class AgentDB(AgentBase):
    """智能体数据库模型"""
    id: int = Field(..., description="智能体ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class AgentStateBase(BaseModel):
    """智能体状态基础模型"""
    agent_id: int = Field(..., description="智能体ID")
    state_data: Dict[str, Any] = Field(..., description="状态数据")
    state_type: str = Field(..., description="状态类型")


class AgentStateCreate(AgentStateBase):
    """智能体状态创建模型"""
    pass


class AgentStateDB(AgentStateBase):
    """智能体状态数据库模型"""
    id: int = Field(..., description="状态ID")
    checkpoint_id: Optional[str] = Field(None, description="检查点ID")
    created_at: datetime = Field(..., description="创建时间")

    class Config:
        from_attributes = True


class AgentTemplateBase(BaseModel):
    """智能体模板基础模型"""
    name: str = Field(..., description="模板名称")
    description: Optional[str] = Field(None, description="模板描述")
    agent_type: AgentType = Field(..., description="智能体类型")
    template_config: Dict[str, Any] = Field(..., description="模板配置")
    is_public: bool = Field(False, description="是否公开")


class AgentTemplateCreate(AgentTemplateBase):
    """智能体模板创建模型"""
    pass


class AgentTemplateUpdate(BaseModel):
    """智能体模板更新模型"""
    name: Optional[str] = Field(None, description="模板名称")
    description: Optional[str] = Field(None, description="模板描述")
    template_config: Optional[Dict[str, Any]] = Field(None, description="模板配置")
    is_public: Optional[bool] = Field(None, description="是否公开")


class AgentTypeInfo(BaseModel):
    """智能体类型信息模型"""
    id: str = Field(..., description="类型标识")
    display_name: str = Field(..., description="显示名称")
    description: str = Field(..., description="类型描述")
    schema: Dict[str, Any] = Field(..., description="配置模式")


class AgentInstanceBase(BaseModel):
    """智能体实例基础模型"""
    agent_id: int = Field(..., description="智能体ID")
    config: Dict[str, Any] = Field(default_factory=dict, description="实例配置")


class AgentInstanceCreate(AgentInstanceBase):
    """智能体实例创建模型"""
    pass


class AgentMessage(BaseModel):
    """智能体消息模型"""
    content: str = Field(..., description="消息内容")
    role: str = Field(..., description="消息角色")
    message_type: str = Field("text", description="消息类型")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="消息元数据")
    timestamp: datetime = Field(default_factory=datetime.now, description="消息时间戳")


class AgentTaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentTask(BaseModel):
    """智能体任务模型"""
    id: Optional[str] = Field(None, description="任务ID")
    title: str = Field(..., description="任务标题")
    description: str = Field(..., description="任务描述")
    task_type: str = Field(..., description="任务类型")
    status: AgentTaskStatus = Field(AgentTaskStatus.PENDING, description="任务状态")
    priority: int = Field(5, description="任务优先级 (1-10)")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="任务参数")
    due_time: Optional[datetime] = Field(None, description="截止时间")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    created_by: Optional[int] = Field(None, description="创建者ID")
    result: Optional[Dict[str, Any]] = Field(None, description="任务结果")
    error: Optional[str] = Field(None, description="错误信息")


# 工作流模型
class WorkflowType(str, Enum):
    """工作流类型枚举"""
    FREE = "free"
    GUIDED = "guided"
    ADAPTATION = "adaptation"
    STRUCTURED = "structured"


class WorkflowBase(BaseModel):
    """工作流基础模型"""
    workflow_type: WorkflowType = Field(..., description="工作流类型")
    config: Dict[str, Any] = Field(default_factory=dict, description="配置数据")
    project_id: int = Field(..., description="项目ID")


class WorkflowCreate(WorkflowBase):
    """工作流创建模型"""
    pass


class WorkflowDB(WorkflowBase):
    """工作流数据库模型"""
    id: str = Field(..., description="工作流ID")
    current_stage: str = Field(..., description="当前阶段")
    start_time: datetime = Field(..., description="启动时间")
    update_time: datetime = Field(..., description="更新时间")
    user_id: int = Field(..., description="用户ID")

    class Config:
        from_attributes = True


class WorkflowSession(BaseModel):
    """工作流会话模型"""
    session_id: str = Field(..., description="会话ID")
    workflow_type: WorkflowType = Field(..., description="工作流类型")
    project_id: int = Field(..., description="项目ID")
    user_id: int = Field(..., description="用户ID")
    status: str = Field(..., description="会话状态")
    current_stage: str = Field(..., description="当前阶段")
    data: Dict[str, Any] = Field(default_factory=dict, description="会话数据")
    start_time: datetime = Field(..., description="启动时间")
    update_time: datetime = Field(..., description="更新时间")


class WorkflowSessionStatus(BaseModel):
    """工作流会话状态模型"""
    session_id: str = Field(..., description="会话ID")
    status: str = Field(..., description="会话状态")
    current_stage: str = Field(..., description="当前阶段")
    progress: float = Field(..., description="进度")
    next_steps: List[str] = Field(default_factory=list, description="下一步选项")
    messages: List[Dict[str, Any]] = Field(default_factory=list, description="消息列表")
    update_time: datetime = Field(..., description="更新时间")


class WorkflowStartConfig(BaseModel):
    """工作流启动配置"""
    workflow_type: WorkflowType = Field(..., description="工作流类型")
    project_id: int = Field(..., description="项目ID")
    initial_data: Dict[str, Any] = Field(default_factory=dict, description="初始数据")
    agents: List[int] = Field(default_factory=list, description="参与智能体ID列表")


class WorkflowTypeInfo(BaseModel):
    """工作流类型信息"""
    id: str = Field(..., description="类型标识")
    name: str = Field(..., description="类型名称")
    description: str = Field(..., description="类型描述")
    capabilities: List[str] = Field(default_factory=list, description="功能列表")
    config_schema: Dict[str, Any] = Field(default_factory=dict, description="配置模式")


class InterventionData(BaseModel):
    """用户干预数据"""
    intervention_type: str = Field(..., description="干预类型")
    content: Dict[str, Any] = Field(..., description="干预内容")
    target_stage: Optional[str] = Field(None, description="目标阶段")


class InterventionResult(BaseModel):
    """干预处理结果"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="结果消息")
    status: WorkflowSessionStatus = Field(..., description="干预后的会话状态")


# 认证模型
class Token(BaseModel):
    """令牌模型"""
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field(..., description="令牌类型")


class TokenData(BaseModel):
    """令牌数据模型"""
    username: Optional[str] = None


# 知识库模型
class KnowledgeItemBase(BaseModel):
    """知识项基础模型"""
    title: str = Field(..., description="知识标题")
    content: str = Field(..., description="知识内容")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class KnowledgeItemCreate(KnowledgeItemBase):
    """知识项创建模型"""
    pass


class KnowledgeItemUpdate(BaseModel):
    """知识项更新模型"""
    title: Optional[str] = Field(None, description="知识标题")
    content: Optional[str] = Field(None, description="知识内容")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")


class KnowledgeItem(KnowledgeItemBase):
    """知识项返回模型"""
    id: int = Field(..., description="知识项ID")
    vector_id: Optional[str] = Field(None, description="向量ID")
    node_id: Optional[str] = Field(None, description="节点ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    created_by: int = Field(..., description="创建者ID")

    class Config:
        from_attributes = True


class KnowledgeItemDB(KnowledgeItemBase):
    """知识项数据库模型"""
    id: int = Field(..., description="知识项ID")
    vector_id: Optional[str] = Field(None, description="向量ID")
    node_id: Optional[str] = Field(None, description="节点ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    created_by: int = Field(..., description="创建者ID")

    class Config:
        from_attributes = True


# 知识管理相关模型
class KnowledgeCreate(BaseModel):
    """知识创建请求模型"""
    
    title: str = Field(..., description="知识标题")
    content: str = Field(..., description="知识内容")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="知识元数据")


class KnowledgeUpdate(BaseModel):
    """知识更新请求模型"""
    
    title: Optional[str] = Field(None, description="知识标题")
    content: Optional[str] = Field(None, description="知识内容")
    metadata: Optional[Dict[str, Any]] = Field(None, description="知识元数据")


class KnowledgeRelation(BaseModel):
    """知识关系模型"""
    
    source_id: int = Field(..., description="源知识项ID")
    target_id: int = Field(..., description="目标知识项ID")
    type: str = Field(..., description="关系类型")
    properties: Dict[str, Any] = Field(default_factory=dict, description="关系属性")


class KnowledgeRelationCreate(BaseModel):
    """知识关系创建请求模型"""
    
    source_id: int = Field(..., description="源知识项ID")
    target_id: int = Field(..., description="目标知识项ID")
    type: str = Field(..., description="关系类型")
    properties: Optional[Dict[str, Any]] = Field(default_factory=dict, description="关系属性")


class KnowledgeSearchParams(BaseModel):
    """知识搜索参数模型"""
    
    query: str = Field(..., description="搜索查询文本")
    limit: int = Field(10, description="返回结果数量限制")
    filters: Optional[Dict[str, Any]] = Field(None, description="过滤条件")


class MetadataSearchParams(BaseModel):
    """元数据搜索参数模型"""
    
    filters: Dict[str, Any] = Field(..., description="元数据过滤条件")
    limit: int = Field(10, description="返回结果数量限制")


class ImportSourceParams(BaseModel):
    """导入知识源参数模型"""
    
    url: Optional[str] = Field(None, description="知识来源URL")
    file_id: Optional[str] = Field(None, description="文件ID")
    type: str = Field(..., description="来源类型，如'url'、'file'、'text'等")
    content: Optional[str] = Field(None, description="文本内容，当type为'text'时使用")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")
    

class KnowledgeSearchResult(BaseModel):
    """知识搜索结果项"""
    
    id: int = Field(..., description="知识ID")
    title: str = Field(..., description="知识标题")
    content: str = Field(..., description="知识内容")
    relevance_score: float = Field(..., description="相关性分数")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="知识元数据")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    created_by: int = Field(..., description="创建者ID")


class KnowledgeSearchResponse(BaseModel):
    """知识搜索响应模型"""
    
    results: List[KnowledgeSearchResult] = Field(default_factory=list, description="搜索结果")
    total: int = Field(0, description="结果总数")
    query: str = Field(..., description="搜索查询文本")
    execution_time_ms: float = Field(0.0, description="执行时间(毫秒)")


class KnowledgeItemDetail(BaseModel):
    """知识项详情模型"""
    
    id: int = Field(..., description="知识ID")
    title: str = Field(..., description="知识标题")
    content: str = Field(..., description="知识内容")
    vector_id: str = Field(..., description="向量存储中的ID")
    node_id: str = Field(..., description="图存储中的节点ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="知识元数据")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    created_by: int = Field(..., description="创建者ID")
