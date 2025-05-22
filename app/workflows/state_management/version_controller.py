"""
版本控制器实现。

该模块提供了对状态版本的控制功能，支持回滚到历史版本等版本管理能力。
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from app.workflows.state_management.multi_level_manager import MultiLevelStateManager, StateLevel


class VersionController:
    """
    版本控制器，负责管理状态版本控制。
    
    提供对状态历史版本的管理、比较和回滚能力。
    """
    
    def __init__(self, state_manager: MultiLevelStateManager) -> None:
        """
        初始化版本控制器。

        参数:
            state_manager: 多层级状态管理器
        """
        self.state_manager = state_manager

    def get_version_history(self, level: StateLevel, id: str) -> List[Dict[str, Any]]:
        """
        获取状态版本历史。

        参数:
            level: 状态层级
            id: 状态ID（如会话ID、作业ID、项目ID）

        返回:
            List[Dict[str, Any]]: 版本历史记录列表
        """
        # 通过多层级状态管理器获取历史
        history = self.state_manager.get_history(level, id)
        
        # 格式化版本历史信息
        return [
            {
                "version_id": item["id"],
                "timestamp": item["timestamp"],
                "metadata": self._extract_metadata(item["state"])
            }
            for item in history
        ]

    async def aget_version_history(self, level: StateLevel, id: str) -> List[Dict[str, Any]]:
        """
        异步获取状态版本历史。

        参数:
            level: 状态层级
            id: 状态ID（如会话ID、作业ID、项目ID）

        返回:
            List[Dict[str, Any]]: 版本历史记录列表
        """
        # 通过多层级状态管理器获取历史
        history = await self.state_manager.aget_history(level, id)
        
        # 格式化版本历史信息
        return [
            {
                "version_id": item["id"],
                "timestamp": item["timestamp"],
                "metadata": self._extract_metadata(item["state"])
            }
            for item in history
        ]

    def _extract_metadata(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        从状态数据中提取元数据。

        参数:
            state: 状态数据

        返回:
            Dict[str, Any]: 元数据
        """
        metadata = {}
        
        # 尝试提取常见元数据字段
        if "metadata" in state:
            metadata = state["metadata"]
        else:
            # 提取可能的元数据字段
            for key in ["version", "created_at", "updated_at", "step", "checkpoint_info"]:
                if key in state:
                    metadata[key] = state[key]
        
        return metadata

    def rollback(self, level: StateLevel, id: str, version_id: str) -> Dict[str, Any]:
        """
        回滚到指定的历史版本。

        参数:
            level: 状态层级
            id: 状态ID（如会话ID、作业ID、项目ID）
            version_id: 要回滚到的版本ID

        返回:
            Dict[str, Any]: 回滚后的状态
        """
        # 获取指定版本的状态
        historic_state = self.state_manager.get_state(level, id, version_id)
        
        # 将当前状态更新为历史版本状态，并添加回滚标记
        historic_state["metadata"] = historic_state.get("metadata", {})
        historic_state["metadata"]["rollback_info"] = {
            "rollback_from": version_id,
            "rollback_time": datetime.utcnow().isoformat(),
        }
        
        # 更新当前状态
        return self.state_manager.update_state(level, id, historic_state)

    async def arollback(self, level: StateLevel, id: str, version_id: str) -> Dict[str, Any]:
        """
        异步回滚到指定的历史版本。

        参数:
            level: 状态层级
            id: 状态ID（如会话ID、作业ID、项目ID）
            version_id: 要回滚到的版本ID

        返回:
            Dict[str, Any]: 回滚后的状态
        """
        # 异步获取指定版本的状态
        historic_state = await self.state_manager.aget_state(level, id, version_id)
        
        # 将当前状态更新为历史版本状态，并添加回滚标记
        historic_state["metadata"] = historic_state.get("metadata", {})
        historic_state["metadata"]["rollback_info"] = {
            "rollback_from": version_id,
            "rollback_time": datetime.utcnow().isoformat(),
        }
        
        # 异步更新当前状态
        return await self.state_manager.aupdate_state(level, id, historic_state)

    def compare_versions(
        self, level: StateLevel, id: str, version_id1: str, version_id2: str
    ) -> Dict[str, Any]:
        """
        比较两个版本的状态差异。

        参数:
            level: 状态层级
            id: 状态ID（如会话ID、作业ID、项目ID）
            version_id1: 第一个版本ID
            version_id2: 第二个版本ID

        返回:
            Dict[str, Any]: 差异信息
        """
        # 获取两个版本的状态
        state1 = self.state_manager.get_state(level, id, version_id1)
        state2 = self.state_manager.get_state(level, id, version_id2)
        
        # 计算差异
        differences = self._compute_differences(state1, state2)
        
        return {
            "version1": version_id1,
            "version2": version_id2,
            "differences": differences
        }

    async def acompare_versions(
        self, level: StateLevel, id: str, version_id1: str, version_id2: str
    ) -> Dict[str, Any]:
        """
        异步比较两个版本的状态差异。

        参数:
            level: 状态层级
            id: 状态ID（如会话ID、作业ID、项目ID）
            version_id1: 第一个版本ID
            version_id2: 第二个版本ID

        返回:
            Dict[str, Any]: 差异信息
        """
        # 异步获取两个版本的状态
        state1 = await self.state_manager.aget_state(level, id, version_id1)
        state2 = await self.state_manager.aget_state(level, id, version_id2)
        
        # 计算差异
        differences = self._compute_differences(state1, state2)
        
        return {
            "version1": version_id1,
            "version2": version_id2,
            "differences": differences
        }

    def _compute_differences(self, state1: Dict[str, Any], state2: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算两个状态之间的差异。

        参数:
            state1: 第一个状态
            state2: 第二个状态

        返回:
            Dict[str, Any]: 差异信息
        """
        differences = {
            "added": {},
            "removed": {},
            "modified": {}
        }
        
        # 获取所有键集合
        all_keys = set(state1.keys()) | set(state2.keys())
        
        for key in all_keys:
            # 如果键只在 state2 中存在，则为新增
            if key not in state1:
                differences["added"][key] = state2[key]
            # 如果键只在 state1 中存在，则为删除
            elif key not in state2:
                differences["removed"][key] = state1[key]
            # 如果键在两个状态中都存在但值不同，则为修改
            elif state1[key] != state2[key]:
                differences["modified"][key] = {
                    "from": state1[key],
                    "to": state2[key]
                }
        
        return differences

    def fork_version(self, level: StateLevel, source_id: str, target_id: str, version_id: Optional[str] = None) -> Dict[str, Any]:
        """
        从指定版本派生新版本。

        参数:
            level: 状态层级
            source_id: 源状态ID
            target_id: 目标状态ID
            version_id: 指定的版本ID，若不提供则使用最新版本

        返回:
            Dict[str, Any]: 派生的新状态
        """
        # 获取源状态
        source_state = self.state_manager.get_state(level, source_id, version_id)
        
        # 添加派生信息
        forked_state = source_state.copy()
        forked_state["metadata"] = forked_state.get("metadata", {})
        forked_state["metadata"]["fork_info"] = {
            "forked_from": source_id,
            "original_version": version_id,
            "fork_time": datetime.utcnow().isoformat(),
        }
        
        # 更新目标状态
        return self.state_manager.update_state(level, target_id, forked_state)

    async def afork_version(self, level: StateLevel, source_id: str, target_id: str, version_id: Optional[str] = None) -> Dict[str, Any]:
        """
        异步从指定版本派生新版本。

        参数:
            level: 状态层级
            source_id: 源状态ID
            target_id: 目标状态ID
            version_id: 指定的版本ID，若不提供则使用最新版本

        返回:
            Dict[str, Any]: 派生的新状态
        """
        # 异步获取源状态
        source_state = await self.state_manager.aget_state(level, source_id, version_id)
        
        # 添加派生信息
        forked_state = source_state.copy()
        forked_state["metadata"] = forked_state.get("metadata", {})
        forked_state["metadata"]["fork_info"] = {
            "forked_from": source_id,
            "original_version": version_id,
            "fork_time": datetime.utcnow().isoformat(),
        }
        
        # 异步更新目标状态
        return await self.state_manager.aupdate_state(level, target_id, forked_state)
