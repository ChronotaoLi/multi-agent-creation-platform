"""
熔断器模式实现模块

该模块基于pybreaker库实现了熔断器模式，用于防止雪崩效应。
"""
import logging
import time
from enum import Enum
from typing import Callable, Any, Optional, Union, List, Type, Tuple, Dict

import pybreaker

logger = logging.getLogger(__name__)


class CircuitBreakerState(str, Enum):
    """熔断器状态枚举"""
    CLOSED = "closed"  # 关闭状态，允许请求通过
    OPEN = "open"      # 开启状态，阻止请求通过
    HALF_OPEN = "half-open"  # 半开状态，允许部分请求通过以测试服务是否恢复


class CircuitBreakerListener(pybreaker.CircuitBreakerListener):
    """熔断器监听器，用于记录熔断器状态变化"""
    
    def __init__(self, logger_instance: Optional[logging.Logger] = None):
        """
        初始化熔断器监听器
        
        参数:
            logger_instance: 日志记录器实例，如果为None则使用模块级别的logger
        """
        self._logger = logger_instance or logger
    
    def before_call(self, cb: pybreaker.CircuitBreaker, func: Callable, *args: Any, **kwargs: Any) -> None:
        """
        在调用受保护函数前被调用
        
        参数:
            cb: 熔断器实例
            func: 被调用的函数
            args: 位置参数
            kwargs: 关键字参数
        """
        self._logger.debug(f"Circuit {cb.name}: Calling {func.__name__}")
    
    def state_change(self, cb: pybreaker.CircuitBreaker, old_state: str, new_state: str) -> None:
        """
        当熔断器状态变化时被调用
        
        参数:
            cb: 熔断器实例
            old_state: 旧状态
            new_state: 新状态
        """
        self._logger.warning(f"Circuit {cb.name}: State changed from {old_state} to {new_state}")
    
    def failure(self, cb: pybreaker.CircuitBreaker, exc: Exception) -> None:
        """
        当函数调用失败时被调用
        
        参数:
            cb: 熔断器实例
            exc: 异常
        """
        self._logger.error(f"Circuit {cb.name}: Call failed with exception: {exc}")
    
    def success(self, cb: pybreaker.CircuitBreaker) -> None:
        """
        当函数调用成功时被调用
        
        参数:
            cb: 熔断器实例
        """
        self._logger.debug(f"Circuit {cb.name}: Call succeeded")


