"""
嵌入生成和管理模块

该模块提供嵌入向量的生成、缓存和管理功能，支持不同的嵌入模型和缓存策略。
"""

import hashlib
import logging
import re
from typing import List, Dict, Any, Optional, Tuple, Union, cast

import numpy as np

# 导入配置和依赖服务
from app.core.config import get_settings
from app.data_access.cache.redis_client import RedisClient
from app.data_access.llm_adapter.base_llm_provider import LLMProvider

logger = logging.getLogger(__name__)

class EmbeddingService:
    """管理文本嵌入生成的服务"""
    
    def __init__(
        self,
        model_name: str,
        model_config: Dict[str, Any],
        llm_service: LLMProvider,
        redis_client: Optional[RedisClient] = None
    ):
        """
        初始化嵌入服务
        
        参数:
            model_name: str - 嵌入模型名称
            model_config: Dict[str, Any] - 模型配置
            llm_service: LLMService - LLM服务，用于生成嵌入
            redis_client: Optional[RedisClient] - Redis客户端（用于分布式缓存）
        """
        self.model_name = model_name
        self.model_config = model_config
        self.llm_service = llm_service
        self.redis_client = redis_client
        self.cache = {}  # 本地内存缓存
        self.cache_ttl = model_config.get("cache_ttl", 3600 * 24)  # 默认缓存24小时
        self.dimensions = model_config.get("dimensions", 1536)  # 默认维度
        
        # 缓存键前缀
        self.cache_prefix = f"embedding:{self.model_name}:"
    
    async def get_embedding(self, text: str) -> List[float]:
        """
        获取文本嵌入
        
        参数:
            text: str - 需要嵌入的文本
            
        返回:
            List[float] - 嵌入向量
        """
        # 预处理文本
        processed_text = await self.preprocess_text(text)
        
        # 计算文本的哈希值作为缓存键
        text_hash = self._get_text_hash(processed_text)
        cache_key = f"{self.cache_prefix}{text_hash}"
        
        # 尝试从缓存获取
        cached_embedding = await self.get_cached_embedding(cache_key)
        if cached_embedding is not None:
            logger.debug(f"Using cached embedding for text hash: {text_hash}")
            return cached_embedding
        
        # 调用LLM服务生成嵌入
        try:
            embedding = await self.llm_service.get_embedding(processed_text)
            
            # 验证嵌入维度
            if len(embedding) != self.dimensions:
                logger.warning(
                    f"Embedding dimension mismatch. Expected {self.dimensions}, got {len(embedding)}"
                )
            
            # 缓存嵌入
            await self.cache_embedding(cache_key, embedding)
            
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise
    
    async def batch_get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        批量获取文本嵌入
        
        参数:
            texts: List[str] - 需要嵌入的文本列表
            
        返回:
            List[List[float]] - 嵌入向量列表
        """
        # 预处理所有文本
        processed_texts = [await self.preprocess_text(text) for text in texts]
        
        # 计算每个文本的哈希值和缓存键
        text_hashes = [self._get_text_hash(text) for text in processed_texts]
        cache_keys = [f"{self.cache_prefix}{text_hash}" for text_hash in text_hashes]
        
        # 缓存结果和未缓存的文本
        cached_results = {}
        texts_to_embed = []
        indices_to_embed = []
        
        # 尝试从缓存获取
        for i, (text, cache_key) in enumerate(zip(processed_texts, cache_keys)):
            cached_embedding = await self.get_cached_embedding(cache_key)
            if cached_embedding is not None:
                cached_results[i] = cached_embedding
            else:
                texts_to_embed.append(text)
                indices_to_embed.append(i)
        
        # 如果有需要嵌入的文本
        if texts_to_embed:
            try:
                # 调用LLM服务批量生成嵌入
                new_embeddings = await self.llm_service.get_embeddings(texts_to_embed)
                
                # 缓存新生成的嵌入
                for idx, embedding in zip(indices_to_embed, new_embeddings):
                    cache_key = cache_keys[idx]
                    cached_results[idx] = embedding
                    await self.cache_embedding(cache_key, embedding)
            except Exception as e:
                logger.error(f"Error generating batch embeddings: {str(e)}")
                raise
        
        # 按原始顺序返回结果
        return [cached_results[i] for i in range(len(texts))]
    
    async def preprocess_text(self, text: str) -> str:
        """
        预处理文本，用于嵌入生成前的标准化
        
        参数:
            text: str - 原始文本
            
        返回:
            str - 预处理后的文本
        """
        if not text:
            return ""
        
        # 替换多个空格为单个空格
        text = re.sub(r"\s+", " ", text)
        
        # 去除前后空格
        text = text.strip()
        
        # 应用自定义预处理逻辑
        # ...（可根据实际需求扩展）
        
        return text
    
    async def cache_embedding(self, cache_key: str, embedding: List[float]) -> None:
        """
        缓存嵌入向量
        
        参数:
            cache_key: str - 缓存键
            embedding: List[float] - 嵌入向量
        """
        # 本地缓存
        self.cache[cache_key] = embedding
        
        # 如果配置了Redis客户端，则同时缓存到Redis
        if self.redis_client:
            try:
                # 将嵌入向量转换为字节
                embedding_bytes = np.array(embedding, dtype=np.float32).tobytes()
                
                # 缓存到Redis，带过期时间
                await self.redis_client.set(
                    cache_key, 
                    embedding_bytes,
                    expire=self.cache_ttl
                )
            except Exception as e:
                logger.warning(f"Failed to cache embedding to Redis: {str(e)}")
    
    async def get_cached_embedding(self, cache_key: str) -> Optional[List[float]]:
        """
        获取缓存的嵌入向量
        
        参数:
            cache_key: str - 缓存键
            
        返回:
            Optional[List[float]] - 缓存的嵌入向量，如果不存在则返回None
        """
        # 首先检查本地缓存
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # 如果配置了Redis客户端，则从Redis获取
        if self.redis_client:
            try:
                embedding_bytes = await self.redis_client.get(cache_key)
                if embedding_bytes:
                    # 将字节转换回嵌入向量
                    embedding = np.frombuffer(embedding_bytes, dtype=np.float32).tolist()
                    
                    # 更新本地缓存
                    self.cache[cache_key] = embedding
                    
                    return embedding
            except Exception as e:
                logger.warning(f"Failed to get cached embedding from Redis: {str(e)}")
        
        return None
    
    async def clear_cache(self) -> None:
        """清除缓存"""
        # 清除本地缓存
        self.cache.clear()
        
        # 如果配置了Redis客户端，则清除Redis缓存
        if self.redis_client:
            try:
                # 获取所有匹配的键
                pattern = f"{self.cache_prefix}*"
                keys = await self.redis_client.keys(pattern)
                
                # 批量删除
                if keys:
                    await self.redis_client.delete(*keys)
                    
                logger.info(f"Cleared {len(keys)} embedding cache entries from Redis")
            except Exception as e:
                logger.warning(f"Failed to clear embedding cache from Redis: {str(e)}")
    
    def _get_text_hash(self, text: str) -> str:
        """
        获取文本的哈希值
        
        参数:
            text: str - 文本
            
        返回:
            str - 哈希值
        """
        return hashlib.md5(text.encode()).hexdigest()
        
    async def get_vector_dimension(self) -> int:
        """
        获取嵌入向量的维度
        
        返回:
            int - 嵌入向量的维度
        """
        return self.dimensions
