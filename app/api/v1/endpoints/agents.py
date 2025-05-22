"""
智能体配置与管理接口

提供智能体创建、查询、更新、删除等API端点
"""
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status

from app.api.v1.deps import (
    get_current_user,
    get_agent_service,
    validate_project_access,
    validate_project_edit_access,
    validate_agent_access
)
from app.api.v1.schemas.agents import (
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    AgentDetail,
    AgentTypeInfo,
    AgentTemplateResponse
)
from app.models.schemas import UserDB, AgentCreate as ModelAgentCreate, AgentUpdate as ModelAgentUpdate
from app.services.interfaces.agent_service import AgentService
from app.utils.error_handlers import ResourceNotFoundError, ResourceConflictError

# 创建路由器
router = APIRouter(
    prefix="/agents",
    tags=["agents"],
    responses={404: {"description": "智能体未找到"}}
)

@router.get("/types", response_model=List[AgentTypeInfo])
async def get_agent_types(
    current_user: Annotated[UserDB, Depends(get_current_user)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)]
):
    """
    获取支持的智能体类型列表
    
    Returns:
        List[AgentTypeInfo]: 智能体类型信息列表
    """
    # 在实际实现中，这些类型信息可能来自配置文件或数据库
    # 这里提供一个基本的实现
    agent_types = [
        AgentTypeInfo(
            type="coordinator",
            name="协调智能体",
            description="负责任务分解、规划和分配",
            config_schema={
                "coordination_strategy": {
                    "type": "string", 
                    "enum": ["hierarchical", "democratic", "expert_based"]
                },
                "planning_depth": {"type": "integer", "minimum": 1, "default": 3}
            },
            icon="coordinator-icon"
        ),
        AgentTypeInfo(
            type="character",
            name="角色智能体",
            description="处理角色相关逻辑和行为",
            config_schema={
                "character_depth": {
                    "type": "string",
                    "enum": ["basic", "detailed", "comprehensive"],
                    "default": "detailed"
                },
                "memory_capacity": {"type": "integer", "minimum": 1, "default": 10}
            },
            icon="character-icon"
        ),
        AgentTypeInfo(
            type="content",
            name="内容智能体",
            description="负责生成故事内容",
            config_schema={
                "style": {
                    "type": "string",
                    "enum": ["descriptive", "dialogue-focused", "action-oriented"]
                },
                "creativity_level": {"type": "integer", "minimum": 1, "maximum": 10, "default": 7}
            },
            icon="content-icon"
        ),
        AgentTypeInfo(
            type="review",
            name="审核智能体",
            description="负责内容审核和质量控制",
            config_schema={
                "review_criteria": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": ["consistency", "grammar", "engagement"]
                },
                "strictness_level": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5}
            },
            icon="review-icon"
        )
    ]
    return agent_types

@router.get("/project/{project_id}", response_model=List[AgentResponse])
async def get_project_agents(
    project_id: int = Path(...),
    agent_type: Optional[str] = Query(None, description="过滤特定类型的智能体"),
    project: Annotated[dict, Depends(validate_project_access)] = None,
    agent_service: Annotated[AgentService, Depends(get_agent_service)] = None
):
    """
    获取特定项目的智能体列表
    
    Args:
        project_id: 项目ID
        agent_type: 可选，过滤特定类型的智能体
        
    Returns:
        List[AgentResponse]: 项目智能体列表
    """
    try:
        # 调用服务获取项目智能体，可能需要修改参数以适应实际接口
        agents = await agent_service.list_agents(
            project_id=project_id, 
            agent_type=agent_type
        )
        return [AgentResponse.model_validate(agent) for agent in agents]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取项目智能体失败: {str(e)}"
        )

