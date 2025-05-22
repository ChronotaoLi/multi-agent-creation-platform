"""
生成工具模块

提供各种内容生成工具
"""

import logging
from typing import Any, Dict, List, Optional, Union

from app.agents.tools import BaseTool
from app.services.interfaces.llm_service import LLMService
from app.models.domain.llm_types import LLMMessage

logger = logging.getLogger(__name__)


class TextGenerationTool(BaseTool):
    """
    文本生成工具
    
    生成文本内容的工具
    """
    
    def __init__(self, llm_service: LLMService, default_model: str = None):
        """
        初始化文本生成工具
        
        参数:
            llm_service: LLM服务实例
            default_model: 默认使用的模型
        """
        super().__init__(
            name="text_generation",
            description="根据提示生成文本内容"
        )
        self.llm_service = llm_service
        self.default_model = default_model
    
    async def __call__(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.7,
        model: str = None
    ) -> str:
        """
        生成文本
        
        参数:
            prompt: 生成提示
            max_tokens: 最大生成令牌数
            temperature: 温度参数，控制随机性
            model: 模型名称，为None则使用默认模型
            
        返回:
            str: 生成的文本
        """
        try:
            # 准备消息
            messages = [
                LLMMessage(role="user", content=prompt)
            ]
            
            # 选择模型
            selected_model = model or self.default_model
            
            # 调用LLM服务
            response = await self.llm_service.chat_completion(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                model=selected_model
            )
            
            return response.content
        except Exception as e:
            logger.error(f"文本生成失败: {str(e)}")
            return f"生成失败: {str(e)}"


