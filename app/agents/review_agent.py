"""
审核智能体模块

负责内容审核和质量控制，基于ReflectionAgent提供反思能力。
"""

import logging
from typing import Any, Dict, List, Optional, Callable

from app.agents.base_agent import BaseAgent
from app.agents.patterns.reflection import ReflectionAgent  # 假设ReflectionAgent已定义
from app.services.interfaces.llm_service import LLMService

logger = logging.getLogger(__name__)


class QualityMetricsCalculator:
    """
    质量指标计算器

    功能：计算内容的各种质量指标
    """

    def __init__(self, metrics_definitions: Dict[str, Dict[str, Any]]):
        """
        初始化计算器

        参数:
            metrics_definitions: 指标定义和计算方法
                示例:
                {
                    "readability": {"method": self._calculate_readability, "weight": 0.3},
                    "coherence": {"method": self._calculate_coherence, "weight": 0.4},
                    "engagement": {"method": self._calculate_engagement, "weight": 0.3}
                }
        """
        self.metrics_definitions = metrics_definitions
        logger.info(f"QualityMetricsCalculator initialized with definitions: {metrics_definitions}")

    def calculate_metrics(self, content: Dict[str, Any]) -> Dict[str, float]:
        """
        计算质量指标

        参数:
            content: 要评估的内容，通常包含文本或其他相关信息
                     示例: {"text": "这是例文本...", "metadata": {...}}

        返回:
            Dict[str, float]: 包含各项指标得分的字典
                              示例: {"readability": 0.8, "coherence": 0.75, "engagement": 0.6}
        """
        calculated_metrics: Dict[str, float] = {}
        if not isinstance(content, dict) or "text" not in content:
            logger.warning("Content for metrics calculation is invalid or missing 'text' field.")
            return calculated_metrics

        raw_text = content.get("text", "")
        if not raw_text:
            logger.warning("Content text is empty, cannot calculate metrics.")
            return calculated_metrics

        for metric_name, definition in self.metrics_definitions.items():
            method: Optional[Callable[[str], float]] = definition.get("method")
            if method and callable(method):
                try:
                    calculated_metrics[metric_name] = method(raw_text)
                except Exception as e:
                    logger.error(f"Error calculating metric {metric_name}: {e}")
                    calculated_metrics[metric_name] = 0.0  # 异常时给默认值
            else:
                logger.warning(f"Method for metric {metric_name} is not defined or not callable.")
        
        logger.info(f"Calculated metrics for content: {calculated_metrics}")
        return calculated_metrics

    def compare_metrics(self, metrics_a: Dict[str, float], metrics_b: Dict[str, float]) -> Dict[str, float]:
        """
        比较两组指标的差异

        参数:
            metrics_a: 第一组指标
            metrics_b: 第二组指标

        返回:
            Dict[str, float]: 各项指标的差异 (metrics_b - metrics_a)
        """
        comparison: Dict[str, float] = {}
        all_keys = set(metrics_a.keys()) | set(metrics_b.keys())
        for key in all_keys:
            comparison[key] = metrics_b.get(key, 0.0) - metrics_a.get(key, 0.0)
        logger.info(f"Metrics comparison result: {comparison}")
        return comparison

    def generate_metrics_report(self, metrics: Dict[str, float]) -> Dict[str, Any]:
        """
        生成指标报告

        参数:
            metrics: 计算得到的指标

        返回:
            Dict[str, Any]: 指标报告，可以包含综合得分、各项指标等
        """
        # 示例：简单加权平均作为综合得分
        overall_score = 0.0
        total_weight = 0.0
        for metric_name, score in metrics.items():
            weight = self.metrics_definitions.get(metric_name, {}).get("weight", 0.0)
            overall_score += score * weight
            total_weight += weight
        
        if total_weight > 0:
            overall_score = overall_score / total_weight
        else:
            overall_score = 0.0 # 避免除零错误

        report = {
            "overall_score": round(overall_score, 3),
            "detailed_metrics": metrics
        }
        logger.info(f"Generated metrics report: {report}")
        return report

    # 示例指标计算方法 (需要具体实现)
    def _calculate_readability(self, text: str) -> float:
        """计算可读性分数 (示例)"""
        # 实际应使用如 Flesch-Kincaid 等算法
        logger.debug(f"Calculating readability for text (length: {len(text)})")
        return min(1.0, len(text) / 1000.0) # 简易示例

    def _calculate_coherence(self, text: str) -> float:
        """计算连贯性分数 (示例)"""
        # 实际应使用 NLP 技术评估语义连贯性
        logger.debug(f"Calculating coherence for text (length: {len(text)})")
        keywords = ["因此", "然而", "此外"]
        score = sum(1 for keyword in keywords if keyword in text)
        return min(1.0, score / 3.0) # 简易示例

    def _calculate_engagement(self, text: str) -> float:
        """计算参与度分数 (示例)"""
        # 实际可分析问题、感叹号等
        logger.debug(f"Calculating engagement for text (length: {len(text)})")
        engagement_chars = ['?', '!']
        score = sum(1 for char in engagement_chars if char in text)
        return min(1.0, score / 5.0) # 简易示例


