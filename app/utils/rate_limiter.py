"""
Redis速率限制模块

提供基于Redis的速率限制功能，用于限制API请求频率和防止滥用。
实现了两种常见的限流算法：固定窗口计数器和滑动窗口计数器。
"""
import time
import logging
import asyncio
from typing import Tuple, Optional, Dict, Any

from app.data_access.cache.redis_client import RedisClient
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class RedisRateLimiter:
    """基于Redis的速率限制器实现"""
    
    def __init__(self, redis_client: RedisClient = None):
        """初始化速率限制器
        
        参数:
            redis_client: RedisClient - Redis客户端实例
        """
        self.redis = redis_client or RedisClient()
    
    async def check_rate_fixed_window(
        self, 
        key: str, 
        max_requests: int, 
        window_seconds: int
    ) -> Tuple[bool, int, float]:
        """固定窗口速率限制检查
        
        参数:
            key: str - 限流键（通常是用户ID或IP地址）
            max_requests: int - 窗口期内允许的最大请求数
            window_seconds: int - 窗口期长度（秒）
            
        返回:
            Tuple[bool, int, float]: 
                - 是否允许访问
                - 当前周期内已处理的请求数
                - 重置窗口的剩余秒数
        """
        # 确保连接
        if not hasattr(self.redis, '_client') or self.redis._client is None:
            await self.redis.connect()
        
        # 构造键名
        rate_key = f"rate:fixed:{key}:{window_seconds}"
        
        # 获取当前时间戳作为窗口标识
        current_time = int(time.time())
        window_key = current_time // window_seconds
        
        # 完整的带窗口标识的键名
        full_key = f"{rate_key}:{window_key}"
        
        # 获取当前计数
        count = await self.redis.get(full_key)
        count = int(count) if count is not None else 0
        
        # 计算窗口重置的剩余时间
        reset_after = window_seconds - (current_time % window_seconds)
        
        # 检查是否超过限制
        if count >= max_requests:
            return False, count, reset_after
        
        # 增加计数并设置过期时间
        count += 1
        await self.redis.set(full_key, count, expire=window_seconds)
        
        return True, count, reset_after
    
    async def check_rate_sliding_window(
        self, 
        key: str, 
        max_requests: int, 
        window_seconds: int
    ) -> Tuple[bool, int, float]:
        """滑动窗口速率限制检查
        
        使用Redis有序集合实现滑动窗口，更准确但消耗更多资源
        
        参数:
            key: str - 限流键（通常是用户ID或IP地址）
            max_requests: int - 窗口期内允许的最大请求数
            window_seconds: int - 窗口期长度（秒）
            
        返回:
            Tuple[bool, int, float]: 
                - 是否允许访问
                - 窗口内当前请求数
                - 最早请求距离移出窗口的剩余秒数
        """
        # 确保连接
        if not hasattr(self.redis, '_client') or self.redis._client is None:
            await self.redis.connect()
        
        # 构造键名
        rate_key = f"rate:sliding:{key}"
        
        # 获取当前时间戳（毫秒）
        current_time = time.time()
        window_start_time = current_time - window_seconds
        
        # 移除窗口外的请求
        await self.redis._client.zremrangebyscore(rate_key, 0, window_start_time)
        
        # 计算窗口内的请求数
        count = await self.redis._client.zcard(rate_key)
        
        # 检查是否超过限制
        if count >= max_requests:
            # 获取最早的请求时间，计算何时会有空位
            earliest = await self.redis._client.zrange(rate_key, 0, 0, withscores=True)
            if earliest:
                earliest_time = earliest[0][1]
                reset_after = earliest_time + window_seconds - current_time
            else:
                reset_after = 0
            return False, count, reset_after
        
        # 添加当前请求到集合
        await self.redis._client.zadd(rate_key, {str(current_time): current_time})
        
        # 设置过期时间
        await self.redis._client.expire(rate_key, window_seconds * 2)
        
        return True, count + 1, window_seconds
    
    async def is_action_allowed(
        self, 
        user_id: str, 
        action: str, 
        max_requests: int, 
        window_seconds: int,
        sliding: bool = True
    ) -> Tuple[bool, Dict[str, Any]]:
        """检查操作是否被允许
        
        高级API，整合了固定窗口和滑动窗口算法
        
        参数:
            user_id: str - 用户标识
            action: str - 操作类型
            max_requests: int - 窗口期内允许的最大请求数
            window_seconds: int - 窗口期长度（秒）
            sliding: bool - 是否使用滑动窗口算法
            
        返回:
            Tuple[bool, Dict[str, Any]]: 
                - 是否允许操作
                - 限流信息字典，包含限制详情
        """
        key = f"{user_id}:{action}"
        
        if sliding:
            allowed, count, reset_after = await self.check_rate_sliding_window(
                key, max_requests, window_seconds
            )
        else:
            allowed, count, reset_after = await self.check_rate_fixed_window(
                key, max_requests, window_seconds
            )
        
        # 构建响应信息
        rate_info = {
            "allowed": allowed,
            "current_count": count,
            "max_requests": max_requests,
            "window_seconds": window_seconds,
            "reset_after": reset_after,
            "algorithm": "sliding" if sliding else "fixed"
        }
        
        return allowed, rate_info
    
    async def close(self):
        """关闭Redis连接"""
        await self.redis.close()


