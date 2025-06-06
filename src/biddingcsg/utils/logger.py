import os
import logging
import sys
from pathlib import Path

def get_logger(module: str = "") -> logging.Logger:
    """
    获取日志记录器
    
    Args:
        module: 模块名称
        
    Returns:
        配置好的日志记录器
    """
    logger_name = f'biddingcsg.{module}' if module else 'biddingcsg'
    logger = logging.getLogger(logger_name)
    
    # 避免重复添加handler
    if logger.handlers:
        return logger
    
    # 设置日志级别
    logger.setLevel(logging.INFO)
    
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器（可选）
    try:
        # 创建日志目录
        log_dir = Path.home() / ".biddingcsg" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # 文件处理器
        file_handler = logging.FileHandler(
            log_dir / "biddingcsg.log",
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
    except Exception as e:
        # 如果文件日志失败，只使用控制台日志
        logger.warning(f"无法创建文件日志处理器: {e}")
    
    # 防止日志向上传播
    logger.propagate = False
    
    return logger

# 默认logger实例
logger = get_logger()