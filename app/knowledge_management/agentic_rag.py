"""
AgenticRAG实现

实现基于智能体驱动的检索增强生成引擎，提供更复杂的查询规划和智能检索
"""

import logging
import asyncio
import json
from typing import Dict, List, Optional, Tuple, Any, Union, Callable

from app.knowledge_management.graph_rag_engine import GraphRAGEngine
from app.knowledge_management.query_planner import QueryPlanner
from app.knowledge_management.result_synthesizer import ResultSynthesizer
from app.knowledge_management.self_critique_agent import SelfCritiqueAgent
from app.data_access.llm_adapter.base_llm_provider import LLMProvider
from app.models.domain.knowledge import KnowledgeItem
from app.core.config import get_settings

logger = logging.getLogger(__name__)

# 获取应用配置
settings = get_settings()

class AgenticRAG:
    """
    智能体驱动的检索增强生成系统
    
    通过智能代理、查询规划和结果合成，提供高级知识检索和问答能力
    """
    
    def __init__(
        self,
        graph_rag_engine: GraphRAGEngine,
        llm_service: LLMProvider,
        query_planner: Optional[QueryPlanner] = None,
        result_synthesizer: Optional[ResultSynthesizer] = None,
        self_critique_agent: Optional[SelfCritiqueAgent] = None,
        max_iterations: int = 3,
        confidence_threshold: float = 0.7,
        debug_mode: bool = False
    ):
        """
        初始化AgenticRAG系统
        
        参数:
            graph_rag_engine: GraphRAGEngine - 基础GraphRAG引擎
            llm_service: LLMProvider - LLM服务实例
            query_planner: Optional[QueryPlanner] - 查询规划器
            result_synthesizer: Optional[ResultSynthesizer] - 结果合成器
            self_critique_agent: Optional[SelfCritiqueAgent] - 自我批评代理
            max_iterations: int - 最大迭代次数
            confidence_threshold: float - 置信度阈值
            debug_mode: bool - 调试模式
        """
        self.graph_rag_engine = graph_rag_engine
        self.llm_service = llm_service
        
        # 初始化组件（如果未提供则创建默认实例）
        self.query_planner = query_planner or QueryPlanner(llm_service=llm_service)
        self.result_synthesizer = result_synthesizer or ResultSynthesizer(llm_service=llm_service)
        self.self_critique_agent = self_critique_agent or SelfCritiqueAgent(llm_service=llm_service)
        
        self.max_iterations = max_iterations
        self.confidence_threshold = confidence_threshold
        self.debug_mode = debug_mode
    
    async def process_query(
        self, 
        query: str,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        处理用户查询，返回增强的响应
        
        参数:
            query: str - 用户查询文本
            context: Optional[Dict[str, Any]] - 上下文信息
            session_id: Optional[str] - 会话ID
            metadata: Optional[Dict[str, Any]] - 元数据
            
        返回:
            Dict[str, Any] - 处理结果
        """
        context = context or {}
        metadata = metadata or {}
        
        # 初始化查询跟踪
        query_trace = {
            "query": query,
            "session_id": session_id,
            "iterations": [],
            "final_response": None,
            "confidence_score": 0.0,
            "query_plans": [],
            "retrieval_results": [],
            "synthesis_steps": [],
            "critique_steps": []
        }
        
        # 1. 查询规划阶段
        query_plan = await self.query_planner.plan_query(
            query=query,
            context=context
        )
        query_trace["query_plans"].append(query_plan)
        
        if self.debug_mode:
            logger.debug(f"查询规划: {json.dumps(query_plan, ensure_ascii=False)}")
        
        # 2. 多轮检索与合成
        iteration = 0
        current_answer = None
        current_confidence = 0.0
        
        while iteration < self.max_iterations:
            iteration_trace = {
                "iteration": iteration + 1,
                "sub_queries": query_plan["sub_queries"],
                "retrieval_results": [],
                "synthesis_result": None,
                "critique_result": None,
                "confidence": 0.0
            }
            
            # 执行子查询
            sub_query_results = []
            for sub_query in query_plan["sub_queries"]:
                # 执行查询
                sub_query_result = await self._execute_sub_query(
                    sub_query=sub_query["query"],
                    strategy=sub_query.get("strategy", "default"),
                    params=sub_query.get("params", {})
                )
                
                sub_query_results.append({
                    "sub_query": sub_query,
                    "result": sub_query_result
                })
                
                iteration_trace["retrieval_results"].append({
                    "sub_query": sub_query,
                    "result_summary": {
                        "answer": sub_query_result["answer"],
                        "quality_score": sub_query_result["quality_score"],
                        "context_count": len(sub_query_result["context"])
                    }
                })
            
            # 添加到跟踪
            query_trace["retrieval_results"].append(sub_query_results)
            
            # 3. 合成结果
            synthesis_result = await self.result_synthesizer.synthesize(
                original_query=query,
                sub_query_results=sub_query_results,
                context=context
            )
            
            iteration_trace["synthesis_result"] = {
                "answer": synthesis_result["answer"],
                "reasoning": synthesis_result.get("reasoning", "")
            }
            
            query_trace["synthesis_steps"].append(synthesis_result)
            
            # 4. 自我批评和改进
            critique_result = await self.self_critique_agent.critique(
                original_query=query,
                current_answer=synthesis_result["answer"],
                sub_query_results=sub_query_results,
                context=context
            )
            
            iteration_trace["critique_result"] = {
                "issues": critique_result["issues"],
                "suggestions": critique_result["suggestions"],
                "confidence": critique_result["confidence"]
            }
            
            query_trace["critique_steps"].append(critique_result)
            
            # 更新置信度和当前回答
            current_confidence = critique_result["confidence"]
            current_answer = synthesis_result["answer"]
            
            iteration_trace["confidence"] = current_confidence
            query_trace["iterations"].append(iteration_trace)
            
            # 如果置信度达到阈值，则中断迭代
            if current_confidence >= self.confidence_threshold:
                if self.debug_mode:
                    logger.debug(f"迭代 {iteration+1} 达到置信度阈值 {current_confidence}，提前结束迭代")
                break
            
            # 如果有改进建议，更新查询计划
            if critique_result["suggestions"] and len(critique_result["suggestions"]) > 0:
                # 基于批评结果改进查询计划
                query_plan = await self.query_planner.refine_plan(
                    original_plan=query_plan,
                    critique=critique_result,
                    context=context
                )
                
                query_trace["query_plans"].append(query_plan)
                
                if self.debug_mode:
                    logger.debug(f"更新的查询规划: {json.dumps(query_plan, ensure_ascii=False)}")
            
            iteration += 1
        
        # 构建最终结果
        final_result = {
            "answer": current_answer,
            "confidence": current_confidence,
            "query_trace": query_trace if self.debug_mode else None,
            "metadata": {
                "iterations": iteration + 1,
                "session_id": session_id,
                **metadata
            }
        }
        
        # 更新查询跟踪
        query_trace["final_response"] = current_answer
        query_trace["confidence_score"] = current_confidence
        
        return final_result
    
    async def _execute_sub_query(
        self, 
        sub_query: str, 
        strategy: str = "default", 
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        执行子查询
        
        参数:
            sub_query: str - 子查询文本
            strategy: str - 检索策略
            params: Dict[str, Any] - 策略参数
            
        返回:
            Dict[str, Any] - 查询结果
        """
        params = params or {}
        
        try:
            # 使用GraphRAG引擎执行查询
            result = await self.graph_rag_engine.query(
                query_text=sub_query,
                strategy=strategy,
                params=params
            )
            
            return result
        except Exception as e:
            logger.error(f"执行子查询时出错: {str(e)}")
            # 返回错误结果
            return {
                "answer": f"在处理子查询时发生错误: {str(e)}",
                "context": [],
                "quality_score": 0.0,
                "strategy": strategy,
                "error": str(e)
            }
    
    async def search_knowledge(
        self, 
        query: str, 
        limit: int = 10, 
        filters: Optional[Dict[str, Any]] = None,
        use_planning: bool = True
    ) -> List[KnowledgeItem]:
        """
        增强版知识搜索方法（兼容KnowledgeService接口）
        
        参数:
            query: str - 搜索查询文本
            limit: int - 结果限制数量
            filters: Optional[Dict[str, Any]] - 过滤条件
            use_planning: bool - 是否使用查询规划
            
        返回:
            List[KnowledgeItem] - 知识项列表
        """
        if not use_planning:
            # 不使用规划，直接调用基础GraphRAG引擎
            return await self.graph_rag_engine.search_knowledge(
                query=query,
                limit=limit,
                filters=filters
            )
        
        # 使用智能规划进行知识搜索
        # 1. 分析查询并创建规划
        query_plan = await self.query_planner.plan_knowledge_search(
            query=query,
            filters=filters,
            limit=limit
        )
        
        # 2. 执行每个子查询
        all_results = []
        for sub_query in query_plan["sub_queries"]:
            # 执行子查询
            sub_results = await self.graph_rag_engine.search_knowledge(
                query=sub_query["query"],
                limit=sub_query.get("limit", max(limit // len(query_plan["sub_queries"]), 3)),
                filters=sub_query.get("filters", filters)
            )
            
            # 添加分数调整
            adjustment = sub_query.get("relevance_weight", 1.0)
            for item in sub_results:
                # 调整相关度分数
                if "metadata" in item and "score" in item.metadata:
                    item.metadata["original_score"] = item.metadata["score"]
                    item.metadata["score"] = item.metadata["score"] * adjustment
                
                # 添加子查询信息
                if "metadata" not in item:
                    item.metadata = {}
                item.metadata["sub_query"] = sub_query["query"]
            
            all_results.extend(sub_results)
        
        # 3. 对结果进行去重和排序
        # 创建ID到项目的映射
        unique_items = {}
        for item in all_results:
            if item.id not in unique_items or \
                (item.id in unique_items and 
                 item.metadata.get("score", 0) > unique_items[item.id].metadata.get("score", 0)):
                unique_items[item.id] = item
        
        # 转换为列表并排序
        sorted_results = list(unique_items.values())
        sorted_results.sort(
            key=lambda x: x.metadata.get("score", 0) if "metadata" in x else 0,
            reverse=True
        )
        
        # 截断到所需的限制
        return sorted_results[:limit]
    
    async def feedback(
        self, 
        query_id: str, 
        feedback: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        提供查询反馈，用于改进系统性能
        
        参数:
            query_id: str - 查询ID
            feedback: Dict[str, Any] - 反馈信息
            
        返回:
            Dict[str, Any] - 处理结果
        """
        # 处理用户反馈的基本实现
        # 在实际系统中，可以扩展为更全面的反馈处理机制
        
        # 记录反馈
        logger.info(f"收到查询 {query_id} 的反馈: {json.dumps(feedback, ensure_ascii=False)}")
        
        # 学习和适应（简单版本）
        if "is_relevant" in feedback and not feedback["is_relevant"]:
            # 如果反馈表明结果不相关，考虑更新内部模型
            if "explanation" in feedback:
                # 可以收集错误案例进行后续改进
                logger.warning(f"查询 {query_id} 的结果被标记为不相关: {feedback.get('explanation', '')}")
        
        # 持久化反馈以供未来训练
        # 实际实现会将反馈存储到数据库或其他持久化存储中
        
        return {
            "status": "success",
            "message": "反馈已接收并处理",
            "query_id": query_id
        }
