"""
状态备份服务实现。

该模块提供了对工作流状态的备份和恢复功能。
"""

import gzip
import json
import pickle
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.data_access.repositories.backup_repository import BackupRepository
from app.workflows.state_management.multi_level_manager import MultiLevelStateManager, StateLevel


class StateBackupService:
    """
    状态备份服务，负责备份和恢复工作流状态。
    
    支持对不同层级状态的完整备份和选择性恢复。
    """
    
    def __init__(
        self, 
        state_manager: MultiLevelStateManager,
        backup_repository: BackupRepository,
        compression_level: int = 9
    ) -> None:
        """
        初始化状态备份服务。

        参数:
            state_manager: 多层级状态管理器
            backup_repository: 备份存储仓库
            compression_level: 压缩级别 (0-9)，默认为最高压缩级别
        """
        self.state_manager = state_manager
        self.backup_repository = backup_repository
        self.compression_level = compression_level

    def create_backup(
        self, level: StateLevel, id: str, description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建状态备份。

        参数:
            level: 状态层级
            id: 状态ID（如会话ID、作业ID、项目ID）
            description: 备份描述信息

        返回:
            Dict[str, Any]: 备份元数据
        """
        # 获取当前状态
        state = self.state_manager.get_state(level, id)
        
        # 准备备份数据
        backup_data = {
            "state": state,
            "level": level.value,
            "id": id,
            "created_at": datetime.utcnow().isoformat(),
            "description": description
        }
        
        # 压缩备份数据
        compressed_data = self._compress_backup(backup_data)
        
        # 生成备份ID
        backup_id = str(uuid.uuid4())
        
        # 存储备份
        self.backup_repository.save_backup(
            backup_id=backup_id,
            level=level.value,
            entity_id=id,
            data=compressed_data,
            description=description,
            created_at=datetime.utcnow()
        )
        
        return {
            "backup_id": backup_id,
            "level": level.value,
            "entity_id": id,
            "created_at": datetime.utcnow().isoformat(),
            "description": description,
            "size_bytes": len(compressed_data)
        }

    async def acreate_backup(
        self, level: StateLevel, id: str, description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        异步创建状态备份。

        参数:
            level: 状态层级
            id: 状态ID（如会话ID、作业ID、项目ID）
            description: 备份描述信息

        返回:
            Dict[str, Any]: 备份元数据
        """
        # 异步获取当前状态
        state = await self.state_manager.aget_state(level, id)
        
        # 准备备份数据
        backup_data = {
            "state": state,
            "level": level.value,
            "id": id,
            "created_at": datetime.utcnow().isoformat(),
            "description": description
        }
        
        # 压缩备份数据
        compressed_data = self._compress_backup(backup_data)
        
        # 生成备份ID
        backup_id = str(uuid.uuid4())
        
        # 异步存储备份
        await self.backup_repository.asave_backup(
            backup_id=backup_id,
            level=level.value,
            entity_id=id,
            data=compressed_data,
            description=description,
            created_at=datetime.utcnow()
        )
        
        return {
            "backup_id": backup_id,
            "level": level.value,
            "entity_id": id,
            "created_at": datetime.utcnow().isoformat(),
            "description": description,
            "size_bytes": len(compressed_data)
        }

    def restore_backup(
        self, backup_id: str, target_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        从备份中恢复状态。

        参数:
            backup_id: 备份ID
            target_id: 目标状态ID，如果不提供则使用备份中的ID

        返回:
            Dict[str, Any]: 恢复操作的结果信息
        """
        # 获取备份
        backup = self.backup_repository.get_backup(backup_id)
        if not backup:
            raise ValueError(f"备份不存在: {backup_id}")
        
        # 解压备份数据
        backup_data = self._decompress_backup(backup["data"])
        
        # 确定恢复的目标ID
        restore_id = target_id if target_id else backup_data["id"]
        
        # 恢复状态
        level = StateLevel(backup_data["level"])
        state = backup_data["state"]
        
        # 添加恢复信息
        if "metadata" not in state:
            state["metadata"] = {}
        
        state["metadata"]["restore_info"] = {
            "restored_from": backup_id,
            "original_id": backup_data["id"],
            "restore_time": datetime.utcnow().isoformat(),
            "is_redirected": target_id is not None and target_id != backup_data["id"]
        }
        
        # 更新状态
        self.state_manager.update_state(level, restore_id, state)
        
        return {
            "backup_id": backup_id,
            "level": level.value,
            "original_id": backup_data["id"],
            "target_id": restore_id,
            "restore_time": datetime.utcnow().isoformat(),
            "success": True
        }

    async def arestore_backup(
        self, backup_id: str, target_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        异步从备份中恢复状态。

        参数:
            backup_id: 备份ID
            target_id: 目标状态ID，如果不提供则使用备份中的ID

        返回:
            Dict[str, Any]: 恢复操作的结果信息
        """
        # 异步获取备份
        backup = await self.backup_repository.aget_backup(backup_id)
        if not backup:
            raise ValueError(f"备份不存在: {backup_id}")
        
        # 解压备份数据
        backup_data = self._decompress_backup(backup["data"])
        
        # 确定恢复的目标ID
        restore_id = target_id if target_id else backup_data["id"]
        
        # 恢复状态
        level = StateLevel(backup_data["level"])
        state = backup_data["state"]
        
        # 添加恢复信息
        if "metadata" not in state:
            state["metadata"] = {}
        
        state["metadata"]["restore_info"] = {
            "restored_from": backup_id,
            "original_id": backup_data["id"],
            "restore_time": datetime.utcnow().isoformat(),
            "is_redirected": target_id is not None and target_id != backup_data["id"]
        }
        
        # 异步更新状态
        await self.state_manager.aupdate_state(level, restore_id, state)
        
        return {
            "backup_id": backup_id,
            "level": level.value,
            "original_id": backup_data["id"],
            "target_id": restore_id,
            "restore_time": datetime.utcnow().isoformat(),
            "success": True
        }

    def list_backups(
        self, level: Optional[StateLevel] = None, entity_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        列出可用的备份。

        参数:
            level: 可选的状态层级过滤
            entity_id: 可选的实体ID过滤

        返回:
            List[Dict[str, Any]]: 备份元数据列表
        """
        level_str = level.value if level else None
        return self.backup_repository.list_backups(level=level_str, entity_id=entity_id)

    async def alist_backups(
        self, level: Optional[StateLevel] = None, entity_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        异步列出可用的备份。

        参数:
            level: 可选的状态层级过滤
            entity_id: 可选的实体ID过滤

        返回:
            List[Dict[str, Any]]: 备份元数据列表
        """
        level_str = level.value if level else None
        return await self.backup_repository.alist_backups(level=level_str, entity_id=entity_id)

    def delete_backup(self, backup_id: str) -> bool:
        """
        删除备份。

        参数:
            backup_id: 备份ID

        返回:
            bool: 操作是否成功
        """
        return self.backup_repository.delete_backup(backup_id)

    async def adelete_backup(self, backup_id: str) -> bool:
        """
        异步删除备份。

        参数:
            backup_id: 备份ID

        返回:
            bool: 操作是否成功
        """
        return await self.backup_repository.adelete_backup(backup_id)

    def get_backup_metadata(self, backup_id: str) -> Dict[str, Any]:
        """
        获取备份元数据。

        参数:
            backup_id: 备份ID

        返回:
            Dict[str, Any]: 备份元数据
        """
        backup = self.backup_repository.get_backup(backup_id)
        if not backup:
            raise ValueError(f"备份不存在: {backup_id}")
        
        return {
            "backup_id": backup["backup_id"],
            "level": backup["level"],
            "entity_id": backup["entity_id"],
            "created_at": backup["created_at"].isoformat() if hasattr(backup["created_at"], "isoformat") else backup["created_at"],
            "description": backup["description"],
            "size_bytes": len(backup["data"]) if "data" in backup else None
        }

    async def aget_backup_metadata(self, backup_id: str) -> Dict[str, Any]:
        """
        异步获取备份元数据。

        参数:
            backup_id: 备份ID

        返回:
            Dict[str, Any]: 备份元数据
        """
        backup = await self.backup_repository.aget_backup(backup_id)
        if not backup:
            raise ValueError(f"备份不存在: {backup_id}")
        
        return {
            "backup_id": backup["backup_id"],
            "level": backup["level"],
            "entity_id": backup["entity_id"],
            "created_at": backup["created_at"].isoformat() if hasattr(backup["created_at"], "isoformat") else backup["created_at"],
            "description": backup["description"],
            "size_bytes": len(backup["data"]) if "data" in backup else None
        }

    def _compress_backup(self, data: Dict[str, Any]) -> bytes:
        """
        压缩备份数据。

        参数:
            data: 要压缩的数据

        返回:
            bytes: 压缩后的数据
        """
        # 使用pickle序列化数据，保留Python对象结构
        serialized = pickle.dumps(data)
        
        # 使用gzip进行压缩
        return gzip.compress(serialized, compresslevel=self.compression_level)

    def _decompress_backup(self, compressed_data: bytes) -> Dict[str, Any]:
        """
        解压备份数据。

        参数:
            compressed_data: 压缩的数据

        返回:
            Dict[str, Any]: 解压后的数据
        """
        # 解压缩
        decompressed = gzip.decompress(compressed_data)
        
        # 反序列化
        return pickle.loads(decompressed)
