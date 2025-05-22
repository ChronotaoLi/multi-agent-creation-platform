"""
查询规划器实现

负责分析用户查询，制定检索策略和子查询计划
"""

import logging
import json
from typing import Dict, List, Optional, Any, Tuple, Union

from app.data_access.llm_adapter.base_llm_provider import LLMProvider
from app.core.config import get_settings

logger = logging.getLogger(__name__)

# 获取应用配置
settings = get_settings()

class QueryPlanner:
    """
    查询规划器
    
    将用户的查询分解为一系列子查询和检索策略，提高知识检索的效率和相关性
    """
    
    def __init__(
        self,
        llm_service: LLMProvider,
        max_sub_queries: int = 5,
        enable_caching: bool = True,
        query_templates: Dict[str, str] = None
    ):
        """
        初始化查询规划器
        
        参数:
            llm_service: LLMProvider - LLM服务实例
            max_sub_queries: int - 最大子查询数量
            enable_caching: bool - 是否启用缓存
            query_templates: Dict[str, str] - 查询模板字典
        """
        self.llm_service = llm_service
        self.max_sub_queries = max_sub_queries
        self.enable_caching = enable_caching
        
        # 默认查询规划提示模板
        self.default_planning_template = """
        你是一个专业的查询规划器。你的任务是将用户的查询分解为多个子查询，以便更有效地从知识库中检索信息。

        用户的原始查询是: "{query}"

        请将此查询分解为最多{max_sub_queries}个子查询。对于每个子查询，请指定:
        1. 子查询文本
        2. 推荐的检索策略 (可选择: "vector", "graph", "hybrid", "default")
        3. 可选的参数

        按照以下JSON格式输出你的规划:
        {{
            "sub_queries": [
                {{
                    "query": "子查询1文本",
                    "strategy": "检索策略",
                    "params": {{
                        "参数名": 参数值
                    }},
                    "explanation": "为什么需要这个子查询的简短解释"
                }},
                ...
            ],
            "reasoning": "规划过程的推理说明"
        }}

        子查询应该覆盖原始查询的不同方面，并且应该尽量简短、明确和独立。
        """
        
        # 知识搜索规划提示模板
        self.knowledge_search_planning_template = """
        你是一个专业的知识搜索规划器。你的任务是将用户的搜索查询分解为多个子查询，以便更有效地从知识库中检索信息。

        用户的原始搜索查询是: "{query}"

        请将此查询分解为最多{max_sub_queries}个子查询。对于每个子查询，请指定:
        1. 子查询文本
        2. 与原始查询的相关性权重 (0.0-1.0的浮点数)
        3. 结果数量限制 (整数)

        按照以下JSON格式输出你的规划:
        {{
            "sub_queries": [
                {{
                    "query": "子查询1文本",
                    "relevance_weight": 0.8,
                    "limit": 5,
                    "filters": {{}}
                }},
                ...
            ],
            "reasoning": "规划过程的推理说明"
        }}

        子查询应该覆盖原始查询的不同方面，并且应该尽量简短、明确和独立。
        """
        
        # 查询细化提示模板
        self.refine_plan_template = """
        你是一个专业的查询规划器。你需要根据批评反馈来改进现有的查询规划。

        原始查询: "{query}"

        当前的查询规划:
        {current_plan}

        批评和建议:
        {critique}

        请修改查询规划以解决这些问题。可以修改现有子查询、添加新的子查询或删除不必要的子查询。

        按照以下JSON格式输出你的更新规划:
        {{
            "sub_queries": [
                {{
                    "query": "子查询1文本",
                    "strategy": "检索策略",
                    "params": {{
                        "参数名": 参数值
                    }},
                    "explanation": "为什么需要这个子查询的简短解释"
                }},
                ...
            ],
            "reasoning": "规划更新的推理说明"
        }}

        确保你的更新解决了批评中指出的所有问题。
        """
        
        # 设置查询模板
        self.query_templates = {
            "planning": self.default_planning_template,
            "knowledge_search": self.knowledge_search_planning_template,
            "refine": self.refine_plan_template
        }
        
        # 添加自定义模板
        if query_templates:
            self.query_templates.update(query_templates)
    
    async def plan_query(
        self, 
        query: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        规划查询的执行策略，将查询分解为子查询
        
        参数:
            query: str - 原始查询文本
            context: Optional[Dict[str, Any]] - 上下文信息
            
        返回:
            Dict[str, Any] - 查询规划结果
        """
        context = context or {}
        
        # 构建规划提示
        planning_prompt = self.query_templates["planning"].format(
            query=query,
            max_sub_queries=self.max_sub_queries
        )
        
        # 调用LLM生成规划
        planning_response = await self.llm_service.generate_text(planning_prompt)
        
        # 解析JSON响应
        try:
            # 尝试直接解析
            plan = json.loads(planning_response)
        except json.JSONDecodeError:
            # 如果失败，尝试从响应中提取JSON部分
            try:
                # 找到第一个{和最后一个}之间的内容
                json_start = planning_response.find('{')
                json_end = planning_response.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = planning_response[json_start:json_end]
                    plan = json.loads(json_str)
                else:
                    # 无法提取JSON，返回默认规划
                    logger.warning(f"无法从规划响应中提取JSON: {planning_response}")
                    plan = self._create_default_plan(query)
            except Exception as e:
                logger.error(f"解析规划响应失败: {str(e)}")
                plan = self._create_default_plan(query)
        
        # 验证和清理规划
        plan = self._validate_and_clean_plan(plan, query)
        
        return plan
    
    async def plan_knowledge_search(
        self, 
        query: str, 
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        为知识搜索创建规划
        
        参数:
            query: str - 原始查询文本
            filters: Optional[Dict[str, Any]] - 过滤条件
            limit: int - 结果限制
            
        返回:
            Dict[str, Any] - 知识搜索规划
        """
        # 构建规划提示
        planning_prompt = self.query_templates["knowledge_search"].format(
            query=query,
            max_sub_queries=min(3, self.max_sub_queries)  # 知识搜索子查询数量限制较少
        )
        
        # 调用LLM生成规划
        planning_response = await self.llm_service.generate_text(planning_prompt)
        
        # 解析JSON响应
        try:
            # 尝试直接解析
            plan = json.loads(planning_response)
        except json.JSONDecodeError:
            # 如果失败，尝试从响应中提取JSON部分
            try:
                # 找到第一个{和最后一个}之间的内容
                json_start = planning_response.find('{')
                json_end = planning_response.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = planning_response[json_start:json_end]
                    plan = json.loads(json_str)
                else:
                    # 无法提取JSON，返回默认规划
                    logger.warning(f"无法从知识搜索规划响应中提取JSON: {planning_response}")
                    plan = self._create_default_knowledge_search_plan(query, limit)
            except Exception as e:
                logger.error(f"解析知识搜索规划响应失败: {str(e)}")
                plan = self._create_default_knowledge_search_plan(query, limit)
        
        # 验证和清理规划
        plan = self._validate_and_clean_knowledge_search_plan(plan, query, filters, limit)
        
        return plan
    
    async def refine_plan(
        self, 
        original_plan: Dict[str, Any], 
        critique: Dict[str, Any], 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        根据批评意见细化查询规划
        
        参数:
            original_plan: Dict[str, Any] - 原始查询规划
            critique: Dict[str, Any] - 批评意见
            context: Optional[Dict[str, Any]] - 上下文信息
            
        返回:
            Dict[str, Any] - 更新后的查询规划
        """
        context = context or {}
        
        # 提取原始查询（从原始计划或上下文中）
        original_query = context.get("original_query", "")
        
        # 将计划和批评转换为字符串形式
        plan_str = json.dumps(original_plan, ensure_ascii=False, indent=2)
        critique_str = json.dumps(critique, ensure_ascii=False, indent=2)
        
        # 构建细化提示
        refine_prompt = self.query_templates["refine"].format(
            query=original_query,
            current_plan=plan_str,
            critique=critique_str
        )
        
        # 调用LLM生成更新后的规划
        refine_response = await self.llm_service.generate_text(refine_prompt)
        
        # 解析JSON响应
        try:
            # 尝试直接解析
            updated_plan = json.loads(refine_response)
        except json.JSONDecodeError:
            # 如果失败，尝试从响应中提取JSON部分
            try:
                # 找到第一个{和最后一个}之间的内容
                json_start = refine_response.find('{')
                json_end = refine_response.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = refine_response[json_start:json_end]
                    updated_plan = json.loads(json_str)
                else:
                    # 无法提取JSON，返回原始规划
                    logger.warning(f"无法从细化响应中提取JSON: {refine_response}")
                    return original_plan
            except Exception as e:
                logger.error(f"解析细化响应失败: {str(e)}")
                return original_plan
        
        # 验证和清理更新后的规划
        updated_plan = self._validate_and_clean_plan(updated_plan, original_query)
        
        return updated_plan
    
    def _create_default_plan(self, query: str) -> Dict[str, Any]:
        """
        创建默认的查询规划
        
        参数:
            query: str - 原始查询文本
            
        返回:
            Dict[str, Any] - 默认查询规划
        """
        return {
            "sub_queries": [
                {
                    "query": query,
                    "strategy": "hybrid",
                    "params": {
                        "top_k": 10
                    },
                    "explanation": "使用原始查询作为子查询"
                }
            ],
            "reasoning": "未能生成自定义规划，使用默认规划。"
        }
    
    def _create_default_knowledge_search_plan(self, query: str, limit: int) -> Dict[str, Any]:
        """
        创建默认的知识搜索规划
        
        参数:
            query: str - 原始查询文本
            limit: int - 结果限制
            
        返回:
            Dict[str, Any] - 默认知识搜索规划
        """
        return {
            "sub_queries": [
                {
                    "query": query,
                    "relevance_weight": 1.0,
                    "limit": limit,
                    "filters": {}
                }
            ],
            "reasoning": "未能生成自定义知识搜索规划，使用默认规划。"
        }
    
    def _validate_and_clean_plan(self, plan: Dict[str, Any], query: str) -> Dict[str, Any]:
        """
        验证和清理查询规划
        
        参数:
            plan: Dict[str, Any] - 原始查询规划
            query: str - 原始查询文本
            
        返回:
            Dict[str, Any] - 清理后的查询规划
        """
        # 确保计划包含所需的字段
        if "sub_queries" not in plan or not isinstance(plan["sub_queries"], list):
            logger.warning("规划中缺少sub_queries字段或格式不正确")
            return self._create_default_plan(query)
        
        # 如果没有子查询，添加一个默认子查询
        if len(plan["sub_queries"]) == 0:
            plan["sub_queries"].append({
                "query": query,
                "strategy": "hybrid",
                "params": {"top_k": 10},
                "explanation": "使用原始查询作为子查询"
            })
        
        # 限制子查询数量
        if len(plan["sub_queries"]) > self.max_sub_queries:
            plan["sub_queries"] = plan["sub_queries"][:self.max_sub_queries]
        
        # 检查并修复每个子查询
        for i, sub_query in enumerate(plan["sub_queries"]):
            # 确保每个子查询有查询文本
            if "query" not in sub_query or not isinstance(sub_query["query"], str):
                sub_query["query"] = query
            
            # 确保策略有效
            if "strategy" not in sub_query or sub_query["strategy"] not in ["vector", "graph", "hybrid", "default"]:
                sub_query["strategy"] = "hybrid"
            
            # 确保params是字典
            if "params" not in sub_query or not isinstance(sub_query["params"], dict):
                sub_query["params"] = {"top_k": 10}
            
            # 确保有解释
            if "explanation" not in sub_query or not isinstance(sub_query["explanation"], str):
                sub_query["explanation"] = f"子查询 {i+1}"
        
        # 确保有推理说明
        if "reasoning" not in plan or not isinstance(plan["reasoning"], str):
            plan["reasoning"] = "规划已验证和清理。"
        
        return plan
    
    def _validate_and_clean_knowledge_search_plan(
        self, 
        plan: Dict[str, Any], 
        query: str, 
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        验证和清理知识搜索规划
        
        参数:
            plan: Dict[str, Any] - 原始知识搜索规划
            query: str - 原始查询文本
            filters: Optional[Dict[str, Any]] - 过滤条件
            limit: int - 结果限制
            
        返回:
            Dict[str, Any] - 清理后的知识搜索规划
        """
        # 确保计划包含所需的字段
        if "sub_queries" not in plan or not isinstance(plan["sub_queries"], list):
            logger.warning("知识搜索规划中缺少sub_queries字段或格式不正确")
            return self._create_default_knowledge_search_plan(query, limit)
        
        # 如果没有子查询，添加一个默认子查询
        if len(plan["sub_queries"]) == 0:
            plan["sub_queries"].append({
                "query": query,
                "relevance_weight": 1.0,
                "limit": limit,
                "filters": filters or {}
            })
        
        # 限制子查询数量
        if len(plan["sub_queries"]) > self.max_sub_queries:
            plan["sub_queries"] = plan["sub_queries"][:self.max_sub_queries]
        
        # 检查并修复每个子查询
        for i, sub_query in enumerate(plan["sub_queries"]):
            # 确保每个子查询有查询文本
            if "query" not in sub_query or not isinstance(sub_query["query"], str):
                sub_query["query"] = query
            
            # 确保相关性权重有效
            if "relevance_weight" not in sub_query or not isinstance(sub_query["relevance_weight"], (int, float)):
                sub_query["relevance_weight"] = 1.0
            else:
                # 确保相关性在0-1范围内
                sub_query["relevance_weight"] = max(0.0, min(1.0, float(sub_query["relevance_weight"])))
            
            # 确保limit有效
            if "limit" not in sub_query or not isinstance(sub_query["limit"], int) or sub_query["limit"] <= 0:
                sub_query["limit"] = limit
            
            # 确保filters是字典
            if "filters" not in sub_query or not isinstance(sub_query["filters"], dict):
                sub_query["filters"] = filters or {}
        
        # 确保有推理说明
        if "reasoning" not in plan or not isinstance(plan["reasoning"], str):
            plan["reasoning"] = "知识搜索规划已验证和清理。"
        
        return plan
