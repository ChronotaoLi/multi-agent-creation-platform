"""
智能体管理服务实现

实现智能体相关的业务逻辑
"""
from typing import Optional, List, Dict
import logging
import json
from datetime import datetime

from app.data_access.repositories.agent_repository import AgentRepository
from app.models.schemas import AgentTypeInfo, Agent, AgentCreate, AgentUpdate
from app.services.interfaces.agent_service import AgentService
from app.services.interfaces.project_service import ProjectService
from app.utils.error_handlers import ResourceNotFoundError, InvalidInputError
from app.utils.validators import validate_json_schema


class AgentServiceImpl:
    """智能体管理服务实现类
    
    实现AgentService接口的所有方法
    """
    
    # 智能体类型与配置模式定义
    AGENT_TYPES = {
        "coordinator": {
            "display_name": "协调智能体",
            "description": "负责任务分解、规划和分配",
            "schema": {
                "type": "object",
                "required": ["model", "temperature"],
                "properties": {
                    "model": {
                        "type": "string",
                        "description": "使用的LLM模型名称"
                    },
                    "temperature": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "生成温度，控制创造性"
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "最大生成令牌数"
                    },
                    "tools_access": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "可访问的工具列表"
                    }
                }
            }
        },
        "character": {
            "display_name": "角色智能体",
            "description": "处理角色相关逻辑和行为",
            "schema": {
                "type": "object",
                "required": ["model", "character_profile"],
                "properties": {
                    "model": {
                        "type": "string",
                        "description": "使用的LLM模型名称"
                    },
                    "character_profile": {
                        "type": "object",
                        "required": ["name", "background"],
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "角色名称"
                            },
                            "background": {
                                "type": "string",
                                "description": "角色背景故事"
                            },
                            "personality": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                },
                                "description": "性格特点列表"
                            },
                            "motivations": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                },
                                "description": "动机列表"
                            }
                        }
                    },
                    "temperature": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "生成温度，控制创造性"
                    }
                }
            }
        },
        "content": {
            "display_name": "内容智能体",
            "description": "负责生成故事内容",
            "schema": {
                "type": "object",
                "required": ["model", "content_type"],
                "properties": {
                    "model": {
                        "type": "string",
                        "description": "使用的LLM模型名称"
                    },
                    "content_type": {
                        "type": "string",
                        "enum": ["story", "dialogue", "scene", "description"],
                        "description": "内容类型"
                    },
                    "style_guide": {
                        "type": "string",
                        "description": "风格指南"
                    },
                    "temperature": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "生成温度，控制创造性"
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "最大生成令牌数"
                    }
                }
            }
        },
        "review": {
            "display_name": "审核智能体",
            "description": "负责内容审核和质量控制",
            "schema": {
                "type": "object",
                "required": ["model", "review_criteria"],
                "properties": {
                    "model": {
                        "type": "string",
                        "description": "使用的LLM模型名称"
                    },
                    "review_criteria": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "审核标准列表"
                    },
                    "strictness_level": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "严格程度"
                    },
                    "temperature": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "生成温度，控制创造性"
                    }
                }
            }
        },
        "memory": {
            "display_name": "记忆智能体",
            "description": "管理上下文和历史信息",
            "schema": {
                "type": "object",
                "required": ["model", "memory_type"],
                "properties": {
                    "model": {
                        "type": "string",
                        "description": "使用的LLM模型名称"
                    },
                    "memory_type": {
                        "type": "string",
                        "enum": ["short_term", "long_term", "hybrid"],
                        "description": "记忆类型"
                    },
                    "vector_store": {
                        "type": "string",
                        "description": "向量存储配置"
                    },
                    "summarization_interval": {
                        "type": "integer",
                        "description": "摘要生成间隔（消息数）"
                    },
                    "temperature": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "生成温度，控制创造性"
                    }
                }
            }
        }
    }
    
    def __init__(
        self,
        agent_repository: AgentRepository,
        project_service: ProjectService,
    ):
        """初始化智能体服务
        
        Args:
            agent_repository: 智能体数据Repository
            project_service: 项目服务
        """
        self.agent_repository = agent_repository
        self.project_service = project_service
        self.logger = logging.getLogger(__name__)
    
    async def get_agent_types(self) -> list[AgentTypeInfo]:
        """获取智能体类型列表
        
        Returns:
            list[AgentTypeInfo]: 智能体类型信息列表
        """
        agent_types = []
        for agent_type, info in self.AGENT_TYPES.items():
            agent_types.append(
                AgentTypeInfo(
                    type=agent_type,
                    display_name=info["display_name"],
                    description=info["description"],
                    config_schema=info["schema"]
                )
            )
        return agent_types
    
    async def get_project_agents(self, project_id: int) -> list[Agent]:
        """获取项目的智能体列表
        
        Args:
            project_id: 项目ID
            
        Returns:
            list[Agent]: 智能体列表
            
        Raises:
            ResourceNotFoundError: 项目不存在
        """
        # 验证项目是否存在
        project = await self.project_service.get_project_by_id(project_id)
        if not project:
            self.logger.error(f"Project with id {project_id} not found when getting agents")
            raise ResourceNotFoundError(f"项目(ID: {project_id})不存在")
        
        return await self.agent_repository.get_by_project_id(project_id)
    
    async def add_agent_to_project(self, project_id: int, agent_data: AgentCreate) -> Agent:
        """添加智能体到项目
        
        Args:
            project_id: 项目ID
            agent_data: 智能体创建数据
            
        Returns:
            Agent: 创建的智能体
            
        Raises:
            ResourceNotFoundError: 项目不存在
            InvalidInputError: 智能体配置无效
        """
        # 验证项目是否存在
        project = await self.project_service.get_project_by_id(project_id)
        if not project:
            self.logger.error(f"Project with id {project_id} not found when adding agent")
            raise ResourceNotFoundError(f"项目(ID: {project_id})不存在")
        
        # 验证智能体类型和配置
        if not await self.validate_agent_config(agent_data.agent_type, agent_data.config):
            self.logger.error(f"Invalid agent configuration for type {agent_data.agent_type}")
            raise InvalidInputError(f"智能体配置无效")
        
        # 创建智能体
        agent = await self.agent_repository.create(
            name=agent_data.name,
            agent_type=agent_data.agent_type,
            config=agent_data.config,
            project_id=project_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        self.logger.info(f"Agent created: {agent.id} for project: {project_id}")
        return agent
    
    async def get_agent_by_id(self, agent_id: int) -> Optional[Agent]:
        """通过ID获取智能体
        
        Args:
            agent_id: 智能体ID
            
        Returns:
            Optional[Agent]: 找到的智能体，如果不存在则返回None
        """
        return await self.agent_repository.get_by_id(agent_id)
    
    async def update_agent(self, agent_id: int, agent_data: AgentUpdate) -> Agent:
        """更新智能体
        
        Args:
            agent_id: 智能体ID
            agent_data: 智能体更新数据
            
        Returns:
            Agent: 更新后的智能体
            
        Raises:
            ResourceNotFoundError: 智能体不存在
            InvalidInputError: 智能体配置无效
        """
        # 验证智能体是否存在
        agent = await self.agent_repository.get_by_id(agent_id)
        if not agent:
            self.logger.error(f"Agent with id {agent_id} not found when updating")
            raise ResourceNotFoundError(f"智能体(ID: {agent_id})不存在")
        
        update_data = agent_data.model_dump(exclude_unset=True)
        
        # 如果更新包含配置，验证配置有效性
        if "config" in update_data:
            if not await self.validate_agent_config(agent.agent_type, update_data["config"]):
                self.logger.error(f"Invalid agent configuration for type {agent.agent_type}")
                raise InvalidInputError(f"智能体配置无效")
        
        # 添加更新时间
        update_data["updated_at"] = datetime.utcnow()
        
        # 更新智能体
        updated_agent = await self.agent_repository.update(agent_id, update_data)
        
        self.logger.info(f"Agent updated: {agent_id}")
        return updated_agent
    
    async def remove_agent(self, agent_id: int) -> None:
        """移除智能体
        
        Args:
            agent_id: 智能体ID
            
        Raises:
            ResourceNotFoundError: 智能体不存在
        """
        # 验证智能体是否存在
        agent = await self.agent_repository.get_by_id(agent_id)
        if not agent:
            self.logger.error(f"Agent with id {agent_id} not found when removing")
            raise ResourceNotFoundError(f"智能体(ID: {agent_id})不存在")
        
        # 删除智能体
        await self.agent_repository.delete(agent_id)
        
        self.logger.info(f"Agent removed: {agent_id}")
    
    async def get_agent_config(self, agent_id: int) -> dict:
        """获取智能体配置
        
        Args:
            agent_id: 智能体ID
            
        Returns:
            dict: 智能体配置
            
        Raises:
            ResourceNotFoundError: 智能体不存在
        """
        # 验证智能体是否存在
        agent = await self.agent_repository.get_by_id(agent_id)
        if not agent:
            self.logger.error(f"Agent with id {agent_id} not found when getting config")
            raise ResourceNotFoundError(f"智能体(ID: {agent_id})不存在")
        
        return agent.config
    
    async def validate_agent_config(self, agent_type: str, config: dict) -> bool:
        """验证智能体配置
        
        Args:
            agent_type: 智能体类型
            config: 配置数据
            
        Returns:
            bool: 配置是否有效
            
        Raises:
            InvalidInputError: 智能体类型不存在
        """
        # 验证智能体类型是否存在
        if agent_type not in self.AGENT_TYPES:
            self.logger.error(f"Agent type {agent_type} not found")
            raise InvalidInputError(f"智能体类型 '{agent_type}' 不存在")
        
        # 获取配置模式
        schema = self.AGENT_TYPES[agent_type]["schema"]
        
        # 验证配置是否符合模式
        is_valid, errors = validate_json_schema(config, schema)
        
        if not is_valid:
            self.logger.error(f"Invalid agent configuration: {errors}")
            return False
        
        return True
