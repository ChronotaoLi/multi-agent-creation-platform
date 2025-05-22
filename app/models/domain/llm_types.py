"""
LLM相关的类型定义

定义与大语言模型交互所需的数据类型
"""
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator


class ProviderType(str, Enum):
    """LLM服务提供者类型"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"
    HUGGINGFACE = "huggingface"
    SELF_HOSTED = "self_hosted"
    OTHER = "other"


class LLMRole(str, Enum):
    """消息角色"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"
    TOOL = "tool"


class MessageContentType(str, Enum):
    """消息内容类型"""
    TEXT = "text"
    IMAGE = "image"
    CODE = "code"
    JSON = "json"
    FILE = "file"
    

class LLMMessage(BaseModel):
    """LLM消息"""
    role: LLMRole
    content: str
    name: Optional[str] = None
    function_call: Optional[Dict[str, Any]] = None
    content_type: Optional[MessageContentType] = MessageContentType.TEXT
    
    class Config:
        use_enum_values = True


class LLMFunction(BaseModel):
    """LLM可调用函数定义"""
    name: str
    description: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    required: Optional[List[str]] = None


class LLMFunctionCall(BaseModel):
    """LLM函数调用结果"""
    name: str
    arguments: str
    

class LLMResponseChoice(BaseModel):
    """LLM响应选项"""
    index: int
    message: LLMMessage
    finish_reason: Optional[str] = None


class LLMUsage(BaseModel):
    """LLM使用量统计"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class LLMResponse(BaseModel):
    """LLM响应"""
    id: str
    object: str
    created: int
    model: str
    choices: List[LLMResponseChoice]
    usage: Optional[LLMUsage] = None
    raw_response: Optional[Dict[str, Any]] = None


class LLMEmbedding(BaseModel):
    """嵌入向量"""
    embedding: List[float]
    index: int = 0
    object: str = "embedding"


class ModelType(str, Enum):
    """模型类型"""
    CHAT = "chat"
    COMPLETION = "completion"
    EMBEDDING = "embedding"
    IMAGE = "image"
    AUDIO = "audio"


class ModelConfig(BaseModel):
    """模型配置"""
    name: str
    provider: ProviderType
    type: ModelType = ModelType.CHAT
    context_window: int = 4096
    pricing_prompt: float = 0.0
    pricing_completion: float = 0.0
    default_max_tokens: Optional[int] = None
    supports_functions: bool = False
    supports_vision: bool = False
    supports_streaming: bool = True
    

class ProviderConfig(BaseModel):
    """提供者配置"""
    type: ProviderType
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    models: List[ModelConfig] = Field(default_factory=list)
    default_model: Optional[str] = None
    default_embedding_model: Optional[str] = None
    organization_id: Optional[str] = None
    
    @validator('default_model', 'default_embedding_model')
    def model_must_exist(cls, v, values):
        if v is not None and 'models' in values:
            model_names = [model.name for model in values['models']]
            if v not in model_names:
                raise ValueError(f"模型 {v} 不在配置的模型列表中")
        return v


class LLMConfig(BaseModel):
    """LLM整体配置"""
    providers: List[ProviderConfig] = Field(default_factory=list)
    default_provider: Optional[ProviderType] = None
    
    @validator('default_provider')
    def provider_must_exist(cls, v, values):
        if v is not None and 'providers' in values:
            provider_types = [provider.type for provider in values['providers']]
            if v not in provider_types:
                raise ValueError(f"提供者 {v} 不在配置的提供者列表中")
        return v


class LLMProvider:
    """LLM提供者
    
    提供与特定LLM服务提供商的交互功能
    """
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.client = None
        
    async def initialize(self) -> None:
        """初始化提供者客户端"""
        raise NotImplementedError("子类必须实现initialize方法")
    
    async def chat_completion(
        self, 
        messages: List[LLMMessage], 
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        functions: Optional[List[LLMFunction]] = None,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> LLMResponse:
        """获取聊天补全响应"""
        raise NotImplementedError("子类必须实现chat_completion方法")
    
    async def get_embeddings(
        self, 
        texts: Union[str, List[str]], 
        model: str
    ) -> Union[LLMEmbedding, List[LLMEmbedding]]:
        """获取文本嵌入向量"""
        raise NotImplementedError("子类必须实现get_embeddings方法")
    
    async def streaming_chat_completion(
        self, 
        messages: List[LLMMessage], 
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        functions: Optional[List[LLMFunction]] = None,
        stop: Optional[List[str]] = None,
        **kwargs
    ):
        """流式获取聊天补全响应"""
        raise NotImplementedError("子类必须实现streaming_chat_completion方法") 