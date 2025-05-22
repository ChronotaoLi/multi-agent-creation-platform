"""
分析工具模块

提供各种内容分析工具
"""

import logging
from typing import Any, Dict, List, Optional, Union

from app.agents.tools import BaseTool
from app.services.interfaces.llm_service import LLMService
from app.models.domain.llm_types import LLMMessage

logger = logging.getLogger(__name__)


class TextAnalysisTool(BaseTool):
    """
    文本分析工具
    
    分析文本内容的工具
    """
    
    def __init__(self, llm_service: LLMService):
        """
        初始化文本分析工具
        
        参数:
            llm_service: LLM服务实例
        """
        super().__init__(
            name="text_analysis",
            description="分析文本内容，提取关键信息、情感和主题"
        )
        self.llm_service = llm_service
        
        # 文本分析的提示模板
        self.analysis_prompt_template = """
请对下面的文本进行全面分析，包括但不限于以下方面：

1. 主题和核心思想
2. 情感倾向和语调
3. 关键信息和要点
4. 文体和写作风格
5. 隐含信息和潜在意图

文本内容:
```
{text}
```

请以JSON格式返回分析结果:
```json
{
  "main_themes": ["主题1", "主题2", ...],
  "sentiment": {
    "polarity": "情感极性（积极/中性/消极）",
    "strength": "情感强度（1-10）",
    "emotions": ["情绪1", "情绪2", ...]
  },
  "key_points": ["要点1", "要点2", ...],
  "style_analysis": {
    "writing_style": "写作风格",
    "formality": "正式程度（正式/中性/非正式）",
    "technical_level": "技术性程度（高/中/低）"
  },
  "implicit_content": ["隐含信息1", "隐含信息2", ...]
}
```
"""
    
    async def __call__(self, text: str) -> Dict[str, Any]:
        """
        分析文本
        
        参数:
            text: 要分析的文本内容
            
        返回:
            Dict[str, Any]: 分析结果
        """
        try:
            # 构造分析提示
            prompt = self.analysis_prompt_template.format(
                text=text
            )
            
            # 调用LLM服务
            messages = [
                LLMMessage(role="system", content="你是一个专业的文本分析专家，擅长理解和解读各类文本。"),
                LLMMessage(role="user", content=prompt)
            ]
            
            response = await self.llm_service.chat_completion(
                messages=messages,
                temperature=0.2
            )
            
            # 提取JSON格式的分析结果
            import json
            import re
            
            # 尝试提取JSON
            json_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
            match = re.search(json_pattern, response.content)
            
            analysis_result = {}
            if match:
                try:
                    analysis_result = json.loads(match.group(1))
                except json.JSONDecodeError:
                    logger.warning("无法解析分析结果JSON数据")
                    analysis_result = {"raw_content": response.content}
            else:
                analysis_result = {"raw_content": response.content}
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"文本分析失败: {str(e)}")
            return {
                "error": f"文本分析失败: {str(e)}"
            }


