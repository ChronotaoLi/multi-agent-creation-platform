"""
Milvus向量数据库访问客户端

提供与Milvus向量数据库交互的基本操作
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
import uuid
import time
from datetime import datetime

from pymilvus import Collection, connections, FieldSchema, CollectionSchema, DataType, utility

from app.core.config import get_settings
from app.utils.error_handlers import VectorStoreError

logger = logging.getLogger(__name__)


class MilvusClient:
    """Milvus向量数据库访问客户端"""
    
    def __init__(
        self,
        uri: str = None,
        user: str = None,
        password: str = None,
        connection_alias: str = "default"
    ):
        """
        初始化Milvus客户端
        
        参数:
            uri: str - Milvus服务端URI，例如 'http://localhost:19530'
            user: str - 用户名
            password: str - 密码
            connection_alias: str - 连接别名
        """
        self.settings = get_settings()
        self.uri = uri or self.settings.milvus_uri
        self.user = user or self.settings.milvus_username
        self.password = password or self.settings.milvus_password
        self.connection_alias = connection_alias
        self._collections = {}  # 集合缓存
        self._connected = False
    
    async def connect(self) -> None:
        """
        连接到Milvus服务器
        
        异常:
            VectorStoreError: 连接失败
        """
        try:
            # 使用pymilvus的connections模块连接到服务器
            connections.connect(
                alias=self.connection_alias,
                uri=self.uri,
                user=self.user,
                password=self.password
            )
            self._connected = True
            logger.info(f"已成功连接到Milvus: {self.uri}")
        except Exception as e:
            logger.error(f"连接Milvus失败: {str(e)}")
            self._connected = False
            raise VectorStoreError(f"连接Milvus失败: {str(e)}")
    
    async def _ensure_connected(self) -> None:
        """
        确保已连接到Milvus服务器
        
        异常:
            VectorStoreError: 未连接到服务器
        """
        if not self._connected:
            await self.connect()
    
    async def create_collection(
        self,
        collection_name: str,
        vector_dimension: int,
        description: str = None,
        index_params: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        创建新的集合
        
        参数:
            collection_name: str - 集合名称
            vector_dimension: int - 向量维度
            description: str - 集合描述
            index_params: Optional[Dict[str, Any]] - 索引参数
        
        异常:
            VectorStoreError: 创建集合失败
        """
        await self._ensure_connected()
        
        try:
            # 检查集合是否已存在
            if utility.has_collection(collection_name):
                logger.info(f"集合 {collection_name} 已存在，跳过创建")
                return
            
            # 定义字段
            fields = [
                # 主键字段
                FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=36, description="主键ID"),
                # 向量字段
                FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=vector_dimension, description="嵌入向量"),
                # 文本内容字段
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535, description="文本内容"),
                # 元数据字段 - 存储为JSON字符串
                FieldSchema(name="metadata", dtype=DataType.VARCHAR, max_length=65535, description="元数据(JSON)"),
                # 创建时间字段
                FieldSchema(name="created_at", dtype=DataType.INT64, description="创建时间戳")
            ]
            
            # 创建集合模式
            schema = CollectionSchema(
                fields=fields,
                description=description or f"Created at {datetime.utcnow().isoformat()}"
            )
            
            # 创建集合
            collection = Collection(name=collection_name, schema=schema)
            
            # 创建索引
            if not index_params:
                index_params = {
                    "index_type": "HNSW",
                    "metric_type": "COSINE", # 余弦相似度
                    "params": {
                        "M": 16,  # 更大的值构建更高质量的图，但消耗更多内存
                        "efConstruction": 200  # 更大的值意味着更高的索引准确度，但构建索引速度更慢
                    }
                }
            
            # 在向量字段上创建索引
            collection.create_index(
                field_name="vector", 
                index_params=index_params
            )
            
            logger.info(f"已成功创建集合 {collection_name} 并添加索引")
        except Exception as e:
            logger.error(f"创建集合失败: {str(e)}")
            raise VectorStoreError(f"创建集合失败: {str(e)}")
    
    async def drop_collection(self, collection_name: str) -> None:
        """
        删除集合
        
        参数:
            collection_name: str - 集合名称
            
        异常:
            VectorStoreError: 删除集合失败
        """
        await self._ensure_connected()
        
        try:
            if utility.has_collection(collection_name):
                # 加载集合实例
                collection = Collection(collection_name)
                # 删除集合
                collection.drop()
                # 从缓存中移除
                if collection_name in self._collections:
                    del self._collections[collection_name]
                logger.info(f"已成功删除集合 {collection_name}")
            else:
                logger.info(f"集合 {collection_name} 不存在，无需删除")
        except Exception as e:
            logger.error(f"删除集合失败: {str(e)}")
            raise VectorStoreError(f"删除集合失败: {str(e)}")
    
    async def get_collection(self, collection_name: str) -> Collection:
        """
        获取集合实例
        
        参数:
            collection_name: str - 集合名称
            
        返回:
            Collection - pymilvus Collection实例
            
        异常:
            VectorStoreError: 获取集合失败
        """
        await self._ensure_connected()
        
        try:
            # 检查集合是否存在
            if not utility.has_collection(collection_name):
                raise VectorStoreError(f"集合 {collection_name} 不存在")
            
            # 缓存中有则直接返回
            if collection_name in self._collections:
                return self._collections[collection_name]
            
            # 创建并加载集合
            collection = Collection(collection_name)
            collection.load()
            
            # 缓存集合
            self._collections[collection_name] = collection
            
            return collection
        except Exception as e:
            if not isinstance(e, VectorStoreError):
                logger.error(f"获取集合失败: {str(e)}")
                raise VectorStoreError(f"获取集合失败: {str(e)}")
            raise
    
    async def insert(
        self,
        collection_name: str,
        vectors: List[List[float]],
        contents: List[str],
        metadatas: List[Dict[str, Any]] = None,
        ids: List[str] = None
    ) -> List[str]:
        """
        向集合中插入数据
        
        参数:
            collection_name: str - 集合名称
            vectors: List[List[float]] - 向量数据列表
            contents: List[str] - 内容文本列表
            metadatas: List[Dict[str, Any]] - 元数据列表（可选）
            ids: List[str] - ID列表，如不提供则自动生成（可选）
            
        返回:
            List[str] - 插入数据的ID列表
            
        异常:
            VectorStoreError: 插入数据失败
        """
        await self._ensure_connected()
        
        # 检查输入参数
        if not vectors or len(vectors) == 0:
            raise ValueError("向量数据不能为空")
        
        if not contents or len(contents) != len(vectors):
            raise ValueError("内容文本数量必须与向量数据数量相同")
        
        # 准备元数据
        if not metadatas:
            metadatas = [{} for _ in range(len(vectors))]
        elif len(metadatas) != len(vectors):
            raise ValueError("元数据数量必须与向量数据数量相同")
        
        # 准备字符串格式的元数据
        import json
        metadata_strs = [json.dumps(m) for m in metadatas]
        
        # 准备ID
        if not ids:
            ids = [str(uuid.uuid4()) for _ in range(len(vectors))]
        elif len(ids) != len(vectors):
            raise ValueError("ID数量必须与向量数据数量相同")
        
        # 当前时间戳
        current_time = int(time.time() * 1000)  # 毫秒级时间戳
        timestamps = [current_time] * len(vectors)
        
        try:
            # 获取集合
            collection = await self.get_collection(collection_name)
            
            # 准备数据
            data = [
                ids,          # id
                vectors,      # vector
                contents,     # content
                metadata_strs,  # metadata
                timestamps    # created_at
            ]
            
            # 插入数据
            result = collection.insert(data)
            
            logger.info(f"已成功向集合 {collection_name} 中插入 {len(vectors)} 条数据")
            return ids
        except Exception as e:
            logger.error(f"插入数据失败: {str(e)}")
            raise VectorStoreError(f"插入数据失败: {str(e)}")
    
    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        top_k: int = 10,
        output_fields: List[str] = None,
        filters: str = None
    ) -> List[Dict[str, Any]]:
        """
        向量搜索
        
        参数:
            collection_name: str - 集合名称
            query_vector: List[float] - 查询向量
            top_k: int - 返回结果数量
            output_fields: List[str] - 返回字段列表
            filters: str - 过滤条件，Milvus表达式格式
            
        返回:
            List[Dict[str, Any]] - 搜索结果列表
            
        异常:
            VectorStoreError: 搜索失败
        """
        await self._ensure_connected()
        
        try:
            # 获取集合
            collection = await self.get_collection(collection_name)
            
            # 默认返回所有字段
            if not output_fields:
                output_fields = ["id", "content", "metadata", "created_at"]
            
            # 搜索参数
            search_params = {
                "metric_type": "COSINE",  # 余弦相似度
                "params": {"ef": 64}  # 更高的ef值会增加搜索精度但减慢速度
            }
            
            # 执行搜索
            results = collection.search(
                data=[query_vector],
                anns_field="vector",
                param=search_params,
                limit=top_k,
                output_fields=output_fields,
                expr=filters
            )
            
            # 处理结果
            hits = results[0]  # 第一个查询的结果
            
            import json
            search_results = []
            for hit in hits:
                # 解析元数据
                metadata = {}
                if "metadata" in output_fields and hit.entity.get("metadata"):
                    try:
                        metadata = json.loads(hit.entity.get("metadata", "{}"))
                    except json.JSONDecodeError:
                        logger.warning(f"解析元数据失败: {hit.entity.get('metadata')}")
                
                # 构建结果
                result = {
                    "id": hit.entity.get("id"),
                    "content": hit.entity.get("content"),
                    "metadata": metadata,
                    "score": hit.score,
                }
                
                # 添加其他可能的输出字段
                for field in output_fields:
                    if field not in ["id", "content", "metadata"] and field in hit.entity:
                        result[field] = hit.entity.get(field)
                
                search_results.append(result)
            
            logger.info(f"集合 {collection_name} 搜索完成，找到 {len(search_results)} 个结果")
            return search_results
        except Exception as e:
            logger.error(f"向量搜索失败: {str(e)}")
            raise VectorStoreError(f"向量搜索失败: {str(e)}")
    
    async def delete_by_ids(self, collection_name: str, ids: List[str]) -> None:
        """
        通过ID删除数据
        
        参数:
            collection_name: str - 集合名称
            ids: List[str] - 要删除的ID列表
            
        异常:
            VectorStoreError: 删除数据失败
        """
        await self._ensure_connected()
        
        try:
            # 获取集合
            collection = await self.get_collection(collection_name)
            
            # 构建删除表达式
            quoted_ids = [f'"{id}"' for id in ids]
            expr = f"id in [{', '.join(quoted_ids)}]"
            
            # 执行删除
            collection.delete(expr)
            
            logger.info(f"已从集合 {collection_name} 中删除 {len(ids)} 条数据")
        except Exception as e:
            logger.error(f"删除数据失败: {str(e)}")
            raise VectorStoreError(f"删除数据失败: {str(e)}")
    
    async def update(
        self,
        collection_name: str,
        id: str,
        vector: Optional[List[float]] = None,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        更新数据
        
        参数:
            collection_name: str - 集合名称
            id: str - 要更新的数据ID
            vector: Optional[List[float]] - 新向量（可选）
            content: Optional[str] - 新内容（可选）
            metadata: Optional[Dict[str, Any]] - 新元数据（可选）
            
        返回:
            bool - 是否更新成功
            
        异常:
            VectorStoreError: 更新数据失败
        """
        await self._ensure_connected()
        
        # 检查是否有更新内容
        if vector is None and content is None and metadata is None:
            logger.warning("没有提供更新内容，跳过更新操作")
            return False
        
        try:
            # 获取集合
            collection = await self.get_collection(collection_name)
            
            # 准备更新数据
            update_data = {}
            
            if vector is not None:
                update_data["vector"] = vector
            
            if content is not None:
                update_data["content"] = content
            
            if metadata is not None:
                import json
                metadata_str = json.dumps(metadata)
                update_data["metadata"] = metadata_str
            
            # 指定要更新的ID
            expr = f'id == "{id}"'
            
            # 执行更新
            collection.upsert([{
                "id": id, 
                **update_data
            }])
            
            logger.info(f"已成功更新集合 {collection_name} 中的数据 {id}")
            return True
        except Exception as e:
            logger.error(f"更新数据失败: {str(e)}")
            raise VectorStoreError(f"更新数据失败: {str(e)}")
    
    async def get_by_id(self, collection_name: str, id: str) -> Optional[Dict[str, Any]]:
        """
        通过ID获取数据
        
        参数:
            collection_name: str - 集合名称
            id: str - 数据ID
            
        返回:
            Optional[Dict[str, Any]] - 数据详情，未找到则返回None
            
        异常:
            VectorStoreError: 获取数据失败
        """
        await self._ensure_connected()
        
        try:
            # 获取集合
            collection = await self.get_collection(collection_name)
            
            # 查询
            expr = f'id == "{id}"'
            results = collection.query(
                expr=expr,
                output_fields=["id", "content", "metadata", "created_at"]
            )
            
            if not results:
                return None
            
            # 解析结果
            result = results[0]
            
            # 解析元数据
            import json
            metadata = {}
            if "metadata" in result and result["metadata"]:
                try:
                    metadata = json.loads(result["metadata"])
                except json.JSONDecodeError:
                    logger.warning(f"解析元数据失败: {result['metadata']}")
            
            # 构建返回数据
            data = {
                "id": result["id"],
                "content": result["content"],
                "metadata": metadata
            }
            
            if "created_at" in result:
                data["created_at"] = result["created_at"]
            
            return data
        except Exception as e:
            logger.error(f"获取数据失败: {str(e)}")
            raise VectorStoreError(f"获取数据失败: {str(e)}")
    
    async def close(self) -> None:
        """
        关闭Milvus连接
        """
        if self._connected:
            try:
                # 释放所有已加载的集合
                for collection_name, collection in self._collections.items():
                    try:
                        collection.release()
                    except:
                        pass
                
                # 断开连接
                connections.disconnect(self.connection_alias)
                self._connected = False
                self._collections = {}
                logger.info("已关闭Milvus连接")
            except Exception as e:
                logger.error(f"关闭Milvus连接失败: {str(e)}")
    
    async def __aenter__(self):
        """
        异步上下文管理器入口
        """
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        异步上下文管理器退出
        """
        await self.close()