class ReviewAgent(ReflectionAgent):
    """
    审核智能体

    功能：审核内容的一致性、质量和其他属性，基于ReflectionAgent提供强大的自我反思能力。
    """

    def __init__(
        self,
        id: str,
        name: str,
        llm_service: LLMService,
        config: Dict[str, Any] = None,
        review_criteria: Optional[Dict[str, Dict[str, Any]]] = None,
        consistency_checks: Optional[List[Dict[str, Any]]] = None,
        quality_thresholds: Optional[Dict[str, float]] = None,
        feedback_templates: Optional[Dict[str, str]] = None,
    ):
        """
        初始化审核智能体

        参数:
            id: 智能体唯一标识符
            name: 智能体名称
            llm_service: LLM服务实例
            config: 智能体配置信息
            review_criteria: 审核标准及权重
                示例: {
                    "clarity": {"description": "清晰度", "weight": 0.3, "prompt": "请评估内容的清晰度..."},
                    "accuracy": {"description": "准确性", "weight": 0.5, "prompt": "请评估内容的准确性..."}
                }
            consistency_checks: 一致性检查项目
                示例: [{"check_type": "style", "details": "确保全篇风格一致"}]
            quality_thresholds: 质量阈值配置
                示例: {"clarity": 0.7, "accuracy": 0.8}
            feedback_templates: 反馈模板集合
                示例: {"positive": "内容质量很高...", "needs_improvement": "内容在以下方面需要改进..."}
        """
        super().__init__(id=id, name=name, agent_type="ReviewAgent", llm_service=llm_service, config=config)
        self.review_criteria = review_criteria or {}
        self.consistency_checks = consistency_checks or []
        self.quality_thresholds = quality_thresholds or {}
        self.feedback_templates = feedback_templates or {}
        
        # 初始化质量指标计算器，如果需要
        # self.quality_calculator = QualityMetricsCalculator(...) # 可根据配置动态初始化
        
        logger.info(f"ReviewAgent '{self.name}' (ID: {self.id}) initialized.")
        logger.debug(f"Review Criteria: {self.review_criteria}")
        logger.debug(f"Consistency Checks: {self.consistency_checks}")
        logger.debug(f"Quality Thresholds: {self.quality_thresholds}")

    async def review_content(
        self, content: Dict[str, Any], criteria_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        审核内容

        参数:
            content: 要审核的内容，通常包含文本、元数据等
                     示例: {"id": "doc123", "text": "这是例文本...", "author": "user1"}
            criteria_names: 指定要审核的标准名称列表。如果为None，则审核所有已定义的标准。

        返回:
            Dict[str, Any]: 审核结果，包含各项标准评分、反馈等
                示例: {
                    "content_id": "doc123",
                    "overall_assessment": "good",
                    "details": {
                        "clarity": {"score": 0.8, "feedback": "清晰易懂"},
                        "accuracy": {"score": 0.9, "feedback": "准确无误"}
                    },
                    "passed_threshold": True
                }
        """
        content_id = content.get("id", "unknown_content")
        logger.info(f"Starting content review for content_id: {content_id}")
        
        review_results: Dict[str, Any] = {"content_id": content_id, "details": {}}
        overall_passed = True

        criteria_to_review = self.review_criteria
        if criteria_names:
            criteria_to_review = {
                k: v for k, v in self.review_criteria.items() if k in criteria_names
            }

        if not criteria_to_review:
            logger.warning("No review criteria specified or found. Skipping review.")
            review_results["overall_assessment"] = "skipped"
            review_results["passed_threshold"] = True # 或 False，取决于业务逻辑
            return review_results

        for criterion_name, criterion_details in criteria_to_review.items():
            prompt = criterion_details.get("prompt", f"请评估内容的 {criterion_details.get('description', criterion_name)}。")
            # 使用父类 ReflectionAgent 的能力进行评估
            # 假设 evaluate_output 返回一个包含 'score' 和 'feedback' 的字典
            # 这里需要适配 ReflectionAgent 的方法或使用LLM直接评估
            raw_text_to_review = content.get("text", "")
            if not raw_text_to_review:
                 logger.warning(f"Content text is empty for criterion {criterion_name}. Skipping this criterion.")
                 evaluation = {"score": 0.0, "feedback": "内容为空，无法评估。"}
            else:
                try:
                    # 模拟LLM调用进行评估
                    # 在实际应用中，这里会调用 self.llm_service.generate 或类似方法
                    # 并可能需要解析LLM的输出以获得结构化的评分和反馈
                    # response_text = await self.llm_service.generate_text(prompt + "\\n内容如下：\\n" + raw_text_to_review)
                    # evaluation = self._parse_llm_review_response(response_text)
                    
                    # 简化示例：使用一个模拟的评估逻辑，或者一个简单的LLM调用
                    # 对于本示例，我们假设一个简单的评分和基于长度的反馈
                    # 实际应调用 self.reflect 或类似方法，或直接调用LLM
                    # response = await self.reflect(raw_text_to_review, prompt) # 假设 reflect 返回结构化数据
                    score = min(1.0, len(raw_text_to_review) / 500.0) # 简单模拟评分
                    feedback_text = f"对 {criterion_name} 的评估完成。"
                    if score < self.quality_thresholds.get(criterion_name, 0.5):
                        feedback_text += f" {criterion_name} 未达到期望标准。"
                        overall_passed = False
                    evaluation = {"score": score, "feedback": feedback_text}

                except Exception as e:
                    logger.error(f"Error during LLM evaluation for {criterion_name}: {e}")
                    evaluation = {"score": 0.0, "feedback": f"评估 {criterion_name} 时出错: {e}"}
                    overall_passed = False
            
            review_results["details"][criterion_name] = evaluation
            
            threshold = self.quality_thresholds.get(criterion_name)
            if threshold is not None and evaluation.get("score", 0.0) < threshold:
                overall_passed = False
                logger.info(f"Criterion '{criterion_name}' score {evaluation.get('score', 0.0)} is below threshold {threshold}.")

        review_results["overall_assessment"] = "passed" if overall_passed else "needs_improvement"
        review_results["passed_threshold"] = overall_passed
        
        logger.info(f"Content review completed for content_id: {content_id}. Overall: {review_results['overall_assessment']}")
        return review_results

    def _parse_llm_review_response(self, response_text: str) -> Dict[str, Any]:
        """
        解析LLM对审核请求的响应。

        参数:
            response_text: LLM返回的文本。

        返回:
            Dict[str, Any]: 包含 'score' 和 'feedback' 的字典。
                           score应为0到1之间的小数。
        """
        # 这是一个非常简化的解析逻辑。实际中可能需要更复杂的解析，
        # 例如，如果LLM被指示以JSON格式响应。
        score = 0.5  # Default score
        feedback = response_text # Default feedback

        # 尝试从文本中提取分数 (例如，如果LLM说 "Score: 0.8")
        import re
        score_match = re.search(r"score:\s*([0-9\.]+)", response_text, re.IGNORECASE)
        if score_match:
            try:
                score = float(score_match.group(1))
                score = max(0.0, min(1.0, score)) # 确保分数在0-1之间
            except ValueError:
                logger.warning(f"Could not parse score from LLM response: {response_text}")
        
        # 可以添加更多逻辑来提取结构化的反馈
        
        return {"score": score, "feedback": feedback}


    async def check_consistency(
        self, content: Dict[str, Any], reference: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        检查内容一致性

        参数:
            content: 要检查的内容
            reference: 参考内容 (可选, 用于对比一致性)

        返回:
            Dict[str, Any]: 一致性检查结果
                示例: {
                    "overall_consistent": True,
                    "checks": [
                        {"check_type": "style", "consistent": True, "details": "风格与参考一致"},
                        {"check_type": "terminology", "consistent": False, "details": "术语'X'与参考中的'Y'不一致"}
                    ]
                }
        """
        logger.info(f"Checking consistency for content_id: {content.get('id', 'unknown_content')}")
        results: Dict[str, Any] = {"overall_consistent": True, "checks": []}

        if not self.consistency_checks:
            logger.info("No consistency checks defined. Skipping.")
            return results
            
        content_text = content.get("text", "")
        reference_text = reference.get("text", "") if reference else ""

        for check_item in self.consistency_checks:
            check_type = check_item.get("check_type", "unknown")
            check_details_desc = check_item.get("details", f"执行 {check_type} 一致性检查。")
            
            # 实际一致性检查逻辑会更复杂，可能涉及LLM调用或特定算法
            # 这里用一个简化示例
            current_check_consistent = True
            feedback_detail = f"{check_type} 一致。"

            if check_type == "style":
                # 示例：如果定义了参考文本，简单比较长度差异作为风格差异的代理
                if reference_text and abs(len(content_text) - len(reference_text)) > len(reference_text) * 0.2:
                    current_check_consistent = False
                    feedback_detail = f"风格（文本长度）与参考差异较大。"
            elif check_type == "terminology":
                # 示例：检查特定术语是否存在
                required_term = check_item.get("required_term")
                if required_term and required_term not in content_text:
                    current_check_consistent = False
                    feedback_detail = f"术语 '{required_term}' 未在内容中找到。"
            # 可以添加更多类型的检查

            if not current_check_consistent:
                results["overall_consistent"] = False

            results["checks"].append({
                "check_type": check_type,
                "consistent": current_check_consistent,
                "details": feedback_detail
            })
            logger.debug(f"Consistency check '{check_type}': {'Consistent' if current_check_consistent else 'Inconsistent'}. Details: {feedback_detail}")
        
        logger.info(f"Consistency check completed. Overall: {'Consistent' if results['overall_consistent'] else 'Inconsistent'}")
        return results

    async def evaluate_quality(self, content: Dict[str, Any]) -> Dict[str, float]:
        """
        评估内容质量 (可以使用 QualityMetricsCalculator)

        参数:
            content: 要评估的内容

        返回:
            Dict[str, float]: 内容质量评分 (各项指标)
        """
        logger.info(f"Evaluating quality for content_id: {content.get('id', 'unknown_content')}")
        # 假设 self.quality_calculator 已经根据需要初始化
        # if hasattr(self, 'quality_calculator') and self.quality_calculator:
        #     return self.quality_calculator.calculate_metrics(content)
        # else:
        #     logger.warning("QualityMetricsCalculator not available. Returning empty quality evaluation.")
        #     return {}
        
        # 简易实现：直接使用 review_content 的部分逻辑来打分，但不生成完整报告
        # 这里的 "quality" 是一个综合性的概念，可以用 review_content 的结果来近似
        review_result = await self.review_content(content)
        quality_scores: Dict[str, float] = {}
        for criterion, details in review_result.get("details", {}).items():
            if isinstance(details, dict) and "score" in details:
                 quality_scores[criterion] = details["score"]
        logger.info(f"Quality evaluation completed: {quality_scores}")
        return quality_scores


    async def generate_feedback(self, review_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成反馈意见

        参数:
            review_results: review_content 方法的返回结果

        返回:
            Dict[str, Any]: 结构化的反馈意见
                示例: {
                    "summary": "内容整体良好，但在准确性方面需改进。",
                    "positive_points": ["清晰度高"],
                    "areas_for_improvement": [
                        {"criterion": "accuracy", "feedback": "部分数据不准确，请核实来源..."}
                    ]
                }
        """
        content_id = review_results.get("content_id", "unknown_content")
        logger.info(f"Generating feedback for review results of content_id: {content_id}")

        feedback: Dict[str, Any] = {
            "summary": "",
            "positive_points": [],
            "areas_for_improvement": [],
        }

        overall_assessment = review_results.get("overall_assessment", "unknown")
        
        if overall_assessment == "passed":
            feedback["summary"] = self.feedback_templates.get("positive", "内容质量符合要求。")
        elif overall_assessment == "needs_improvement":
            feedback["summary"] = self.feedback_templates.get("needs_improvement", "内容在某些方面需要改进。")
        else: # 'skipped' or other
            feedback["summary"] = self.feedback_templates.get("neutral", "内容审核已完成。")

        for criterion, details in review_results.get("details", {}).items():
            if isinstance(details, dict):
                score = details.get("score", 0.0)
                criterion_feedback = details.get("feedback", "")
                threshold = self.quality_thresholds.get(criterion, 0.0) # 假设默认阈值为0，总是通过

                if score >= threshold: # 或者使用一个更明确的"通过"标记
                    feedback["positive_points"].append(f"{criterion}: {criterion_feedback} (得分: {score:.2f})")
                else:
                    feedback["areas_for_improvement"].append({
                        "criterion": criterion,
                        "feedback": criterion_feedback,
                        "score": score,
                        "threshold": threshold
                    })
        
        # 如果没有具体的改进点，但总体评价是需要改进，可以添加通用提示
        if overall_assessment == "needs_improvement" and not feedback["areas_for_improvement"]:
             feedback["areas_for_improvement"].append({
                 "criterion": "general",
                 "feedback": "请整体审阅并提升内容质量。",
                 "score": None,
                 "threshold": None
             })

        logger.info(f"Feedback generated for content_id: {content_id}: {feedback}")
        return feedback

    async def approve_content(self, content_id: str, review_results: Dict[str, Any]) -> bool:
        """
        批准内容 (基于审核结果)

        参数:
            content_id: 内容ID
            review_results: 来自 review_content 的审核结果

        返回:
            bool: 如果内容通过所有质量阈值，则返回 True，否则 False
        """
        passed = review_results.get("passed_threshold", False)
        if passed:
            logger.info(f"Content ID '{content_id}' approved based on review results.")
        else:
            logger.warning(f"Content ID '{content_id}' not approved. Review assessment: {review_results.get('overall_assessment', 'unknown')}")
        return passed

    async def request_revisions(
        self, content_id: str, revision_requests: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        请求内容修订 (可以发送给其他智能体或用户)

        参数:
            content_id: 内容ID
            revision_requests: 修订请求列表，每个请求包含需要修订的方面和具体说明
                示例: [{"area": "accuracy", "instruction": "请核实第3段的数据来源。"}]

        返回:
            Dict[str, Any]: 确认修订请求已发出的消息
        """
        logger.info(f"Requesting revisions for content_id: {content_id} with requests: {revision_requests}")
        # 实际实现中，这里可能会通过消息总线发送一个命令给负责修改的智能体或系统
        # 例如: await self.send_command(target_agent_id, "revise_content", {"content_id": content_id, "requests": revision_requests})
        
        # 对于本示例，我们只记录日志并返回一个确认
        response = {
            "status": "revision_requested",
            "content_id": content_id,
            "num_requests": len(revision_requests),
            "details": revision_requests
        }
        logger.debug(f"Revision request details: {response}")
        return response

    async def verify_revision(
        self, original_content: Dict[str, Any], revised_content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        验证修订后的内容 (通常会再次调用 review_content)

        参数:
            original_content: 原始内容
            revised_content: 修订后的内容

        返回:
            Dict[str, Any]: 修订验证结果，通常是 review_content 的输出
        """
        original_id = original_content.get("id", "unknown_original")
        revised_id = revised_content.get("id", "unknown_revised")
        logger.info(f"Verifying revision for content. Original ID: {original_id}, Revised ID: {revised_id}")
        
        # 重新审核修订后的内容
        verification_result = await self.review_content(revised_content)
        
        logger.info(f"Revision verification completed. Assessment: {verification_result.get('overall_assessment')}")
        return verification_result