class StoryAnalysisTool(BaseTool):
    """
    故事分析工具
    
    分析故事内容的工具
    """
    
    def __init__(self, llm_service: LLMService):
        """
        初始化故事分析工具
        
        参数:
            llm_service: LLM服务实例
        """
        super().__init__(
            name="story_analysis",
            description="分析故事结构、情节、人物和主题"
        )
        self.llm_service = llm_service
        
        # 故事分析的提示模板
        self.analysis_prompt_template = """
请对下面的故事内容进行专业的文学分析，包括但不限于以下方面：

1. 故事结构（开头、发展、高潮、结局）
2. 情节发展和冲突
3. 人物分析和角色弧线
4. 主题和中心思想
5. 象征和隐喻
6. 叙事风格和语调
7. 故事类型和流派
8. 文化和社会背景影响

故事内容:
```
{story}
```

请以JSON格式返回分析结果:
```json
{
  "structure": {
    "beginning": "开头分析",
    "middle": "中间部分分析",
    "climax": "高潮部分分析",
    "ending": "结局分析"
  },
  "plot": {
    "main_conflict": "主要冲突",
    "development": "情节发展描述",
    "resolution": "问题解决方式",
    "pacing": "节奏评价"
  },
  "characters": [
    {
      "name": "角色名",
      "role": "角色作用",
      "development": "发展轨迹",
      "motivation": "动机"
    }
  ],
  "themes": ["主题1", "主题2", ...],
  "symbols": ["象征1", "象征2", ...],
  "narrative_style": {
    "point_of_view": "叙事视角",
    "tone": "语调",
    "style": "写作风格"
  },
  "genre": ["类型1", "类型2", ...],
  "cultural_context": ["文化背景要素1", "文化背景要素2", ...]
}
```
"""
    
    async def __call__(self, story: str) -> Dict[str, Any]:
        """
        分析故事
        
        参数:
            story: 要分析的故事内容
            
        返回:
            Dict[str, Any]: 分析结果
        """
        try:
            # 构造分析提示
            prompt = self.analysis_prompt_template.format(
                story=story
            )
            
            # 调用LLM服务
            messages = [
                LLMMessage(role="system", content="你是一个专业的文学评论家，擅长故事分析和评价。"),
                LLMMessage(role="user", content=prompt)
            ]
            
            response = await self.llm_service.chat_completion(
                messages=messages,
                temperature=0.3
            )
            
            # 提取JSON格式的分析结果
            import json
            import re
            
            # 尝试提取JSON
            json_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
            match = re.search(json_pattern, response.content)
            
            analysis_result = {}
            if match:
                try:
                    analysis_result = json.loads(match.group(1))
                except json.JSONDecodeError:
                    logger.warning("无法解析故事分析结果JSON数据")
                    analysis_result = {"raw_content": response.content}
            else:
                analysis_result = {"raw_content": response.content}
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"故事分析失败: {str(e)}")
            return {
                "error": f"故事分析失败: {str(e)}"
            }


