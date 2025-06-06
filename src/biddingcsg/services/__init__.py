"""
服务层模块

包含系统的各种服务，如LLM服务、爬虫服务、数据库服务等。
专注于解决实时状态更新和进程间通信问题。
"""

# 存储服务
from .storage import LocalStorageService
from .database_manager import DatabaseManager
from .database_storage import DatabaseStorageService

# 爬虫服务
from .crawler import BiddingCrawlerService

# 信息提取服务
from .info_extractor import InfoExtractor, create_info_extractor

# 暂时注释导入，等实现后再启用
# from .llm import LLMService
# from .status import StatusService
# from .messaging import MessageBus

__all__ = [
    # 存储服务
    "LocalStorageService",
    "DatabaseManager", 
    "DatabaseStorageService",
    
    # 爬虫服务
    "BiddingCrawlerService",
    
    # 信息提取服务
    "InfoExtractor",
    "create_info_extractor",
    
    # 未来的服务
    # "LLMService",
    # "StatusService",
    # "MessageBus"
] 