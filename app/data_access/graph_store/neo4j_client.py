"""
Neo4j客户端封装模块

该模块封装了对Neo4j图数据库的操作，提供了节点创建、关系创建、查询执行等功能。
支持Neo4j 5.x版本。
"""

import logging
from typing import List, Dict, Any, Optional, Union, Tuple

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession, AsyncTransaction
from neo4j.exceptions import Neo4jError

logger = logging.getLogger(__name__)

class Neo4jClient:
    """封装Neo4j图数据库操作的客户端类"""
    
    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        database: str = "neo4j"
    ):
        """
        初始化Neo4j客户端
        
        参数:
            uri: str - Neo4j服务URI
            user: str - 用户名
            password: str - 密码
            database: str - 数据库名称，默认为"neo4j"
        """
        self.uri = uri
        self.user = user
        self.password = password
        self.database = database
        self._driver: Optional[AsyncDriver] = None
    
    async def connect(self) -> None:
        """连接到Neo4j服务"""
        try:
            self._driver = AsyncGraphDatabase.driver(
                self.uri, 
                auth=(self.user, self.password)
            )
            
            # 测试连接
            async with self._driver.session(database=self.database) as session:
                result = await session.run("RETURN 1 as test")
                record = await result.single()
                if record and record["test"] == 1:
                    logger.info(f"Successfully connected to Neo4j at {self.uri}")
                else:
                    raise Exception("Neo4j connection test failed")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {str(e)}")
            raise
    
    async def create_node(
        self, 
        labels: List[str], 
        properties: Dict[str, Any]
    ) -> str:
        """
        创建节点
        
        参数:
            labels: List[str] - 节点标签列表
            properties: Dict[str, Any] - 节点属性
            
        返回:
            str - 创建的节点ID
        """
        if not self._driver:
            await self.connect()
        
        # 构建标签字符串
        labels_str = ":".join(labels)
        
        # 构建属性参数字典
        params = {"props": properties}
        
        # Cypher查询语句
        query = f"""
        CREATE (n:{labels_str} $props)
        RETURN id(n) as node_id
        """
        
        try:
            async with self._driver.session(database=self.database) as session:
                result = await session.run(query, params)
                record = await result.single()
                node_id = str(record["node_id"])
                logger.debug(f"Created node with ID: {node_id} and labels: {labels}")
                return node_id
        except Exception as e:
            logger.error(f"Failed to create node: {str(e)}")
            raise
    
    async def create_relationship(
        self, 
        start_node: str, 
        end_node: str, 
        rel_type: str, 
        properties: Dict[str, Any] = None
    ) -> None:
        """
        创建关系
        
        参数:
            start_node: str - 起始节点ID
            end_node: str - 结束节点ID
            rel_type: str - 关系类型
            properties: Dict[str, Any] - 关系属性
        """
        if not self._driver:
            await self.connect()
        
        # 默认空属性
        properties = properties or {}
        
        # 构建查询参数
        params = {
            "start_id": int(start_node),
            "end_id": int(end_node),
            "props": properties
        }
        
        # Cypher查询语句
        query = f"""
        MATCH (a), (b)
        WHERE id(a) = $start_id AND id(b) = $end_id
        CREATE (a)-[r:{rel_type} $props]->(b)
        RETURN id(r) as rel_id
        """
        
        try:
            async with self._driver.session(database=self.database) as session:
                result = await session.run(query, params)
                record = await result.single()
                rel_id = record["rel_id"]
                logger.debug(
                    f"Created relationship with ID: {rel_id}, type: {rel_type} "
                    f"from node {start_node} to node {end_node}"
                )
        except Exception as e:
            logger.error(f"Failed to create relationship: {str(e)}")
            raise
    
    async def query(
        self, 
        cypher: str, 
        params: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        执行Cypher查询
        
        参数:
            cypher: str - Cypher查询语句
            params: Dict[str, Any] - 查询参数
            
        返回:
            List[Dict[str, Any]] - 查询结果列表
        """
        if not self._driver:
            await self.connect()
        
        params = params or {}
        
        try:
            async with self._driver.session(database=self.database) as session:
                result = await session.run(cypher, params)
                records = await result.values()
                
                # 处理结果
                data = []
                for record in records:
                    # 转换Neo4j类型到Python原生类型
                    row = {}
                    for i, field in enumerate(result.keys()):
                        row[field] = self._convert_neo4j_types(record[i])
                    data.append(row)
                
                return data
        except Exception as e:
            logger.error(f"Failed to execute query: {str(e)}")
            raise
    
    async def get_node(self, node_id: str) -> Dict[str, Any]:
        """
        获取节点
        
        参数:
            node_id: str - 节点ID
            
        返回:
            Dict[str, Any] - 节点数据，包含标签和属性
        """
        if not self._driver:
            await self.connect()
        
        query = """
        MATCH (n)
        WHERE id(n) = $node_id
        RETURN labels(n) as labels, properties(n) as properties
        """
        
        params = {"node_id": int(node_id)}
        
        try:
            async with self._driver.session(database=self.database) as session:
                result = await session.run(query, params)
                record = await result.single()
                
                if not record:
                    logger.warning(f"Node with ID {node_id} not found")
                    return {}
                
                # 构建节点数据
                node_data = {
                    "id": node_id,
                    "labels": record["labels"],
                    "properties": self._convert_neo4j_types(record["properties"])
                }
                
                return node_data
        except Exception as e:
            logger.error(f"Failed to get node {node_id}: {str(e)}")
            raise
            
    async def update_node(
        self, 
        node_id: str, 
        properties: Dict[str, Any]
    ) -> bool:
        """
        更新节点属性
        
        参数:
            node_id: str - 节点ID
            properties: Dict[str, Any] - 新的节点属性
            
        返回:
            bool - 更新是否成功
        """
        if not self._driver:
            await self.connect()
        
        query = """
        MATCH (n)
        WHERE id(n) = $node_id
        SET n = $props
        RETURN count(n) as updated
        """
        
        params = {
            "node_id": int(node_id),
            "props": properties
        }
        
        try:
            async with self._driver.session(database=self.database) as session:
                result = await session.run(query, params)
                record = await result.single()
                
                success = record and record["updated"] > 0
                if success:
                    logger.debug(f"Updated properties of node {node_id}")
                else:
                    logger.warning(f"Node with ID {node_id} not found for update")
                
                return success
        except Exception as e:
            logger.error(f"Failed to update node {node_id}: {str(e)}")
            raise
    
    async def get_nodes_by_label(
        self, 
        label: str, 
        properties: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        通过标签获取节点
        
        参数:
            label: str - 节点标签
            properties: Dict[str, Any] - 过滤属性
            
        返回:
            List[Dict[str, Any]] - 节点列表
        """
        if not self._driver:
            await self.connect()
        
        # 构建属性过滤条件
        prop_conditions = []
        params = {}
        
        if properties:
            for key, value in properties.items():
                param_name = f"prop_{key}"
                prop_conditions.append(f"n.{key} = ${param_name}")
                params[param_name] = value
        
        # 构建查询语句
        query = f"MATCH (n:{label})"
        if prop_conditions:
            query += " WHERE " + " AND ".join(prop_conditions)
        query += " RETURN id(n) as id, properties(n) as properties, labels(n) as labels"
        
        try:
            async with self._driver.session(database=self.database) as session:
                result = await session.run(query, params)
                records = await result.values()
                
                nodes = []
                for record in records:
                    node = {
                        "id": str(record[0]),
                        "properties": self._convert_neo4j_types(record[1]),
                        "labels": record[2]
                    }
                    nodes.append(node)
                
                return nodes
        except Exception as e:
            logger.error(f"Failed to get nodes by label {label}: {str(e)}")
            raise
    
    async def delete_node(self, node_id: str) -> None:
        """
        删除节点
        
        参数:
            node_id: str - 节点ID
        """
        if not self._driver:
            await self.connect()
        
        # 删除节点及其所有关系
        query = """
        MATCH (n)
        WHERE id(n) = $node_id
        DETACH DELETE n
        """
        
        params = {"node_id": int(node_id)}
        
        try:
            async with self._driver.session(database=self.database) as session:
                await session.run(query, params)
                logger.debug(f"Deleted node with ID: {node_id}")
        except Exception as e:
            logger.error(f"Failed to delete node {node_id}: {str(e)}")
            raise
    
    async def get_graph(
        self, 
        query: str, 
        params: Dict[str, Any] = None
    ) -> List[Tuple]:
        """
        获取图结构
        
        参数:
            query: str - 查询语句，必须返回节点和关系
            params: Dict[str, Any] - 查询参数
            
        返回:
            List[Tuple] - 节点和关系的元组列表
        """
        if not self._driver:
            await self.connect()
        
        params = params or {}
        
        try:
            async with self._driver.session(database=self.database) as session:
                result = await session.run(query, params)
                records = await result.values()
                
                graph = []
                for record in records:
                    # 转换所有记录为Python原生类型
                    row = []
                    for item in record:
                        row.append(self._convert_neo4j_types(item))
                    graph.append(tuple(row))
                
                return graph
        except Exception as e:
            logger.error(f"Failed to get graph: {str(e)}")
            raise
    
    async def close(self) -> None:
        """关闭Neo4j连接"""
        if self._driver:
            await self._driver.close()
            self._driver = None
            logger.info("Neo4j connection closed")
    
    def _convert_neo4j_types(self, value: Any) -> Any:
        """
        转换Neo4j类型到Python原生类型
        
        参数:
            value: Any - 需要转换的值
            
        返回:
            Any - 转换后的值
        """
        if isinstance(value, list):
            return [self._convert_neo4j_types(item) for item in value]
        elif isinstance(value, dict):
            return {k: self._convert_neo4j_types(v) for k, v in value.items()}
        else:
            return value
