"""
数据模型模块

定义系统中使用的所有数据模型和实体类。
"""

# 配置模型
from .config import CrawlerConfig

# 数据库模型
from .database import (
    CrawlItem, LLMAnalysis, LLMSummary, LLMSession, AnalysisError,
    CrawlStatus, AnalysisStatus, DATABASE_SCHEMA, DATABASE_INDEXES
)

# 暂时注释导入，等实现后再启用
# from .bidding import BiddingNotice, BiddingResult
# from .status import StatusUpdate, ProcessStatus

__all__ = [
    # 配置模型
    "CrawlerConfig",
    
    # 数据库模型
    "CrawlItem", "LLMAnalysis", "LLMSummary", "LLMSession", "AnalysisError",
    "CrawlStatus", "AnalysisStatus", "DATABASE_SCHEMA", "DATABASE_INDEXES",
    
    # 未来的模型
    # "BiddingNotice",
    # "BiddingResult", 
    # "StatusUpdate",
    # "ProcessStatus",
] 