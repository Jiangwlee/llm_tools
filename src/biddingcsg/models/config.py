from dataclasses import dataclass, field
from datetime import datetime, date
from pathlib import Path
from typing import Optional, List
import os

@dataclass
class CrawlerConfig:
    """爬虫配置数据模型"""
    
    # 基本搜索参数
    search_keyword: str = ""
    max_pages: int = 10
    announcement_type: str = "服务"  # 服务/招标公告/公示公告
    earliest_date: Optional[str] = None  # YYYY-MM-DD格式，None表示不限制
    
    # 输出配置
    output_directory: str = "./output/bidding_data"
    
    # 高级参数
    request_delay: float = 2.0  # 请求间隔（秒）
    enable_dedup: bool = True   # 启用去重
    save_metadata: bool = True  # 保存元数据
    save_raw_html: bool = True  # 保存原始HTML
    
    # 浏览器配置
    headless_mode: bool = True  # 无头模式
    timeout: int = 30  # 页面加载超时（秒）
    
    def __post_init__(self):
        """配置验证和规范化"""
        # 验证搜索关键词
        if not self.search_keyword.strip():
            raise ValueError("搜索关键词不能为空")
        
        # 验证最大页数
        if self.max_pages <= 0:
            raise ValueError("最大页数必须大于0")
        
        # 验证日期格式
        if self.earliest_date:
            try:
                datetime.strptime(self.earliest_date, "%Y-%m-%d")
            except ValueError:
                raise ValueError("最早日期格式必须是 YYYY-MM-DD")
        
        # 创建输出目录
        Path(self.output_directory).mkdir(parents=True, exist_ok=True)
    
    @property
    def formatted_earliest_date(self) -> Optional[str]:
        """获取格式化的最早日期"""
        return self.earliest_date
    
    @property
    def html_output_dir(self) -> Path:
        """HTML文件输出目录"""
        return Path(self.output_directory) / "raw_html"
    
    @property
    def metadata_output_dir(self) -> Path:
        """元数据输出目录"""
        return Path(self.output_directory) / "metadata"
    
    @property
    def logs_output_dir(self) -> Path:
        """日志输出目录"""
        return Path(self.output_directory) / "logs"
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "search_keyword": self.search_keyword,
            "max_pages": self.max_pages,
            "announcement_type": self.announcement_type,
            "earliest_date": self.earliest_date,
            "output_directory": self.output_directory,
            "request_delay": self.request_delay,
            "enable_dedup": self.enable_dedup,
            "save_metadata": self.save_metadata,
            "save_raw_html": self.save_raw_html,
            "headless_mode": self.headless_mode,
            "timeout": self.timeout
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'CrawlerConfig':
        """从字典创建配置对象"""
        return cls(**data)

@dataclass
class CrawlResult:
    """爬取结果数据模型"""
    
    url: str
    title: str
    content: str
    date: str
    announcement_type: str
    company: str
    project_name: str
    
    # 文件路径信息
    html_file_path: Optional[str] = None
    metadata_file_path: Optional[str] = None
    
    # 时间戳
    crawl_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "date": self.date,
            "announcement_type": self.announcement_type,
            "company": self.company,
            "project_name": self.project_name,
            "html_file_path": self.html_file_path,
            "metadata_file_path": self.metadata_file_path,
            "crawl_timestamp": self.crawl_timestamp
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'CrawlResult':
        """从字典创建结果对象"""
        return cls(**data)

@dataclass 
class CrawlSession:
    """爬取会话信息"""
    
    session_id: str
    config: CrawlerConfig
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    end_time: Optional[str] = None
    status: str = "running"  # running, completed, failed
    total_pages_crawled: int = 0
    total_items_found: int = 0
    results: List[CrawlResult] = field(default_factory=list)
    error_message: Optional[str] = None
    
    def mark_completed(self):
        """标记为完成状态"""
        self.status = "completed"
        self.end_time = datetime.now().isoformat()
    
    def mark_failed(self, error_message: str):
        """标记为失败状态"""
        self.status = "failed"
        self.end_time = datetime.now().isoformat()
        self.error_message = error_message
    
    def add_result(self, result: CrawlResult):
        """添加爬取结果"""
        self.results.append(result)
        self.total_items_found = len(self.results)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "config": self.config.to_dict(),
            "start_time": self.start_time,
            "end_time": self.end_time,
            "status": self.status,
            "total_pages_crawled": self.total_pages_crawled,
            "total_items_found": self.total_items_found,
            "results": [result.to_dict() for result in self.results],
            "error_message": self.error_message
        } 