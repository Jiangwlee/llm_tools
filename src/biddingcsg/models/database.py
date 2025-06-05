"""
数据库模型定义

定义了所有数据库表的结构，包括：
- crawl_items: 爬虫抓取的原始数据
- llm_analysis: LLM分析结果
- llm_summaries: 内容摘要
- llm_sessions: 批处理会话
- analysis_errors: 分析错误记录
"""

import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import hashlib
import json


@dataclass
class SimpleConfig:
    """简单配置类，用于数据库相关操作"""
    output_dir: str = "output"


class CrawlStatus(Enum):
    """爬虫状态枚举"""
    PENDING = "pending"      # 待处理
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"        # 失败
    SKIPPED = "skipped"      # 跳过


class AnalysisStatus(Enum):
    """分析状态枚举"""
    PENDING = "pending"      # 待分析
    ANALYZING = "analyzing"  # 分析中
    COMPLETED = "completed"  # 分析完成
    FAILED = "failed"        # 分析失败
    PARTIAL = "partial"      # 部分完成


@dataclass
class CrawlItem:
    """爬虫数据项模型"""
    id: Optional[int] = None
    url: str = ""
    title: str = ""
    content_html: str = ""  # HTML内容直接存储
    content_md5: str = ""   # 内容MD5哈希
    metadata: str = "{}"    # JSON格式的元数据
    page_type: str = ""     # 页面类型（list/detail）
    crawl_timestamp: Optional[datetime] = None
    status: CrawlStatus = CrawlStatus.PENDING
    error_message: str = ""
    
    @property
    def metadata_dict(self) -> Dict[str, Any]:
        """获取元数据字典"""
        try:
            return json.loads(self.metadata) if self.metadata else {}
        except json.JSONDecodeError:
            return {}
    
    @metadata_dict.setter
    def metadata_dict(self, value: Dict[str, Any]):
        """设置元数据字典"""
        self.metadata = json.dumps(value, ensure_ascii=False)
    
    def calculate_content_md5(self) -> str:
        """计算内容MD5哈希"""
        if self.content_html:
            self.content_md5 = hashlib.md5(self.content_html.encode('utf-8')).hexdigest()
        return self.content_md5


@dataclass
class LLMAnalysis:
    """LLM分析结果模型"""
    id: Optional[int] = None
    crawl_item_id: int = 0
    
    # 项目基本信息
    project_name: str = ""
    project_code: str = ""
    tender_agency: str = ""
    budget_amount: str = ""
    
    # 时间信息
    announcement_date: str = ""
    registration_deadline: str = ""
    bid_deadline: str = ""
    opening_date: str = ""
    
    # 联系信息
    contact_person: str = ""
    contact_phone: str = ""
    contact_email: str = ""
    
    # 技术要求
    technical_requirements: str = ""
    qualification_requirements: str = ""
    
    # 其他信息
    document_fees: str = ""
    guarantee_amount: str = ""
    additional_info: str = ""
    
    # 分析元数据
    analysis_timestamp: Optional[datetime] = None
    llm_model: str = ""
    confidence_score: float = 0.0
    status: AnalysisStatus = AnalysisStatus.PENDING
    error_message: str = ""


@dataclass
class LLMSummary:
    """LLM摘要模型"""
    id: Optional[int] = None
    crawl_item_id: int = 0
    summary_text: str = ""
    key_points: str = ""     # JSON数组格式
    risk_assessment: str = ""
    recommendation: str = ""
    summary_timestamp: Optional[datetime] = None
    llm_model: str = ""
    status: AnalysisStatus = AnalysisStatus.PENDING
    
    @property
    def key_points_list(self) -> List[str]:
        """获取关键点列表"""
        try:
            return json.loads(self.key_points) if self.key_points else []
        except json.JSONDecodeError:
            return []
    
    @key_points_list.setter
    def key_points_list(self, value: List[str]):
        """设置关键点列表"""
        self.key_points = json.dumps(value, ensure_ascii=False)


@dataclass
class LLMSession:
    """LLM批处理会话模型"""
    id: Optional[int] = None
    session_name: str = ""
    description: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_items: int = 0
    processed_items: int = 0
    success_items: int = 0
    failed_items: int = 0
    llm_model: str = ""
    config_snapshot: str = "{}"  # JSON格式的配置快照
    status: AnalysisStatus = AnalysisStatus.PENDING
    
    @property
    def progress_percentage(self) -> float:
        """获取进度百分比"""
        if self.total_items == 0:
            return 0.0
        return (self.processed_items / self.total_items) * 100
    
    @property
    def success_rate(self) -> float:
        """获取成功率"""
        if self.processed_items == 0:
            return 0.0
        return (self.success_items / self.processed_items) * 100


