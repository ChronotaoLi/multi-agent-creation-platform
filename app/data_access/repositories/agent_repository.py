"""
智能体数据Repository模块

提供智能体配置和状态相关的数据访问方法
"""
from typing import List, Optional, Dict, Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.agent import Agent, AgentState
from app.data_access.repositories.base_repository import BaseRepository


class AgentRepository(BaseRepository[Agent]):
    """智能体数据Repository
    
    提供智能体相关的数据访问方法
    """
    
    def __init__(self, db: AsyncSession):
        """初始化AgentRepository
        
        Args:
            db: 数据库会话
        """
        super().__init__(Agent, db)
    
    async def get_by_project(self, project_id: int, agent_type: Optional[str] = None) -> List[Agent]:
        """获取项目的智能体列表
        
        Args:
            project_id: 项目ID
            agent_type: 可选的智能体类型过滤条件
            
        Returns:
            List[Agent]: 智能体列表
        """
        # 构建基础查询
        query = select(Agent).where(Agent.project_id == project_id)
        
        # 如果指定了智能体类型，添加过滤条件
        if agent_type:
            query = query.where(Agent.agent_type == agent_type)
            
        # 执行查询
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def update_config(self, agent_id: int, config_data: Dict[str, Any]) -> Optional[Agent]:
        """更新智能体配置
        
        Args:
            agent_id: 智能体ID
            config_data: 新的配置数据
            
        Returns:
            Optional[Agent]: 更新后的智能体，如果不存在则返回None
        """
        # 获取智能体
        agent = await self.get_by_id(agent_id)
        if not agent:
            return None
            
        # 更新配置
        agent.config = config_data
        
        # 保存更改
        await self.db.commit()
        await self.db.refresh(agent)
        
        return agent
    
    async def save_state(self, agent_id: int, state_data: Dict[str, Any]) -> AgentState:
        """保存智能体状态
        
        Args:
            agent_id: 智能体ID
            state_data: 状态数据
            
        Returns:
            AgentState: 保存的状态
        """
        # 创建新状态记录
        agent_state = AgentState(
            agent_id=agent_id,
            state_data=state_data
        )
        
        # 保存到数据库
        self.db.add(agent_state)
        await self.db.commit()
        await self.db.refresh(agent_state)
        
        return agent_state
    
    async def get_latest_state(self, agent_id: int) -> Optional[AgentState]:
        """获取智能体的最新状态
        
        Args:
            agent_id: 智能体ID
            
        Returns:
            Optional[AgentState]: 最新状态，如果不存在则返回None
        """
        query = (
            select(AgentState)
            .where(AgentState.agent_id == agent_id)
            .order_by(AgentState.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def get_state_history(self, agent_id: int, limit: int = 10) -> List[AgentState]:
        """获取智能体的状态历史
        
        Args:
            agent_id: 智能体ID
            limit: 返回的最大状态数
            
        Returns:
            List[AgentState]: 状态历史列表
        """
        query = (
            select(AgentState)
            .where(AgentState.agent_id == agent_id)
            .order_by(AgentState.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all()) 