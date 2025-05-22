"""
知识管理服务接口

定义知识管理相关的业务逻辑接口
"""
from typing import Optional, Protocol, List, Dict, Any, Tuple

from app.models.schemas import KnowledgeCreate, KnowledgeUpdate, KnowledgeItem, KnowledgeRelation


class KnowledgeService(Protocol):
    """知识管理服务接口
    
    定义知识管理相关的业务逻辑方法
    """
    
    async def search_knowledge(self, query: str, limit: int = 10, filters: Optional[dict] = None) -> list[KnowledgeItem]:
        """搜索知识
        
        Args:
            query: 搜索查询文本
            limit: 结果限制数量
            filters: 过滤条件（可选）
            
        Returns:
            list[KnowledgeItem]: 符合条件的知识项列表
        """
        ...
    
    async def add_knowledge(self, knowledge_data: KnowledgeCreate, user_id: int) -> KnowledgeItem:
        """添加知识
        
        Args:
            knowledge_data: 知识创建数据
            user_id: 创建者用户ID
            
        Returns:
            KnowledgeItem: 创建的知识项
            
        Raises:
            ResourceConflictError: 知识项已存在
        """
        ...
    
    async def get_knowledge_by_id(self, knowledge_id: int) -> Optional[KnowledgeItem]:
        """通过ID获取知识
        
        Args:
            knowledge_id: 知识ID
            
        Returns:
            Optional[KnowledgeItem]: 找到的知识项，如果不存在则返回None
        """
        ...
    
    async def update_knowledge(self, knowledge_id: int, knowledge_data: KnowledgeUpdate) -> KnowledgeItem:
        """更新知识
        
        Args:
            knowledge_id: 知识ID
            knowledge_data: 知识更新数据
            
        Returns:
            KnowledgeItem: 更新后的知识项
            
        Raises:
            ResourceNotFoundError: 知识项不存在
        """
        ...
    
    async def delete_knowledge(self, knowledge_id: int) -> None:
        """删除知识
        
        Args:
            knowledge_id: 知识ID
            
        Raises:
            ResourceNotFoundError: 知识项不存在
        """
        ...
    
    async def search_by_metadata(self, metadata_filter: dict, limit: int = 10) -> list[KnowledgeItem]:
        """通过元数据搜索知识
        
        Args:
            metadata_filter: 元数据过滤条件
            limit: 结果限制数量
            
        Returns:
            list[KnowledgeItem]: 符合条件的知识项列表
        """
        ...
    
    async def batch_add_knowledge(self, knowledge_data_list: list[KnowledgeCreate], user_id: int) -> list[KnowledgeItem]:
        """批量添加知识
        
        Args:
            knowledge_data_list: 知识创建数据列表
            user_id: 创建者用户ID
            
        Returns:
            list[KnowledgeItem]: 创建的知识项列表
            
        Raises:
            ResourceConflictError: 部分知识项已存在
        """
        ...
        
    async def extract_knowledge_graph(self, text: str, user_id: int) -> Tuple[list[KnowledgeItem], list[KnowledgeRelation]]:
        """从文本中提取知识图谱
        
        Args:
            text: 要分析的文本
            user_id: 用户ID
            
        Returns:
            Tuple[list[KnowledgeItem], list[KnowledgeRelation]]: 提取的知识项和关系
        """
        ...
        
    async def add_knowledge_relation(self, source_id: int, target_id: int, relation_type: str, properties: Optional[Dict[str, Any]] = None) -> KnowledgeRelation:
        """添加知识项之间的关系
        
        Args:
            source_id: 源知识项ID
            target_id: 目标知识项ID
            relation_type: 关系类型
            properties: 关系属性（可选）
            
        Returns:
            KnowledgeRelation: 创建的关系
            
        Raises:
            ResourceNotFoundError: 知识项不存在
        """
        ...
        
    async def get_related_knowledge(self, knowledge_id: int, relation_types: Optional[List[str]] = None, depth: int = 1) -> Tuple[list[KnowledgeItem], list[KnowledgeRelation]]:
        """获取与指定知识项相关的知识
        
        Args:
            knowledge_id: 知识项ID
            relation_types: 关系类型过滤（可选）
            depth: 图遍历深度
            
        Returns:
            Tuple[list[KnowledgeItem], list[KnowledgeRelation]]: 相关知识项和关系
            
        Raises:
            ResourceNotFoundError: 知识项不存在
        """
        ...
        
    async def hybrid_search(self, query: str, limit: int = 10, filters: Optional[dict] = None) -> list[KnowledgeItem]:
        """混合搜索（向量+全文）
        
        Args:
            query: 搜索查询文本
            limit: 结果限制数量
            filters: 过滤条件（可选）
            
        Returns:
            list[KnowledgeItem]: 符合条件的知识项列表
        """
        ...
        
    async def graph_rag_query(self, query: str, context_ids: Optional[List[int]] = None) -> str:
        """使用知识图谱增强的RAG进行查询
        
        Args:
            query: 查询文本
            context_ids: 上下文知识项ID列表（可选）
            
        Returns:
            str: 生成的回答
        """
        ...
