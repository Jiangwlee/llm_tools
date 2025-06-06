"""
工具模块包

提供各种实用工具函数
"""

from .realtimelog import add_realtime_log, clear_realtime_log, get_realtime_log

__all__ = [
    'add_realtime_log',
    'clear_realtime_log', 
    'get_realtime_log'
] 