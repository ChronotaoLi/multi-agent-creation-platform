"""
知识管理智能体实现

负责外部知识获取、更新和管理的智能体
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from app.agents.base_agent import BaseAgent
from app.services.interfaces.llm_service import LLMService
from app.models.domain.llm_types import LLMMessage
from app.data_access.vector_store.vector_store_service import VectorStoreService

logger = logging.getLogger(__name__)


class KnowledgeAgent(BaseAgent):
    """
    知识管理智能体
    
    负责外部知识获取、整合和管理，提供世界知识支持
    """
    
    def __init__(
        self,
        id: str,
        name: str,
        llm_service: LLMService,
        vector_store_service: VectorStoreService,
        config: Dict[str, Any] = None
    ):
        """
        初始化知识管理智能体
        
        参数:
            id: 智能体唯一标识符
            name: 智能体名称
            llm_service: LLM服务实例
            vector_store_service: 向量存储服务实例
            config: 智能体配置信息
        """
        super().__init__(id, name, "knowledge", llm_service, config or {})
        
        # 向量存储服务
        self.vector_store_service = vector_store_service
        
        # 知识库索引名称
        self.knowledge_index = config.get("knowledge_index", "knowledge_base_index")
        
        # 知识获取配置
        self.knowledge_config = config.get("knowledge_config", {
            "confidence_threshold": 0.7,  # 可信度阈值
            "max_search_results": 10,     # 最大搜索结果数
            "context_window_size": 5000,  # 上下文窗口大小（字符）
            "update_frequency": 30        # 知识更新频率（天）
        })
        
        # 知识领域分类
        self.knowledge_domains = config.get("knowledge_domains", {
            "general": "通用知识",
            "science": "科学知识",
            "history": "历史知识",
            "culture": "文化知识",
            "geography": "地理知识",
            "literature": "文学知识"
        })
        
        # 系统提示模板
        self.system_prompt_template = config.get("system_prompt_template", """
你是一个负责知识获取和管理的智能体，需要提供准确、全面的信息来支持创作过程。

在回答问题或提供信息时，你应该：
1. 提供准确、客观的事实信息
2. 区分事实和观点
3. 引用可靠的信息来源
4. 承认知识的局限性
5. 在不确定时表明信息的置信度

请保持中立立场，不带偏见地呈现信息，支持其他智能体进行高质量创作。
""")
        
        # 最后更新时间记录
        self.last_update_timestamps = {}
    
    async def query_knowledge(self, query: str, domain: str = None, limit: int = 5) -> Dict[str, Any]:
        """
        查询知识库
        
        参数:
            query: 查询问题
            domain: 可选的知识领域过滤器
            limit: 返回结果数量限制
            
        返回:
            Dict[str, Any]: 查询结果和相关信息
        """
        try:
            # 构建过滤器
            filters = {}
            if domain and domain in self.knowledge_domains:
                filters["domain"] = domain
            
            # 从向量存储中搜索相关知识
            search_results = await self.vector_store_service.search(
                query=query,
                index_name=self.knowledge_index,
                limit=limit,
                filters=filters
            )
            
            if not search_results:
                logger.info(f"知识库中没有查询到 '{query}' 相关信息")
                return {
                    "query": query,
                    "results": [],
                    "answer": "知识库中没有相关信息。需要获取此知识。",
                    "confidence": 0.0
                }
            
            # 提取结果内容和元数据
            results = []
            for result in search_results:
                results.append({
                    "content": result["text"],
                    "metadata": result["metadata"],
                    "score": result["score"]
                })
            
            # 根据检索结果生成综合回答
            answer = await self._synthesize_answer(query, results)
            
            # 计算综合置信度
            confidence = sum(result["score"] for result in results) / len(results)
            
            response = {
                "query": query,
                "results": results,
                "answer": answer,
                "confidence": confidence,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"查询知识库 '{query}'，找到 {len(results)} 个结果，置信度: {confidence:.2f}")
            return response
            
        except Exception as e:
            logger.error(f"查询知识库失败: {str(e)}")
            return {
                "query": query,
                "results": [],
                "error": str(e),
                "confidence": 0.0
            }
    
    async def acquire_knowledge(self, query: str, domain: str = None) -> Dict[str, Any]:
        """
        获取新知识并添加到知识库
        
        参数:
            query: 知识查询
            domain: 知识领域分类
            
        返回:
            Dict[str, Any]: 获取的知识及其相关信息
        """
        try:
            # 构建知识获取提示
            prompt = f"""
