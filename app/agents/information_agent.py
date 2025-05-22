"""
信息智能体模块 - 负责外部知识获取和整合
"""

from typing import Any, Dict, List, Callable, Optional
from .base_agent import BaseAgent
from ..services.interfaces.knowledge_service import KnowledgeService
from ..data_access.llm_adapter.base_llm_provider import LLMService


class FactCheckingService:
    """
    事实核查服务，验证内容的事实准确性
    """
    
    def __init__(self, 
                 verification_databases: List[Dict[str, Any]], 
                 confidence_thresholds: Dict[str, float]):
        """
        初始化事实核查服务
        
        Args:
            verification_databases: 验证数据库列表
            confidence_thresholds: 信心阈值配置
        """
        self.verification_databases = verification_databases
        self.confidence_thresholds = confidence_thresholds
    
    def check_fact(self, statement: str) -> Dict[str, Any]:
        """
        检查单个事实的准确性
        
        Args:
            statement: 要检查的事实陈述
            
        Returns:
            包含验证结果的字典
        """
        # 基本实现，真实场景需要连接实际的验证数据源
        result = {
            "statement": statement,
            "is_verified": False,
            "confidence": 0.0,
            "source": None,
            "explanation": None
        }
        
        # 模拟简单的验证逻辑
        for db in self.verification_databases:
            # 在真实实现中，这里会查询实际的数据库
            confidence = 0.8  # 模拟置信度
            if confidence > self.confidence_thresholds.get("default", 0.7):
                result["is_verified"] = True
                result["confidence"] = confidence
                result["source"] = db.get("name", "Unknown")
                result["explanation"] = f"验证通过来源: {db.get('name', 'Unknown')}"
                break
                
        return result
    
    def batch_check_facts(self, statements: List[str]) -> List[Dict[str, Any]]:
        """
        批量检查多个事实的准确性
        
        Args:
            statements: 要检查的事实陈述列表
            
        Returns:
            验证结果列表
        """
        return [self.check_fact(statement) for statement in statements]
    
    def generate_correction(self, statement: str, verification_result: Dict[str, Any]) -> str:
        """
        根据验证结果生成修正建议
        
        Args:
            statement: 原始陈述
            verification_result: 验证结果
            
        Returns:
            修正建议
        """
        if verification_result["is_verified"]:
            return f"该陈述是准确的: '{statement}'"
        
        # 在实际实现中，这里可能会查询更正数据库或使用LLM生成更正
        return f"该陈述可能不准确: '{statement}'. 建议进一步核实或修改表述。"
    
    def calculate_factual_accuracy(self, content: Dict[str, Any]) -> float:
        """
        计算内容的整体事实准确度
        
        Args:
            content: 内容数据
            
        Returns:
            准确度得分 (0.0-1.0)
        """
        # 提取内容中的事实陈述
        # 在实际实现中，这里会使用更复杂的逻辑来提取陈述
        statements = [content.get("description", "")]
        if "details" in content:
            for detail in content["details"]:
                statements.append(detail)
        
        # 验证所有陈述
        results = self.batch_check_facts(statements)
        
        # 计算准确度得分
        if not results:
            return 1.0
            
        verified_count = sum(1 for r in results if r["is_verified"])
        return verified_count / len(results)


