"""
知识库查询、管理接口

提供知识检索、添加、更新、删除等API端点
"""
from typing import Annotated, List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, status

from app.api.v1.deps import (
    get_current_user,
    get_knowledge_service
)
from app.api.v1.schemas.knowledge import (
    KnowledgeCreate,
    KnowledgeUpdate,
    KnowledgeItemResponse,
    KnowledgeItemDetail,
    KnowledgeSearchResponse,
    KnowledgeRelationCreate,
    KnowledgeRelationResponse,
    RelatedEntitiesResponse,
    GraphSearchParams
)
from app.models.schemas import UserDB, KnowledgeCreate as ModelKnowledgeCreate, KnowledgeUpdate as ModelKnowledgeUpdate
from app.services.interfaces.knowledge_service import KnowledgeService
from app.utils.error_handlers import ResourceNotFoundError, ResourceConflictError

# 创建路由器
router = APIRouter(
    prefix="/knowledge",
    tags=["knowledge"],
    responses={404: {"description": "知识未找到"}}
)

@router.get(
    "/search",
    response_model=KnowledgeSearchResponse,
    response_description="知识搜索结果"
)
async def search_knowledge(
    query: str = Query(..., description="搜索查询文本"),
    limit: int = Query(10, ge=1, le=100, description="结果数量限制"),
    metadata_filter: str = Query(None, description="元数据过滤（JSON字符串）"),
    current_user: Annotated[UserDB, Depends(get_current_user)] = None,
    knowledge_service: Annotated[KnowledgeService, Depends(get_knowledge_service)] = None
):
    """
    语义搜索知识库
    
    Args:
        query: 搜索查询文本
        limit: 结果数量限制
        metadata_filter: 元数据过滤（JSON字符串）
        
    Returns:
        KnowledgeSearchResponse: 知识搜索结果
    """
    try:
        # 解析元数据过滤条件
        filters = None
        if metadata_filter:
            import json
            try:
                filters = json.loads(metadata_filter)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="元数据过滤参数必须是有效的JSON字符串"
                )
        
        # 调用服务进行搜索
        results = await knowledge_service.search_knowledge(
            query=query, 
            limit=limit, 
            filters=filters
        )
        
        # 构造响应
        items = [KnowledgeItemResponse.model_validate(item) for item in results]
        return KnowledgeSearchResponse(
            query=query,
            items=items,
            total=len(items)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"搜索知识失败: {str(e)}"
        )

@router.post("/", response_model=KnowledgeItemResponse, status_code=201)
async def add_knowledge(
    knowledge_data: KnowledgeCreate,
    current_user: Annotated[UserDB, Depends(get_current_user)] = None,
    knowledge_service: Annotated[KnowledgeService, Depends(get_knowledge_service)] = None
):
    """
    添加知识到知识库
    
    Args:
        knowledge_data: 知识创建数据
        
    Returns:
        KnowledgeItemResponse: 创建的知识项信息
    """
    try:
        # 转换API模型到服务层模型
        model_knowledge_data = ModelKnowledgeCreate(
            content=knowledge_data.content,
            content_type=knowledge_data.content_type,
            source=knowledge_data.source,
            metadata=knowledge_data.metadata
        )
        
        # 调用服务添加知识
        knowledge_item = await knowledge_service.add_knowledge(
            model_knowledge_data,
            current_user.id
        )
        
        return KnowledgeItemResponse.model_validate(knowledge_item)
    except ResourceConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"添加知识失败: {str(e)}"
        )

@router.post("/batch", response_model=List[KnowledgeItemResponse], status_code=201)
async def batch_add_knowledge(
    knowledge_data_list: List[KnowledgeCreate],
    current_user: Annotated[UserDB, Depends(get_current_user)] = None,
    knowledge_service: Annotated[KnowledgeService, Depends(get_knowledge_service)] = None
):
    """
    批量添加知识到知识库
    
    Args:
        knowledge_data_list: 知识创建数据列表
        
    Returns:
        List[KnowledgeItemResponse]: 创建的知识项信息列表
    """
    try:
        # 转换API模型到服务层模型
        model_knowledge_data_list = [
            ModelKnowledgeCreate(
                content=item.content,
                content_type=item.content_type,
                source=item.source,
                metadata=item.metadata
            )
            for item in knowledge_data_list
        ]
        
        # 调用服务批量添加知识
        knowledge_items = await knowledge_service.batch_add_knowledge(
            model_knowledge_data_list,
            current_user.id
        )
        
        return [KnowledgeItemResponse.model_validate(item) for item in knowledge_items]
    except ResourceConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量添加知识失败: {str(e)}"
        )

