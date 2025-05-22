"""
智能体工具函数模块

提供智能体系统中常用的工具函数
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)


def generate_id(prefix: str = "") -> str:
    """
    生成唯一ID
    
    参数:
        prefix: ID前缀
        
    返回:
        str: 唯一ID
    """
    unique_id = str(uuid.uuid4()).replace("-", "")[:12]
    if prefix:
        return f"{prefix}_{unique_id}"
    return unique_id


def format_elapsed_time(seconds: float) -> str:
    """
    格式化时间间隔为人类可读形式
    
    参数:
        seconds: 秒数
        
    返回:
        str: 格式化的时间字符串
    """
    if seconds < 60:
        return f"{seconds:.1f}秒"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}分钟"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}小时"


async def retry_async(
    func,
    max_retries: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: Tuple[Exception] = (Exception,)
) -> Any:
    """
    异步重试函数
    
    参数:
        func: 要重试的异步函数
        max_retries: 最大重试次数
        delay: 初始延迟时间(秒)
        backoff_factor: 退避因子
        exceptions: 要捕获的异常类型
        
    返回:
        Any: 函数返回值
    
    抛出:
        Exception: 超过重试次数后仍然失败
    """
    retries = 0
    current_delay = delay
    
    while True:
        try:
            return await func()
        except exceptions as e:
            retries += 1
            if retries > max_retries:
                logger.error(f"函数 {func.__name__} 在重试 {max_retries} 次后仍然失败: {str(e)}")
                raise
                
            logger.warning(f"函数 {func.__name__} 失败，将在 {current_delay:.1f}秒 后重试 ({retries}/{max_retries}): {str(e)}")
            await asyncio.sleep(current_delay)
            current_delay *= backoff_factor


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    截断文本
    
    参数:
        text: 要截断的文本
        max_length: 最大长度
        suffix: 截断后的后缀
        
    返回:
        str: 截断后的文本
    """
    if not text or len(text) <= max_length:
        return text
    return text[:max_length] + suffix


def merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    合并两个字典，处理冲突键
    
    参数:
        dict1: 第一个字典
        dict2: 第二个字典
        
    返回:
        Dict[str, Any]: 合并后的字典
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # 递归合并嵌套字典
            result[key] = merge_dicts(result[key], value)
        elif key in result and isinstance(result[key], list) and isinstance(value, list):
            # 合并列表，去重
            result[key] = list(set(result[key] + value))
        else:
            # 覆盖或添加键值
            result[key] = value
            
    return result


def extract_json_from_text(text: str) -> Dict[str, Any]:
    """
    从文本中提取JSON
    
    参数:
        text: 包含JSON的文本
        
    返回:
        Dict[str, Any]: 提取的JSON对象，如果提取失败则返回空字典
    """
    import re
    
    # 尝试提取带有代码块的JSON
    pattern_code_block = r"```(?:json)?\s*([\s\S]*?)\s*```"
    match = re.search(pattern_code_block, text)
    
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    
    # 尝试提取普通的JSON对象
    pattern_json_object = r"\{[\s\S]*\}"
    match = re.search(pattern_json_object, text)
    
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    
    return {}


def is_json_valid(text: str) -> bool:
    """
    检查文本是否为有效的JSON
    
    参数:
        text: 要检查的文本
        
    返回:
        bool: 是否为有效的JSON
    """
    try:
        json.loads(text)
        return True
    except json.JSONDecodeError:
        return False


def format_command_message(command_dict: Dict[str, Any]) -> str:
    """
    格式化命令消息为人类可读字符串
    
    参数:
        command_dict: 命令字典
        
    返回:
        str: 格式化的命令消息
    """
    if not command_dict:
        return "空命令"
        
    parts = []
    
    # 添加命令类型
    cmd_type = command_dict.get("type", "未知类型")
    parts.append(f"类型: {cmd_type}")
    
    # 添加命令内容
    content = command_dict.get("content")
    if content:
        if isinstance(content, str):
            content = truncate_text(content, 50)
        parts.append(f"内容: {content}")
        
    # 添加其他关键字段
    for key in ["action", "source_id", "target_ids"]:
        if key in command_dict:
            value = command_dict[key]
            parts.append(f"{key}: {value}")
            
    return " | ".join(parts)


