"""
通用验证函数模块

提供各种数据格式的验证功能
"""
import json
import re
import uuid
from typing import List, Optional, Tuple, Dict, Any

import jsonschema
from jsonschema import ValidationError


def validate_email(email: str) -> bool:
    """验证电子邮件格式
    
    Args:
        email: 电子邮件地址
        
    Returns:
        bool: 格式是否有效
    """
    # 简单的电子邮件格式正则表达式
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_uuid(uuid_str: str) -> bool:
    """验证UUID格式
    
    Args:
        uuid_str: UUID字符串
        
    Returns:
        bool: 格式是否有效
    """
    try:
        uuid_obj = uuid.UUID(uuid_str)
        return str(uuid_obj) == uuid_str
    except (ValueError, AttributeError):
        return False


def validate_state_id(state_id: str) -> bool:
    """验证状态ID格式
    
    状态ID可以是UUID或其他特定格式
    
    Args:
        state_id: 状态ID字符串
        
    Returns:
        bool: 格式是否有效
    """
    # 本例中使用UUID格式作为状态ID
    return validate_uuid(state_id)


def validate_content_type(content_type: str, allowed_types: Optional[List[str]] = None) -> bool:
    """验证内容类型
    
    Args:
        content_type: 内容类型
        allowed_types: 允许的类型列表，如果为None则不检查
        
    Returns:
        bool: 内容类型是否有效
    """
    if allowed_types is None:
        # 默认允许的内容类型
        allowed_types = ["story", "character", "scene", "plot", "dialogue", "image", "audio"]
    
    return content_type in allowed_types


def validate_json_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """验证JSON数据符合指定schema
    
    Args:
        data: 要验证的JSON数据
        schema: JSON Schema
        
    Returns:
        Tuple[bool, List[str]]: (是否有效, 错误信息列表)
    """
    validator = jsonschema.Draft7Validator(schema)
    errors = list(validator.iter_errors(data))
    
    if not errors:
        return True, []
    
    # 格式化错误信息
    error_messages = []
    for error in errors:
        # 构建错误路径
        path = "/".join(str(part) for part in error.path) if error.path else ""
        message = f"{path}: {error.message}" if path else error.message
        error_messages.append(message)
    
    return False, error_messages


def validate_float(value: Any) -> bool:
    """验证值是否为有效的浮点数
    
    Args:
        value: 要验证的值
        
    Returns:
        bool: 是否为有效的浮点数
    """
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def validate_integer(value: Any) -> bool:
    """验证值是否为有效的整数
    
    Args:
        value: 要验证的值
        
    Returns:
        bool: 是否为有效的整数
    """
    try:
        int(value)
        return True
    except (TypeError, ValueError):
        return False


def validate_boolean(value: Any) -> bool:
    """验证值是否为有效的布尔值
    
    Args:
        value: 要验证的值
        
    Returns:
        bool: 是否为有效的布尔值
    """
    return isinstance(value, bool) or value in ("true", "false", "True", "False", 0, 1)
