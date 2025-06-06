"""
招标公告爬虫包

第一阶段功能:
1. 数据下载：爬虫将网页内容下载成本地 HTML 文件，避免重复爬取
2. 配置UI：提供表单式的配置页，设置爬虫参数、输出目录
"""

__version__ = "1.0.0"
__author__ = "Assistant"
__description__ = "招标公告数据爬虫工具"

# 导出主要组件
from .models.config import CrawlerConfig, CrawlResult, CrawlSession
from .services.storage import LocalStorageService
from .services.crawler import BiddingCrawlerService
from .services.info_extractor import InfoExtractor, create_info_extractor
from .ui.components.model_selector import ModelSelector, get_model_selector
from .ui.pages.crawler_config import CrawlerConfigPage

# 版本信息
version_info = {
    'version': __version__,
    'author': __author__,
    'description': __description__,
    'stage': 'Phase 1 - Data Collection & UI',
    'features': [
        '网页内容下载到本地HTML文件',
        '智能去重避免重复爬取',
        '表单式配置界面',
        '实时日志显示',
        '进度跟踪',
        '本地文件存储管理'
    ]
}

def get_version_info():
    """获取版本信息"""
    return version_info

# 包级别的便捷函数
def create_default_config(search_keyword: str, output_dir: str = "./output") -> CrawlerConfig:
    """
    创建默认配置
    
    Args:
        search_keyword: 搜索关键词
        output_dir: 输出目录
        
    Returns:
        CrawlerConfig: 配置对象
    """
    return CrawlerConfig(
        search_keyword=search_keyword,
        output_directory=output_dir
    )

def run_crawler_from_config(config: CrawlerConfig) -> CrawlSession:
    """
    从配置运行爬虫
    
    Args:
        config: 爬虫配置
        
    Returns:
        CrawlSession: 爬取会话结果
    """
    storage = LocalStorageService(config)
    crawler = BiddingCrawlerService(config, storage)
    return crawler.start_crawling()

# 导出所有公共接口
__all__ = [
    # 数据模型
    'CrawlerConfig',
    'CrawlResult', 
    'CrawlSession',
    
    # 服务组件
    'LocalStorageService',
    'BiddingCrawlerService',
    'InfoExtractor',
    'create_info_extractor',
    
    # UI组件
    'LogViewer',
    'ProgressViewer',
    'ModelSelector',
    'get_model_selector',
    'CrawlerConfigPage',
    
    # 便捷函数
    'create_default_config',
    'run_crawler_from_config',
    'get_version_info'
] 