class InformationAgent(BaseAgent):
    """
    信息智能体：获取、验证和整合外部信息，丰富内容的事实基础
    """
    
    def __init__(self, 
                 id: str, 
                 name: str, 
                 llm_service: LLMService,
                 knowledge_service: KnowledgeService = None,
                 config: Dict[str, Any] = None):
        """
        初始化信息智能体
        
        Args:
            id: 智能体唯一标识
            name: 智能体名称
            llm_service: LLM服务实例
            knowledge_service: 知识服务实例
            config: 配置参数
        """
        super().__init__(id, name, llm_service)
        
        # 初始化配置
        config = config or {}
        self.knowledge_sources = config.get("knowledge_sources", {})
        self.verification_criteria = config.get("verification_criteria", {})
        
        # 初始化查询转换器和源评估器
        self.query_transformers = {}
        self.source_evaluators = {}
        
        # 设置默认转换器
        self._setup_default_transformers()
        
        # 设置默认评估器
        self._setup_default_evaluators()
        
        # 设置知识服务
        self.knowledge_service = knowledge_service
        
        # 设置事实核查服务
        verification_databases = config.get("verification_databases", [])
        confidence_thresholds = config.get("confidence_thresholds", {"default": 0.7})
        self.fact_checking_service = FactCheckingService(
            verification_databases, 
            confidence_thresholds
        )
        
    def _setup_default_transformers(self) -> None:
        """设置默认的查询转换器"""
        
        def general_transformer(query: str) -> str:
            """一般性查询转换器"""
            return query
            
        def web_transformer(query: str) -> str:
            """网页查询优化转换器"""
            return f"site:reliable-source.com {query}"
        
        self.query_transformers = {
            "general": general_transformer,
            "web": web_transformer,
        }
        
    def _setup_default_evaluators(self) -> None:
        """设置默认的源评估器"""
        
        def recency_evaluator(source: Dict[str, Any]) -> float:
            """基于时间评估源可靠性"""
            # 在真实实现中，这会检查源的时间戳
            return source.get("recency_score", 0.5)
            
        def authority_evaluator(source: Dict[str, Any]) -> float:
            """基于权威性评估源可靠性"""
            # 在真实实现中，这会检查源的权威性指标
            return source.get("authority_score", 0.5)
        
        self.source_evaluators = {
            "recency": recency_evaluator,
            "authority": authority_evaluator,
        }
        
    def search_information(self, 
                           query: str, 
                           source_types: List[str] = None) -> List[Dict[str, Any]]:
        """
        搜索相关信息
        
        Args:
            query: 搜索查询
            source_types: 要搜索的源类型列表
            
        Returns:
            搜索结果列表
        """
        source_types = source_types or ["general"]
        results = []
        
        for source_type in source_types:
            # 转换查询以适应特定源
            transformer = self.query_transformers.get(source_type, 
                                                     self.query_transformers["general"])
            transformed_query = transformer(query)
            
            # 使用知识服务搜索
            if self.knowledge_service:
                # 在真实实现中，这里会调用知识服务的搜索方法
                search_results = self.knowledge_service.search(
                    query=transformed_query, 
                    source_type=source_type
                )
                
                for result in search_results:
                    # 评估源可靠性
                    reliability_scores = {}
                    for evaluator_name, evaluator in self.source_evaluators.items():
                        reliability_scores[evaluator_name] = evaluator(result)
                    
                    # 计算整体可靠性分数
                    overall_reliability = sum(reliability_scores.values()) / len(reliability_scores)
                    result["reliability_score"] = overall_reliability
                    result["reliability_details"] = reliability_scores
                    
                    results.append(result)
            else:
                # 模拟搜索结果用于测试
                sample_result = {
                    "id": f"result-{len(results)+1}",
                    "content": f"样本信息关于 {query}",
                    "source": f"{source_type}-source",
                    "metadata": {
                        "date": "2025-01-01",
                        "author": "Sample Author"
                    },
                    "reliability_score": 0.75,
                    "reliability_details": {"recency": 0.8, "authority": 0.7}
                }
                results.append(sample_result)
        
        # 按可靠性排序
        results.sort(key=lambda x: x.get("reliability_score", 0), reverse=True)
        return results
    
    def verify_information(self, information: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证信息的准确性
        
        Args:
            information: 要验证的信息
            
        Returns:
            验证结果
        """
        # 提取核心陈述进行验证
        statement = information.get("content", "")
        verification_result = self.fact_checking_service.check_fact(statement)
        
        # 添加验证信息到原始信息中
        verified_information = information.copy()
        verified_information["verification"] = verification_result
        
        # 如果需要，生成更正建议
        if not verification_result["is_verified"]:
            correction = self.fact_checking_service.generate_correction(
                statement, 
                verification_result
            )
            verified_information["correction_suggestion"] = correction
            
        return verified_information
    
    def integrate_information(self, 
                              content: Dict[str, Any], 
                              information: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        将外部信息整合到内容中
        
        Args:
            content: 原始内容
            information: 要整合的信息列表
            
        Returns:
            整合后的内容
        """
        # 深拷贝内容以避免修改原始对象
        import copy
        integrated_content = copy.deepcopy(content)
        
        if not information:
            return integrated_content
            
        # 收集已验证的信息
        verified_info = []
        for info in information:
            if info.get("verification", {}).get("is_verified", False):
                verified_info.append(info)
        
        # 使用LLM服务整合信息
        if verified_info and self.llm_service:
            prompt = self._create_integration_prompt(integrated_content, verified_info)
            integration_result = self.llm_service.generate_text(prompt)
            
            # 在实际实现中，这里会解析LLM的响应并更新内容
            # 简化实现：仅添加信息来源引用
            if "references" not in integrated_content:
                integrated_content["references"] = []
                
            for info in verified_info:
                integrated_content["references"].append({
                    "source": info.get("source", "Unknown"),
                    "content": info.get("content", ""),
                    "reliability": info.get("reliability_score", 0)
                })
                
        return integrated_content
    
    def _create_integration_prompt(self, 
                                  content: Dict[str, Any], 
                                  information: List[Dict[str, Any]]) -> str:
        """
        创建用于信息整合的提示
        
        Args:
            content: 原始内容
            information: 要整合的信息
            
        Returns:
            提示字符串
        """
        content_str = str(content.get("description", ""))
        if "details" in content:
            content_str += "\n\n详细信息:\n" + "\n".join(content["details"])
            
        info_str = "\n\n".join([
            f"来源 {i+1}: {info.get('content', '')}" 
            for i, info in enumerate(information)
        ])
        
        prompt = f"""
        你需要将以下信息整合到内容中：
        
        原始内容:
        {content_str}
        
        要整合的信息:
        {info_str}
        
        请以自然、流畅的方式整合这些信息，确保事实准确性和内容一致性。
        """
        
        return prompt
    
    def transform_query(self, query: str, source_type: str) -> str:
        """
        转换查询以适应特定知识源
        
        Args:
            query: 原始查询
            source_type: 知识源类型
            
        Returns:
            转换后的查询
        """
        transformer = self.query_transformers.get(source_type, 
                                                self.query_transformers["general"])
        return transformer(query)
    
    def evaluate_source_reliability(self, source: Dict[str, Any]) -> float:
        """
        评估信息源可靠性
        
        Args:
            source: 信息源数据
            
        Returns:
            可靠性评分 (0.0-1.0)
        """
        scores = []
        for evaluator_name, evaluator in self.source_evaluators.items():
            scores.append(evaluator(source))
            
        if not scores:
            return 0.5
            
        return sum(scores) / len(scores)
    
    def generate_research_summary(self, 
                                 research_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        生成研究结果摘要
        
        Args:
            research_results: 研究结果列表
            
        Returns:
            研究摘要
        """
        if not research_results:
            return {"summary": "未找到相关研究结果", "reliability": 0.0}
            
        # 计算整体可靠性
        reliability_scores = [r.get("reliability_score", 0.5) for r in research_results]
        overall_reliability = sum(reliability_scores) / len(reliability_scores)
        
        # 使用LLM生成摘要
        sources_text = "\n\n".join([
            f"来源 {i+1} ({r.get('reliability_score', 0.5):.2f}): {r.get('content', '')}"
            for i, r in enumerate(research_results)
        ])
        
        prompt = f"""
        基于以下研究结果生成简洁明了的摘要。考虑每个来源的可靠性评分。
        
        研究结果:
        {sources_text}
        
        请提供一个全面但简明的摘要，重点强调可靠来源的信息。
        """
        
        summary = ""
        if self.llm_service:
            summary = self.llm_service.generate_text(prompt)
        else:
            # 简单摘要用于测试
            summary = f"基于{len(research_results)}个信息源的研究结果摘要。整体可靠性: {overall_reliability:.2f}"
            
        return {
            "summary": summary,
            "reliability": overall_reliability,
            "sources_count": len(research_results),
            "top_sources": [
                {"source": r.get("source", "Unknown"), "reliability": r.get("reliability_score", 0.5)}
                for r in sorted(research_results, 
                               key=lambda x: x.get("reliability_score", 0), 
                               reverse=True)[:3]
            ]
        }
    
    def suggest_additional_research(self, 
                                   content: Dict[str, Any], 
                                   current_research: List[Dict[str, Any]]) -> List[str]:
        """
        建议额外的研究方向
        
        Args:
            content: 当前内容
            current_research: 当前已有的研究
            
        Returns:
            建议的研究查询列表
        """
        # 使用LLM识别潜在的研究缺口
        if not self.llm_service:
            return ["建议额外研究主题的示例"]
            
        content_str = str(content.get("description", ""))
        if "details" in content:
            content_str += "\n\n详细信息:\n" + "\n".join(content["details"])
            
        research_str = "\n\n".join([
            f"已研究 {i+1}: {r.get('content', '')}" 
            for i, r in enumerate(current_research)
        ])
        
        prompt = f"""
        基于以下内容和已有研究，识别需要进一步研究的关键问题或主题。
        
        当前内容:
        {content_str}
        
        已有研究:
        {research_str}
        
        请提出3-5个具体的研究问题，这些问题的回答将增强内容的深度和准确性。
        """
        
        response = self.llm_service.generate_text(prompt)
        
        # 解析响应获取查询列表
        # 实际实现中应该有更复杂的解析逻辑
        queries = [q.strip() for q in response.split("\n") if q.strip()]
        return queries[:5]  # 最多返回5个查询
