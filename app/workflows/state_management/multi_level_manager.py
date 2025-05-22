"""
多层级状态管理器实现。

该模块提供了对不同级别（会话、作业、项目、全局）状态的管理功能。
"""

import enum
from typing import Any, Dict, List, Optional, Tuple, Protocol, Iterator, AsyncIterator

# 定义BaseSaver协议，替代导入
class BaseSaver(Protocol):
    """检查点保存器协议。"""
    
    def get(self, config: Dict[str, Any]) -> Any:
        """获取检查点。"""
        ...
    
    async def aget(self, config: Dict[str, Any]) -> Any:
        """异步获取检查点。"""
        ...
    
    def put(self, config: Dict[str, Any], checkpoint: Any, metadata: Dict[str, Any], new_versions: Dict[str, Any]) -> Dict[str, Any]:
        """存储检查点。"""
        ...
    
    async def aput(self, config: Dict[str, Any], checkpoint: Any, metadata: Dict[str, Any], new_versions: Dict[str, Any]) -> Dict[str, Any]:
        """异步存储检查点。"""
        ...
    
    def list(self, config: Dict[str, Any], **kwargs) -> Iterator[Dict[str, Any]]:
        """列出检查点。"""
        ...
    
    async def alist(self, config: Dict[str, Any], **kwargs) -> AsyncIterator[Dict[str, Any]]:
        """异步列出检查点。"""
        ...

from app.workflows.state_management.enhanced_store import EnhancedStoreManager


class StateLevel(enum.Enum):
    """状态层级类型枚举。"""
    
    SESSION = "session"  # 会话级状态
    JOB = "job"          # 作业级状态
    PROJECT = "project"  # 项目级状态
    GLOBAL = "global"    # 全局状态


