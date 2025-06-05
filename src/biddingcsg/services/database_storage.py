"""
数据库存储服务

基于SQLite数据库的存储服务，用于替代基于文件的存储
与FileStorageService接口兼容，支持渐进式迁移
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from .database_manager import DatabaseManager
from ..models.database import CrawlItem, CrawlStatus


class DatabaseStorageService:
    """数据库存储服务"""
    
    def __init__(self, config, db_path: Optional[str] = None):
        """
        初始化数据库存储服务
        
        Args:
            config: 爬虫配置
            db_path: 数据库路径，如果为None则使用默认路径
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 初始化数据库管理器
        if db_path is None:
            # 默认数据库路径，支持多种配置格式
            output_dir = getattr(config, 'output_directory', None) or getattr(config, 'output_dir', 'output')
            db_dir = Path(output_dir) / "data"
            db_path = db_dir / "crawler.db"
        
        self.db_manager = DatabaseManager(db_path)
        
        # 缓存最近的查询结果
        self._cache = {}
        self._cache_ttl = 300  # 5分钟缓存
    
    def save_html_content(self, url: str, content: str, metadata: Dict[str, Any] = None) -> str:
        """
        保存HTML内容到数据库
        
        Args:
            url: 页面URL
            content: HTML内容
            metadata: 元数据
            
        Returns:
            数据项ID字符串
        """
        # 检查是否已存在
        existing_item = self.db_manager.get_crawl_item_by_url(url)
        
        if existing_item:
            # 更新现有记录
            existing_item.content_html = content
            existing_item.metadata = json.dumps(metadata or {}, ensure_ascii=False)
            existing_item.status = CrawlStatus.COMPLETED
            
            success = self.db_manager.update_crawl_item(existing_item)
            if success:
                self.logger.debug(f"更新HTML内容: {url}")
                return str(existing_item.id)
            else:
                raise Exception(f"更新数据库记录失败: {url}")
        else:
            # 创建新记录
            item = CrawlItem(
                url=url,
                title=self._extract_title_from_content(content),
                content_html=content,
                metadata=json.dumps(metadata or {}, ensure_ascii=False),
                page_type=self._determine_page_type(content, metadata),
                crawl_timestamp=datetime.now(),
                status=CrawlStatus.COMPLETED
            )
            
            item_id = self.db_manager.insert_crawl_item(item)
            self.logger.debug(f"保存HTML内容: {url} -> ID: {item_id}")
            return str(item_id)
    
    def load_html_content(self, identifier: str) -> Optional[str]:
        """
        从数据库加载HTML内容
        
        Args:
            identifier: 可以是URL或数据项ID
            
        Returns:
            HTML内容或None
        """
        try:
            # 首先尝试作为ID查询
            if identifier.isdigit():
                item = self.db_manager.get_crawl_item_by_id(int(identifier))
            else:
                # 作为URL查询
                item = self.db_manager.get_crawl_item_by_url(identifier)
            
            if item:
                return item.content_html
            
        except Exception as e:
            self.logger.error(f"加载HTML内容失败: {identifier}, 错误: {e}")
        
        return None
    
    def save_metadata(self, url: str, metadata: Dict[str, Any]) -> str:
        """
        保存元数据到数据库
        
        Args:
            url: 页面URL
            metadata: 元数据字典
            
        Returns:
            数据项ID字符串
        """
        existing_item = self.db_manager.get_crawl_item_by_url(url)
        
        if existing_item:
            # 合并元数据
            try:
                existing_metadata = json.loads(existing_item.metadata) if existing_item.metadata else {}
                existing_metadata.update(metadata)
                existing_item.metadata = json.dumps(existing_metadata, ensure_ascii=False)
                
                self.db_manager.update_crawl_item(existing_item)
                return str(existing_item.id)
            except Exception as e:
                self.logger.error(f"更新元数据失败: {url}, 错误: {e}")
                raise
        else:
            # 创建新记录（只有元数据）
            item = CrawlItem(
                url=url,
                title=metadata.get('title', '无标题'),
                metadata=json.dumps(metadata, ensure_ascii=False),
                page_type=self._determine_page_type("", metadata),
                crawl_timestamp=datetime.now(),
                status=CrawlStatus.PENDING
            )
            
            item_id = self.db_manager.insert_crawl_item(item)
            return str(item_id)
    
    def load_metadata(self, identifier: str) -> Optional[Dict[str, Any]]:
        """
        从数据库加载元数据
        
        Args:
            identifier: 可以是URL或数据项ID
            
        Returns:
            元数据字典或None
        """
        try:
            if identifier.isdigit():
                item = self.db_manager.get_crawl_item_by_id(int(identifier))
            else:
                item = self.db_manager.get_crawl_item_by_url(identifier)
            
            if item and item.metadata:
                return json.loads(item.metadata)
                
        except Exception as e:
            self.logger.error(f"加载元数据失败: {identifier}, 错误: {e}")
        
        return None
    
    def generate_filename(self, url: str, page_type: str = "detail") -> str:
        """
        生成文件名（兼容性方法，实际返回数据项ID）
        
        Args:
            url: 页面URL
            page_type: 页面类型
            
        Returns:
            数据项ID字符串
        """
        # 查找现有记录
        item = self.db_manager.get_crawl_item_by_url(url)
        if item:
            return str(item.id)
        
        # 创建新记录
        item = CrawlItem(
            url=url,
            page_type=page_type,
            crawl_timestamp=datetime.now(),
            status=CrawlStatus.PENDING
        )
        
        item_id = self.db_manager.insert_crawl_item(item)
        return str(item_id)
    
    def get_saved_urls(self, page_type: str = None) -> List[str]:
        """
        获取已保存的URL列表
        
        Args:
            page_type: 页面类型过滤
            
        Returns:
            URL列表
        """
        try:
            if page_type:
                # 使用自定义查询
                with self.db_manager.get_cursor() as cursor:
                    cursor.execute(
                        "SELECT url FROM crawl_items WHERE page_type = ? ORDER BY crawl_timestamp DESC",
                        (page_type,)
                    )
                    return [row[0] for row in cursor.fetchall()]
            else:
                with self.db_manager.get_cursor() as cursor:
                    cursor.execute("SELECT url FROM crawl_items ORDER BY crawl_timestamp DESC")
                    return [row[0] for row in cursor.fetchall()]
                    
        except Exception as e:
            self.logger.error(f"获取URL列表失败: {e}")
            return []
    
    def get_file_count(self, page_type: str = None) -> int:
        """
        获取已保存的文件数量
        
        Args:
            page_type: 页面类型过滤
            
        Returns:
            文件数量
        """
        try:
            if page_type:
                with self.db_manager.get_cursor() as cursor:
                    cursor.execute(
                        "SELECT COUNT(*) FROM crawl_items WHERE page_type = ?",
                        (page_type,)
                    )
                    return cursor.fetchone()[0]
            else:
                with self.db_manager.get_cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM crawl_items")
                    return cursor.fetchone()[0]
                    
        except Exception as e:
            self.logger.error(f"获取文件数量失败: {e}")
            return 0
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        获取存储统计信息
        
        Returns:
            统计信息字典
        """
        return self.db_manager.get_database_stats()
    
    def cleanup_old_files(self, days: int = 30) -> int:
        """
        清理旧数据
        
        Args:
            days: 保留天数
            
        Returns:
            清理的记录数量
        """
        return self.db_manager.cleanup_old_data(days)
    
    def clear_cache(self):
        """清理缓存"""
        self._cache.clear()
        self.logger.info("缓存已清理")
    
    def get_crawl_items_paginated(self, page: int = 1, page_size: int = 50, 
                                  status: CrawlStatus = None) -> Tuple[List[Dict], int]:
        """
        分页获取爬虫数据项
        
        Args:
            page: 页码（从1开始）
            page_size: 每页大小
            status: 状态过滤
            
        Returns:
            (数据项字典列表, 总数量)
        """
        try:
            if status:
                items = self.db_manager.get_crawl_items_by_status(status, page_size * page)
                # 简单分页处理
                start_idx = (page - 1) * page_size
                end_idx = start_idx + page_size
                page_items = items[start_idx:end_idx]
                total_count = len(items)
            else:
                page_items, total_count = self.db_manager.get_crawl_items_paginated(page, page_size)
            
            # 转换为字典格式
            result_items = []
            for item in page_items:
                item_dict = {
                    'id': item.id,
                    'url': item.url,
                    'title': item.title,
                    'page_type': item.page_type,
                    'crawl_timestamp': item.crawl_timestamp.isoformat() if item.crawl_timestamp else None,
                    'status': item.status.value,
                    'content_size': len(item.content_html),
                    'has_content': bool(item.content_html),
                    'metadata': item.metadata_dict
                }
                result_items.append(item_dict)
            
            return result_items, total_count
            
        except Exception as e:
            self.logger.error(f"分页查询失败: {e}")
            return [], 0
    
    def _extract_title_from_content(self, content: str) -> str:
        """从HTML内容中提取标题"""
        if not content:
            return "无标题"
        
        try:
            import re
            title_match = re.search(r'<title[^>]*>(.*?)</title>', content, re.IGNORECASE | re.DOTALL)
            if title_match:
                title = title_match.group(1).strip()
                if title:
                    return title
        except:
            pass
        
        return "无标题"
    
    def _determine_page_type(self, content: str, metadata: Dict = None) -> str:
        """确定页面类型"""
        if metadata and 'page_type' in metadata:
            return metadata['page_type']
        
        # 基于内容判断
        if content:
            if '详情' in content or '公告内容' in content:
                return 'detail'
            elif '列表' in content or '更多' in content:
                return 'list'
        
        return 'detail'  # 默认为详情页
    
    def close(self):
        """关闭数据库连接"""
        self.db_manager.close_connection()
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close() 