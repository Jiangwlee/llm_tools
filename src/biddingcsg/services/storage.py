import json
import hashlib
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse
import logging

from ..models.config import CrawlerConfig, CrawlResult, CrawlSession

logger = logging.getLogger(__name__)

class LocalStorageService:
    """本地存储服务"""
    
    def __init__(self, config: CrawlerConfig):
        """
        初始化存储服务
        
        Args:
            config: 爬虫配置对象
        """
        self.config = config
        self.base_dir = Path(config.output_directory)
        
        # 设置目录路径
        self.html_dir = config.html_output_dir
        self.metadata_dir = config.metadata_output_dir
        self.logs_dir = config.logs_output_dir
        
        # 爬取记录文件
        self.crawl_records_file = self.metadata_dir / "crawl_records.json"
        self.session_file = self.metadata_dir / "sessions.json"
        
        # 内存中的去重集合
        self.crawled_urls: Set[str] = set()
        
        # 初始化目录和加载历史记录
        self.setup_directories()
        self.load_crawl_records()
    
    def setup_directories(self):
        """创建输出目录结构"""
        directories = [
            self.html_dir,
            self.metadata_dir,
            self.logs_dir,
            self.html_dir / datetime.now().strftime("%Y-%m-%d")  # 按日期分目录
        ]
        
        for dir_path in directories:
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"创建目录: {dir_path}")
    
    def load_crawl_records(self):
        """加载历史爬取记录"""
        if self.crawl_records_file.exists():
            try:
                with open(self.crawl_records_file, 'r', encoding='utf-8') as f:
                    records = json.load(f)
                    self.crawled_urls = set(records.get('crawled_urls', []))
                logger.info(f"加载了 {len(self.crawled_urls)} 条历史爬取记录")
            except Exception as e:
                logger.warning(f"加载爬取记录失败: {e}")
                self.crawled_urls = set()
        else:
            logger.info("未找到历史爬取记录，从空开始")
    
    def save_crawl_records(self):
        """保存爬取记录到文件"""
        try:
            records = {
                'crawled_urls': list(self.crawled_urls),
                'last_updated': datetime.now().isoformat()
            }
            with open(self.crawl_records_file, 'w', encoding='utf-8') as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
            logger.info(f"保存了 {len(self.crawled_urls)} 条爬取记录")
        except Exception as e:
            logger.error(f"保存爬取记录失败: {e}")
    
    def check_duplicate(self, url: str) -> bool:
        """
        检查URL是否已爬取
        
        Args:
            url: 要检查的URL
            
        Returns:
            bool: True表示已爬取（重复），False表示未爬取
        """
        if not self.config.enable_dedup:
            return False
        
        return url in self.crawled_urls
    
    def generate_filename(self, url: str, metadata: Dict) -> str:
        """
        生成文件名
        
        Args:
            url: 网页URL
            metadata: 元数据字典
            
        Returns:
            str: 生成的文件名
        """
        # 解析域名
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.replace('www.', '').replace('.', '_')
        
        # 生成URL哈希（用于去重和唯一标识）
        url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()[:8]
        
        # 时间戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 项目名称（如果有）
        project_name = metadata.get('project_name', '').replace(' ', '_')[:20]
        if project_name:
            project_name = f"_{project_name}"
        
        filename = f"{domain}_{timestamp}_{url_hash}{project_name}.html"
        return filename
    
    def save_html_content(self, url: str, content: str, metadata: Dict) -> CrawlResult:
        """
        保存HTML内容和元数据
        
        Args:
            url: 网页URL
            content: HTML内容
            metadata: 元数据字典
            
        Returns:
            CrawlResult: 爬取结果对象
        """
        try:
            # 检查重复
            if self.check_duplicate(url):
                logger.info(f"URL已存在，跳过保存: {url}")
                return None
            
            # 生成文件名
            filename = self.generate_filename(url, metadata)
            
            # 按日期分目录保存
            date_dir = self.html_dir / datetime.now().strftime("%Y-%m-%d")
            date_dir.mkdir(exist_ok=True)
            
            html_file_path = date_dir / filename
            
            # 保存HTML文件
            if self.config.save_raw_html:
                with open(html_file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"保存HTML文件: {html_file_path}")
            
            # 保存元数据
            metadata_file_path = None
            if self.config.save_metadata:
                metadata_file_path = self._save_metadata(filename, url, content, metadata)
            
            # 创建爬取结果对象
            result = CrawlResult(
                url=url,
                title=metadata.get('title', ''),
                content=metadata.get('content_text', ''),
                date=metadata.get('date', ''),
                announcement_type=metadata.get('announcement_type', ''),
                company=metadata.get('company', ''),
                project_name=metadata.get('project_name', ''),
                html_file_path=str(html_file_path) if self.config.save_raw_html else None,
                metadata_file_path=str(metadata_file_path) if metadata_file_path else None
            )
            
            # 记录已爬取URL
            self.crawled_urls.add(url)
            
            return result
            
        except Exception as e:
            logger.error(f"保存HTML内容失败: {e}")
            return None
    
    def _save_metadata(self, filename: str, url: str, content: str, metadata: Dict) -> Path:
        """
        保存元数据到JSON文件
        
        Args:
            filename: HTML文件名
            url: 网页URL
            content: HTML内容
            metadata: 元数据字典
            
        Returns:
            Path: 元数据文件路径
        """
        try:
            # 元数据文件名
            metadata_filename = filename.replace('.html', '_metadata.json')
            metadata_file_path = self.metadata_dir / metadata_filename
            
            # 完整的元数据
            full_metadata = {
                'url': url,
                'filename': filename,
                'crawl_timestamp': datetime.now().isoformat(),
                'content_length': len(content),
                'content_hash': hashlib.md5(content.encode('utf-8')).hexdigest(),
                **metadata
            }
            
            # 保存JSON文件
            with open(metadata_file_path, 'w', encoding='utf-8') as f:
                json.dump(full_metadata, f, ensure_ascii=False, indent=2)
            
            logger.info(f"保存元数据文件: {metadata_file_path}")
            return metadata_file_path
            
        except Exception as e:
            logger.error(f"保存元数据失败: {e}")
            return None
    
    def save_session(self, session: CrawlSession):
        """
        保存爬取会话信息
        
        Args:
            session: 爬取会话对象
        """
        try:
            # 加载现有会话记录
            sessions = []
            if self.session_file.exists():
                with open(self.session_file, 'r', encoding='utf-8') as f:
                    sessions = json.load(f)
            
            # 更新或添加当前会话
            session_dict = session.to_dict()
            
            # 查找是否已存在相同session_id的记录
            updated = False
            for i, existing_session in enumerate(sessions):
                if existing_session['session_id'] == session.session_id:
                    sessions[i] = session_dict
                    updated = True
                    break
            
            # 如果不存在，则添加新记录
            if not updated:
                sessions.append(session_dict)
            
            # 保存到文件
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(sessions, f, ensure_ascii=False, indent=2)
            
            logger.info(f"保存爬取会话: {session.session_id}")
            
        except Exception as e:
            logger.error(f"保存会话信息失败: {e}")
    
    def load_sessions(self) -> List[CrawlSession]:
        """
        加载所有爬取会话
        
        Returns:
            List[CrawlSession]: 会话列表
        """
        try:
            if not self.session_file.exists():
                return []
            
            with open(self.session_file, 'r', encoding='utf-8') as f:
                sessions_data = json.load(f)
            
            sessions = []
            for session_data in sessions_data:
                # 重构配置对象
                config_data = session_data['config']
                config = CrawlerConfig.from_dict(config_data)
                
                # 重构结果对象
                results = []
                for result_data in session_data.get('results', []):
                    results.append(CrawlResult.from_dict(result_data))
                
                # 创建会话对象
                session = CrawlSession(
                    session_id=session_data['session_id'],
                    config=config,
                    start_time=session_data['start_time'],
                    end_time=session_data.get('end_time'),
                    status=session_data['status'],
                    total_pages_crawled=session_data['total_pages_crawled'],
                    total_items_found=session_data['total_items_found'],
                    results=results,
                    error_message=session_data.get('error_message')
                )
                sessions.append(session)
            
            logger.info(f"加载了 {len(sessions)} 个历史会话")
            return sessions
            
        except Exception as e:
            logger.error(f"加载会话信息失败: {e}")
            return []
    
    def get_storage_stats(self) -> Dict:
        """
        获取存储统计信息
        
        Returns:
            Dict: 统计信息字典
        """
        try:
            stats = {
                'total_crawled_urls': len(self.crawled_urls),
                'html_files_count': 0,
                'metadata_files_count': 0,
                'total_storage_size': 0,
                'latest_crawl_date': None
            }
            
            # 统计HTML文件
            if self.html_dir.exists():
                html_files = list(self.html_dir.rglob('*.html'))
                stats['html_files_count'] = len(html_files)
                
                # 计算总大小
                total_size = sum(f.stat().st_size for f in html_files if f.exists())
                stats['total_storage_size'] = total_size
            
            # 统计元数据文件
            if self.metadata_dir.exists():
                metadata_files = list(self.metadata_dir.glob('*_metadata.json'))
                stats['metadata_files_count'] = len(metadata_files)
            
            # 最新爬取日期
            sessions = self.load_sessions()
            if sessions:
                latest_session = max(sessions, key=lambda s: s.start_time)
                stats['latest_crawl_date'] = latest_session.start_time
            
            return stats
            
        except Exception as e:
            logger.error(f"获取存储统计失败: {e}")
            return {}
    
    def cleanup_old_files(self, days_to_keep: int = 30):
        """
        清理旧文件
        
        Args:
            days_to_keep: 保留的天数
        """
        try:
            cutoff_date = datetime.now().timestamp() - (days_to_keep * 24 * 3600)
            
            # 清理HTML文件
            if self.html_dir.exists():
                for html_file in self.html_dir.rglob('*.html'):
                    if html_file.stat().st_mtime < cutoff_date:
                        html_file.unlink()
                        logger.info(f"删除旧HTML文件: {html_file}")
            
            # 清理元数据文件
            if self.metadata_dir.exists():
                for metadata_file in self.metadata_dir.glob('*_metadata.json'):
                    if metadata_file.stat().st_mtime < cutoff_date:
                        metadata_file.unlink()
                        logger.info(f"删除旧元数据文件: {metadata_file}")
            
            logger.info(f"清理 {days_to_keep} 天前的旧文件完成")
            
        except Exception as e:
            logger.error(f"清理旧文件失败: {e}")
    
    def __del__(self):
        """析构函数，保存爬取记录"""
        try:
            self.save_crawl_records()
        except Exception:
            pass  # 忽略析构时的错误 