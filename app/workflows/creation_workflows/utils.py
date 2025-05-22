"""
工作流工具函数，提供状态管理、内容处理和干预处理等通用功能
"""

from typing import Any, Dict, List, Optional, Union, TypedDict, cast
from datetime import datetime
import uuid
import json
import re
import hashlib


def generate_id(prefix: str = "") -> str:
    """
    生成唯一ID
    
    参数:
        prefix: str - ID前缀
        
    返回:
        str - 唯一ID
    """
    unique_id = str(uuid.uuid4())
    if prefix:
        return f"{prefix}_{unique_id}"
    return unique_id


def timestamp_now() -> str:
    """
    获取当前ISO格式时间戳
    
    返回:
        str - ISO格式时间戳
    """
    return datetime.utcnow().isoformat()


def merge_state_updates(current_state: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    智能合并状态更新
    
    参数:
        current_state: Dict[str, Any] - 当前状态
        updates: Dict[str, Any] - 状态更新
        
    返回:
        Dict[str, Any] - 合并后的状态
    """
    merged = {**current_state}
    
    for key, value in updates.items():
        # 特殊处理列表类型，避免覆盖
        if key in merged and isinstance(merged[key], list) and isinstance(value, list):
            merged[key] = merged[key] + value
        # 特殊处理嵌套字典，进行深度合并
        elif key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = merge_state_updates(merged[key], value)
        # 其他情况直接覆盖
        else:
            merged[key] = value
    
    # 更新时间戳
    merged["updated_at"] = timestamp_now()
    
    return merged


def calculate_content_hash(content: Union[str, Dict[str, Any], List[Any]]) -> str:
    """
    计算内容哈希值，用于内容变更检测
    
    参数:
        content: Union[str, Dict[str, Any], List[Any]] - 要计算哈希的内容
        
    返回:
        str - 哈希值
    """
    if isinstance(content, (dict, list)):
        content_str = json.dumps(content, sort_keys=True)
    else:
        content_str = str(content)
    
    return hashlib.md5(content_str.encode('utf-8')).hexdigest()


def extract_text_properties(content: Dict[str, Any]) -> Dict[str, Any]:
    """
    从内容中提取文本属性
    
    参数:
        content: Dict[str, Any] - 内容数据
        
    返回:
        Dict[str, Any] - 文本属性
    """
    text_properties = {}
    
    # 如果有direct_text字段，提取基本文本属性
    if "text" in content:
        text = content["text"]
        word_count = len(re.findall(r'\w+', text))
        sentence_count = len(re.findall(r'[.!?]+', text))
        paragraph_count = len(text.split("\n\n"))
        
        text_properties.update({
            "word_count": word_count,
            "sentence_count": sentence_count,
            "paragraph_count": paragraph_count,
            "estimated_read_time": word_count / 200  # 假设阅读速度为每分钟200字
        })
    
    # 如果有结构化内容，提取结构信息
    if "sections" in content:
        sections = content["sections"]
        section_count = len(sections)
        
        text_properties.update({
            "section_count": section_count
        })
        
        # 计算每个部分的字数
        section_word_counts = {}
        for section in sections:
            section_name = section.get("name", "unnamed")
            section_text = section.get("content", "")
            section_word_counts[section_name] = len(re.findall(r'\w+', section_text))
        
        text_properties["section_word_counts"] = section_word_counts
    
    return text_properties


def format_intervention_response(intervention_data: Dict[str, Any], user_response: Dict[str, Any]) -> Dict[str, Any]:
    """
    格式化用户干预响应
    
    参数:
        intervention_data: Dict[str, Any] - 干预数据
        user_response: Dict[str, Any] - 用户响应
        
    返回:
        Dict[str, Any] - 格式化的响应
    """
    intervention_type = intervention_data.get("type", "general")
    response_option = user_response.get("option", {})
    response_data = user_response.get("data", {})
    
    formatted_response = {
        "intervention_id": intervention_data.get("intervention_id", ""),
        "response_type": intervention_type,
        "selected_option": response_option.get("id") if isinstance(response_option, dict) else response_option,
        "option_text": response_option.get("text") if isinstance(response_option, dict) else "",
        "timestamp": timestamp_now(),
        "data": response_data
    }
    
    # 对特定类型的干预进行额外处理
    if intervention_type == "content_review":
        formatted_response["approved"] = response_option.get("id") == "approve"
        formatted_response["feedback"] = response_data.get("feedback", "")
    
    elif intervention_type == "quality_feedback":
        formatted_response["refinement_requested"] = response_option.get("id") == "refine"
        formatted_response["feedback_provided"] = response_data.get("feedback", "")
    
    return formatted_response


def create_log_entry(log_type: str, details: Dict[str, Any]) -> Dict[str, Any]:
    """
    创建日志条目
    
    参数:
        log_type: str - 日志类型
        details: Dict[str, Any] - 详情
        
    返回:
        Dict[str, Any] - 日志条目
    """
    return {
        "log_id": generate_id("log"),
        "type": log_type,
        "timestamp": timestamp_now(),
        **details
    }


def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """
    从文本中提取关键词
    
    参数:
        text: str - 文本内容
        max_keywords: int - 最大关键词数量
        
    返回:
        List[str] - 关键词列表
    """
    # 实际实现应使用NLP技术提取关键词
    # 这里使用简化实现，按频率取词
    
    # 去除标点符号和转换为小写
    clean_text = re.sub(r'[^\w\s]', '', text.lower())
    
    # 分词
    words = clean_text.split()
    
    # 去除常见停用词（简化版）
    stop_words = {
        'a', 'an', 'the', 'and', 'or', 'but', 'is', 'are', 'was', 'were',
        'in', 'on', 'at', 'by', 'for', 'with', 'about', 'to', 'from'
    }
    filtered_words = [word for word in words if word not in stop_words and len(word) > 1]
    
    # 计算词频
    word_freq = {}
    for word in filtered_words:
        word_freq[word] = word_freq.get(word, 0) + 1
    
    # 按频率排序并取前N个
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, freq in sorted_words[:max_keywords]]


def summarize_state_for_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    为智能体准备状态摘要，移除不必要的详细信息
    
    参数:
        state: Dict[str, Any] - 完整状态
        
    返回:
        Dict[str, Any] - 状态摘要
    """
    # 提取关键状态信息
    summary = {
        "status": state.get("status", ""),
        "current_stage": state.get("current_stage", ""),
        "progress": state.get("progress", 0.0)
    }
    
    # 提取当前内容的摘要
    content = state.get("content", {})
    if content:
        # 计算内容大小和特征
        content_summary = {}
        for key, value in content.items():
            if isinstance(value, str) and len(value) > 100:
                # 对长文本进行摘要
                content_summary[key] = {
                    "type": "text",
                    "length": len(value),
                    "preview": value[:100] + "...",
                    "keywords": extract_keywords(value, 5)
                }
            elif isinstance(value, dict):
                # 对字典进行摘要
                content_summary[key] = {
                    "type": "object",
                    "keys": list(value.keys()),
                    "size": len(value)
                }
            elif isinstance(value, list):
                # 对列表进行摘要
                content_summary[key] = {
                    "type": "list",
                    "length": len(value),
                    "preview": str(value[:3])[:100] + ("..." if len(value) > 3 else "")
                }
            else:
                # 其他类型直接包含
                content_summary[key] = value
        
        summary["content_summary"] = content_summary
    
    # 提取元数据摘要
    metadata = state.get("metadata", {})
    if metadata:
        metadata_summary = {}
        for key, value in metadata.items():
            if isinstance(value, dict) and len(value) > 10:
                metadata_summary[key] = {
                    "type": "object",
                    "keys": list(value.keys()),
                    "size": len(value)
                }
            elif isinstance(value, list) and len(value) > 10:
                metadata_summary[key] = {
                    "type": "list",
                    "length": len(value)
                }
            else:
                metadata_summary[key] = value
        
        summary["metadata_summary"] = metadata_summary
    
    # 提取最新的日志
    logs = state.get("creation_logs", [])
    if logs:
        summary["recent_logs"] = logs[-5:]  # 最近5条日志
    
    # 提取错误信息
    if "error" in state:
        summary["error"] = state["error"]
    
    # 提取干预状态
    if state.get("awaiting_intervention", False):
        summary["awaiting_intervention"] = True
        summary["intervention_data"] = state.get("intervention_data", {})
    
    return summary


def validate_workflow_parameters(workflow_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    验证工作流参数是否有效
    
    参数:
        workflow_type: str - 工作流类型
        parameters: Dict[str, Any] - 工作流参数
        
    返回:
        Dict[str, Any] - 验证结果，包含是否有效和错误信息
    """
    result = {
        "valid": True,
        "errors": {},
        "sanitized_parameters": {}
    }
    
    # 复制并初步清理参数
    sanitized = {k: v for k, v in parameters.items() if v is not None}
    
    # 根据工作流类型验证参数
    if workflow_type == "free":
        # 验证free模式参数
        if "inspiration_threshold" in sanitized:
            try:
                threshold = float(sanitized["inspiration_threshold"])
                if threshold < 0 or threshold > 1:
                    result["valid"] = False
                    result["errors"]["inspiration_threshold"] = "阈值必须在0到1之间"
                else:
                    sanitized["inspiration_threshold"] = threshold
            except (ValueError, TypeError):
                result["valid"] = False
                result["errors"]["inspiration_threshold"] = "阈值必须是有效的浮点数"
    
    elif workflow_type == "guided":
        # 验证guided模式参数
        if "work_type" in sanitized:
            work_type = sanitized["work_type"]
            valid_types = ["story", "article", "poem"]
            if work_type not in valid_types:
                result["valid"] = False
                result["errors"]["work_type"] = f"作品类型必须是以下之一: {', '.join(valid_types)}"
    
    elif workflow_type == "structured":
        # 验证structured模式参数
        valid_template_types = ["novel", "article"]
        if "template_type" in sanitized:
            template_type = sanitized["template_type"]
            if template_type not in valid_template_types:
                result["valid"] = False
                result["errors"]["template_type"] = f"模板类型必须是以下之一: {', '.join(valid_template_types)}"
        
        valid_template_ids = {
            "novel": ["basic"],
            "article": ["academic"]
        }
        if "template_id" in sanitized and "template_type" in sanitized:
            template_id = sanitized["template_id"]
            template_type = sanitized["template_type"]
            if template_type in valid_template_types:
                valid_ids = valid_template_ids.get(template_type, [])
                if template_id not in valid_ids:
                    result["valid"] = False
                    result["errors"]["template_id"] = f"'{template_type}'类型的模板ID必须是以下之一: {', '.join(valid_ids)}"
    
    elif workflow_type == "adaptation":
        # 验证adaptation模式参数
        valid_formats = ["screenplay", "summary", "different_genre"]
        if "target_format" in sanitized:
            target_format = sanitized["target_format"]
            if target_format not in valid_formats:
                result["valid"] = False
                result["errors"]["target_format"] = f"目标格式必须是以下之一: {', '.join(valid_formats)}"
        
        if "adaptation_parameters" in sanitized:
            adaptation_params = sanitized["adaptation_parameters"]
            if not isinstance(adaptation_params, dict):
                result["valid"] = False
                result["errors"]["adaptation_parameters"] = "改编参数必须是字典类型"
            elif "target_genre" in adaptation_params and sanitized.get("target_format") == "different_genre":
                valid_genres = ["adventure", "romance", "mystery", "horror", "scifi", "fantasy", "thriller"]
                if adaptation_params["target_genre"] not in valid_genres:
                    result["valid"] = False
                    result["errors"]["adaptation_parameters.target_genre"] = f"目标体裁必须是以下之一: {', '.join(valid_genres)}"
    else:
        result["valid"] = False
        result["errors"]["workflow_type"] = f"未知的工作流类型: {workflow_type}"
    
    result["sanitized_parameters"] = sanitized
    return result 