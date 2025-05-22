"""
智能体工具模块

定义BaseTool基类和各种专用工具
"""

import abc
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class BaseTool(abc.ABC):
    """
    工具基类
    
    所有智能体工具的基类
    """
    
    def __init__(self, name: str, description: str):
        """
        初始化工具
        
        参数:
            name: 工具名称
            description: 工具描述
        """
        self.name = name
        self.description = description
    
    async def __call__(self, *args, **kwargs) -> Any:
        """
        调用工具
        
        参数:
            *args: 位置参数
            **kwargs: 关键字参数
            
        返回:
            Any: 工具调用结果
        """
        raise NotImplementedError("子类必须实现__call__方法")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将工具转换为字典表示
        
        返回:
            Dict[str, Any]: 工具字典表示
        """
        return {
            "name": self.name,
            "description": self.description
        }


# 导入所有工具类和注册表
from app.agents.tools.search_tools import (
    SearchToolRegistry, VectorSearchTool, GraphSearchTool
)
from app.agents.tools.generation_tools import (
    GenerationToolRegistry, TextGenerationTool, StoryGenerationTool, CharacterGenerationTool
)
from app.agents.tools.analysis_tools import (
    AnalysisToolRegistry, TextAnalysisTool, StoryAnalysisTool, CharacterAnalysisTool
)

__all__ = [
    'BaseTool',
    'SearchToolRegistry',
    'VectorSearchTool',
    'GraphSearchTool',
    'GenerationToolRegistry',
    'TextGenerationTool',
    'StoryGenerationTool',
    'CharacterGenerationTool',
    'AnalysisToolRegistry',
    'TextAnalysisTool',
    'StoryAnalysisTool',
    'CharacterAnalysisTool'
]