请获取关于以下问题的知识：

问题: {query}

请提供详细、准确的信息。包括：
1. 核心事实和定义
2. 相关背景信息
3. 多角度观点（如果适用）
4. 参考来源或引用（如果有）

你的回答将被用于创作辅助，请确保信息客观、中立、准确。
"""
            
            # 调用LLM获取知识
            messages = [
                LLMMessage(role="system", content=self.system_prompt_template),
                LLMMessage(role="user", content=prompt)
            ]
            
            response = await self.llm_service.chat_completion(
                messages=messages,
                temperature=0.3  # 使用低温度以获得更客观的回答
            )
            
            # 如果未指定领域，尝试自动分类
            if not domain:
                domain = await self._classify_domain(query, response.content)
            
            # 准备知识条目
            knowledge_entry = {
                "query": query,
                "content": response.content,
                "domain": domain,
                "confidence": 0.8,  # 初始可信度
                "source": "llm_generation",
                "timestamp": datetime.now().isoformat(),
                "last_verified": datetime.now().isoformat()
            }
            
            # 存储到向量数据库
            await self.vector_store_service.store_text(
                text=response.content,
                metadata=knowledge_entry,
                index_name=self.knowledge_index
            )
            
            logger.info(f"获取并存储了关于 '{query}' 的新知识，领域: {domain}")
            return knowledge_entry
            
        except Exception as e:
            logger.error(f"获取知识失败: {str(e)}")
            return {
                "query": query,
                "error": str(e),
                "status": "failed"
            }
    
    async def update_knowledge(self, knowledge_id: str, new_content: str = None) -> Dict[str, Any]:
        """
        更新已有知识条目
        
        参数:
            knowledge_id: 知识条目ID
            new_content: 新的内容，如果为None则自动获取更新
            
        返回:
            Dict[str, Any]: 更新后的知识条目
        """
        try:
            # 获取原始知识条目
            filters = {"id": knowledge_id}
            results = await self.vector_store_service.search(
                query="",  # 空查询，仅通过ID过滤
                index_name=self.knowledge_index,
                limit=1,
                filters=filters
            )
            
            if not results:
                logger.warning(f"知识条目 {knowledge_id} 不存在")
                return {"error": f"知识条目 {knowledge_id} 不存在"}
            
            original_entry = results[0]["metadata"]
            query = original_entry.get("query", "")
            
            # 如果没有提供新内容，自动获取更新
            if not new_content:
                # 调用LLM获取最新知识
                prompt = f"""
请提供关于以下主题的最新知识：

主题: {query}

原始内容:
{results[0]["text"]}

