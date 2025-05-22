"""
Redis功能演示API端点

提供展示Redis在FastAPI中实际应用的API端点，包括缓存、分布式锁、速率限制等功能。
"""
import time
import asyncio
from typing import Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel

from app.data_access.cache.redis_client import RedisClient
from app.data_access.cache.redis_cache import RedisCache, get_cache
from app.utils.rate_limiter import rate_limit

router = APIRouter(prefix="/redis-demo", tags=["redis-demo"])


# 模型定义
class CacheItem(BaseModel):
    """缓存项模型"""
    key: str
    value: Any
    ttl: int = 300  # 默认5分钟过期


class LockRequest(BaseModel):
    """锁请求模型"""
    resource_id: str
    timeout: int = 30
    wait_timeout: int = 5


class MessageRequest(BaseModel):
    """消息发布请求"""
    channel: str
    message: Any


# 依赖项
async def get_client():
    """获取Redis客户端"""
    client = RedisClient()
    try:
        yield client
    finally:
        await client.close()


# 端点定义
@router.get("/cache/{key}", summary="获取缓存值")
async def get_cache_item(key: str, cache: RedisCache = Depends(get_cache)):
    """
    获取缓存中的值
    
    - **key**: 缓存键名
    """
    value = await cache.get(key)
    if value is None:
        raise HTTPException(status_code=404, detail="键不存在")
    return {"key": key, "value": value}


@router.post("/cache", summary="设置缓存值")
async def set_cache_item(item: CacheItem, cache: RedisCache = Depends(get_cache)):
    """
    设置缓存值
    
    - **key**: 缓存键名
    - **value**: 要存储的值
    - **ttl**: 过期时间(秒)，默认300秒
    """
    success = await cache.set(item.key, item.value, expiry=item.ttl)
    if not success:
        raise HTTPException(status_code=500, detail="设置缓存失败")
    return {"status": "success", "message": f"已设置缓存 {item.key}，过期时间 {item.ttl}秒"}


@router.delete("/cache/{key}", summary="删除缓存")
async def delete_cache_item(key: str, cache: RedisCache = Depends(get_cache)):
    """
    删除缓存键
    
    - **key**: 要删除的缓存键名
    """
    success = await cache.delete(key)
    if not success:
        raise HTTPException(status_code=500, detail="删除缓存失败")
    return {"status": "success", "message": f"已删除缓存 {key}"}


@router.post("/lock", summary="获取分布式锁")
async def acquire_resource_lock(
    request: LockRequest, 
    background_tasks: BackgroundTasks,
    client: RedisClient = Depends(get_client)
):
    """
    获取资源的分布式锁，并在后台模拟工作
    
    - **resource_id**: 资源ID
    - **timeout**: 锁超时时间(秒)
    - **wait_timeout**: 等待锁的超时时间(秒)
    """
    lock_id = await client.acquire_lock(
        request.resource_id, 
        timeout=request.timeout,
        wait_timeout=request.wait_timeout
    )
    
    if not lock_id:
        raise HTTPException(
            status_code=423, 
            detail=f"资源 {request.resource_id} 当前正在被其他进程使用，无法获取锁"
        )
    
    # 后台处理任务
    async def process_resource():
        try:
            # 模拟处理资源
            await asyncio.sleep(5)  # 假设需要5秒
        finally:
            # 释放锁
            await client.release_lock(request.resource_id, lock_id)
    
    # 启动后台任务
    background_tasks.add_task(process_resource)
    
    return {
        "status": "success", 
        "message": f"已获取资源 {request.resource_id} 的锁，正在后台处理",
        "lock_id": lock_id
    }


@router.post("/publish", summary="发布消息")
async def publish_message(
    message_req: MessageRequest,
    client: RedisClient = Depends(get_client)
):
    """
    发布消息到Redis频道
    
    - **channel**: 频道名称
    - **message**: 消息内容
    """
    recipients = await client.publish(message_req.channel, message_req.message)
    return {
        "status": "success",
        "channel": message_req.channel,
        "recipients": recipients,
        "message": "消息已发布"
    }


