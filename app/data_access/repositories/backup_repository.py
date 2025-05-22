"""
备份存储仓库实现。

该模块提供了对状态备份数据的存储和检索功能。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union


class BackupRepository:
    """
    备份存储仓库，负责备份数据的持久化。
    """
    
    def __init__(self) -> None:
        """初始化备份存储仓库。"""
        # 使用内存字典作为临时存储，实际应用中应使用数据库
        self._backups: Dict[str, Dict[str, Any]] = {}
    
    def save_backup(
        self,
        backup_id: str,
        level: str,
        entity_id: str,
        data: bytes,
        description: Optional[str] = None,
        created_at: Optional[datetime] = None
    ) -> None:
        """
        保存备份数据。

        参数:
            backup_id: 备份ID
            level: 状态层级
            entity_id: 实体ID
            data: 备份数据（已压缩）
            description: 备份描述
            created_at: 创建时间
        """
        self._backups[backup_id] = {
            "backup_id": backup_id,
            "level": level,
            "entity_id": entity_id,
            "data": data,
            "description": description,
            "created_at": created_at or datetime.utcnow(),
            "size_bytes": len(data)
        }
    
    async def asave_backup(
        self,
        backup_id: str,
        level: str,
        entity_id: str,
        data: bytes,
        description: Optional[str] = None,
        created_at: Optional[datetime] = None
    ) -> None:
        """
        异步保存备份数据。

        参数:
            backup_id: 备份ID
            level: 状态层级
            entity_id: 实体ID
            data: 备份数据（已压缩）
            description: 备份描述
            created_at: 创建时间
        """
        # 异步版本，在内存实现中与同步版本相同
        self.save_backup(
            backup_id, level, entity_id, data, description, created_at
        )
    
    def get_backup(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """
        获取备份数据。

        参数:
            backup_id: 备份ID

        返回:
            Dict[str, Any]: 备份数据，若不存在则返回None
        """
        return self._backups.get(backup_id)
    
    async def aget_backup(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """
        异步获取备份数据。

        参数:
            backup_id: 备份ID

        返回:
            Dict[str, Any]: 备份数据，若不存在则返回None
        """
        # 异步版本，在内存实现中与同步版本相同
        return self.get_backup(backup_id)
    
    def list_backups(
        self, level: Optional[str] = None, entity_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        列出备份。

        参数:
            level: 状态层级（可选）
            entity_id: 实体ID（可选）

        返回:
            List[Dict[str, Any]]: 备份列表
        """
        backups = list(self._backups.values())
        
        # 根据条件过滤
        if level:
            backups = [b for b in backups if b["level"] == level]
        if entity_id:
            backups = [b for b in backups if b["entity_id"] == entity_id]
        
        # 排序：最新的排在前面
        backups.sort(key=lambda x: x["created_at"], reverse=True)
        
        # 移除实际数据以减少响应大小
        return [{k: v for k, v in b.items() if k != "data"} for b in backups]
    
    async def alist_backups(
        self, level: Optional[str] = None, entity_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        异步列出备份。

        参数:
            level: 状态层级（可选）
            entity_id: 实体ID（可选）

        返回:
            List[Dict[str, Any]]: 备份列表
        """
        # 异步版本，在内存实现中与同步版本相同
        return self.list_backups(level, entity_id)
    
    def delete_backup(self, backup_id: str) -> bool:
        """
        删除备份。

        参数:
            backup_id: 备份ID

        返回:
            bool: 操作是否成功
        """
        if backup_id in self._backups:
            del self._backups[backup_id]
            return True
        return False
    
    async def adelete_backup(self, backup_id: str) -> bool:
        """
        异步删除备份。

        参数:
            backup_id: 备份ID

        返回:
            bool: 操作是否成功
        """
        # 异步版本，在内存实现中与同步版本相同
        return self.delete_backup(backup_id) 