"""
API路由模块

汇总并注册所有API端点。
"""
from fastapi import APIRouter
import logging

# 设置日志记录
logger = logging.getLogger(__name__)

# 创建主路由器
api_router = APIRouter()

# 导入所有API端点模块
try:
    from app.api.v1.endpoints import (
        users, agents, workflows, 
        knowledge, knowledge_enhancement, projects, content, redis_demo
    )
    
    # 添加路由 - 使用异常处理确保鲁棒性
    if hasattr(users, 'router') and users.router is not None:
        api_router.include_router(users.router)
    else:
        logger.error("users.router 不存在或为None")
        
    if hasattr(projects, 'router') and projects.router is not None:
        api_router.include_router(projects.router)
    else:
        logger.error("projects.router 不存在或为None")
        
    if hasattr(agents, 'router') and agents.router is not None:
        api_router.include_router(agents.router)
    else:
        logger.error("agents.router 不存在或为None")
        
    if hasattr(workflows, 'router') and workflows.router is not None:
        api_router.include_router(workflows.router)
    else:
        logger.error("workflows.router 不存在或为None")
        
    if hasattr(content, 'router') and content.router is not None:
        api_router.include_router(content.router)
    else:
        logger.error("content.router 不存在或为None")
        
    if hasattr(knowledge, 'router') and knowledge.router is not None:
        api_router.include_router(knowledge.router)
    else:
        logger.error("knowledge.router 不存在或为None")
        
    if hasattr(knowledge_enhancement, 'router') and knowledge_enhancement.router is not None:
        api_router.include_router(knowledge_enhancement.router)
    else:
        logger.error("knowledge_enhancement.router 不存在或为None")
        
    if hasattr(redis_demo, 'router') and redis_demo.router is not None:
        api_router.include_router(redis_demo.router)
    else:
        logger.error("redis_demo.router 不存在或为None")
        
except Exception as e:
    logger.error(f"导入路由出错: {str(e)}") 