"""
LangGraph状态模型

使用TypedDict定义强类型的工作流状态，为LangGraph状态图提供结构化状态定义
"""
from typing import Dict, List, Optional, Any, Annotated, Sequence
from typing_extensions import TypedDict, NotRequired

from operator import add
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class CreationState(TypedDict):
    """创作过程状态

    LangGraph创作工作流状态定义，包含项目、内容、步骤和智能体状态信息
    """
    # 项目标识符
    project_id: str
    # 内容项列表（可包含故事、角色、场景等）
    content_items: List[Dict[str, Any]]
    # 当前步骤
    current_step: str
    # 各智能体状态
    agent_states: Dict[str, Dict[str, Any]]
    # 消息历史，使用自定义reducer确保消息被追加而非覆盖
    messages: Annotated[List[Dict[str, Any]], add_messages]
    # 元数据
    metadata: Dict[str, Any]


class CoreSystemState(TypedDict):
    """核心系统状态

    系统级别状态定义，包含会话、工作流、智能体池和系统配置信息
    """
    # 活跃会话信息
    active_sessions: Dict[str, Dict[str, Any]]
    # 工作流状态
    workflows: Dict[str, Dict[str, Any]]
    # 智能体池
    agent_pool: Dict[str, Dict[str, Any]]
    # 事件列表
    events: Annotated[List[Dict[str, Any]], add]
    # 配置信息
    configs: Dict[str, Any]
    # LangGraph检查点ID
    checkpoint_id: NotRequired[str]


class CharacterAgentState(TypedDict):
    """角色智能体状态

    角色智能体的内部状态定义，包含性格、认知、情感、社交等维度
    """
    # 智能体ID
    id: str
    # 角色名称
    name: str
    # 性格特征
    personality: Dict[str, Any]
    # 认知属性
    cognitive: Dict[str, Any]
    # 情感状态
    emotional: Dict[str, Any]
    # 社交关系
    social: Dict[str, Any]
    # 记忆列表，使用add确保记忆被追加而非覆盖
    memories: Annotated[List[Dict[str, Any]], add]
    # 信念系统
    beliefs: Dict[str, Any]
    # 目标列表
    goals: List[Dict[str, Any]]
    # 消息列表，使用add_messages确保消息被追加
    messages: Annotated[Sequence[BaseMessage], add_messages]


class ContentAgentState(TypedDict):
    """内容智能体状态

    内容智能体的内部状态定义，包含内容结构、素材、主题等
    """
    # 智能体ID
    id: str
    # 内容类型（故事、场景、对话等）
    content_type: str
    # 内容结构
    structure: Dict[str, Any]
    # 素材库
    materials: Dict[str, Any]
    # 主题与风格
    themes: List[str]
    # 生成历史，使用add确保历史被追加
    generation_history: Annotated[List[Dict[str, Any]], add]
    # 消息列表
    messages: Annotated[Sequence[BaseMessage], add_messages]


class CoordiationAgentState(TypedDict):
    """协调智能体状态

    协调智能体的内部状态定义，包含任务分配、计划和监控信息
    """
    # 智能体ID
    id: str
    # 当前项目
    project_id: str
    # 任务队列，使用add确保任务被追加
    tasks: Annotated[List[Dict[str, Any]], add]
    # 任务分配信息
    assignments: Dict[str, List[str]]
    # 进度跟踪
    progress: Dict[str, Any]
    # 计划
    plans: List[Dict[str, Any]]
    # 消息列表
    messages: Annotated[Sequence[BaseMessage], add_messages]
    # 创作状态概要
    state_summary: Dict[str, Any]


class WorkflowState(TypedDict):
    """工作流状态

    工作流执行状态定义，包含工作流类型、阶段和配置信息
    """
    # 工作流ID
    id: str
    # 工作流类型
    workflow_type: str
    # 当前阶段
    current_stage: str
    # 阶段历史，使用add确保历史被追加
    stage_history: Annotated[List[Dict[str, Any]], add]
    # 工作流配置
    config: Dict[str, Any]
    # 启动时间
    start_time: str
    # 更新时间
    update_time: str
    # 关联项目ID
    project_id: str
    # 用户ID
    user_id: str
