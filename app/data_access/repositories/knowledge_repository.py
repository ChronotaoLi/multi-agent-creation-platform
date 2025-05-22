"""
知识库数据Repository模块

提供知识项和知识关系相关的数据访问方法
"""
from typing import List, Optional, Dict, Any

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.knowledge import KnowledgeItem, KnowledgeRelation
from app.data_access.repositories.base_repository import BaseRepository


class KnowledgeRepository(BaseRepository[KnowledgeItem]):
    """知识库数据Repository
    
    提供知识项相关的数据访问方法
    """
    
    def __init__(self, db: AsyncSession):
        """初始化KnowledgeRepository
        
        Args:
            db: 数据库会话
        """
        super().__init__(KnowledgeItem, db)
    
    async def search_by_metadata(self, metadata_filters: Dict[str, Any]) -> List[KnowledgeItem]:
        """基于元数据搜索知识项
        
        Args:
            metadata_filters: 元数据过滤条件，键值对形式
            
        Returns:
            List[KnowledgeItem]: 符合条件的知识项列表
        """
        # 构建查询
        query = select(KnowledgeItem)
        
        # 对于PostgreSQL可以使用JSONB操作符，但这里使用通用方法
        # 在实际应用中，可以根据数据库类型优化此查询
        # 这里简化处理，假设前端传来的是精确匹配
        result = await self.db.execute(query)
        items = list(result.scalars().all())
        
        # 在Python中过滤，实际应用中应优化为数据库级别过滤
        filtered_items = []
        for item in items:
            if not metadata_filters:
                filtered_items.append(item)
                continue
                
            match = True
            for key, value in metadata_filters.items():
                if key not in item.metadata or item.metadata[key] != value:
                    match = False
                    break
                    
            if match:
                filtered_items.append(item)
                
        return filtered_items
    
    async def update_vector_id(self, knowledge_id: int, vector_id: str) -> Optional[KnowledgeItem]:
        """更新知识项的向量ID
        
        用于将关系数据库中的知识项与向量数据库中的向量关联
        
        Args:
            knowledge_id: 知识项ID
            vector_id: 向量数据库中的ID
            
        Returns:
            Optional[KnowledgeItem]: 更新后的知识项，如果不存在则返回None
        """
        # 获取知识项
        item = await self.get_by_id(knowledge_id)
        if not item:
            return None
            
        # 更新向量ID
        item.vector_id = vector_id
        
        # 保存更改
        await self.db.commit()
        await self.db.refresh(item)
        
        return item
    
    async def update_node_id(self, knowledge_id: int, node_id: str) -> Optional[KnowledgeItem]:
        """更新知识项的图节点ID
        
        用于将关系数据库中的知识项与图数据库中的节点关联
        
        Args:
            knowledge_id: 知识项ID
            node_id: 图数据库中的节点ID
            
        Returns:
            Optional[KnowledgeItem]: 更新后的知识项，如果不存在则返回None
        """
        # 获取知识项
        item = await self.get_by_id(knowledge_id)
        if not item:
            return None
            
        # 更新节点ID
        item.node_id = node_id
        
        # 保存更改
        await self.db.commit()
        await self.db.refresh(item)
        
        return item
    
    async def create_relation(self, source_id: int, target_id: int, relation_type: str, 
                             metadata: Optional[Dict[str, Any]] = None) -> KnowledgeRelation:
        """创建知识项之间的关系
        
        Args:
            source_id: 源知识项ID
            target_id: 目标知识项ID
            relation_type: 关系类型
            metadata: 可选的关系元数据
            
        Returns:
            KnowledgeRelation: 创建的关系
        """
        # 创建关系
        relation = KnowledgeRelation(
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            metadata=metadata or {}
        )
        
        # 保存到数据库
        self.db.add(relation)
        await self.db.commit()
        await self.db.refresh(relation)
        
        return relation
    
    async def get_relations(self, item_id: int, relation_type: Optional[str] = None, 
                           as_source: bool = True, as_target: bool = True) -> List[KnowledgeRelation]:
        """获取知识项的关系
        
        Args:
            item_id: 知识项ID
            relation_type: 可选的关系类型过滤条件
            as_source: 是否包含作为源的关系
            as_target: 是否包含作为目标的关系
            
        Returns:
            List[KnowledgeRelation]: 关系列表
        """
        # 构建查询条件
        conditions = []
        
        if as_source:
            conditions.append(KnowledgeRelation.source_id == item_id)
            
        if as_target:
            conditions.append(KnowledgeRelation.target_id == item_id)
            
        # 没有指定源或目标时，返回空列表
        if not conditions:
            return []
            
        # 构建基础查询
        query = select(KnowledgeRelation).where(or_(*conditions))
        
        # 如果指定了关系类型，添加过滤条件
        if relation_type:
            query = query.where(KnowledgeRelation.relation_type == relation_type)
            
        # 执行查询
        result = await self.db.execute(query)
        return list(result.scalars().all())
