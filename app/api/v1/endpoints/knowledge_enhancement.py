"""
知识管理增强层API端点

提供增强的知识查询、规划、信息源管理等接口
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body, Path, Query, status
from fastapi.responses import JSONResponse

from app.api.v1.schemas.knowledge_enhancement import (
    EnhancedQueryRequest, QueryPlanningRequest, KnowledgeSourceCreate,
    RelationUpdate, FormatConversionRequest, EnhancedKnowledgeResponse,
    QueryPlanResponse, KnowledgeSourceResponse, RelationUpdateResponse,
    FormatConversionResponse
)
from app.models.domain.knowledge_models import KnowledgeResponse, KnowledgeFeedback
from app.knowledge_management.knowledge_enhancement import KnowledgeEnhancement
from app.knowledge_management.factory import KnowledgeFactory
from app.core.dependencies import get_current_user, get_llm_service, get_vector_store, get_graph_store

router = APIRouter(prefix="/knowledge/enhance", tags=["知识管理增强"])

async def get_knowledge_enhancement() -> KnowledgeEnhancement:
    """
    获取知识管理增强层实例的依赖函数
    
    返回:
        KnowledgeEnhancement - 知识管理增强层实例
    """
    # 使用工厂方法创建实例
    # 在实际应用中，可能需要缓存实例或使用依赖注入框架
    vector_store = await get_vector_store()
    graph_store = await get_graph_store()
    llm_service = await get_llm_service()
    
    enhancement = await KnowledgeFactory.create_knowledge_enhancement(
        vector_store=vector_store,
        graph_store=graph_store,
        llm_service=llm_service
    )
    
    return enhancement

@router.post("/query", response_model=EnhancedKnowledgeResponse)
async def enhanced_query(
    request: EnhancedQueryRequest = Body(...),
    current_user = Depends(get_current_user),
    enhancement: KnowledgeEnhancement = Depends(get_knowledge_enhancement)
):
    """
    执行增强知识查询
    """
    try:
        result = await enhancement.enhanced_query(request)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"增强查询失败: {str(e)}"
        )

@router.post("/plan", response_model=QueryPlanResponse)
async def plan_query(
    request: QueryPlanningRequest = Body(...),
    current_user = Depends(get_current_user),
    enhancement: KnowledgeEnhancement = Depends(get_knowledge_enhancement)
):
    """
    规划查询执行
    """
    try:
        result = await enhancement.plan_query(request)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询规划失败: {str(e)}"
        )

@router.get("/search", response_model=KnowledgeResponse)
async def standard_search(
    query: str = Query(..., description="搜索查询文本"),
    limit: int = Query(10, description="结果数量限制", ge=1, le=100),
    strategy: str = Query("hybrid", description="检索策略"),
    current_user = Depends(get_current_user),
    enhancement: KnowledgeEnhancement = Depends(get_knowledge_enhancement)
):
    """
    执行标准知识搜索
    """
    try:
        result = await enhancement.standard_search(
            query=query,
            limit=limit,
            strategy=strategy
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"知识搜索失败: {str(e)}"
        )

@router.post("/sources", response_model=KnowledgeSourceResponse, status_code=201)
async def add_knowledge_source(
    request: KnowledgeSourceCreate = Body(...),
    current_user = Depends(get_current_user),
    enhancement: KnowledgeEnhancement = Depends(get_knowledge_enhancement)
):
    """
    添加知识源
    """
    try:
        result = await enhancement.add_knowledge_source(request)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"添加知识源失败: {str(e)}"
        )

@router.patch("/sources/{source_id}/relations", response_model=RelationUpdateResponse)
async def update_source_relations(
    source_id: str = Path(..., description="信息源ID"),
    updates: RelationUpdate = Body(...),
    current_user = Depends(get_current_user),
    enhancement: KnowledgeEnhancement = Depends(get_knowledge_enhancement)
):
    """
    更新信息源关系
    """
    try:
        result = await enhancement.update_source_relations(source_id, updates)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新信息源关系失败: {str(e)}"
        )

@router.post("/sources/convert", response_model=FormatConversionResponse)
async def convert_source_format(
    request: FormatConversionRequest = Body(...),
    current_user = Depends(get_current_user),
    enhancement: KnowledgeEnhancement = Depends(get_knowledge_enhancement)
):
    """
    转换信息源格式
    """
    try:
        result = await enhancement.convert_source_format(request)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"转换信息源格式失败: {str(e)}"
        )

@router.post("/feedback")
async def provide_feedback(
    feedback: KnowledgeFeedback = Body(...),
    current_user = Depends(get_current_user),
    enhancement: KnowledgeEnhancement = Depends(get_knowledge_enhancement)
):
    """
    提供查询反馈
    """
    try:
        result = await enhancement.provide_feedback(feedback)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"提供反馈失败: {str(e)}"
        )

@router.get("/sources/{source_id}", response_model=KnowledgeSourceResponse)
async def get_source_with_relations(
    source_id: str = Path(..., description="信息源ID"),
    relation_types: Optional[List[str]] = Query(None, description="关系类型列表"),
    depth: int = Query(1, description="关系深度", ge=0, le=3),
    current_user = Depends(get_current_user),
    enhancement: KnowledgeEnhancement = Depends(get_knowledge_enhancement)
):
    """
    获取带关系的信息源
    """
    try:
        source_data = await enhancement.source_manager.get_source_with_relations(
            source_id=source_id,
            relation_types=relation_types,
            depth=depth
        )
        
        return {
            "source_id": source_id,
            "content": source_data.get("content", ""),
            "metadata": source_data.get("metadata", {}),
            "chunks": source_data.get("chunks"),
            "relations_data": source_data.get("relations_data")
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取信息源失败: {str(e)}"
        ) 