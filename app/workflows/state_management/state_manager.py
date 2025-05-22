"""
状态管理器实现。

该模块提供了对工作流状态的统一管理功能。
"""

from typing import Any, Dict, List, Optional, Set, Tuple, Union
import uuid
from datetime import datetime

from app.workflows.state_management.enhanced_store import EnhancedStoreManager
from app.workflows.state_management.multi_level_manager import MultiLevelStateManager, StateLevel
from app.workflows.state_management.state_backup_service import StateBackupService


class StateManager:
    """
    状态管理器，提供统一的状态管理接口。
    
    该类整合了多层级状态管理、备份/恢复和版本控制等功能。
    """
    
    def __init__(
        self,
        multi_level_manager: MultiLevelStateManager,
        backup_service: Optional[StateBackupService] = None,
    ) -> None:
        """
        初始化状态管理器。

        参数:
            multi_level_manager: 多层级状态管理器
            backup_service: 备份服务（可选）
        """
        self.multi_level_manager = multi_level_manager
        self.backup_service = backup_service
    
    def get_session_state(
        self, session_id: str, checkpoint_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取会话状态。

        参数:
            session_id: 会话ID
            checkpoint_id: 检查点ID（可选）

        返回:
            Dict[str, Any]: 会话状态
        """
        return self.multi_level_manager.get_state(StateLevel.SESSION, session_id, checkpoint_id)
    
    async def aget_session_state(
        self, session_id: str, checkpoint_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        异步获取会话状态。

        参数:
            session_id: 会话ID
            checkpoint_id: 检查点ID（可选）

        返回:
            Dict[str, Any]: 会话状态
        """
        return await self.multi_level_manager.aget_state(StateLevel.SESSION, session_id, checkpoint_id)
    
    def update_session_state(
        self, session_id: str, values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        更新会话状态。

        参数:
            session_id: 会话ID
            values: 要更新的值

        返回:
            Dict[str, Any]: 更新后的会话状态
        """
        return self.multi_level_manager.update_state(StateLevel.SESSION, session_id, values)
    
    async def aupdate_session_state(
        self, session_id: str, values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        异步更新会话状态。

        参数:
            session_id: 会话ID
            values: 要更新的值

        返回:
            Dict[str, Any]: 更新后的会话状态
        """
        return await self.multi_level_manager.aupdate_state(StateLevel.SESSION, session_id, values)
    
    def get_project_state(
        self, project_id: str, checkpoint_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取项目状态。

        参数:
            project_id: 项目ID
            checkpoint_id: 检查点ID（可选）

        返回:
            Dict[str, Any]: 项目状态
        """
        return self.multi_level_manager.get_state(StateLevel.PROJECT, project_id, checkpoint_id)
    
    async def aget_project_state(
        self, project_id: str, checkpoint_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        异步获取项目状态。

        参数:
            project_id: 项目ID
            checkpoint_id: 检查点ID（可选）

        返回:
            Dict[str, Any]: 项目状态
        """
        return await self.multi_level_manager.aget_state(StateLevel.PROJECT, project_id, checkpoint_id)
    
    def update_project_state(
        self, project_id: str, values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        更新项目状态。

        参数:
            project_id: 项目ID
            values: 要更新的值

        返回:
            Dict[str, Any]: 更新后的项目状态
        """
        return self.multi_level_manager.update_state(StateLevel.PROJECT, project_id, values)
    
    async def aupdate_project_state(
        self, project_id: str, values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        异步更新项目状态。

        参数:
            project_id: 项目ID
            values: 要更新的值

        返回:
            Dict[str, Any]: 更新后的项目状态
        """
        return await self.multi_level_manager.aupdate_state(StateLevel.PROJECT, project_id, values)
    
    def get_global_state(self) -> Dict[str, Any]:
        """
        获取全局状态。

        返回:
            Dict[str, Any]: 全局状态
        """
        return self.multi_level_manager.get_state(StateLevel.GLOBAL, "global")
    
    async def aget_global_state(self) -> Dict[str, Any]:
        """
        异步获取全局状态。

        返回:
            Dict[str, Any]: 全局状态
        """
        return await self.multi_level_manager.aget_state(StateLevel.GLOBAL, "global")
    
    def update_global_state(self, values: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新全局状态。

        参数:
            values: 要更新的值

        返回:
            Dict[str, Any]: 更新后的全局状态
        """
        return self.multi_level_manager.update_state(StateLevel.GLOBAL, "global", values)
    
    async def aupdate_global_state(self, values: Dict[str, Any]) -> Dict[str, Any]:
        """
        异步更新全局状态。

        参数:
            values: 要更新的值

        返回:
            Dict[str, Any]: 更新后的全局状态
        """
        return await self.multi_level_manager.aupdate_state(StateLevel.GLOBAL, "global", values)
    
    def backup_state(
        self, level: StateLevel, id: str, description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        备份状态。

        参数:
            level: 状态级别
            id: 状态ID
            description: 备份描述

        返回:
            Dict[str, Any]: 备份元数据
        """
        if not self.backup_service:
            raise ValueError("备份服务未初始化")
        
        return self.backup_service.create_backup(level, id, description)
    
    async def abackup_state(
        self, level: StateLevel, id: str, description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        异步备份状态。

        参数:
            level: 状态级别
            id: 状态ID
            description: 备份描述

        返回:
            Dict[str, Any]: 备份元数据
        """
        if not self.backup_service:
            raise ValueError("备份服务未初始化")
        
        return await self.backup_service.acreate_backup(level, id, description)
    
    def restore_state(
        self, backup_id: str, target_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        恢复状态。

        参数:
            backup_id: 备份ID
            target_id: 目标ID（可选）

        返回:
            Dict[str, Any]: 恢复操作结果
        """
        if not self.backup_service:
            raise ValueError("备份服务未初始化")
        
        return self.backup_service.restore_backup(backup_id, target_id)
    
    async def arestore_state(
        self, backup_id: str, target_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        异步恢复状态。

        参数:
            backup_id: 备份ID
            target_id: 目标ID（可选）

        返回:
            Dict[str, Any]: 恢复操作结果
        """
        if not self.backup_service:
            raise ValueError("备份服务未初始化")
        
        return await self.backup_service.arestore_backup(backup_id, target_id)
    
    def list_backups(
        self, level: Optional[StateLevel] = None, id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        列出备份。

        参数:
            level: 状态级别（可选）
            id: 状态ID（可选）

        返回:
            List[Dict[str, Any]]: 备份列表
        """
        if not self.backup_service:
            raise ValueError("备份服务未初始化")
        
        return self.backup_service.list_backups(level, id)
    
    async def alist_backups(
        self, level: Optional[StateLevel] = None, id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        异步列出备份。

        参数:
            level: 状态级别（可选）
            id: 状态ID（可选）

        返回:
            List[Dict[str, Any]]: 备份列表
        """
        if not self.backup_service:
            raise ValueError("备份服务未初始化")
        
        return await self.backup_service.alist_backups(level, id)
        
    def get_state_history(
        self, level: StateLevel, id: str
    ) -> List[Dict[str, Any]]:
        """
        获取状态历史。

        参数:
            level: 状态级别
            id: 状态ID

        返回:
            List[Dict[str, Any]]: 状态历史
        """
        return self.multi_level_manager.get_history(level, id)
    
    async def aget_state_history(
        self, level: StateLevel, id: str
    ) -> List[Dict[str, Any]]:
        """
        异步获取状态历史。

        参数:
            level: 状态级别
            id: 状态ID

        返回:
            List[Dict[str, Any]]: 状态历史
        """
        return await self.multi_level_manager.aget_history(level, id) 