@router.post("/project/{project_id}", response_model=AgentResponse, status_code=201)
async def add_agent(
    project_id: int = Path(...),
    agent_data: AgentCreate = None,
    project: Annotated[dict, Depends(validate_project_edit_access)] = None,
    agent_service: Annotated[AgentService, Depends(get_agent_service)] = None,
    current_user: Annotated[UserDB, Depends(get_current_user)] = None
):
    """
    向项目添加智能体
    
    Args:
        project_id: 项目ID
        agent_data: 智能体创建数据
        
    Returns:
        AgentResponse: 创建的智能体信息
    """
    try:
        # 转换API模型到服务层模型
        model_agent_data = ModelAgentCreate(
            name=agent_data.name,
            agent_type=agent_data.agent_type,
            config=agent_data.config,
            project_id=project_id
        )
        
        # 调用服务创建智能体
        agent = await agent_service.create_agent(model_agent_data, current_user.id)
        
        # 触发智能体创建事件（在实际实现中）
        # await event_bus.publish("agent.created", {"agent_id": agent.id, "project_id": project_id})
        
        return AgentResponse.model_validate(agent)
    except ResourceConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建智能体失败: {str(e)}"
        )

@router.get("/{agent_id}", response_model=AgentDetail)
async def get_agent_detail(
    agent_id: int = Path(...),
    agent: Annotated[dict, Depends(validate_agent_access)] = None,
    agent_service: Annotated[AgentService, Depends(get_agent_service)] = None
):
    """
    获取特定智能体的详细信息
    
    Args:
        agent_id: 智能体ID
        
    Returns:
        AgentDetail: 智能体详细信息
    """
    try:
        # validate_agent_access 依赖已经验证了访问权限并返回了智能体
        # 获取智能体额外信息如能力和状态
        capabilities = await agent_service.get_agent_capabilities(agent_id)
        
        # 如果智能体有活跃实例，获取实例状态
        instances = await agent_service.list_agent_instances(agent_id=agent_id, status="active", limit=1)
        status_info = {}
        if instances:
            status_info = await agent_service.get_agent_status(instances[0].id)
        
        # 构建详细响应
        agent_detail = AgentDetail(
            **AgentResponse.model_validate(agent).model_dump(),
            capabilities=capabilities,
            status=status_info,
            history=[]  # 这里可以添加历史记录的查询逻辑
        )
        
        return agent_detail
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取智能体详情失败: {str(e)}"
        )

@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: int = Path(...),
    agent_data: AgentUpdate = None,
    agent: Annotated[dict, Depends(validate_agent_access)] = None,
    agent_service: Annotated[AgentService, Depends(get_agent_service)] = None
):
    """
    更新智能体配置
    
    Args:
        agent_id: 智能体ID
        agent_data: 智能体更新数据
        
    Returns:
        AgentResponse: 更新后的智能体信息
    """
    try:
        # 转换API模型到服务层模型
        model_agent_data = ModelAgentUpdate(
            name=agent_data.name,
            config=agent_data.config
        )
        
        # 调用服务更新智能体
        updated_agent = await agent_service.update_agent(agent_id, model_agent_data)
        
        # 触发智能体更新事件（在实际实现中）
        # await event_bus.publish("agent.updated", {"agent_id": agent_id})
        
        return AgentResponse.model_validate(updated_agent)
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新智能体失败: {str(e)}"
        )

@router.delete("/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: int = Path(...),
    agent: Annotated[dict, Depends(validate_agent_access)] = None,
    agent_service: Annotated[AgentService, Depends(get_agent_service)] = None
):
    """
    从项目中删除智能体
    
    Args:
        agent_id: 智能体ID
    """
    try:
        await agent_service.delete_agent(agent_id)
        
        # 触发智能体删除事件（在实际实现中）
        # await event_bus.publish("agent.deleted", {"agent_id": agent_id})
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除智能体失败: {str(e)}"
        )

@router.get("/templates", response_model=List[AgentTemplateResponse])
async def get_agent_templates(
    current_user: Annotated[UserDB, Depends(get_current_user)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
    agent_type: Optional[str] = Query(None, description="过滤特定类型的模板")
):
    """
    获取智能体模板列表
    
    Args:
        agent_type: 可选，过滤特定类型的模板
        
    Returns:
        List[AgentTemplateResponse]: 智能体模板列表
    """
    try:
        # 查询用户可访问的模板（公开的和用户自己创建的）
        templates = await agent_service.list_agent_templates(
            user_id=current_user.id,
            agent_type=agent_type,
            is_public=True
        )
        
        return [AgentTemplateResponse.model_validate(template) for template in templates]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取智能体模板失败: {str(e)}"
        )
