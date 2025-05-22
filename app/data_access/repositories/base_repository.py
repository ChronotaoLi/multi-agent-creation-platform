"""
基础Repository模块

定义所有Repository共用的基类和接口
"""
from typing import Dict, Generic, List, Optional, Type, TypeVar, Union, Any

from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.data_access.db_session import Base

# 定义泛型类型变量，用于表示ORM模型类型
T = TypeVar('T', bound=Base)


class BaseRepository(Generic[T]):
    """所有Repository的基类
    
    提供通用的数据访问方法
    
    Attributes:
        model: ORM模型类
        db: 数据库会话
    """
    
    def __init__(self, model: Type[T], db: AsyncSession):
        """初始化Repository
        
        Args:
            model: ORM模型类
            db: 数据库会话
        """
        self.model = model
        self.db = db
    
    async def get_by_id(self, id: Union[int, str]) -> Optional[T]:
        """通过ID获取实体
        
        Args:
            id: 实体ID
            
        Returns:
            Optional[T]: 找到的实体，如果不存在则返回None
        """
        query = select(self.model).where(self.model.id == id)
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """获取所有实体（分页）
        
        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            List[T]: 实体列表
        """
        query = select(self.model).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def create(self, obj_in: Dict[str, Any]) -> T:
        """创建实体
        
        Args:
            obj_in: 创建实体的数据
            
        Returns:
            T: 创建的实体
        """
        obj = self.model(**obj_in)  # type: ignore
        self.db.add(obj)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj
    
    async def update(self, id: Union[int, str], obj_in: Dict[str, Any]) -> Optional[T]:
        """更新实体
        
        Args:
            id: 实体ID
            obj_in: 更新实体的数据
            
        Returns:
            Optional[T]: 更新后的实体，如果不存在则返回None
        """
        # 先获取要更新的对象
        obj = await self.get_by_id(id)
        if not obj:
            return None
        
        # 构建更新语句
        stmt = (
            update(self.model)
            .where(self.model.id == id)
            .values(**obj_in)
            .execution_options(synchronize_session="fetch")
        )
        
        await self.db.execute(stmt)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj
    
    async def delete(self, id: Union[int, str]) -> None:
        """删除实体
        
        Args:
            id: 实体ID
        """
        stmt = delete(self.model).where(self.model.id == id)
        await self.db.execute(stmt)
        await self.db.commit()
    
    async def exists(self, id: Union[int, str]) -> bool:
        """检查实体是否存在
        
        Args:
            id: 实体ID
            
        Returns:
            bool: 实体是否存在
        """
        query = select(func.count(self.model.id)).where(self.model.id == id)
        result = await self.db.execute(query)
        return result.scalar() > 0
    
    async def count(self, **filters) -> int:
        """计算满足条件的实体数量
        
        Args:
            **filters: 过滤条件
            
        Returns:
            int: 实体数量
        """
        query = select(func.count(self.model.id))
        
        # 添加过滤条件
        for attr, value in filters.items():
            if hasattr(self.model, attr):
                query = query.where(getattr(self.model, attr) == value)
        
        result = await self.db.execute(query)
        return result.scalar()
