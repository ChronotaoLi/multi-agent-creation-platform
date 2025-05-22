"""
角色智能体 (CharacterAgent)

负责管理故事角色的行为、对话、状态和特性，确保角色在故事中表现一致且有深度。
"""

import asyncio
from typing import Dict, List, Any, Optional, cast

from app.agents.base_agent import BaseAgent
from app.models.state_models import CharacterAgentState
from app.services.interfaces.llm_service import LLMService
from langchain_core.messages import BaseMessage # 确保 CharacterAgentState 中的 messages 类型被正确导入

class CharacterAgent(BaseAgent):
    """
    角色智能体，管理角色的所有方面，包括其状态、行为和与其他实体的交互。
    """

    def __init__(
        self,
        id: str,
        name: str,
        llm_service: LLMService,
        character_schema: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化角色智能体。

        参数:
            id: 智能体的唯一标识符。
            name: 智能体的名称，通常是角色的名字。
            llm_service: 用于语言模型交互的服务。
            character_schema: 定义角色初始属性、性格、背景等的字典。
            config: 智能体的特定配置选项。
        """
        super().__init__(id=id, name=name, agent_type="character", llm_service=llm_service, config=config)

        self.character_schema: Dict[str, Any] = character_schema
        self.config: Dict[str, Any] = config if config else {}

        # 从 schema 初始化特定属性，如果schema中没有，则使用默认值
        self.personality_traits: Dict[str, float] = self.character_schema.get("personality_traits", {})
        self.cognitive_model: Dict[str, Any] = self.character_schema.get("cognitive_model", {})
        self.emotional_model: Dict[str, Any] = self.character_schema.get("emotional_model", {})
        self.dialogue_patterns: List[Dict[str, Any]] = self.character_schema.get("dialogue_patterns", [])

        # 初始化角色状态，确保所有 CharacterAgentState 的字段都被正确初始化
        # 注意：CharacterAgentState 是一个 TypedDict，不能直接实例化。
        # 我们需要创建一个符合其结构的字典。
        self.character_state: CharacterAgentState = cast(CharacterAgentState, {
            "id": id,
            "name": name,
            "personality": self.character_schema.get("personality", {}),
            "cognitive": self.character_schema.get("cognitive", {}),
            "emotional": self.character_schema.get("emotional", {"current_mood": "neutral"}), # 示例默认情绪
            "social": self.character_schema.get("social", {"relationships": {}}),
            "memories": self.character_schema.get("initial_memories", []),
            "beliefs": self.character_schema.get("beliefs", {}),
            "goals": self.character_schema.get("goals", []),
            "messages": [] # 初始消息为空
        })

        self.logger.info(f"角色智能体 {self.name} (ID: {self.id}) 已初始化。")

    def update_character_state(self, new_state_partial: Dict[str, Any]) -> None:
        """
        更新角色状态。
        允许部分更新角色的内部状态，例如情感、目标或记忆。

        参数:
            new_state_partial: 包含要更新的状态字段的字典。
        """
        # 这里需要更细致地处理 TypedDict 的更新
        # 例如，对于列表类型的字段 (memories, goals, messages)，通常是追加而不是替换
        # 对于字典类型的字段 (personality, cognitive, etc.)，可能是深度合并

        for key, value in new_state_partial.items():
            if key in self.character_state:
                if isinstance(self.character_state[key], list) and isinstance(value, list):
                    # 对于 'memories' 和 'goals'，通常是追加
                    if key in ['memories', 'goals']:
                        self.character_state[key].extend(value) # type: ignore
                    elif key == 'messages': # messages 通常由 LangGraph 的 add_messages处理，这里谨慎处理
                         self.character_state[key].extend(value) # type: ignore
                    else:
                        # 其他列表字段，根据需要决定是替换还是合并
                        self.character_state[key] = value # type: ignore
                elif isinstance(self.character_state[key], dict) and isinstance(value, dict):
                    # 深度合并字典类型的状态
                    # self.character_state[key].update(value) # 这只是浅合并
                    self._deep_update_dict(self.character_state[key], value) # type: ignore
                else:
                    self.character_state[key] = value # type: ignore
            else:
                self.logger.warning(f"尝试更新的状态字段 '{key}' 在 CharacterAgentState 中不存在。")
        self.logger.info(f"角色 {self.name} 的状态已更新。")

    def _deep_update_dict(self, d: Dict, u: Dict) -> Dict:
        """辅助函数，用于深度更新字典。"""
        for k, v in u.items():
            if isinstance(v, dict):
                d[k] = self._deep_update_dict(d.get(k, {}), v)
            else:
                d[k] = v
        return d

    async def generate_dialogue(self, context: Dict[str, Any], tone: Optional[str] = None) -> str:
        """
        根据当前上下文和可选的语气生成角色对话。

        参数:
            context: 对话发生的上下文信息，可能包括场景描述、其他角色等。
            tone: 可选，指定对话的语气 (例如："happy", "sad", "angry")。

        返回:
            生成的对话字符串。
        """
        # 实现将依赖于LLMService和角色的性格、状态
        self.logger.debug(f"角色 {self.name} 正在生成对话，上下文: {context}, 语气: {tone}")
        # 示例: 构建提示并调用LLM
        prompt = (
            f"作为角色 {self.name} (性格: {self.character_state['personality']}), "
            f"在以下情境中回应: {context}.\n"
            f"当前情绪: {self.character_state['emotional'].get('current_mood', 'neutral')}. "
            f"{f'语气请保持 {tone}.' if tone else ''}"
        )
        
        # 假设LLMService有一个generate方法
        # response = await self.llm_service.generate(prompt, max_tokens=150) 
        # return response.text
        # 当前llm_service接口不明确，暂时返回固定文本
        # TODO: 对接真实的LLMService实现
        await asyncio.sleep(0.1) # 模拟异步操作
        return f"{self.name}: 这是基于上下文 '{context.get('topic', '未知话题')}' 和语气 '{tone if tone else '默认'}' 生成的一段对话。"

    async def make_decision(self, options: List[Dict[str, Any]], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        角色在给定选项和当前上下文的情况下做出决策。

        参数:
            options: 一个包含可选决策的列表，每个决策是一个字典。
            context: 决策的上下文信息。

        返回:
            角色选择的决策（字典）。
        """
        # 实现将考虑角色的目标、性格和当前状态
        self.logger.debug(f"角色 {self.name} 正在做决策，选项: {options}, 上下文: {context}")
        # TODO: 实现决策逻辑，可能调用LLM
        await asyncio.sleep(0.1) # 模拟异步操作
        if options:
            return options[0] # 简单返回第一个选项作为示例
        return {"decision": "no_valid_options", "reason": "选项列表为空"}

    async def react_to_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        角色对外部事件或内部状态变化作出反应。

        参数:
            event: 描述事件的字典。

        返回:
            角色反应的结果或产生的任何新动作/状态更新。
        """
        self.logger.debug(f"角色 {self.name} 正在对事件 {event.get('type', '未知类型')} 作出反应。")
        # TODO: 实现事件反应逻辑，可能更新内部状态，生成对话或动作
        await asyncio.sleep(0.1) # 模拟异步操作
        # 示例：如果事件是“发现物品”，更新记忆
        if event.get("type") == "discovery" and "item_name" in event:
            memory_entry = {"type": "event_reaction", "event": event, "thought": f"我发现了 {event['item_name']}!"}
            self.update_character_state({"memories": [memory_entry]})
            return {"reaction": "memorized_discovery", "item": event['item_name']}
        return {"reaction": "acknowledged", "event_type": event.get("type")}

    def update_relationships(self, other_character_id: str, interaction: Dict[str, Any]) -> None:
        """
        根据与另一个角色的互动来更新角色间的关系。

        参数:
            other_character_id: 另一个角色的ID。
            interaction: 描述互动的字典，例如互动类型、结果等。
        """
        self.logger.debug(f"角色 {self.name} 正在更新与 {other_character_id} 的关系，互动: {interaction}")
        current_social_state = self.character_state.get("social", {})
        if not isinstance(current_social_state, dict):
             current_social_state = {} # 如果social不是dict，则重置
        relationships = current_social_state.get("relationships", {})
        if not isinstance(relationships, dict):
            relationships = {} # 如果relationships不是dict，则重置

        # 示例：简单地记录互动次数
        if other_character_id not in relationships:
            relationships[other_character_id] = {"interaction_count": 0, "sentiment": "neutral"}
        
        relationships[other_character_id]["interaction_count"] = relationships[other_character_id].get("interaction_count", 0) + 1
        # TODO: 更复杂的关系更新逻辑，可能基于互动内容调整情感等
        
        new_social_state = {**current_social_state, "relationships": relationships}
        # TypedDict 不支持直接赋值给 self.character_state["social"]，需要通过 update_character_state
        self.update_character_state({"social": new_social_state}) 

    async def get_memory(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        根据查询检索角色的相关记忆。

        参数:
            query: 用于搜索记忆的查询字符串。
            limit: 返回记忆的最大数量。

        返回:
            一个包含相关记忆的列表。
        """
        self.logger.debug(f"角色 {self.name} 正在检索记忆，查询: {query}, 限制: {limit}")
        # TODO: 实现记忆检索逻辑，可能涉及向量搜索或关键词匹配
        # 此处简单返回最新的几个记忆作为示例
        all_memories = self.character_state.get("memories", [])
        if not isinstance(all_memories, list):
            all_memories = [] # 确保是列表
        
        # 简单的基于query的过滤示例 (非常基础)
        relevant_memories = []
        for mem in reversed(all_memories):
            if isinstance(mem, dict) and query.lower() in str(mem.values()).lower():
                relevant_memories.append(mem)
            if len(relevant_memories) >= limit:
                break
        await asyncio.sleep(0.1) # 模拟异步操作
        return relevant_memories

    async def process_feedback(self, feedback: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理关于角色行为或对话的反馈，并可能据此调整内部状态或模型。

        参数:
            feedback: 包含反馈信息的字典，例如用户评价、指导等。

        返回:
            处理反馈后的确认或结果。
        """
        self.logger.debug(f"角色 {self.name} 正在处理反馈: {feedback}")
        # TODO: 实现反馈处理逻辑，可能调整性格、目标或对话模式
        # 示例：如果反馈是关于某个对话的，记录下来
        if feedback.get("type") == "dialogue_critique":
            critique_memory = {"type": "feedback", "feedback_data": feedback, "reflection": "我需要改进我的对话方式。"}
            self.update_character_state({"memories": [critique_memory]})
            return {"status": "feedback_processed", "action": "logged_critique"}
        await asyncio.sleep(0.1) # 模拟异步操作
        return {"status": "feedback_acknowledged"}

    # 覆盖基类中的 _handle_action, _handle_query 等方法以实现 CharacterAgent 的特定行为
    # 例如，一个 action可能是角色执行某个动作，一个 query 可能是查询角色的当前想法

    async def _handle_action(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        处理针对此角色智能体的动作命令。
        覆盖BaseAgent._handle_action
        """
        content = message.get("content", {})
        action_name = content.get("action", "")
        parameters = content.get("parameters", {})
        self.logger.info(f"角色 {self.name} 收到动作 '{action_name}'，参数: {parameters}")

        # TODO: 根据action_name执行特定动作逻辑
        # 例如: action_name == "move_to", parameters == {"location": "forest"}
        # 这可能涉及到调用 make_decision, react_to_event 或直接更新状态

        await asyncio.sleep(0.1) # 模拟异步操作
        return {
            "command_type": "response",
            "content": {
                "status": "action_completed",
                "action_name": action_name,
                "result": f"动作 '{action_name}' 已由 {self.name} 执行 (模拟)。",
                "response_to": message.get("id")
            },
            "source_id": self.id,
            "target_ids": [message.get("source_id")]
        }

    async def _handle_query(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        处理针对此角色智能体的查询命令。
        覆盖BaseAgent._handle_query
        """
        content = message.get("content", {})
        query_type = content.get("query", "")
        parameters = content.get("parameters", {})
        self.logger.info(f"角色 {self.name} 收到查询 '{query_type}'，参数: {parameters}")

        response_data = {}
        if query_type == "get_current_mood":
            response_data = {"mood": self.character_state.get("emotional", {}).get("current_mood")}
        elif query_type == "get_recent_memory":
            memories = await self.get_memory(query="", limit=1)
            response_data = {"memory": memories[0] if memories else None}
        else:
            response_data = {"error": f"未知查询类型: {query_type}"}
        
        await asyncio.sleep(0.1) # 模拟异步操作
        return {
            "command_type": "response",
            "content": {
                "status": "query_answered",
                "query_type": query_type,
                "data": response_data,
                "response_to": message.get("id")
            },
            "source_id": self.id,
            "target_ids": [message.get("source_id")]
        }

# 可以在文件末尾添加一个简单的测试或者示例用法，但这通常在测试文件中完成
# if __name__ == '__main__':
#     # 这是一个非常简化的LLMService模拟，实际中会更复杂
#     class MockLLMService(LLMService):
#         async def generate(self, prompt: str, **kwargs) -> Any:
#             class MockResponse: 
#                 def __init__(self, text): self.text = text
#             return MockResponse(f"LLM mock response to: {prompt[:50]}...")
#         async def generate_embedding(self, text: str, **kwargs) -> List[float]:
#             return [0.1] * 128 # 返回一个固定长度的模拟嵌入

#     async def main():
#         mock_llm = MockLLMService()
#         character_schema_example = {
#             "personality_traits": {"bravery": 0.8, "kindness": 0.6},
#             "cognitive_model": {"problem_solving_skill": 0.7},
#             "emotional_model": {"baseline_happiness": 0.75},
#             "dialogue_patterns": [{"trigger": "greeting", "response": "Hello there!"}],
#             "initial_memories": [{"type": "background", "content": "Born in a small village."}],
#             "goals": [{"type": "main_quest", "description": "Find the lost artifact."}]
#         }

#         agent = CharacterAgent(
#             id="char_001", 
#             name="Arin", 
#             llm_service=mock_llm, 
#             character_schema=character_schema_example
#         )

#         print(f"Agent Name: {agent.name}")
#         print(f"Agent ID: {agent.id}")
#         print(f"Initial State: {agent.character_state}")

#         dialogue = await agent.generate_dialogue(context={"topic": "the weather"}, tone="cheerful")
#         print(f"Generated Dialogue: {dialogue}")

#         decision = await agent.make_decision(options=[{"action": "go_left"}, {"action": "go_right"}], context={"situation": "at a crossroads"})
#         print(f"Decision Made: {decision}")
        
#         agent.update_character_state({"emotional": {"current_mood": "excited"}, "goals":[{"type":"new","description":"Explore cave"}]})
#         print(f"Updated State (mood): {agent.character_state['emotional']['current_mood']}")
#         print(f"Updated State (goals): {agent.character_state['goals']}")

#         memories = await agent.get_memory(query="village", limit=1)
#         print(f"Retrieved Memory: {memories}")

#     if __name__ == '__main__':
#         import asyncio
#         asyncio.run(main())
