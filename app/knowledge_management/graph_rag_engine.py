"""
GraphRAG引擎实现

实现基于图的检索增强生成引擎，整合Neo4j的图存储能力与向量检索
"""

import logging
import json
from typing import Dict, List, Optional, Tuple, Any, Union, Callable

from app.knowledge_management.hybrid_knowledge import HybridKnowledgeManager
from app.data_access.llm_adapter.base_llm_provider import LLMProvider
from app.data_access.cache.redis_client import RedisClient
from app.models.domain.knowledge import KnowledgeItem
from app.core.config import get_settings

logger = logging.getLogger(__name__)

# 获取配置
settings = get_settings()

class GraphRAGEngine:
    """
    实现基于图的检索增强生成引擎
    
    整合了向量检索和图检索的能力，提供更丰富的上下文理解
    """
    
    def __init__(
        self,
        hybrid_knowledge: HybridKnowledgeManager,
        llm_service: LLMProvider,
        redis_client: RedisClient = None,
        retrieval_strategies: Dict[str, Callable] = None,
        prompt_templates: Dict[str, str] = None,
        knowledge_formatter: Callable = None,
        response_formatter: Callable = None,
        max_context_length: int = 4000
    ):
        """
        初始化GraphRAG引擎
        
        参数:
            hybrid_knowledge: HybridKnowledgeManager - 混合知识管理器
            llm_service: LLMProvider - LLM服务实例
            redis_client: RedisClient - Redis客户端（用于缓存）
            retrieval_strategies: Dict[str, Callable] - 检索策略映射
            prompt_templates: Dict[str, str] - 提示模板映射
            knowledge_formatter: Callable - 知识格式化器
            response_formatter: Callable - 响应格式化器
            max_context_length: int - 最大上下文长度
        """
        self.hybrid_knowledge = hybrid_knowledge
        self.llm_service = llm_service
        self.redis_client = redis_client or RedisClient()
        self.max_context_length = max_context_length
        
        # 注册默认的检索策略
        self.retrieval_strategies = {
            "default": self._default_retrieval_strategy,
            "vector": self._vector_retrieval_strategy,
            "graph": self._graph_retrieval_strategy,
            "hybrid": self._hybrid_retrieval_strategy,
        }
        
        # 添加自定义检索策略
        if retrieval_strategies:
            self.retrieval_strategies.update(retrieval_strategies)
        
        # 默认提示模板
        self.default_prompt_template = """
        使用以下上下文回答问题。如果上下文中没有答案，请明确说明你不知道，不要编造答案。

        上下文:
        {context}

        问题:
        {query}
        
        答案:
        """
        
        # 设置提示模板
        self.prompt_templates = {
            "default": self.default_prompt_template,
            "qa": """
            使用以下知识库信息回答用户问题。如果知识库中没有答案，请明确说明你不知道，不要编造答案。
            
            知识库信息:
            {context}
            
            用户问题:
            {query}
            
            答案:
            """,
            "summarize": """
            根据以下上下文信息，为用户提供一个简洁但全面的摘要。
            
            上下文:
            {context}
            
            用户问题:
            {query}
            
            摘要:
            """
        }
        
        # 添加自定义提示模板
        if prompt_templates:
            self.prompt_templates.update(prompt_templates)
        
        # 设置格式化器
        self.knowledge_formatter = knowledge_formatter or self._default_knowledge_formatter
        self.response_formatter = response_formatter or self._default_response_formatter
    
    async def search_knowledge(
        self, 
        query: str, 
        limit: int = 10, 
        filters: Optional[Dict[str, Any]] = None
    ) -> List[KnowledgeItem]:
        """
        符合KnowledgeService接口的知识搜索方法
        
        参数:
            query: str - 搜索查询文本
            limit: int - 结果限制数量
            filters: Optional[Dict[str, Any]] - 过滤条件
            
        返回:
            List[KnowledgeItem] - 知识项列表
        """
        # 使用默认的混合检索策略
        results = await self.hybrid_knowledge.search(
            query=query,
            limit=limit,
            filters=filters,
            strategy="hybrid"
        )
        
        # 将结果转换为KnowledgeItem列表
        knowledge_items = []
        for result in results:
            # 提取ID，如果ID是图节点ID，则保留原样，否则生成临时ID
            knowledge_id = result.get("id", f"tmp_{len(knowledge_items)}")
            
            # 创建KnowledgeItem实例
            item = KnowledgeItem(
                id=str(knowledge_id),
                content=result.get("content", ""),
                metadata={
                    "score": result.get("score", 0.0),
                    "source": result.get("source", "unknown"),
                    **{k: v for k, v in result.items() if k not in ["id", "content", "score", "source"]}
                }
            )
            knowledge_items.append(item)
        
        return knowledge_items
    
    async def query(
        self, 
        query_text: str, 
        strategy: str = "default", 
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        增强的查询方法，提供额外功能
        
        参数:
            query_text: str - 查询文本
            strategy: str - 检索策略名称
            params: Dict[str, Any] - 额外参数
            
        返回:
            Dict[str, Any] - 查询结果
        """
        params = params or {}
        
        # 获取检索策略
        retrieval_strategy = self.retrieval_strategies.get(
            strategy, self.retrieval_strategies["default"]
        )
        
        # 检索知识
        knowledge_context = await self.retrieve_knowledge(
            query_text=query_text,
            strategy=strategy, 
            params=params
        )
        
        # 生成响应
        response = await self.generate_response(
            query_text=query_text,
            knowledge_context=knowledge_context,
            strategy=strategy
        )
        
        # 评估响应质量
        quality_score = await self._evaluate_response_quality(
            query=query_text,
            response=response,
            knowledge=knowledge_context
        )
        
        # 返回结果
        return {
            "answer": response,
            "context": knowledge_context,
            "quality_score": quality_score,
            "strategy": strategy
        }
    
    async def retrieve_knowledge(
        self, 
        query_text: str, 
        strategy: str, 
        params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        检索知识
        
        参数:
            query_text: str - 查询文本
            strategy: str - 检索策略名称
            params: Dict[str, Any] - 额外参数
            
        返回:
            List[Dict[str, Any]] - 检索到的知识
        """
        # 获取检索策略
        retrieval_strategy = self.retrieval_strategies.get(
            strategy, self.retrieval_strategies["default"]
        )
        
        # 执行检索
        knowledge_items = await retrieval_strategy(
            query_text=query_text,
            **params
        )
        
        return knowledge_items
    
    async def generate_response(
        self, 
        query_text: str, 
        knowledge_context: List[Dict[str, Any]], 
        strategy: str
    ) -> str:
        """
        生成响应
        
        参数:
            query_text: str - 查询文本
            knowledge_context: List[Dict[str, Any]] - 知识上下文
            strategy: str - 策略名称
            
        返回:
            str - 生成的响应
        """
        # 获取提示模板
        prompt_template = self.prompt_templates.get(
            strategy, self.prompt_templates["default"]
        )
        
        # 准备LLM上下文
        context = await self._prepare_context(knowledge_context)
        
        # 截断上下文以适应LLM限制
        context = await self._truncate_context(context)
        
        # 准备完整提示
        prompt = prompt_template.format(
            context=context,
            query=query_text
        )
        
        # 调用LLM生成响应
        response = await self.llm_service.generate_text(prompt)
        
        # 应用响应格式化
        formatted_response = await self._apply_response_formatting(response)
        
        return formatted_response
    
    async def register_strategy(
        self, 
        name: str, 
        retrieval_func: Callable, 
        prompt_template: str
    ) -> None:
        """
        注册检索策略
        
        参数:
            name: str - 策略名称
            retrieval_func: Callable - 检索函数
            prompt_template: str - 提示模板
        """
        self.retrieval_strategies[name] = retrieval_func
        self.prompt_templates[name] = prompt_template
        logger.info(f"Registered retrieval strategy: {name}")
    
    async def register_formatter(self, formatter_type: str, formatter_func: Callable) -> None:
        """
        注册格式化器
        
        参数:
            formatter_type: str - 格式化器类型，"knowledge"或"response"
            formatter_func: Callable - 格式化函数
        """
        if formatter_type == "knowledge":
            self.knowledge_formatter = formatter_func
        elif formatter_type == "response":
            self.response_formatter = formatter_func
        else:
            raise ValueError(f"未知的格式化器类型: {formatter_type}")
        
        logger.info(f"Registered {formatter_type} formatter")
    
    async def _prepare_context(self, knowledge_items: List[Dict[str, Any]]) -> str:
        """
        准备LLM上下文
        
        参数:
            knowledge_items: List[Dict[str, Any]] - 知识项列表
            
        返回:
            str - 格式化的上下文
        """
        # 使用知识格式化器格式化每个知识项
        formatted_items = []
        for i, item in enumerate(knowledge_items):
            formatted_item = self.knowledge_formatter(item)
            formatted_items.append(f"[{i+1}] {formatted_item}")
        
        # 合并为单个字符串
        context = "\n\n".join(formatted_items)
        
        return context
    
    async def _truncate_context(self, context: str) -> str:
        """
        截断上下文以适应LLM限制
        
        参数:
            context: str - 完整上下文
            
        返回:
            str - 截断后的上下文
        """
        # 简单截断实现
        if len(context) > self.max_context_length:
            context = context[:self.max_context_length] + "..."
        
        return context
    
    async def _apply_response_formatting(self, response: str) -> str:
        """
        应用响应格式化
        
        参数:
            response: str - 原始响应
            
        返回:
            str - 格式化后的响应
        """
        return self.response_formatter(response)
    
    async def _evaluate_response_quality(
        self, 
        query: str, 
        response: str, 
        knowledge: List[Dict[str, Any]]
    ) -> float:
        """
        评估响应质量
        
        参数:
            query: str - 查询文本
            response: str - 生成的响应
            knowledge: List[Dict[str, Any]] - 知识上下文
            
        返回:
            float - 质量分数(0-1)
        """
        # 简单实现：使用LLM自我评估
        # 在实际应用中，可以扩展为更复杂的评估逻辑
        eval_prompt = f"""
        评估以下回答的质量。考虑以下因素：
        1. 答案与问题的相关性
        2. 答案是否基于提供的知识
        3. 答案的完整性和准确性
        
        问题: {query}
        
        参考知识:
        {await self._prepare_context(knowledge)}
        
        生成的回答:
        {response}
        
        质量评分（0-100的整数，其中100表示最高质量）:
        """
        
        eval_response = await self.llm_service.generate_text(eval_prompt)
        
        # 尝试从回答中提取分数
        try:
            # 假设回答格式为一个数字
            score_text = eval_response.strip()
            # 提取数字
            score = float(''.join(c for c in score_text if c.isdigit() or c == '.'))
            # 转换为0-1范围
            normalized_score = min(100, max(0, score)) / 100
            return normalized_score
        except Exception:
            logger.warning("无法从评估响应中提取分数，返回默认值0.5")
            return 0.5
    
    async def _default_retrieval_strategy(
        self, 
        query_text: str, 
        top_k: int = 5, 
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        默认检索策略（使用混合检索）
        
        参数:
            query_text: str - 查询文本
            top_k: int - 返回结果数量
            **kwargs - 额外参数
            
        返回:
            List[Dict[str, Any]] - 检索结果
        """
        return await self._hybrid_retrieval_strategy(query_text, top_k, **kwargs)
    
    async def _vector_retrieval_strategy(
        self, 
        query_text: str, 
        top_k: int = 5, 
        filters: Dict[str, Any] = None, 
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        向量检索策略
        
        参数:
            query_text: str - 查询文本
            top_k: int - 返回结果数量
            filters: Dict[str, Any] - 过滤条件
            **kwargs - 额外参数
            
        返回:
            List[Dict[str, Any]] - 检索结果
        """
        # 使用向量检索
        results = await self.hybrid_knowledge.search(
            query=query_text,
            limit=top_k,
            filters=filters,
            strategy="vector"
        )
        
        return results
    
    async def _graph_retrieval_strategy(
        self, 
        query_text: str, 
        top_k: int = 5, 
        filters: Dict[str, Any] = None, 
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        图检索策略
        
        参数:
            query_text: str - 查询文本
            top_k: int - 返回结果数量
            filters: Dict[str, Any] - 过滤条件
            **kwargs - 额外参数
            
        返回:
            List[Dict[str, Any]] - 检索结果
        """
        # 使用图检索
        results = await self.hybrid_knowledge.search(
            query=query_text,
            limit=top_k,
            filters=filters,
            strategy="graph"
        )
        
        return results
    
    async def _hybrid_retrieval_strategy(
        self, 
        query_text: str, 
        top_k: int = 5, 
        filters: Dict[str, Any] = None, 
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        混合检索策略（向量+图）
        
        参数:
            query_text: str - 查询文本
            top_k: int - 返回结果数量
            filters: Dict[str, Any] - 过滤条件
            **kwargs - 额外参数
            
        返回:
            List[Dict[str, Any]] - 检索结果
        """
        # 使用混合检索
        results = await self.hybrid_knowledge.search(
            query=query_text,
            limit=top_k,
            filters=filters,
            strategy="hybrid"
        )
        
        return results
    
    def _default_knowledge_formatter(self, item: Dict[str, Any]) -> str:
        """
        默认知识格式化器
        
        参数:
            item: Dict[str, Any] - 知识项
            
        返回:
            str - 格式化后的知识文本
        """
        content = item.get("content", "")
        score = item.get("score", 0.0)
        
        # 提取有用的元数据
        metadata = {}
        for key, value in item.items():
            if key not in ["id", "content", "score", "source"] and value is not None:
                metadata[key] = value
        
        # 格式化元数据字符串
        metadata_str = ""
        if metadata:
            metadata_str = f" [元数据: {', '.join([f'{k}={v}' for k, v in metadata.items()])}]"
        
        # 返回格式化文本
        return f"{content}{metadata_str} (相关度: {score:.2f})"
    
    def _default_response_formatter(self, response: str) -> str:
        """
        默认响应格式化器
        
        参数:
            response: str - 原始响应
            
        返回:
            str - 格式化后的响应
        """
        # 简单实现：清理响应中的多余空白
        cleaned_response = response.strip()
        
        return cleaned_response
