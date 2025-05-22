"""
智能体通信模块

提供智能体之间的通信机制
"""

from app.agents.communication.command import EnhancedCommand, CommandFactory
from app.agents.communication.message_bus import MessageBus, Subscription

# 避免循环导入问题，将CommandProcessor的导入延后
__all__ = [
    'EnhancedCommand',
    'CommandFactory',
    'MessageBus',
    'Subscription',
    'CommandProcessor'
]

# 将CommandProcessor放在最后导入，减少循环导入的可能性
from app.agents.communication.processor import CommandProcessor