class CircuitBreaker:
    """
    熔断器类，用于防止雪崩效应
    
    通过包装可能失败的操作，在服务不可用时快速失败，避免资源浪费和连锁故障。
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        exception_types: Union[Type[Exception], Tuple[Type[Exception], ...]] = (Exception,),
        excluded_exceptions: Optional[List[Union[Type[Exception], Callable[[Exception], bool]]]] = None,
        listeners: Optional[List[pybreaker.CircuitBreakerListener]] = None,
    ):
        """
        初始化熔断器
        
        参数:
            name: 熔断器名称
            failure_threshold: 触发熔断的连续失败次数
            recovery_timeout: 从开启状态到半开状态的恢复时间(秒)
            exception_types: 计入失败的异常类型
            excluded_exceptions: 不计入失败的异常类型或判断函数列表
            listeners: 熔断器监听器列表
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.exception_types = exception_types
        
        # 创建默认监听器
        if listeners is None:
            listeners = [CircuitBreakerListener()]
        
        # 创建pybreaker实例
        self._breaker = pybreaker.CircuitBreaker(
            fail_max=failure_threshold,
            reset_timeout=recovery_timeout,
            exclude=excluded_exceptions or [],
            listeners=listeners,
            name=name,
        )
        
        self._last_failure_time: Optional[float] = None
    
    @property
    def state(self) -> CircuitBreakerState:
        """获取当前熔断器状态"""
        return CircuitBreakerState(self._breaker.current_state)
    
    @property
    def failure_count(self) -> int:
        """获取当前连续失败次数"""
        return self._breaker.fail_counter
    
    @property
    def last_failure_time(self) -> Optional[float]:
        """获取最后一次失败时间"""
        return self._last_failure_time
    
    def execute(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """
        执行函数，应用熔断逻辑
        
        参数:
            func: 要执行的函数
            args: 位置参数
            kwargs: 关键字参数
            
        返回值:
            函数执行结果
            
        异常:
            CircuitBreakerError: 熔断器开启时抛出
        """
        try:
            return self._breaker.call(func, *args, **kwargs)
        except Exception as e:
            if not isinstance(e, pybreaker.CircuitBreakerError):
                self._last_failure_time = time.time()
            raise
    
    async def async_execute(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """
        异步执行函数，应用熔断逻辑
        
        参数:
            func: 要执行的异步函数
            args: 位置参数
            kwargs: 关键字参数
            
        返回值:
            函数执行结果
            
        异常:
            CircuitBreakerError: 熔断器开启时抛出
        """
        try:
            # 对于异步函数，我们需要使用特殊参数
            if kwargs.get("__pybreaker_call_async", False):
                kwargs.pop("__pybreaker_call_async")
                return await self._breaker(func, __pybreaker_call_async=True)(*args, **kwargs)
            else:
                result = self._breaker.call(func, *args, **kwargs)
                if hasattr(result, "__await__"):
                    return await result
                return result
        except Exception as e:
            if not isinstance(e, pybreaker.CircuitBreakerError):
                self._last_failure_time = time.time()
            raise
    
    def reset(self) -> None:
        """重置熔断器状态为关闭"""
        self._breaker.close()
        self._last_failure_time = None
    
    def force_open(self) -> None:
        """强制熔断器进入开启状态"""
        self._breaker.open()
        self._last_failure_time = time.time()
    
    def force_half_open(self) -> None:
        """强制熔断器进入半开状态"""
        self._breaker.half_open()


class CircuitBreakerRegistry:
    """
    熔断器注册表，用于管理多个熔断器实例
    """
    
    def __init__(self):
        """初始化熔断器注册表"""
        self._breakers: Dict[str, CircuitBreaker] = {}
    
    def get_or_create(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        exception_types: Union[Type[Exception], Tuple[Type[Exception], ...]] = (Exception,),
        excluded_exceptions: Optional[List[Union[Type[Exception], Callable[[Exception], bool]]]] = None,
        listeners: Optional[List[pybreaker.CircuitBreakerListener]] = None,
    ) -> CircuitBreaker:
        """
        获取或创建熔断器
        
        如果指定名称的熔断器不存在，则创建一个新的熔断器。
        
        参数:
            name: 熔断器名称
            failure_threshold: 触发熔断的连续失败次数
            recovery_timeout: 从开启状态到半开状态的恢复时间(秒)
            exception_types: 计入失败的异常类型
            excluded_exceptions: 不计入失败的异常类型或判断函数列表
            listeners: 熔断器监听器列表
            
        返回值:
            熔断器实例
        """
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                exception_types=exception_types,
                excluded_exceptions=excluded_exceptions,
                listeners=listeners,
            )
        return self._breakers[name]
    
    def get(self, name: str) -> Optional[CircuitBreaker]:
        """
        获取熔断器
        
        参数:
            name: 熔断器名称
            
        返回值:
            熔断器实例，如果不存在则返回None
        """
        return self._breakers.get(name)
    
    def all(self) -> Dict[str, CircuitBreaker]:
        """
        获取所有熔断器
        
        返回值:
            熔断器字典，键为熔断器名称，值为熔断器实例
        """
        return self._breakers.copy()
    
    def reset_all(self) -> None:
        """重置所有熔断器状态"""
        for breaker in self._breakers.values():
            breaker.reset()


# 全局熔断器注册表实例
circuit_breaker_registry = CircuitBreakerRegistry() 