@router.get("/rate-limited", summary="速率限制演示")
async def rate_limited_endpoint(
    request: Request,
    rate_info: Dict[str, Any] = Depends(
        lambda: rate_limit(
            user_id="demo_user",  # 实际应用中应该使用auth中的用户ID
            action="rate_limited_demo",
            max_requests=5,
            window_seconds=60,
            sliding=True
        )
    )
):
    """
    演示速率限制功能的端点
    
    每分钟最多允许5次请求
    """
    if not rate_info["allowed"]:
        raise HTTPException(
            status_code=429, 
            detail=f"请求过于频繁，请在 {rate_info['reset_after']:.1f} 秒后重试",
            headers={"X-Rate-Limit-Reset": str(int(time.time() + rate_info["reset_after"]))}
        )
    
    return {
        "status": "success",
        "message": "请求成功处理",
        "rate_limit_info": {
            "current_count": rate_info["current_count"],
            "max_requests": rate_info["max_requests"],
            "window_seconds": rate_info["window_seconds"],
            "remaining": rate_info["max_requests"] - rate_info["current_count"]
        }
    }


@router.get("/leaderboard", summary="获取排行榜")
async def get_leaderboard(
    client: RedisClient = Depends(get_client)
):
    """
    获取模拟游戏排行榜
    
    使用Redis有序集合实现的排行榜功能
    """
    leaderboard_key = "demo:game:leaderboard"
    
    # 初始化一些数据（实际应用中这部分应该在游戏逻辑中）
    users = {
        "player1": 120,
        "player2": 85,
        "player3": 95,
        "player4": 150,
        "player5": 110
    }
    
    # 更新排行榜
    await client.zadd(leaderboard_key, users)
    
    # 获取前5名玩家
    top_players = await client.zrange(
        leaderboard_key, 
        0, 
        4, 
        withscores=True
    )
    
    # 排行榜数据（反转顺序，高分在前）
    leaderboard = []
    rank = len(top_players)
    for player, score in reversed(top_players):
        leaderboard.append({
            "rank": rank,
            "player": player,
            "score": int(score)
        })
        rank -= 1
    
    return {
        "leaderboard": leaderboard,
        "total_players": await client._client.zcard(leaderboard_key)
    }


@router.post("/idempotent/{task_id}", summary="幂等性API演示")
async def idempotent_operation(
    task_id: str,
    client: RedisClient = Depends(get_client)
):
    """
    演示幂等性操作
    
    即使多次调用相同的task_id，操作也只会执行一次
    
    - **task_id**: 任务ID，用于确保幂等性
    """
    # 使用分布式锁实现幂等性
    idempotency_key = f"idempotent:{task_id}"
    
    # 检查操作是否已完成
    result = await client.get(idempotency_key)
    if result:
        return {
            "status": "success",
            "message": "操作已完成(之前的请求)",
            "result": result,
            "idempotent": True
        }
    
    # 尝试获取锁
    lock_id = await client.acquire_lock(f"lock:{idempotency_key}", timeout=30, wait_timeout=5)
    if not lock_id:
        return {
            "status": "pending",
            "message": "操作正在处理中",
            "idempotent": True
        }
    
    try:
        # 再次检查(双重检查，防止竞态条件)
        result = await client.get(idempotency_key)
        if result:
            return {
                "status": "success",
                "message": "操作已完成(之前的请求)",
                "result": result,
                "idempotent": True
            }
        
        # 执行实际操作(模拟)
        await asyncio.sleep(2)  # 模拟耗时操作
        operation_result = {
            "task_id": task_id,
            "timestamp": time.time(),
            "data": "操作结果数据"
        }
        
        # 存储结果(无过期时间，或根据业务需求设置)
        await client.set(idempotency_key, operation_result)
        
        return {
            "status": "success",
            "message": "操作已完成(新请求)",
            "result": operation_result,
            "idempotent": False
        }
    finally:
        # 释放锁
        await client.release_lock(f"lock:{idempotency_key}", lock_id) 