请提供最新、准确的信息，特别是对原始内容的更新或修正。
"""
                
                messages = [
                    LLMMessage(role="system", content=self.system_prompt_template),
                    LLMMessage(role="user", content=prompt)
                ]
                
                response = await self.llm_service.chat_completion(
                    messages=messages,
                    temperature=0.3
                )
                
                new_content = response.content
            
            # 更新知识条目
            updated_entry = original_entry.copy()
            updated_entry["content"] = new_content
            updated_entry["last_updated"] = datetime.now().isoformat()
            updated_entry["update_count"] = updated_entry.get("update_count", 0) + 1
            
            # 删除原条目并存储更新后的条目
            await self.vector_store_service.delete_by_filter(
                index_name=self.knowledge_index,
                filters=filters
            )
            
            await self.vector_store_service.store_text(
                text=new_content,
                metadata=updated_entry,
                index_name=self.knowledge_index
            )
            
            logger.info(f"更新了知识条目 {knowledge_id}")
            return updated_entry
            
        except Exception as e:
            logger.error(f"更新知识失败: {str(e)}")
            return {
                "id": knowledge_id,
                "error": str(e),
                "status": "failed"
            }
    
    async def verify_knowledge(self, knowledge_entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证知识条目的准确性
        
        参数:
            knowledge_entry: 要验证的知识条目
            
        返回:
            Dict[str, Any]: 验证结果
        """
        try:
            # 提取知识内容
            content = knowledge_entry.get("content", "")
            query = knowledge_entry.get("query", "")
            
            # 构建验证提示
            prompt = f"""
请验证以下知识的准确性：

主题: {query}

知识内容:
{content}

请评估：
1. 事实准确性：内容中的事实陈述是否准确
2. 全面性：是否涵盖了主题的关键方面
3. 时效性：内容是否包含过时信息
4. 客观性：内容是否保持中立，不带偏见

请以JSON格式返回评估结果：
```json
{{
  "accuracy_score": 0-10分,
  "completeness_score": 0-10分,
  "timeliness_score": 0-10分,
  "objectivity_score": 0-10分,
  "overall_score": 0-10分,
  "factual_errors": ["错误1", "错误2", ...],
  "missing_information": ["缺失信息1", "缺失信息2", ...],
  "outdated_content": ["过时内容1", "过时内容2", ...],
  "bias_issues": ["偏见问题1", "偏见问题2", ...],
  "verification_notes": "综合评价和建议"
}}
```
"""
            
            # 调用LLM进行验证
            messages = [
                LLMMessage(role="system", content="你是一个专业的知识验证专家，擅长评估信息的准确性、完整性和客观性。请保持严格的批判思维和中立立场。"),
                LLMMessage(role="user", content=prompt)
            ]
            
            response = await self.llm_service.chat_completion(
                messages=messages,
                temperature=0.3
            )
            
            content = response.content
            # 提取JSON部分
            import re
            
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = content
                
            # 解析验证结果
            verification_result = json.loads(json_str)
            
            # 更新知识条目的验证信息
            if "id" in knowledge_entry:
                verified_entry = knowledge_entry.copy()
                verified_entry["verification"] = verification_result
                verified_entry["last_verified"] = datetime.now().isoformat()
                verified_entry["confidence"] = verification_result.get("overall_score", 0) / 10  # 转换为0-1范围
                
                # 更新存储的条目
                filters = {"id": knowledge_entry["id"]}
                await self.vector_store_service.delete_by_filter(
                    index_name=self.knowledge_index,
                    filters=filters
                )
                
                await self.vector_store_service.store_text(
                    text=knowledge_entry.get("content", ""),
                    metadata=verified_entry,
                    index_name=self.knowledge_index
                )
                
                logger.info(f"验证了知识条目 {knowledge_entry.get('id')}, 得分: {verification_result.get('overall_score', 0)}")
                return verified_entry
            else:
                # 如果没有ID，只返回验证结果
                return {
                    "original_entry": knowledge_entry,
                    "verification": verification_result
                }
            
        except Exception as e:
            logger.error(f"验证知识失败: {str(e)}")
            return {
                "error": str(e),
                "status": "failed",
                "original_entry": knowledge_entry
            }
    
    async def schedule_knowledge_updates(self) -> Dict[str, Any]:
        """
        调度知识更新任务，检查过期知识并更新
        
        返回:
            Dict[str, Any]: 更新统计信息
        """
        try:
            # 获取当前时间
            now = datetime.now()
            update_frequency = self.knowledge_config.get("update_frequency", 30)  # 默认30天更新一次
            
            # 构建查询过滤器，查找需要更新的知识条目
            outdated_filters = {
                "last_updated_before": (now - datetime.timedelta(days=update_frequency)).isoformat()
            }
            
            # 从向量存储中搜索过期知识
            outdated_results = await self.vector_store_service.search(
                query="",  # 空查询，仅通过过期时间过滤
                index_name=self.knowledge_index,
                limit=100,  # 每次调度更新一批知识
                filters=outdated_filters
            )
            
            if not outdated_results:
                logger.info("没有需要更新的知识条目")
                return {"updated": 0, "failed": 0, "skipped": 0, "message": "没有需要更新的知识条目"}
            
            # 更新统计
            stats = {
                "updated": 0,
                "failed": 0,
                "skipped": 0,
                "entries": []
            }
            
            # 处理每个过期知识条目
            for result in outdated_results:
                entry = result["metadata"]
                entry_id = entry.get("id")
                
                # 跳过最近已更新的条目
                if entry_id in self.last_update_timestamps:
                    last_update = self.last_update_timestamps[entry_id]
                    if (now - datetime.fromisoformat(last_update)).days < update_frequency:
                        stats["skipped"] += 1
                        continue
                
                try:
                    # 更新知识条目
                    updated_entry = await self.update_knowledge(entry_id)
                    if "error" in updated_entry:
                        stats["failed"] += 1
                        stats["entries"].append({"id": entry_id, "status": "failed", "error": updated_entry["error"]})
                    else:
                        stats["updated"] += 1
                        stats["entries"].append({"id": entry_id, "status": "updated"})
                        self.last_update_timestamps[entry_id] = now.isoformat()
                except Exception as e:
                    stats["failed"] += 1
                    stats["entries"].append({"id": entry_id, "status": "failed", "error": str(e)})
            
            logger.info(f"完成知识更新调度，更新: {stats['updated']}，失败: {stats['failed']}，跳过: {stats['skipped']}")
            return stats
            
        except Exception as e:
            logger.error(f"知识更新调度失败: {str(e)}")
            return {"error": str(e), "status": "failed"}
    
    async def explore_knowledge_domain(self, domain: str, depth: int = 2) -> Dict[str, Any]:
        """
        探索指定知识领域，生成概览和结构
        
        参数:
            domain: 知识领域
            depth: 探索深度（层级）
            
        返回:
            Dict[str, Any]: 知识领域探索结果
        """
        if domain not in self.knowledge_domains:
            return {"error": f"未知的知识领域: {domain}", "available_domains": list(self.knowledge_domains.keys())}
        
        try:
            # 获取领域中的知识条目
            filters = {"domain": domain}
            results = await self.vector_store_service.search(
                query="",  # 空查询，仅通过领域过滤
                index_name=self.knowledge_index,
                limit=100,  # 获取足够多的条目以构建概览
                filters=filters
            )
            
            if not results:
                logger.info(f"领域 '{domain}' 中没有知识条目")
                # 如果没有条目，尝试生成领域知识结构
                return await self._generate_domain_structure(domain, depth)
            
            # 提取领域中的主要主题和概念
            topics = []
            for result in results:
                entry = result["metadata"]
                topics.append({
                    "id": entry.get("id", ""),
                    "query": entry.get("query", ""),
                    "confidence": entry.get("confidence", 0),
                    "last_updated": entry.get("last_updated", "")
                })
            
            # 构建提示，让LLM分析领域结构
            topics_text = "\n".join([f"- {topic['query']}" for topic in topics[:20]])  # 限制数量
            
            prompt = f"""
请分析以下 {domain} 领域的主题列表，并构建一个层次化的知识结构：

主题列表：
{topics_text}

请基于这些主题及你的专业知识，创建一个{depth}层深度的知识结构，包括：
1. 主要类别和子类别
2. 关键概念及其关系
3. 领域的核心知识点

请以JSON格式返回知识结构：
```json
{{
  "domain": "{domain}",
  "description": "领域概述",
  "main_categories": [
    {{
      "name": "类别1",
      "description": "类别描述",
      "subcategories": [
        {{
          "name": "子类别1",
          "description": "子类别描述",
          "key_concepts": ["概念1", "概念2", ...]
        }},
        ...
      ],
      "key_concepts": ["概念1", "概念2", ...]
    }},
    ...
  ],
  "core_principles": ["原则1", "原则2", ...],
  "related_domains": ["相关领域1", "相关领域2", ...]
}}
```
"""
            
            # 调用LLM分析领域结构
            messages = [
                LLMMessage(role="system", content="你是一个专业的知识组织专家，擅长分析和构建知识领域的概念层次结构和关系网络。"),
                LLMMessage(role="user", content=prompt)
            ]
            
            response = await self.llm_service.chat_completion(
                messages=messages,
                temperature=0.4
            )
            
            content = response.content
            # 提取JSON部分
            import re
            
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = content
                
            # 解析领域结构
            domain_structure = json.loads(json_str)
            
            # 添加元数据
            domain_structure["topic_count"] = len(topics)
            domain_structure["available_entries"] = topics[:20]  # 只包含部分条目作为示例
            domain_structure["domain_description"] = self.knowledge_domains.get(domain, "")
            
            logger.info(f"探索了知识领域 '{domain}'，识别了 {len(domain_structure.get('main_categories', []))} 个主要类别")
            return domain_structure
            
        except Exception as e:
            logger.error(f"探索知识领域失败: {str(e)}")
            return {"error": str(e), "status": "failed", "domain": domain}
    
    async def link_related_knowledge(self, knowledge_id: str, max_links: int = 5) -> Dict[str, Any]:
        """
        查找并链接与指定知识条目相关的其他知识
        
        参数:
            knowledge_id: 知识条目ID
            max_links: 最大链接数量
            
        返回:
            Dict[str, Any]: 链接结果
        """
        try:
            # 获取原始知识条目
            filters = {"id": knowledge_id}
            results = await self.vector_store_service.search(
                query="",  # 空查询，仅通过ID过滤
                index_name=self.knowledge_index,
                limit=1,
                filters=filters
            )
            
            if not results:
                logger.warning(f"知识条目 {knowledge_id} 不存在")
                return {"error": f"知识条目 {knowledge_id} 不存在"}
            
            original_entry = results[0]["metadata"]
            query = original_entry.get("query", "")
            content = results[0]["text"]
            
            # 使用内容作为查询，查找相关条目
            related_results = await self.vector_store_service.search(
                query=content,
                index_name=self.knowledge_index,
                limit=max_links + 1,  # 多获取一个，因为可能包含自身
                filters={}
            )
            
            # 过滤掉自身
            related_entries = []
            for result in related_results:
                entry_id = result["metadata"].get("id", "")
                if entry_id != knowledge_id:  # 排除自身
                    related_entries.append({
                        "id": entry_id,
                        "query": result["metadata"].get("query", ""),
                        "domain": result["metadata"].get("domain", ""),
                        "similarity_score": result["score"],
                        "snippet": result["text"][:200] + "..." if len(result["text"]) > 200 else result["text"]
                    })
                
                if len(related_entries) >= max_links:
                    break
            
            # 更新原条目的相关知识链接
            updated_entry = original_entry.copy()
            updated_entry["related_knowledge"] = [entry["id"] for entry in related_entries]
            updated_entry["last_linked"] = datetime.now().isoformat()
            
            # 更新存储
            await self.vector_store_service.delete_by_filter(
                index_name=self.knowledge_index,
                filters=filters
            )
            
            await self.vector_store_service.store_text(
                text=content,
                metadata=updated_entry,
                index_name=self.knowledge_index
            )
            
            # 构建返回结果
            result = {
                "knowledge_id": knowledge_id,
                "query": query,
                "related_entries": related_entries,
                "link_count": len(related_entries)
            }
            
            logger.info(f"为知识条目 {knowledge_id} 链接了 {len(related_entries)} 个相关条目")
            return result
            
        except Exception as e:
            logger.error(f"链接相关知识失败: {str(e)}")
            return {"error": str(e), "status": "failed", "knowledge_id": knowledge_id}
    
    async def _synthesize_answer(self, query: str, results: List[Dict[str, Any]]) -> str:
        """
        根据检索结果合成回答
        
        参数:
            query: 查询问题
            results: 检索结果列表
            
        返回:
            str: 合成的回答
        """
        # 提取检索到的内容
        contents = []
        for result in results:
            contents.append(result["content"])
        
        context = "\n\n".join(contents)
        
        # 限制上下文长度
        max_length = self.knowledge_config.get("context_window_size", 5000)
        if len(context) > max_length:
            context = context[:max_length] + "..."
        
        # 构建提示
        prompt = f"""
基于以下检索到的信息，回答问题：

问题：{query}

检索到的信息：
{context}

请基于上述信息提供准确、简洁的回答。如果信息不足以完全回答问题，请明确指出。
"""
        
        # 调用LLM合成回答
        messages = [
            LLMMessage(role="system", content=self.system_prompt_template),
            LLMMessage(role="user", content=prompt)
        ]
        
        try:
            response = await self.llm_service.chat_completion(
                messages=messages,
                temperature=0.3
            )
            
            return response.content
        
        except Exception as e:
            logger.error(f"合成回答失败: {str(e)}")
            # 如果LLM调用失败，返回最相关的结果作为回答
            if results:
                return f"(自动提取的回答) {results[0]['content'][:500]}..."
            else:
                return "无法合成回答，检索结果为空。"
    
    async def _classify_domain(self, query: str, content: str) -> str:
        """
        自动分类知识领域
        
        参数:
            query: 查询问题
            content: 知识内容
            
        返回:
            str: 识别的领域
        """
        # 构建提示
        domains_text = "\n".join([f"- {key}: {desc}" for key, desc in self.knowledge_domains.items()])
        
        prompt = f"""
请将以下内容分类到最合适的知识领域：

问题：{query}

内容：
{content[:500]}...

可选的知识领域：
{domains_text}

请仅返回最合适的领域代码（如"general"、"science"等），不要有任何其他内容。
"""
        
        # 调用LLM分类领域
        messages = [
            LLMMessage(role="system", content="你是一个专业的知识分类专家，擅长识别内容所属的知识领域。"),
            LLMMessage(role="user", content=prompt)
        ]
        
        try:
            response = await self.llm_service.chat_completion(
                messages=messages,
                temperature=0.1  # 使用很低的温度以获得一致的分类结果
            )
            
            domain = response.content.strip().lower()
            
            # 检查是否是有效的领域
            if domain not in self.knowledge_domains:
                logger.warning(f"分类结果 '{domain}' 不是有效的领域，使用默认领域 'general'")
                return "general"
            
            return domain
            
        except Exception as e:
            logger.error(f"分类领域失败: {str(e)}")
            # 出错时返回默认领域
            return "general"
    
    async def _generate_domain_structure(self, domain: str, depth: int) -> Dict[str, Any]:
        """
        为空领域生成知识结构框架
        
        参数:
            domain: 知识领域
            depth: 结构深度
            
        返回:
            Dict[str, Any]: 领域知识结构
        """
        # 获取领域描述
        domain_description = self.knowledge_domains.get(domain, f"{domain}领域")
        
        # 构建提示
        prompt = f"""
请为 {domain_description} 创建一个全面的知识结构框架。

该领域目前在知识库中没有条目，请创建一个完整的知识框架，包括：
1. 主要类别和子类别（深度为{depth}层）
2. 每个类别的关键概念
3. 领域的核心原则和理论
4. 与其他领域的关系

请以JSON格式返回知识结构：
```json
{{
  "domain": "{domain}",
  "description": "领域详细描述",
  "main_categories": [
    {{
      "name": "主要类别1",
      "description": "类别描述",
      "subcategories": [
        {{
          "name": "子类别1",
          "description": "子类别描述",
          "key_concepts": ["概念1", "概念2", ...]
        }},
        ...
      ],
      "key_concepts": ["概念1", "概念2", ...]
    }},
    ...
  ],
  "core_principles": ["原则1", "原则2", ...],
  "related_domains": ["相关领域1", "相关领域2", ...]
}}
```
"""
        
        # 调用LLM生成领域结构
        messages = [
            LLMMessage(role="system", content="你是一个专业的知识组织专家，擅长创建全面、结构化的知识领域框架。"),
            LLMMessage(role="user", content=prompt)
        ]
        
        try:
            response = await self.llm_service.chat_completion(
                messages=messages,
                temperature=0.5  # 使用适中的温度以获得创意性的结构
            )
            
            content = response.content
            # 提取JSON部分
            import re
            
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = content
                
            # 解析领域结构
            domain_structure = json.loads(json_str)
            
            # 添加生成标志
            domain_structure["generated"] = True
            domain_structure["timestamp"] = datetime.now().isoformat()
            
            logger.info(f"为空领域 '{domain}' 生成了知识结构框架")
            return domain_structure
            
        except Exception as e:
            logger.error(f"生成领域结构失败: {str(e)}")
            return {
                "error": str(e),
                "domain": domain,
                "status": "failed"
            }