@dataclass
class AnalysisError:
    """分析错误记录模型"""
    id: Optional[int] = None
    crawl_item_id: Optional[int] = None
    session_id: Optional[int] = None
    error_type: str = ""     # 错误类型
    error_message: str = ""  # 错误消息
    error_details: str = ""  # 详细错误信息（JSON格式）
    timestamp: Optional[datetime] = None
    retry_count: int = 0
    resolved: bool = False
    
    @property
    def error_details_dict(self) -> Dict[str, Any]:
        """获取错误详情字典"""
        try:
            return json.loads(self.error_details) if self.error_details else {}
        except json.JSONDecodeError:
            return {}
    
    @error_details_dict.setter
    def error_details_dict(self, value: Dict[str, Any]):
        """设置错误详情字典"""
        self.error_details = json.dumps(value, ensure_ascii=False)


# 数据库表结构定义
DATABASE_SCHEMA = {
    "crawl_items": """
        CREATE TABLE IF NOT EXISTS crawl_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL DEFAULT '',
            content_html TEXT NOT NULL DEFAULT '',
            content_md5 TEXT NOT NULL DEFAULT '',
            metadata TEXT NOT NULL DEFAULT '{}',
            page_type TEXT NOT NULL DEFAULT '',
            crawl_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL DEFAULT 'pending',
            error_message TEXT DEFAULT ''
        )
    """,
    
    "llm_analysis": """
        CREATE TABLE IF NOT EXISTS llm_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            crawl_item_id INTEGER NOT NULL,
            
            -- 项目基本信息
            project_name TEXT DEFAULT '',
            project_code TEXT DEFAULT '',
            tender_agency TEXT DEFAULT '',
            budget_amount TEXT DEFAULT '',
            
            -- 时间信息
            announcement_date TEXT DEFAULT '',
            registration_deadline TEXT DEFAULT '',
            bid_deadline TEXT DEFAULT '',
            opening_date TEXT DEFAULT '',
            
            -- 联系信息
            contact_person TEXT DEFAULT '',
            contact_phone TEXT DEFAULT '',
            contact_email TEXT DEFAULT '',
            
            -- 技术要求
            technical_requirements TEXT DEFAULT '',
            qualification_requirements TEXT DEFAULT '',
            
            -- 其他信息
            document_fees TEXT DEFAULT '',
            guarantee_amount TEXT DEFAULT '',
            additional_info TEXT DEFAULT '',
            
            -- 分析元数据
            analysis_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            llm_model TEXT DEFAULT '',
            confidence_score REAL DEFAULT 0.0,
            status TEXT NOT NULL DEFAULT 'pending',
            error_message TEXT DEFAULT '',
            
            -- 外键
            FOREIGN KEY (crawl_item_id) REFERENCES crawl_items (id) ON DELETE CASCADE
        )
    """,
    
    "llm_summaries": """
        CREATE TABLE IF NOT EXISTS llm_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            crawl_item_id INTEGER NOT NULL UNIQUE,
            summary_text TEXT DEFAULT '',
            key_points TEXT DEFAULT '[]',
            risk_assessment TEXT DEFAULT '',
            recommendation TEXT DEFAULT '',
            summary_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            llm_model TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',
            
            -- 外键
            FOREIGN KEY (crawl_item_id) REFERENCES crawl_items (id) ON DELETE CASCADE
        )
    """,
    
    "llm_sessions": """
        CREATE TABLE IF NOT EXISTS llm_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_name TEXT NOT NULL,
            description TEXT DEFAULT '',
            start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            end_time DATETIME DEFAULT NULL,
            total_items INTEGER DEFAULT 0,
            processed_items INTEGER DEFAULT 0,
            success_items INTEGER DEFAULT 0,
            failed_items INTEGER DEFAULT 0,
            llm_model TEXT DEFAULT '',
            config_snapshot TEXT DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'pending'
        )
    """,
    
    "analysis_errors": """
        CREATE TABLE IF NOT EXISTS analysis_errors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            crawl_item_id INTEGER DEFAULT NULL,
            session_id INTEGER DEFAULT NULL,
            error_type TEXT NOT NULL DEFAULT '',
            error_message TEXT NOT NULL DEFAULT '',
            error_details TEXT DEFAULT '{}',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            retry_count INTEGER DEFAULT 0,
            resolved BOOLEAN DEFAULT FALSE,
            
            -- 外键
            FOREIGN KEY (crawl_item_id) REFERENCES crawl_items (id) ON DELETE SET NULL,
            FOREIGN KEY (session_id) REFERENCES llm_sessions (id) ON DELETE SET NULL
        )
    """
} 