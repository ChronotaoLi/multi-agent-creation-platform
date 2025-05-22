"""
重试机制实现模块

该模块基于tenacity库实现了指数退避重试装饰器，用于处理可能失败的操作。
"""
from functools import wraps
from typing import Callable, Type, Tuple, TypeVar, Optional, Any, Union, cast

from tenacity import (
    retry as tenacity_retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryError,
)

# 定义泛型类型变量
T = TypeVar('T')


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 10.0,
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    基于tenacity的指数退避重试装饰器
    
    参数:
        max_retries: 最大重试次数
        base_delay: 基础延迟时间(秒)
        max_delay: 最大延迟时间(秒)
        exceptions: 需要捕获的异常类型或异常类型元组
        
    返回值:
        装饰器函数
    
    示例:
        @retry_with_backoff(max_retries=5, base_delay=1, max_delay=30)
        def call_external_service():
            # 可能失败的操作
            pass
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                retry_decorator = tenacity_retry(
                    stop=stop_after_attempt(max_retries),
                    wait=wait_exponential(multiplier=base_delay, min=base_delay, max=max_delay),
                    retry=retry_if_exception_type(exceptions),
                    reraise=True,
                )
                return retry_decorator(func)(*args, **kwargs)
            except RetryError as e:
                # 重试失败后，抛出原始异常
                if e.last_attempt.failed:
                    raise e.last_attempt.exception()
                raise
        return cast(Callable[..., T], wrapper)
    return decorator


async def async_retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 10.0,
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = (Exception,),
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    异步版本的指数退避重试装饰器
    
    参数:
        max_retries: 最大重试次数
        base_delay: 基础延迟时间(秒)
        max_delay: 最大延迟时间(秒)
        exceptions: 需要捕获的异常类型或异常类型元组
        
    返回值:
        异步装饰器函数
    
    示例:
        @async_retry_with_backoff(max_retries=5, base_delay=1, max_delay=30)
        async def call_external_service():
            # 可能失败的异步操作
            pass
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                retry_decorator = tenacity_retry(
                    stop=stop_after_attempt(max_retries),
                    wait=wait_exponential(multiplier=base_delay, min=base_delay, max=max_delay),
                    retry=retry_if_exception_type(exceptions),
                    reraise=True,
                )
                
                # 如果函数是异步的，我们需要await结果
                result = retry_decorator(func)(*args, **kwargs)
                if hasattr(result, "__await__"):
                    return await result
                return result
            except RetryError as e:
                # 重试失败后，抛出原始异常
                if e.last_attempt.failed:
                    raise e.last_attempt.exception()
                raise
        return wrapper
    return decorator 