# 全局实例
_rate_limiter = None

def get_rate_limiter() -> RedisRateLimiter:
    """获取速率限制器单例实例
    
    返回:
        RedisRateLimiter: 速率限制器实例
    """
    global _rate_limiter
    
    if _rate_limiter is None:
        settings = get_settings()
        redis_url = getattr(settings, "redis_url", None)
        redis_client = RedisClient(redis_url=redis_url)
        _rate_limiter = RedisRateLimiter(redis_client)
        
    return _rate_limiter


# 创建FastAPI依赖
async def rate_limit(
    user_id: str, 
    action: str = "default", 
    max_requests: int = 100, 
    window_seconds: int = 60,
    sliding: bool = True
) -> Dict[str, Any]:
    """
    FastAPI依赖项，用于API路由的速率限制
    
    用法:
    ```python
    @app.get("/api/resource")
    async def get_resource(
        rate_info: Dict[str, Any] = Depends(
            lambda: rate_limit(user_id="user123", action="get_resource", max_requests=5, window_seconds=60)
        )
    ):
        if not rate_info["allowed"]:
            raise HTTPException(status_code=429, detail="Too Many Requests")
        return {"data": "resource data"}
    ```
    
    参数:
        user_id: str - 用户标识
        action: str - 操作类型
        max_requests: int - 窗口期内允许的最大请求数
        window_seconds: int - 窗口期长度（秒）
        sliding: bool - 是否使用滑动窗口算法
        
    返回:
        Dict[str, Any]: 限流信息字典
    """
    limiter = get_rate_limiter()
    _, rate_info = await limiter.is_action_allowed(
        user_id, action, max_requests, window_seconds, sliding
    )
    return rate_info


# 使用示例
async def example():
    """速率限制器使用示例"""
    limiter = RedisRateLimiter()
    
    # 模拟处理请求
    for i in range(12):
        # 检查API请求限制
        allowed, info = await limiter.is_action_allowed(
            user_id="test_user", 
            action="api_call", 
            max_requests=10, 
            window_seconds=60
        )
        
        status = "允许" if allowed else "拒绝"
        logger.info(f"请求 {i+1}: {status}, 当前计数: {info['current_count']}/{info['max_requests']}")
        
        if not allowed:
            logger.info(f"超出限制! 请等待 {info['reset_after']:.2f}秒后重试")
        
        # 模拟请求间隔
        await asyncio.sleep(0.5)
    
    await limiter.close()


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 运行示例
    asyncio.run(example()) 