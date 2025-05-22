"""
Redis客户端使用示例模块

展示如何使用RedisClient进行分布式锁、有序集合和发布/订阅等操作。
"""
import asyncio
import logging
from typing import Dict, Any

from app.data_access.cache.redis_client import RedisClient

logger = logging.getLogger(__name__)

async def distributed_lock_example():
    """
    分布式锁使用示例
    
    演示如何使用Redis分布式锁保护并发资源
    """
    # 创建Redis客户端
    client = RedisClient()
    
    # 方式一：手动获取和释放锁
    lock_id = await client.acquire_lock("my_resource", timeout=30, wait_timeout=5)
    if lock_id:
        try:
            # 临界区代码 - 访问共享资源
            logger.info("获取到锁，处理共享资源")
            await asyncio.sleep(1)  # 模拟处理
        finally:
            # 释放锁
            await client.release_lock("my_resource", lock_id)
            logger.info("释放锁")
    else:
        logger.warning("无法获取锁，资源可能正在被其他进程使用")
    
    # 方式二：使用上下文管理器（更简洁优雅）
    try:
        async with client.lock("my_resource", timeout=30):
            logger.info("通过上下文管理器获取到锁，处理共享资源")
            await asyncio.sleep(1)  # 模拟处理
    except TimeoutError:
        logger.warning("无法获取锁，超时")
    
    await client.close()


async def sorted_set_example():
    """
    有序集合使用示例
    
    演示如何使用Redis的有序集合实现排行榜功能
    """
    # 创建Redis客户端
    client = RedisClient()
    
    # 创建排行榜
    leaderboard_key = "game:leaderboard"
    
    # 添加分数
    users = {
        "user1": 100,
        "user2": 85,
        "user3": 95,
        "user4": 120
    }
    await client.zadd(leaderboard_key, users)
    logger.info("添加用户分数到排行榜")
    
    # 获取前3名
    top_users = await client.zrange(leaderboard_key, 0, 2, withscores=True)
    logger.info(f"排行榜前3名: {top_users}")
    
    # 获取90分以上的用户
    high_score_users = await client.zrangebyscore(leaderboard_key, 90, float('inf'), withscores=True)
    logger.info(f"90分以上的用户: {high_score_users}")
    
    # 删除用户
    await client.zrem(leaderboard_key, "user2")
    logger.info("从排行榜中移除user2")
    
    # 获取更新后的排行榜
    updated_leaderboard = await client.zrange(leaderboard_key, 0, -1, withscores=True)
    logger.info(f"更新后的排行榜: {updated_leaderboard}")
    
    await client.close()


async def pubsub_example():
    """
    发布/订阅使用示例
    
    演示如何使用Redis的发布/订阅功能进行消息通信
    """
    # 创建Redis客户端
    publisher = RedisClient()
    subscriber = RedisClient()
    
    # 消息处理回调
    async def message_handler(channel: str, message: Any):
        logger.info(f"收到来自频道 {channel} 的消息: {message}")
    
    # 启动订阅任务
    async def subscribe_task():
        # 订阅频道
        pubsub = await subscriber.subscribe("news", "alerts")
        # 监听消息
        await subscriber.listen_channel(pubsub, message_handler)
    
    # 启动任务但不等待完成
    task = asyncio.create_task(subscribe_task())
    
    # 稍等一下确保订阅已设置
    await asyncio.sleep(1)
    
    # 发布消息
    await publisher.publish("news", "这是一条新闻")
    await publisher.publish("alerts", "这是一个警报")
    await publisher.publish("news", {"title": "复杂消息", "content": "这是一个JSON消息"})
    
    # 等待一会儿以便看到消息处理
    await asyncio.sleep(2)
    
    # 取消订阅任务
    task.cancel()
    
    # 清理
    await publisher.close()
    await subscriber.close()


async def combined_example():
    """
    综合示例
    
    演示Redis在多智能体创作平台中的应用场景
    """
    client = RedisClient()
    
    # 1. 使用有序集合跟踪智能体任务优先级
    task_queue = "agents:task_queue"
    tasks = {
        "task:1001": 10,  # 高优先级
        "task:1002": 5,   # 中优先级
        "task:1003": 8,   # 中高优先级
    }
    await client.zadd(task_queue, tasks)
    
    # 2. 使用分布式锁确保只有一个服务能处理特定任务
    async def process_highest_priority_task():
        # 获取优先级最高的任务
        highest_tasks = await client.zrange(task_queue, -1, -1)
        if not highest_tasks:
            return "没有待处理任务"
            
        task_id = highest_tasks[0]
        
        # 使用分布式锁确保只有一个进程处理该任务
        async with client.lock(f"lock:{task_id}", timeout=30):
            # 处理任务
            logger.info(f"处理任务 {task_id}")
            await asyncio.sleep(1)  # 模拟处理
            
            # 从队列中移除任务
            await client.zrem(task_queue, task_id)
            
            # 将结果发布到相关频道
            await client.publish("tasks:completed", {
                "task_id": task_id,
                "status": "completed",
                "result": "任务完成结果"
            })
            
            return f"成功处理任务 {task_id}"
    
    result = await process_highest_priority_task()
    logger.info(result)
    
    # 查看剩余任务
    remaining_tasks = await client.zrange(task_queue, 0, -1, withscores=True)
    logger.info(f"剩余任务: {remaining_tasks}")
    
    await client.close()


async def main():
    """主函数"""
    logger.info("==== 分布式锁示例 ====")
    await distributed_lock_example()
    
    logger.info("\n==== 有序集合示例 ====")
    await sorted_set_example()
    
    logger.info("\n==== 发布/订阅示例 ====")
    await pubsub_example()
    
    logger.info("\n==== 综合应用示例 ====")
    await combined_example()


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 运行主函数
    asyncio.run(main()) 