@router.get("/{knowledge_id}", response_model=KnowledgeItemDetail)
async def get_knowledge_detail(
    knowledge_id: int = Path(...),
    current_user: Annotated[UserDB, Depends(get_current_user)] = None,
    knowledge_service: Annotated[KnowledgeService, Depends(get_knowledge_service)] = None
):
    """
    获取特定知识的详细信息
    
    Args:
        knowledge_id: 知识ID
        
    Returns:
        KnowledgeItemDetail: 知识详细信息
    """
    try:
        # 获取知识项
        knowledge_item = await knowledge_service.get_knowledge_by_id(knowledge_id)
        
        if not knowledge_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"知识项 {knowledge_id} 不存在"
            )
            
        # 获取相关实体（只需要获取第一层关系）
        related_items, relations = await knowledge_service.get_related_knowledge(
            knowledge_id, 
            depth=1
        )
        
        # 构建详细响应
        detail = KnowledgeItemDetail(
            **KnowledgeItemResponse.model_validate(knowledge_item).model_dump(),
            relation_count=len(relations),
            related_items_preview=[KnowledgeItemResponse.model_validate(item) for item in related_items[:5]]
        )
        
        return detail
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取知识详情失败: {str(e)}"
        )

@router.patch("/{knowledge_id}", response_model=KnowledgeItemResponse)
async def update_knowledge(
    knowledge_id: int = Path(...),
    knowledge_data: KnowledgeUpdate = None,
    current_user: Annotated[UserDB, Depends(get_current_user)] = None,
    knowledge_service: Annotated[KnowledgeService, Depends(get_knowledge_service)] = None
):
    """
    更新知识信息
    
    Args:
        knowledge_id: 知识ID
        knowledge_data: 知识更新数据
        
    Returns:
        KnowledgeItemResponse: 更新后的知识信息
    """
    try:
        # 转换API模型到服务层模型
        model_knowledge_data = ModelKnowledgeUpdate(
            content=knowledge_data.content,
            metadata=knowledge_data.metadata
        )
        
        # 调用服务更新知识
        updated_knowledge = await knowledge_service.update_knowledge(
            knowledge_id, 
            model_knowledge_data
        )
        
        return KnowledgeItemResponse.model_validate(updated_knowledge)
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新知识失败: {str(e)}"
        )

@router.delete("/{knowledge_id}", status_code=204)
async def delete_knowledge(
    knowledge_id: int = Path(...),
    current_user: Annotated[UserDB, Depends(get_current_user)] = None,
    knowledge_service: Annotated[KnowledgeService, Depends(get_knowledge_service)] = None
):
    """
    删除知识
    
    Args:
        knowledge_id: 知识ID
    """
    try:
        await knowledge_service.delete_knowledge(knowledge_id)
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除知识失败: {str(e)}"
        )

@router.post("/extract", response_model=List[KnowledgeItemResponse], status_code=201)
async def extract_knowledge(
    text: str = Body(..., embed=True, description="要提取知识的文本内容"),
    current_user: Annotated[UserDB, Depends(get_current_user)] = None,
    knowledge_service: Annotated[KnowledgeService, Depends(get_knowledge_service)] = None
):
    """
    从文本中提取知识
    
    Args:
        text: 要提取知识的文本内容
        
    Returns:
        List[KnowledgeItemResponse]: 提取的知识项列表
    """
    try:
        # 调用服务从文本中提取知识图谱
        knowledge_items, _ = await knowledge_service.extract_knowledge_graph(
            text, 
            current_user.id
        )
        
        return [KnowledgeItemResponse.model_validate(item) for item in knowledge_items]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"提取知识失败: {str(e)}"
        )