def safe_json_dumps(obj: Any) -> str:
    """
    安全地序列化对象为JSON字符串
    
    参数:
        obj: 要序列化的对象
        
    返回:
        str: JSON字符串
    """
    try:
        return json.dumps(obj, ensure_ascii=False)
    except (TypeError, OverflowError, ValueError) as e:
        logger.warning(f"无法序列化对象为JSON: {str(e)}")
        # 尝试转换为可序列化的对象
        if isinstance(obj, dict):
            safe_dict = {}
            for k, v in obj.items():
                try:
                    # 测试是否可以序列化
                    json.dumps({k: v})
                    safe_dict[k] = v
                except:
                    safe_dict[k] = str(v)
            return json.dumps(safe_dict, ensure_ascii=False)
        else:
            return json.dumps(str(obj), ensure_ascii=False)


class RateLimiter:
    """速率限制器，用于控制API调用频率"""
    
    def __init__(self, calls_limit: int = 10, period: float = 60.0):
        """
        初始化速率限制器
        
        参数:
            calls_limit: 时间段内的最大调用次数
            period: 时间段长度(秒)
        """
        self.calls_limit = calls_limit
        self.period = period
        self.calls = []
        
    async def wait_if_needed(self) -> float:
        """
        如果需要，等待直到可以执行新的调用
        
        返回:
            float: 等待的时间(秒)
        """
        now = time.time()
        
        # 清理过期的调用记录
        self.calls = [call_time for call_time in self.calls if now - call_time < self.period]
        
        if len(self.calls) >= self.calls_limit:
            # 需要等待最早的调用过期
            oldest_call = min(self.calls)
            wait_time = oldest_call + self.period - now
            
            if wait_time > 0:
                logger.info(f"速率限制: 等待 {wait_time:.2f} 秒")
                await asyncio.sleep(wait_time)
                return wait_time
                
        # 记录新的调用
        self.calls.append(time.time())
        return 0.0


class Timer:
    """计时器，用于测量操作耗时"""
    
    def __init__(self, name: str = None):
        """
        初始化计时器
        
        参数:
            name: 计时器名称
        """
        self.name = name or "操作"
        self.start_time = None
        self.end_time = None
        
    def __enter__(self):
        """开始计时"""
        self.start_time = time.time()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """结束计时并输出耗时"""
        self.end_time = time.time()
        elapsed = self.end_time - self.start_time
        logger.info(f"{self.name} 耗时: {format_elapsed_time(elapsed)}")
        
    async def __aenter__(self):
        """异步开始计时"""
        self.start_time = time.time()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步结束计时并输出耗时"""
        self.end_time = time.time()
        elapsed = self.end_time - self.start_time
        logger.info(f"{self.name} 耗时: {format_elapsed_time(elapsed)}")


def create_agent_config(
    system_prompt: str,
    persona: Dict[str, Any] = None,
    mode: str = "chat",
    tools: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    创建智能体配置
    
    参数:
        system_prompt: 系统提示
        persona: 智能体角色设定
        mode: 智能体模式，可选值: "chat", "completion", "tool"
        tools: 工具列表
        
    返回:
        Dict[str, Any]: 智能体配置
    """
    config = {
        "mode": mode,
        "system_prompt": system_prompt
    }
    
    if persona:
        config["persona"] = persona
    
    if tools:
        config["tools"] = tools
    
    return config


def parse_agent_response(response: str) -> Dict[str, Any]:
    """
    解析智能体响应
    
    参数:
        response: 智能体响应文本
        
    返回:
        Dict[str, Any]: 解析结果
    """
    # 尝试提取JSON
    json_data = extract_json_from_text(response)
    
    # 如果提取到了JSON，返回
    if json_data:
        return {
            "content": response,
            "structured_data": json_data
        }
    
    # 否则，分析文本
    result = {
        "content": response,
    }
    
    # 检测是否包含代码块
    import re
    code_blocks = re.findall(r"```(.*?)```", response, re.DOTALL)
    if code_blocks:
        result["code_blocks"] = code_blocks
    
    # 检测是否包含列表
    list_items = re.findall(r"^\s*[-*]\s*(.*?)$", response, re.MULTILINE)
    if list_items:
        result["list_items"] = list_items
    
    return result


def normalize_agent_name(name: str) -> str:
    """
    标准化智能体名称
    
    参数:
        name: 智能体名称
        
    返回:
        str: 标准化的名称
    """
    # 移除特殊字符
    import re
    normalized = re.sub(r"[^\w\s\-]", "", name)
    
    # 替换空格为下划线
    normalized = normalized.replace(" ", "_")
    
    # 转换为小写
    normalized = normalized.lower()
    
    # 如果为空，返回默认名称
    if not normalized:
        return "agent"
        
    return normalized