class StoryGenerationTool(BaseTool):
    """
    故事生成工具
    
    生成故事内容的工具
    """
    
    def __init__(self, llm_service: LLMService, default_model: str = None):
        """
        初始化故事生成工具
        
        参数:
            llm_service: LLM服务实例
            default_model: 默认使用的模型
        """
        super().__init__(
            name="story_generation",
            description="根据主题和风格生成故事"
        )
        self.llm_service = llm_service
        self.default_model = default_model
        
        # 故事生成的提示模板
        self.story_prompt_template = """
请根据以下要求创作一个故事：

主题: {theme}
长度: {length}
风格: {style}
{characters_desc}

请创作一个符合以上要求的完整故事，要素齐全，情节合理，人物丰满。
故事应包含开头、发展、高潮和结局等完整结构。
"""
    
    async def __call__(
        self,
        theme: str,
        length: str = "medium",
        style: str = "neutral",
        characters: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        生成故事
        
        参数:
            theme: 故事主题
            length: 故事长度，可选 "short", "medium", "long"
            style: 故事风格，如 "neutral", "humorous", "dramatic", "suspenseful"等
            characters: 角色信息列表，每个角色是一个字典，包含name, role, background等
            
        返回:
            Dict[str, Any]: 生成的故事内容和元信息
        """
        try:
            # 处理长度参数
            length_tokens = {
                "short": 500,
                "medium": 1000,
                "long": 2000
            }.get(length.lower(), 1000)
            
            # 处理角色信息
            characters_desc = ""
            if characters and len(characters) > 0:
                characters_desc = "角色: \n"
                for char in characters:
                    name = char.get("name", "未知角色")
                    role = char.get("role", "")
                    background = char.get("background", "")
                    characters_desc += f"- {name}: {role} {background}\n"
            
            # 构造故事生成提示
            prompt = self.story_prompt_template.format(
                theme=theme,
                length=length,
                style=style,
                characters_desc=characters_desc
            )
            
            # 生成故事
            messages = [
                LLMMessage(role="system", content="你是一个专业的故事创作者，擅长根据主题和要求创作引人入胜的故事。"),
                LLMMessage(role="user", content=prompt)
            ]
            
            # 调用LLM服务
            response = await self.llm_service.chat_completion(
                messages=messages,
                temperature=0.8,
                max_tokens=length_tokens,
                model=self.default_model
            )
            
            # 返回故事内容和元信息
            return {
                "story": response.content,
                "metadata": {
                    "theme": theme,
                    "length": length,
                    "style": style,
                    "characters": characters or []
                }
            }
        except Exception as e:
            logger.error(f"故事生成失败: {str(e)}")
            return {
                "story": f"故事生成失败: {str(e)}",
                "metadata": {
                    "error": str(e)
                }
            }


class CharacterGenerationTool(BaseTool):
    """
    角色生成工具
    
    生成角色信息的工具
    """
    
    def __init__(self, llm_service: LLMService, default_model: str = None):
        """
        初始化角色生成工具
        
        参数:
            llm_service: LLM服务实例
            default_model: 默认使用的模型
        """
        super().__init__(
            name="character_generation",
            description="根据要求生成角色信息"
        )
        self.llm_service = llm_service
        self.default_model = default_model
        
        # 角色生成的提示模板
        self.character_prompt_template = """
请根据以下信息创建一个详细的角色描述：

姓名: {name}
角色: {role}
背景: {background}
性格特点: {personality_traits}

请创建一个完整的角色档案，包含以下内容：
1. 基本信息（年龄、性别、外貌等）
2. 详细背景故事
3. 性格特点和心理动机
4. 特殊能力或技能
5. 关系网络
6. 成长经历和转折点
7. 价值观和信念

请以JSON格式返回结果，包括以下字段:
```json
{
  "name": "角色名",
  "basic_info": {
    "age": "年龄",
    "gender": "性别",
    "appearance": "外貌描述"
  },
  "background": "详细背景故事",
  "personality": ["性格特点列表"],
  "abilities": ["能力或技能列表"],
  "relationships": ["关系描述列表"],
  "development": "成长经历和转折点",
  "values": ["价值观和信念列表"]
}
```
"""
    
    async def __call__(
        self,
        name: str,
        role: str = None,
        background: str = None,
        personality_traits: List[str] = None
    ) -> Dict[str, Any]:
        """
        生成角色
        
        参数:
            name: 角色姓名
            role: 角色定位，如"主角"、"反派"等
            background: 角色背景简述
            personality_traits: 性格特点列表
            
        返回:
            Dict[str, Any]: 生成的角色信息
        """
        try:
            # 处理可选参数
            role = role or "未指定"
            background = background or "未提供背景信息"
            personality_traits_str = ", ".join(personality_traits) if personality_traits else "未指定性格特点"
            
            # 构造角色生成提示
            prompt = self.character_prompt_template.format(
                name=name,
                role=role,
                background=background,
                personality_traits=personality_traits_str
            )
            
            # 生成角色
            messages = [
                LLMMessage(role="system", content="你是一个专业的角色设计师，擅长创造独特而有深度的角色。"),
                LLMMessage(role="user", content=prompt)
            ]
            
            # 调用LLM服务
            response = await self.llm_service.chat_completion(
                messages=messages,
                temperature=0.7,
                max_tokens=1500,
                model=self.default_model
            )
            
            # 提取JSON格式的角色信息
            import json
            import re
            
            # 尝试提取JSON
            json_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
            match = re.search(json_pattern, response.content)
            
            character_info = {}
            if match:
                try:
                    character_info = json.loads(match.group(1))
                except json.JSONDecodeError:
                    logger.warning("无法解析角色JSON数据")
                    character_info = {"raw_content": response.content}
            else:
                character_info = {"raw_content": response.content}
            
            # 添加输入参数
            character_info["input_parameters"] = {
                "name": name,
                "role": role,
                "background": background,
                "personality_traits": personality_traits
            }
            
            return character_info
            
        except Exception as e:
            logger.error(f"角色生成失败: {str(e)}")
            return {
                "error": f"角色生成失败: {str(e)}",
                "name": name
            }


class GenerationToolRegistry:
    """
    生成工具注册表
    
    管理和提供各种内容生成工具
    """
    
    def __init__(self, llm_service: LLMService):
        """
        初始化生成工具注册表
        
        参数:
            llm_service: LLM服务实例
        """
        self.tools: Dict[str, BaseTool] = {}
        self.llm_service = llm_service
        
        # 初始化默认工具
        self._init_default_tools()
    
    def _init_default_tools(self) -> None:
        """初始化默认生成工具"""
        # 文本生成工具
        text_generation = TextGenerationTool(
            llm_service=self.llm_service
        )
        self.register_tool(text_generation)
        
        # 故事生成工具
        story_generation = StoryGenerationTool(
            llm_service=self.llm_service
        )
        self.register_tool(story_generation)
        
        # 角色生成工具
        character_generation = CharacterGenerationTool(
            llm_service=self.llm_service
        )
        self.register_tool(character_generation)
    
    def register_tool(self, tool: BaseTool) -> None:
        """
        注册工具
        
        参数:
            tool: 要注册的工具
        """
        self.tools[tool.name] = tool
        logger.info(f"注册生成工具: {tool.name}")
    
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
