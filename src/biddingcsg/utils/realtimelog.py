"""
实时日志工具模块

提供实时日志的读写功能
"""

from ..config.paths import BiddingPaths


def add_realtime_log(message: str, base_path: str = None):
    """
    添加实时日志.

    将 message 追加到 BiddingPaths.get_logs_dir() 目录下的 realtime.log 文件中。
    
    Args:
        message: 要写入的日志消息
        base_path: 基础路径，如果不提供则使用默认路径
    """
    if base_path:
        log_file = BiddingPaths.get_logs_dir(base_path) / "realtime.log"
    else:
        log_file = BiddingPaths.get_logs_dir() / "realtime.log"
    
    # 确保日志目录存在
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(message)


def clear_realtime_log(base_path: str = None):
    """
    清空实时日志.

    将 BiddingPaths.get_logs_dir() 目录下的 realtime.log 文件清空。
    
    Args:
        base_path: 基础路径，如果不提供则使用默认路径
    """
    if base_path:
        log_file = BiddingPaths.get_logs_dir(base_path) / "realtime.log"
    else:
        log_file = BiddingPaths.get_logs_dir() / "realtime.log"
    
    # 确保日志目录存在
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(log_file, "w", encoding="utf-8") as f:
        f.write("")


def get_realtime_log(base_path: str = None) -> str:
    """
    读取实时日志内容.
    
    Args:
        base_path: 基础路径，如果不提供则使用默认路径
        
    Returns:
        日志文件的内容，如果文件不存在则返回空字符串
    """
    if base_path:
        log_file = BiddingPaths.get_logs_dir(base_path) / "realtime.log"
    else:
        log_file = BiddingPaths.get_logs_dir() / "realtime.log"
    
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "" 