"""
通用工具函数模块

提供ID生成、时间处理、JSON处理等通用工具函数。
"""
import json
import re
import secrets
import string
import uuid
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set

import ulid


def generate_uuid() -> str:
    """生成UUID字符串

    Returns:
        str: UUID字符串
    """
    return str(uuid.uuid4())


def generate_ulid() -> str:
    """生成ULID（有序的唯一标识符）

    ULID (Universally Unique Lexicographically Sortable Identifier)
    比UUID更好的特性：
    1. 128位兼容UUID
    2. 按字典顺序排序（时间戳优先）
    3. 编码为32个字符的字符串（比UUID的36个字符更短）
    4. 使用Crockford的base32编码（耐人类错误阅读）
    5. 大小写不敏感
    6. 不使用特殊字符（URL安全）

    Returns:
        str: ULID字符串
    """
    return str(ulid.new())


def generate_short_id(length: int = 8) -> str:
    """生成短ID

    Args:
        length: ID长度

    Returns:
        str: 短ID字符串
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def get_utc_now() -> datetime:
    """获取当前UTC时间

    Returns:
        datetime: 当前UTC时间
    """
    return datetime.now(timezone.utc)


def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """格式化日期时间

    Args:
        dt: 日期时间
        format_str: 格式字符串

    Returns:
        str: 格式化后的字符串
    """
    return dt.strftime(format_str)


def json_dumps(obj: Any, **kwargs) -> str:
    """JSON序列化，支持datetime

    Args:
        obj: 要序列化的对象
        **kwargs: 其他参数

    Returns:
        str: JSON字符串
    """
    def default(o):
        if isinstance(o, datetime):
            return o.isoformat()
        return str(o)
    
    return json.dumps(obj, default=default, ensure_ascii=False, **kwargs)


def json_loads(json_str: str, **kwargs) -> Any:
    """JSON反序列化

    Args:
        json_str: JSON字符串
        **kwargs: 其他参数

    Returns:
        Any: 反序列化后的对象
    """
    return json.loads(json_str, **kwargs)


def snake_to_camel(snake_str: str) -> str:
    """下划线命名转驼峰命名

    Args:
        snake_str: 下划线命名的字符串

    Returns:
        str: 驼峰命名的字符串
    """
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def camel_to_snake(camel_str: str) -> str:
    """驼峰命名转下划线命名

    Args:
        camel_str: 驼峰命名的字符串

    Returns:
        str: 下划线命名的字符串
    """
    camel_str = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', camel_str)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', camel_str).lower()


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """截断文本

    Args:
        text: 原文本
        max_length: 最大长度
        suffix: 后缀

    Returns:
        str: 截断后的文本
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
    """将嵌套字典展平为单层字典

    Args:
        d: 嵌套字典
        parent_key: 父键
        sep: 分隔符

    Returns:
        Dict[str, Any]: 展平后的字典
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def deep_merge(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """深度合并两个字典

    Args:
        dict1: 第一个字典
        dict2: 第二个字典（优先级更高）

    Returns:
        Dict[str, Any]: 合并后的字典
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    
    return result


def get_nested_value(data: Dict[str, Any], key_path: str, default: Any = None, sep: str = '.') -> Any:
    """获取嵌套字典中的值

    Args:
        data: 字典
        key_path: 键路径，如 "a.b.c"
        default: 默认值
        sep: 分隔符

    Returns:
        Any: 对应的值，如果不存在则返回默认值
    """
    keys = key_path.split(sep)
    current = data
    
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    
    return current


def set_nested_value(data: Dict[str, Any], key_path: str, value: Any, sep: str = '.') -> Dict[str, Any]:
    """设置嵌套字典中的值

    Args:
        data: 字典
        key_path: 键路径，如 "a.b.c"
        value: 要设置的值
        sep: 分隔符

    Returns:
        Dict[str, Any]: 更新后的字典
    """
    keys = key_path.split(sep)
    current = data
    
    # 遍历除最后一个键外的所有键
    for key in keys[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]
    
    # 设置最后一个键的值
    current[keys[-1]] = value
    
    return data


def is_json_serializable(obj: Any) -> bool:
    """检查对象是否可JSON序列化

    Args:
        obj: 要检查的对象

    Returns:
        bool: 是否可JSON序列化
    """
    try:
        json.dumps(obj)
        return True
    except (TypeError, OverflowError):
        return False


class InMemoryLockManager:
    """内存锁管理器，用于并发控制

    适合单实例部署环境下的锁管理。
    """
    
    def __init__(self):
        """初始化内存锁管理器"""
        self.locks: Dict[str, asyncio.Lock] = {}  # 资源名称到锁对象的映射
        self.lock_creation_lock = asyncio.Lock()  # 用于保护锁创建过程的锁
        self.logger = logging.getLogger("InMemoryLockManager")  # 日志记录器
    
    @asynccontextmanager
    async def acquire(self, resource_name: str, timeout: float = 10.0):
        """获取资源锁

        参数:
            resource_name: 资源名称，作为锁的唯一标识符
            timeout: 获取锁的超时时间(秒)
            
        异常:
            TimeoutError: 超时未获取到锁时抛出
            
        用法:
            async with lock_manager.acquire("resource_name"):
                # 在锁保护下的代码块
        """
        # 确保资源锁存在
        async with self.lock_creation_lock:
            if resource_name not in self.locks:
                self.locks[resource_name] = asyncio.Lock()
                self.logger.debug(f"为资源 {resource_name} 创建了新锁")
        
        # 获取资源对应的锁
        lock = self.locks[resource_name]
        
        # 尝试获取锁，带超时机制
        try:
            # 创建一个Future对象，用于超时控制
            acquire_task = asyncio.create_task(lock.acquire())
            done, pending = await asyncio.wait(
                [acquire_task], timeout=timeout
            )
            
            if acquire_task in pending:
                # 超时未获取到锁
                acquire_task.cancel()
                raise TimeoutError(f"获取资源 {resource_name} 的锁超时，超过 {timeout} 秒")
            
            # 获取锁成功
            self.logger.debug(f"获取资源 {resource_name} 的锁成功")
            
            try:
                # 返回上下文
                yield
            finally:
                # 释放锁
                lock.release()
                self.logger.debug(f"释放资源 {resource_name} 的锁")
        
        except Exception as e:
            self.logger.error(f"获取或使用资源 {resource_name} 的锁时发生错误: {str(e)}")
            raise