class MultiLevelStateManager:
    """
    多层级状态管理器，管理不同级别的状态层次。
    """
    
    def __init__(
        self,
        store_manager: EnhancedStoreManager,
        checkpointer: BaseSaver
    ) -> None:
        """
        初始化多层级状态管理器。

        参数:
            store_manager: 存储管理器
            checkpointer: 检查点保存器
        """
        self.store_manager = store_manager
        self.checkpointer = checkpointer

    def _get_namespace(self, level: StateLevel) -> Tuple[str, ...]:
        """
        根据状态层级获取命名空间。

        参数:
            level: 状态层级

        返回:
            Tuple[str, ...]: 命名空间元组
        """
        # 返回不同级别的命名空间前缀
        return (f"multi_agent_platform:{level.value}",)

    def get_state(
        self, level: StateLevel, id: str, checkpoint_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取特定级别的状态。

        参数:
            level: 状态层级
            id: 状态ID（如会话ID、作业ID、项目ID）
            checkpoint_id: 检查点ID，若提供则从检查点加载状态

        返回:
            Dict[str, Any]: 状态数据
        """
        namespace = self._get_namespace(level)
        
        # 如果提供了检查点ID，从检查点加载
        if checkpoint_id:
            config = {"configurable": {"thread_id": id, "checkpoint_id": checkpoint_id}}
            try:
                return self.checkpointer.get(config)
            except Exception as e:
                raise ValueError(
                    f"从检查点加载状态失败 (level={level.value}, id={id}, checkpoint_id={checkpoint_id}): {str(e)}"
                ) from e
        
        # 否则从存储中获取当前状态
        try:
            return self.store_manager.get(namespace, id) or {}
        except Exception as e:
            raise ValueError(
                f"获取状态失败 (level={level.value}, id={id}): {str(e)}"
            ) from e

    async def aget_state(
        self, level: StateLevel, id: str, checkpoint_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        异步获取特定级别的状态。

        参数:
            level: 状态层级
            id: 状态ID（如会话ID、作业ID、项目ID）
            checkpoint_id: 检查点ID，若提供则从检查点加载状态

        返回:
            Dict[str, Any]: 状态数据
        """
        namespace = self._get_namespace(level)
        
        # 如果提供了检查点ID，从检查点加载
        if checkpoint_id:
            config = {"configurable": {"thread_id": id, "checkpoint_id": checkpoint_id}}
            try:
                return await self.checkpointer.aget(config)
            except Exception as e:
                raise ValueError(
                    f"从检查点异步加载状态失败 (level={level.value}, id={id}, checkpoint_id={checkpoint_id}): {str(e)}"
                ) from e
        
        # 否则从存储中获取当前状态
        try:
            return await self.store_manager.aget(namespace, id) or {}
        except Exception as e:
            raise ValueError(
                f"异步获取状态失败 (level={level.value}, id={id}): {str(e)}"
            ) from e

    def update_state(
        self, level: StateLevel, id: str, values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        更新特定级别的状态。

        参数:
            level: 状态层级
            id: 状态ID（如会话ID、作业ID、项目ID）
            values: 要更新的状态值

        返回:
            Dict[str, Any]: 更新后的完整状态
        """
        namespace = self._get_namespace(level)
        
        # 获取当前状态
        current_state = self.get_state(level, id) or {}
        
        # 更新状态
        current_state.update(values)
        
        # 存储更新后的状态
        try:
            self.store_manager.put(namespace, id, current_state)
            
            # 保存检查点
            config = {"configurable": {"thread_id": id}}
            self.checkpointer.put(config, current_state, {}, {})
            
            return current_state
        except Exception as e:
            raise ValueError(
                f"更新状态失败 (level={level.value}, id={id}): {str(e)}"
            ) from e

    async def aupdate_state(
        self, level: StateLevel, id: str, values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        异步更新特定级别的状态。

        参数:
            level: 状态层级
            id: 状态ID（如会话ID、作业ID、项目ID）
            values: 要更新的状态值

        返回:
            Dict[str, Any]: 更新后的完整状态
        """
        namespace = self._get_namespace(level)
        
        # 获取当前状态
        current_state = await self.aget_state(level, id) or {}
        
        # 更新状态
        current_state.update(values)
        
        # 存储更新后的状态
        try:
            await self.store_manager.aput(namespace, id, current_state)
            
            # 保存检查点
            config = {"configurable": {"thread_id": id}}
            await self.checkpointer.aput(config, current_state, {}, {})
            
            return current_state
        except Exception as e:
            raise ValueError(
                f"异步更新状态失败 (level={level.value}, id={id}): {str(e)}"
            ) from e

    def get_history(self, level: StateLevel, id: str) -> List[Dict[str, Any]]:
        """
        获取状态历史。

        参数:
            level: 状态层级
            id: 状态ID（如会话ID、作业ID、项目ID）

        返回:
            List[Dict[str, Any]]: 状态历史记录列表
        """
        config = {"configurable": {"thread_id": id}}
        
        try:
            # 获取检查点历史记录
            checkpoints = list(self.checkpointer.list(config))
            
            # 加载每个检查点的状态
            history = []
            for checkpoint in checkpoints:
                checkpoint_config = {"configurable": {"thread_id": id, "checkpoint_id": checkpoint["id"]}}
                state = self.checkpointer.get(checkpoint_config)
                history.append({
                    "id": checkpoint["id"],
                    "timestamp": checkpoint["ts"],
                    "state": state
                })
            
            return history
        except Exception as e:
            raise ValueError(
                f"获取状态历史失败 (level={level.value}, id={id}): {str(e)}"
            ) from e

    async def aget_history(self, level: StateLevel, id: str) -> List[Dict[str, Any]]:
        """
        异步获取状态历史。

        参数:
            level: 状态层级
            id: 状态ID（如会话ID、作业ID、项目ID）

        返回:
            List[Dict[str, Any]]: 状态历史记录列表
        """
        config = {"configurable": {"thread_id": id}}
        
        try:
            # 获取检查点历史记录
            checkpoints = list(await self.checkpointer.alist(config))
            
            # 加载每个检查点的状态
            history = []
            for checkpoint in checkpoints:
                checkpoint_config = {"configurable": {"thread_id": id, "checkpoint_id": checkpoint["id"]}}
                state = await self.checkpointer.aget(checkpoint_config)
                history.append({
                    "id": checkpoint["id"],
                    "timestamp": checkpoint["ts"],
                    "state": state
                })
            
            return history
        except Exception as e:
            raise ValueError(
                f"异步获取状态历史失败 (level={level.value}, id={id}): {str(e)}"
            ) from e

    def delete_state(self, level: StateLevel, id: str) -> None:
        """
        删除特定级别的状态。

        参数:
            level: 状态层级
            id: 状态ID（如会话ID、作业ID、项目ID）
        """
        namespace = self._get_namespace(level)
        
        try:
            # 删除存储中的状态
            self.store_manager.delete(namespace, id)
        except Exception as e:
            raise ValueError(
                f"删除状态失败 (level={level.value}, id={id}): {str(e)}"
            ) from e

    async def adelete_state(self, level: StateLevel, id: str) -> None:
        """
        异步删除特定级别的状态。

        参数:
            level: 状态层级
            id: 状态ID（如会话ID、作业ID、项目ID）
        """
        namespace = self._get_namespace(level)
        
        try:
            # 异步删除存储中的状态
            await self.store_manager.adelete(namespace, id)
        except Exception as e:
            raise ValueError(
                f"异步删除状态失败 (level={level.value}, id={id}): {str(e)}"
            ) from e