@router.post("/relations", response_model=KnowledgeRelationResponse, status_code=201)
async def create_knowledge_relation(
    relation_data: KnowledgeRelationCreate,
    current_user: Annotated[UserDB, Depends(get_current_user)] = None,
    knowledge_service: Annotated[KnowledgeService, Depends(get_knowledge_service)] = None
):
    """
    创建知识项之间的关系
    
    Args:
        relation_data: 关系创建数据
        
    Returns:
        KnowledgeRelationResponse: 创建的关系信息
    """
    try:
        # 调用服务创建知识关系
        relation = await knowledge_service.add_knowledge_relation(
            source_id=relation_data.source_id,
            target_id=relation_data.target_id,
            relation_type=relation_data.relation_type,
            properties=relation_data.properties
        )
        
        return KnowledgeRelationResponse.model_validate(relation)
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建知识关系失败: {str(e)}"
        )

@router.get("/related-entities/{entity_id}", response_model=RelatedEntitiesResponse)
async def get_related_entities(
    entity_id: int = Path(...),
    relation_types: Optional[List[str]] = Query(None, description="关系类型过滤"),
    depth: int = Query(1, ge=1, le=3, description="图遍历深度"),
    current_user: Annotated[UserDB, Depends(get_current_user)] = None,
    knowledge_service: Annotated[KnowledgeService, Depends(get_knowledge_service)] = None
):
    """
    获取与特定实体相关的其他实体
    
    Args:
        entity_id: 实体ID
        relation_types: 关系类型过滤
        depth: 图遍历深度
        
    Returns:
        RelatedEntitiesResponse: 相关实体列表
    """
    try:
        # 获取相关知识
        related_items, relations = await knowledge_service.get_related_knowledge(
            knowledge_id=entity_id,
            relation_types=relation_types,
            depth=depth
        )
        
        # 构建响应
        return RelatedEntitiesResponse(
            entity_id=entity_id,
            related_items=[KnowledgeItemResponse.model_validate(item) for item in related_items],
            relations=[KnowledgeRelationResponse.model_validate(rel) for rel in relations]
        )
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取相关实体失败: {str(e)}"
        )

@router.post(
    "/graph-search",
    response_model=KnowledgeSearchResponse,
    response_description="图搜索结果"
)
async def graph_search(
    search_params: GraphSearchParams,
    current_user: Annotated[UserDB, Depends(get_current_user)] = None,
    knowledge_service: Annotated[KnowledgeService, Depends(get_knowledge_service)] = None
):
    """
    基于图结构的知识搜索
    
    Args:
        search_params: 图搜索参数
        
    Returns:
        KnowledgeSearchResponse: 知识搜索结果
    """
    try:
        # 解析过滤条件
        filters = None
        if search_params.filters:
            import json
            try:
                filters = json.loads(search_params.filters)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="过滤器参数必须是有效的JSON字符串"
                )
        
        # 调用服务进行图搜索
        results = await knowledge_service.graph_search_knowledge(
            query=search_params.query,
            relation_types=search_params.relation_types,
            filters=filters,
            limit=search_params.limit,
            depth=search_params.depth
        )
        
        # 构造响应
        items = [KnowledgeItemResponse.model_validate(item) for item in results]
        return KnowledgeSearchResponse(
            query=search_params.query,
            items=items,
            total=len(items)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"图搜索知识失败: {str(e)}"
        )

@router.post("/query", response_model=Dict[str, Any])
async def rag_query(
    query: str = Body(..., embed=True, description="查询文本"),
    context_ids: Optional[List[int]] = Body(None, embed=True, description="上下文知识项ID列表"),
    current_user: Annotated[UserDB, Depends(get_current_user)] = None,
    knowledge_service: Annotated[KnowledgeService, Depends(get_knowledge_service)] = None
):
    """
    使用知识图谱增强的RAG进行查询
    
    Args:
        query: 查询文本
        context_ids: 上下文知识项ID列表
        
    Returns:
        Dict[str, Any]: 查询结果
    """
    try:
        # 调用服务进行图谱增强的查询
        answer = await knowledge_service.graph_rag_query(query, context_ids)
        
        return {
            "query": query,
            "answer": answer,
            "context_count": len(context_ids) if context_ids else 0
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询失败: {str(e)}"
        )
