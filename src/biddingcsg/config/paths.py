"""
路径配置模块

定义项目中使用的全局路径常量
"""

from pathlib import Path

# 默认基础路径
DEFAULT_BASE_PATH = "output/"

# 主要数据目录
BIDDING_DATA_DIR = "bidding_data"

# 子目录定义
RAW_HTML_DIR = "raw_html"
PRICE_DIR = "price"
STATS_DIR = "stats"
METADATA_DIR = "metadata"
CACHE_DIR = "cache"
LOGS_DIR = "logs"

# 完整路径常量
class BiddingPaths:
    """投标数据路径管理"""
    
    @staticmethod
    def get_data_dir(base_path: str = DEFAULT_BASE_PATH) -> Path:
        """获取主数据目录"""
        return Path(base_path) / BIDDING_DATA_DIR
    
    @staticmethod
    def get_raw_html_dir(base_path: str = DEFAULT_BASE_PATH) -> Path:
        """获取原始HTML文件目录"""
        return Path(base_path) / BIDDING_DATA_DIR / RAW_HTML_DIR
    
    @staticmethod
    def get_price_dir(base_path: str = DEFAULT_BASE_PATH) -> Path:
        """获取价格提取结果目录"""
        return Path(base_path) / BIDDING_DATA_DIR / PRICE_DIR
    
    @staticmethod
    def get_stats_dir(base_path: str = DEFAULT_BASE_PATH) -> Path:
        """获取统计数据目录"""
        return Path(base_path) / BIDDING_DATA_DIR / STATS_DIR
    
    @staticmethod
    def get_metadata_dir(base_path: str = DEFAULT_BASE_PATH) -> Path:
        """获取元数据目录"""
        return Path(base_path) / BIDDING_DATA_DIR / METADATA_DIR
    
    @staticmethod
    def get_cache_dir(base_path: str = DEFAULT_BASE_PATH) -> Path:
        """获取缓存目录"""
        return Path(base_path) / BIDDING_DATA_DIR / CACHE_DIR
    
    @staticmethod
    def get_logs_dir(base_path: str = DEFAULT_BASE_PATH) -> Path:
        """获取日志目录"""
        return Path(base_path) / BIDDING_DATA_DIR / LOGS_DIR
    
    @staticmethod
    def ensure_directories(base_path: str = DEFAULT_BASE_PATH) -> None:
        """确保所有必要目录存在"""
        directories = [
            BiddingPaths.get_data_dir(base_path),
            BiddingPaths.get_raw_html_dir(base_path),
            BiddingPaths.get_price_dir(base_path),
            BiddingPaths.get_stats_dir(base_path),
            BiddingPaths.get_metadata_dir(base_path),
            BiddingPaths.get_cache_dir(base_path),
            BiddingPaths.get_logs_dir(base_path)
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

# 文件命名模式
class FilePatterns:
    """文件命名模式"""
    
    # 价格提取文件
    PRICE_EXTRACTION_BATCH = "price_extraction_{keyword}_{timestamp}.json"
    PRICE_EXTRACTION_TEST = "price_extraction_test_{keyword}_{timestamp}.json"
    PRICE_EXTRACTION_GLOB = "price_extraction_*.json"
    
    # HTML文件
    HTML_ANNOUNCEMENT = "公示公告*.html"
    
    # 统计文件
    STATS_SUMMARY = "stats_summary_{timestamp}.json"
    
    # 元数据文件
    METADATA_INDEX = "file_index_{timestamp}.json"
    METADATA_TASK = "task_metadata_{task_id}.json"
    METADATA_MAPPING = "file_mapping_{keyword}.json"
    METADATA_HISTORY = "processing_history_{timestamp}.json"
    
    # 日志文件
    LOG_CRAWLER = "crawler_{timestamp}.log"
    LOG_EXTRACTION = "extraction_{timestamp}.log"

# 文件大小常量
class FileSizes:
    """文件大小相关常量"""
    
    KB = 1024
    MB = 1024 * 1024
    GB = 1024 * 1024 * 1024
    
    # 显示阈值
    SIZE_DISPLAY_MB_THRESHOLD = 1.0  # 大于1MB显示MB
    SIZE_DISPLAY_KB_THRESHOLD = 1.0  # 大于1KB显示KB 