class CharacterAnalysisTool(BaseTool):
    """
    角色分析工具
    
    分析角色信息的工具
    """
    
    def __init__(self, llm_service: LLMService):
        """
        初始化角色分析工具
        
        参数:
            llm_service: LLM服务实例
        """
        super().__init__(
            name="character_analysis",
            description="深入分析角色的特性、动机和发展"
        )
        self.llm_service = llm_service
        
        # 角色分析的提示模板
        self.analysis_prompt_template = """
请对以下角色信息进行深入的分析，包括但不限于以下方面：

1. 性格特点和心理分析
2. 动机和目标
3. 内在冲突和矛盾
4. 发展潜力和成长空间
5. 与其他角色的关系
6. 叙事功能和角色定位
7. 象征意义和主题价值
8. 可信度和立体感评估

角色信息:
```json
{character_json}
```

请以JSON格式返回分析结果:
```json
{
  "psychology": {
    "core_traits": ["特质1", "特质2", ...],
    "inner_conflicts": ["冲突1", "冲突2", ...],
    "strengths": ["优点1", "优点2", ...],
    "weaknesses": ["缺点1", "缺点2", ...]
  },
  "motivation": {
    "primary_goal": "主要目标",
    "hidden_desires": ["隐藏欲望1", "隐藏欲望2", ...],
    "driving_forces": ["驱动力1", "驱动力2", ...]
  },
  "development_potential": {
    "growth_areas": ["成长领域1", "成长领域2", ...],
    "transformation_points": ["转变点1", "转变点2", ...]
  },
  "relationships": {
    "potential_allies": ["潜在盟友1", "潜在盟友2", ...],
    "potential_enemies": ["潜在敌人1", "潜在敌人2", ...],
    "key_dynamics": ["关键关系动态1", "关键关系动态2", ...]
  },
  "narrative_function": ["叙事功能1", "叙事功能2", ...],
  "symbolic_value": ["象征意义1", "象征意义2", ...],
  "credibility_assessment": "可信度评估（1-10）",
  "depth_assessment": "角色深度评估（1-10）"
}
```
"""
    
    async def __call__(self, character: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析角色
        
        参数:
            character: 要分析的角色信息字典
            
        返回:
            Dict[str, Any]: 分析结果
        """
        try:
            import json
            
            # 将角色信息转换为JSON字符串
            character_json = json.dumps(character, ensure_ascii=False, indent=2)
            
            # 构造分析提示
            prompt = self.analysis_prompt_template.format(
                character_json=character_json
            )
            
            # 调用LLM服务
            messages = [
                LLMMessage(role="system", content="你是一个专业的角色分析师，擅长深入解读和评估各类角色。"),
                LLMMessage(role="user", content=prompt)
            ]
            
            response = await self.llm_service.chat_completion(
                messages=messages,
                temperature=0.3
            )
            
            # 提取JSON格式的分析结果
            import re
            
            # 尝试提取JSON
            json_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
            match = re.search(json_pattern, response.content)
            
            analysis_result = {}
            if match:
                try:
                    analysis_result = json.loads(match.group(1))
                except json.JSONDecodeError:
                    logger.warning("无法解析角色分析结果JSON数据")
                    analysis_result = {"raw_content": response.content}
            else:
                analysis_result = {"raw_content": response.content}
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"角色分析失败: {str(e)}")
            return {
                "error": f"角色分析失败: {str(e)}"
            }


class AnalysisToolRegistry:
    """
    分析工具注册表
    
    管理和提供各种内容分析工具
    """
    
    def __init__(self, llm_service: LLMService):
        """
        初始化分析工具注册表
        
        参数:
            llm_service: LLM服务实例
        """
        self.tools: Dict[str, BaseTool] = {}
        self.llm_service = llm_service
        
        # 初始化默认工具
        self._init_default_tools()
    
    def _init_default_tools(self) -> None:
        """初始化默认分析工具"""
        # 文本分析工具
        text_analysis = TextAnalysisTool(
            llm_service=self.llm_service
        )
        self.register_tool(text_analysis)
        
        # 故事分析工具
        story_analysis = StoryAnalysisTool(
            llm_service=self.llm_service
        )
        self.register_tool(story_analysis)
        
        # 角色分析工具
        character_analysis = CharacterAnalysisTool(
            llm_service=self.llm_service
        )
        self.register_tool(character_analysis)
    
    def register_tool(self, tool: BaseTool) -> None:
        """
        注册工具
        
        参数:
            tool: 要注册的工具
        """
        self.tools[tool.name] = tool
        logger.info(f"注册分析工具: {tool.name}")
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """
        获取工具
        
        参数:
            tool_name: 工具名称
            
        返回:
            Optional[BaseTool]: 找到的工具，不存在则返回None
        """
        return self.tools.get(tool_name)
    
    def list_tools(self) -> List[str]:
        """
        列出所有工具
        
        返回:
            List[str]: 工具名称列表
        """
        return list(self.tools.keys())
        
    async def analyze_text(self, text: str) -> Dict[str, Any]:
        """
        分析文本
        
        参数:
            text: 要分析的文本
            
        返回:
            Dict[str, Any]: 分析结果
        """
        if "text_analysis" not in self.tools:
            logger.warning("文本分析工具未注册")
            return {}
            
        tool = self.tools["text_analysis"]
        return await tool(text)
    
    async def analyze_story(self, story: str) -> Dict[str, Any]:
        """
        分析故事
        
        参数:
            story: 要分析的故事内容
            
        返回:
            Dict[str, Any]: 分析结果
        """
        if "story_analysis" not in self.tools:
            logger.warning("故事分析工具未注册")
            return {}
            
        tool = self.tools["story_analysis"]
        return await tool(story)
    
    async def analyze_character(self, character: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析角色
        
        参数:
            character: 要分析的角色信息
            
        返回:
            Dict[str, Any]: 分析结果
        """
        if "character_analysis" not in self.tools:
            logger.warning("角色分析工具未注册")
            return {}
            
        tool = self.tools["character_analysis"]
        return await tool(character)
