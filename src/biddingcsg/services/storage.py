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
        # 页面类型前缀（如果有）
        page_type = metadata.get('page_type', '')
        page_type_prefix = ''
        logger.info(f"页面类型: {page_type}")
        if page_type:
            # 清理页面类型，移除特殊字符
            clean_page_type = page_type.replace('/', '_').replace('\\', '_').replace(':', '_')
            page_type_prefix = f"{clean_page_type}_"
        
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
        
        filename = f"{page_type_prefix}{domain}_{timestamp}_{url_hash}{project_name}.html"
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
    
    def clear_all_cache(self) -> Dict[str, int]:
        """
        清空所有缓存数据，删除metadata和raw_html目录下的全部数据
        
        Returns:
            Dict[str, int]: 清理统计信息，包含删除的文件数量
        """
        try:
            stats = {
                'html_files_deleted': 0,
                'metadata_files_deleted': 0,
                'directories_cleaned': 0
            }
            
            # 打印调试信息
            logger.info(f"开始清理缓存...")
            logger.info(f"HTML目录: {self.html_dir}")
            logger.info(f"元数据目录: {self.metadata_dir}")
            logger.info(f"HTML目录存在: {self.html_dir.exists()}")
            logger.info(f"元数据目录存在: {self.metadata_dir.exists()}")
            
            # 清理HTML文件目录
            if self.html_dir.exists():
                html_files = list(self.html_dir.rglob('*.html'))
                logger.info(f"找到HTML文件 {len(html_files)} 个")
                
                for html_file in html_files:
                    try:
                        logger.info(f"正在删除HTML文件: {html_file}")
                        html_file.unlink()
                        stats['html_files_deleted'] += 1
                        logger.info(f"成功删除HTML文件: {html_file}")
                    except Exception as e:
                        logger.warning(f"删除HTML文件失败 {html_file}: {e}")
                
                # 删除日期子目录（如果为空）
                for date_dir in self.html_dir.iterdir():
                    if date_dir.is_dir():
                        try:
                            # 检查目录是否为空
                            if not any(date_dir.iterdir()):
                                date_dir.rmdir()
                                stats['directories_cleaned'] += 1
                                logger.info(f"删除空目录: {date_dir}")
                            else:
                                logger.info(f"目录不为空，跳过: {date_dir}")
                        except OSError as e:
                            logger.warning(f"删除目录失败 {date_dir}: {e}")
            else:
                logger.warning(f"HTML目录不存在: {self.html_dir}")
            
            # 清理元数据文件目录
            if self.metadata_dir.exists():
                metadata_files = list(self.metadata_dir.glob('*.json'))
                logger.info(f"找到元数据文件 {len(metadata_files)} 个")
                
                for metadata_file in metadata_files:
                    try:
                        logger.info(f"正在删除元数据文件: {metadata_file}")
                        metadata_file.unlink()
                        stats['metadata_files_deleted'] += 1
                        logger.info(f"成功删除元数据文件: {metadata_file}")
                    except Exception as e:
                        logger.warning(f"删除元数据文件失败 {metadata_file}: {e}")
            else:
                logger.warning(f"元数据目录不存在: {self.metadata_dir}")
            
            # 清空爬取URL记录
            old_count = len(self.crawled_urls)
            self.crawled_urls.clear()
            self.save_crawl_records()
            logger.info(f"清空爬取URL记录: {old_count} -> {len(self.crawled_urls)}")
            
            logger.info(f"缓存清理完成: 删除HTML文件 {stats['html_files_deleted']} 个, "
                       f"删除元数据文件 {stats['metadata_files_deleted']} 个, "
                       f"清理目录 {stats['directories_cleaned']} 个")
            
            return stats
            
        except Exception as e:
            logger.error(f"清空缓存失败: {e}", exc_info=True)
            return {'html_files_deleted': 0, 'metadata_files_deleted': 0, 'directories_cleaned': 0}
    
    def __del__(self):
        """析构函数，保存爬取记录"""
        try:
            self.save_crawl_records()
        except Exception:
            pass  # 忽略析构时的错误 