"""
嵌入服务模块

提供文本嵌入服务，用于向量搜索和语义相似度计算
"""

import logging
from typing import Any, Dict, List, Optional, Union
import numpy as np
import asyncio

from app.data_access.llm_adapter.base_llm_provider import LLMProvider
from app.data_access.llm_adapter.openai_provider import OpenAIProvider
from app.data_access.llm_adapter.anthropic_provider import AnthropicProvider

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    嵌入服务类
    
    提供文本嵌入功能，支持多种嵌入模型和提供商
    """
    
    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        model_name: str = "text-embedding-3-small",
        dimensions: int = 1536,
        batch_size: int = 20,
        max_retries: int = 3,
        timeout: int = 60
    ):
        """
        初始化嵌入服务
        
        参数:
            provider: LLM提供商实例，如果不提供则默认使用OpenAI
            model_name: 嵌入模型名称
            dimensions: 嵌入向量维度
            batch_size: 批处理大小
            max_retries: 最大重试次数
            timeout: 超时时间（秒）
        """
        self.provider = provider or OpenAIProvider()
        self.model_name = model_name
        self.dimensions = dimensions
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.timeout = timeout
        
        # 维度映射，根据不同模型确定维度
        self.model_dimensions = {
            # OpenAI模型
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
            # Anthropic模型
            "claude-3-opus": 4096,
            "claude-3-sonnet": 4096,
            "claude-3-haiku": 4096,
            # 自定义模型维度可继续添加
        }
        
        # 如果提供了模型名称，更新维度
        if model_name in self.model_dimensions:
            self.dimensions = self.model_dimensions[model_name]
    
    async def get_embedding(self, text: str) -> List[float]:
        """
        获取单个文本的嵌入向量
        
        参数:
            text: 需要嵌入的文本
            
        返回:
            List[float]: 嵌入向量
        """
        # 单个文本处理为列表，复用batch处理逻辑
        embeddings = await self.get_embeddings([text])
        return embeddings[0] if embeddings else []
    
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        批量获取文本的嵌入向量
        
        参数:
            texts: 需要嵌入的文本列表
            
        返回:
            List[List[float]]: 嵌入向量列表
        """
        if not texts:
            return []
        
        try:
            # 分批处理，避免请求过大
            batches = [texts[i:i + self.batch_size] for i in range(0, len(texts), self.batch_size)]
            
            # 并行处理所有批次
            embedding_tasks = [self._process_batch(batch) for batch in batches]
            all_embeddings = await asyncio.gather(*embedding_tasks)
            
            # 合并结果
            return [embedding for batch_embeddings in all_embeddings for embedding in batch_embeddings]
        except Exception as e:
            logger.error(f"获取嵌入向量失败: {str(e)}")
            # 返回空向量
            return [self._get_empty_embedding() for _ in texts]
    
    async def _process_batch(self, texts: List[str]) -> List[List[float]]:
        """
        处理一批文本的嵌入请求
        
        参数:
            texts: 需要嵌入的文本批次
            
        返回:
            List[List[float]]: 嵌入向量列表
        """
        retries = 0
        last_error = None
        
        # 重试逻辑
        while retries < self.max_retries:
            try:
                # 根据提供商类型调用不同的API
                if isinstance(self.provider, OpenAIProvider):
                    # OpenAI嵌入API
                    response = await self.provider.client.embeddings.create(
                        input=texts,
                        model=self.model_name,
                        timeout=self.timeout
                    )
                    return [item.embedding for item in response.data]
                elif isinstance(self.provider, AnthropicProvider):
                    # Anthropic嵌入API (假设实现)
                    # 注意：目前Anthropic可能没有官方的嵌入API，这里只是示例
                    raise NotImplementedError("Anthropic嵌入API尚未实现")
                else:
                    # 默认实现，调用通用方法
                    return await self._get_generic_embeddings(texts)
            except Exception as e:
                last_error = e
                retries += 1
                # 指数退避
                await asyncio.sleep(2 ** retries)
        
        # 所有重试都失败
        logger.error(f"获取嵌入向量重试{self.max_retries}次后失败: {str(last_error)}")
        return [self._get_empty_embedding() for _ in texts]
    
    async def _get_generic_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        通用的嵌入处理方法，用于未专门实现的提供商
        
        参数:
            texts: 需要嵌入的文本列表
            
        返回:
            List[List[float]]: 嵌入向量列表
        """
        # 这里可以实现调用通用API的逻辑，但目前返回空向量
        logger.warning(f"使用未专门实现的提供商获取嵌入向量: {type(self.provider).__name__}")
        return [self._get_empty_embedding() for _ in texts]
    
    def _get_empty_embedding(self) -> List[float]:
        """
        生成空的嵌入向量（全零）
        
        返回:
            List[float]: 空嵌入向量
        """
        return [0.0] * self.dimensions
    
    def normalize_embedding(self, embedding: List[float]) -> List[float]:
        """
        归一化嵌入向量
        
        参数:
            embedding: 嵌入向量
            
        返回:
            List[float]: 归一化后的嵌入向量
        """
        # 使用L2范数归一化
        norm = np.linalg.norm(embedding)
        if norm > 0:
            return [float(val / norm) for val in embedding]
        return embedding
    
    def cosine_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        计算两个嵌入向量间的余弦相似度
        
        参数:
            embedding1: 第一个嵌入向量
            embedding2: 第二个嵌入向量
            
        返回:
            float: 余弦相似度，范围[-1, 1]
        """
        # 空向量处理
        if not embedding1 or not embedding2:
            return 0.0
        
        # 确保维度一致
        if len(embedding1) != len(embedding2):
            raise ValueError(f"嵌入向量维度不匹配: {len(embedding1)} vs {len(embedding2)}")
        
        # 计算余弦相似度
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        # 避免除以零
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        return dot_product / (norm1 * norm2) 