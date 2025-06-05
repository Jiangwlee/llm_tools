"""
数据迁移工具

将现有的基于文件的数据迁移到SQLite数据库中
支持HTML文件和元数据的批量迁移，包含进度跟踪和错误处理
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import hashlib

from ..services.database_manager import DatabaseManager
from ..services.storage import FileStorageService
from ..models.database import CrawlItem, CrawlStatus
from ..models.config import CrawlConfig


class DataMigrationTool:
    """数据迁移工具"""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None, 
                 output_dir: str = "output"):
        """
        初始化数据迁移工具
        
        Args:
            db_manager: 数据库管理器实例
            output_dir: 输出目录路径
        """
        self.db_manager = db_manager or DatabaseManager()
        self.output_dir = Path(output_dir)
        self.logger = logging.getLogger(__name__)
        
        # 创建临时存储服务来读取现有文件
        temp_config = CrawlConfig()
        temp_config.output_dir = str(self.output_dir)
        self.storage = FileStorageService(temp_config)
        
        # 迁移统计
        self.stats = {
            'total_files': 0,
            'migrated_count': 0,
            'skipped_count': 0,
            'error_count': 0,
            'errors': []
        }
    
    def scan_existing_files(self) -> List[Tuple[Path, Dict]]:
        """
        扫描现有的HTML文件和元数据
        
        Returns:
            [(html_file_path, metadata_dict), ...]
        """
        html_files = []
        
        if not self.output_dir.exists():
            self.logger.warning(f"输出目录不存在: {self.output_dir}")
            return html_files
        
        # 扫描所有.html文件
        for html_file in self.output_dir.rglob("*.html"):
            try:
                # 查找对应的元数据文件
                metadata_file = html_file.with_suffix('.json')
                metadata = {}
                
                if metadata_file.exists():
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                
                html_files.append((html_file, metadata))
                
            except Exception as e:
                self.logger.error(f"处理文件时出错 {html_file}: {e}")
                self.stats['errors'].append(f"扫描文件 {html_file}: {e}")
        
        self.stats['total_files'] = len(html_files)
        self.logger.info(f"发现 {len(html_files)} 个HTML文件")
        
        return html_files
    
    def extract_url_from_metadata(self, metadata: Dict, html_file: Path) -> Optional[str]:
        """
        从元数据中提取URL
        
        Args:
            metadata: 元数据字典
            html_file: HTML文件路径
            
        Returns:
            提取的URL或None
        """
        # 尝试从不同字段提取URL
        url_fields = ['url', 'source_url', 'page_url', 'link']
        
        for field in url_fields:
            if field in metadata and metadata[field]:
                return metadata[field]
        
        # 如果元数据中没有URL，尝试从文件名推断
        filename = html_file.stem
        if filename.startswith('http'):
            # 文件名可能是URL的编码版本
            try:
                import urllib.parse
                return urllib.parse.unquote(filename)
            except:
                pass
        
        # 生成一个基于文件路径的虚拟URL
        relative_path = html_file.relative_to(self.output_dir)
        return f"file://{relative_path}"
    
    def extract_title_from_metadata(self, metadata: Dict, html_content: str) -> str:
        """
        从元数据或HTML内容中提取标题
        
        Args:
            metadata: 元数据字典
            html_content: HTML内容
            
        Returns:
            提取的标题
        """
        # 尝试从元数据获取标题
        title_fields = ['title', 'project_name', 'name', 'subject']
        
        for field in title_fields:
            if field in metadata and metadata[field]:
                return str(metadata[field]).strip()
        
        # 尝试从HTML中提取title标签
        try:
            import re
            title_match = re.search(r'<title[^>]*>(.*?)</title>', html_content, re.IGNORECASE | re.DOTALL)
            if title_match:
                title = title_match.group(1).strip()
                if title:
                    return title
        except:
            pass
        
        return "无标题"
    
    def determine_page_type(self, metadata: Dict, html_content: str) -> str:
        """
        确定页面类型
        
        Args:
            metadata: 元数据字典
            html_content: HTML内容
            
        Returns:
            页面类型 ('list' 或 'detail')
        """
        # 从元数据获取页面类型
        if 'page_type' in metadata:
            return metadata['page_type']
        
        # 从其他字段推断
        if 'type' in metadata:
            page_type = metadata['type'].lower()
            if 'list' in page_type or 'index' in page_type:
                return 'list'
            elif 'detail' in page_type or 'item' in page_type:
                return 'detail'
        
        # 基于内容特征推断
        if '详情' in html_content or '公告内容' in html_content:
            return 'detail'
        elif '列表' in html_content or '更多' in html_content:
            return 'list'
        
        # 默认为详情页
        return 'detail'
    
    def create_crawl_item_from_file(self, html_file: Path, metadata: Dict) -> CrawlItem:
        """
        从文件创建CrawlItem对象
        
        Args:
            html_file: HTML文件路径
            metadata: 元数据字典
            
        Returns:
            CrawlItem对象
        """
        # 读取HTML内容
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
        except Exception as e:
            self.logger.error(f"读取HTML文件失败 {html_file}: {e}")
            html_content = ""
        
        # 提取基本信息
        url = self.extract_url_from_metadata(metadata, html_file)
        title = self.extract_title_from_metadata(metadata, html_content)
        page_type = self.determine_page_type(metadata, html_content)
        
        # 获取文件时间作为爬取时间
        crawl_timestamp = datetime.fromtimestamp(html_file.stat().st_mtime)
        
        # 创建CrawlItem
        item = CrawlItem(
            url=url,
            title=title,
            content_html=html_content,
            metadata=json.dumps(metadata, ensure_ascii=False),
            page_type=page_type,
            crawl_timestamp=crawl_timestamp,
            status=CrawlStatus.COMPLETED
        )
        
        # 计算MD5
        item.calculate_content_md5()
        
        return item
    
    def migrate_single_file(self, html_file: Path, metadata: Dict) -> bool:
        """
        迁移单个文件
        
        Args:
            html_file: HTML文件路径
            metadata: 元数据字典
            
        Returns:
            是否成功迁移
        """
        try:
            # 创建CrawlItem
            item = self.create_crawl_item_from_file(html_file, metadata)
            
            # 检查是否已存在（根据URL）
            existing_item = self.db_manager.get_crawl_item_by_url(item.url)
            if existing_item:
                self.logger.debug(f"URL已存在，跳过: {item.url}")
                self.stats['skipped_count'] += 1
                return True
            
            # 插入到数据库
            item_id = self.db_manager.insert_crawl_item(item)
            self.logger.debug(f"成功迁移文件: {html_file} -> ID: {item_id}")
            self.stats['migrated_count'] += 1
            
            return True
            
        except Exception as e:
            error_msg = f"迁移文件失败 {html_file}: {e}"
            self.logger.error(error_msg)
            self.stats['error_count'] += 1
            self.stats['errors'].append(error_msg)
            return False
    
    def migrate_all_files(self, dry_run: bool = False) -> Dict:
        """
        迁移所有文件
        
        Args:
            dry_run: 是否为试运行（不实际写入数据库）
            
        Returns:
            迁移统计信息
        """
        self.logger.info("开始数据迁移...")
        
        # 重置统计
        self.stats = {
            'total_files': 0,
            'migrated_count': 0,
            'skipped_count': 0,
            'error_count': 0,
            'errors': []
        }
        
        # 扫描文件
        files_to_migrate = self.scan_existing_files()
        
        if not files_to_migrate:
            self.logger.warning("没有找到需要迁移的文件")
            return self.stats
        
        # 迁移文件
        for i, (html_file, metadata) in enumerate(files_to_migrate, 1):
            if dry_run:
                self.logger.info(f"[试运行] 处理文件 {i}/{len(files_to_migrate)}: {html_file}")
                self.stats['migrated_count'] += 1
            else:
                self.logger.info(f"迁移文件 {i}/{len(files_to_migrate)}: {html_file}")
                self.migrate_single_file(html_file, metadata)
            
            # 每处理100个文件输出一次进度
            if i % 100 == 0:
                self.logger.info(f"进度: {i}/{len(files_to_migrate)} 文件已处理")
        
        # 输出最终统计
        self.logger.info("数据迁移完成！")
        self.logger.info(f"总文件数: {self.stats['total_files']}")
        self.logger.info(f"成功迁移: {self.stats['migrated_count']}")
        self.logger.info(f"跳过重复: {self.stats['skipped_count']}")
        self.logger.info(f"迁移失败: {self.stats['error_count']}")
        
        if self.stats['errors']:
            self.logger.warning(f"错误详情:")
            for error in self.stats['errors'][:10]:  # 只显示前10个错误
                self.logger.warning(f"  - {error}")
            if len(self.stats['errors']) > 10:
                self.logger.warning(f"  ... 还有 {len(self.stats['errors']) - 10} 个错误")
        
        return self.stats
    
    def verify_migration(self) -> Dict:
        """
        验证迁移结果
        
        Returns:
            验证统计信息
        """
        self.logger.info("验证迁移结果...")
        
        # 获取数据库统计
        db_stats = self.db_manager.get_database_stats()
        
        # 扫描文件系统中的文件数量
        files_to_migrate = self.scan_existing_files()
        file_count = len(files_to_migrate)
        
        verification = {
            'files_on_disk': file_count,
            'items_in_database': db_stats['total_crawl_items'],
            'migration_coverage': 0.0,
            'database_stats': db_stats
        }
        
        if file_count > 0:
            verification['migration_coverage'] = (db_stats['total_crawl_items'] / file_count) * 100
        
        self.logger.info(f"验证结果:")
        self.logger.info(f"  文件系统中的文件: {verification['files_on_disk']}")
        self.logger.info(f"  数据库中的记录: {verification['items_in_database']}")
        self.logger.info(f"  迁移覆盖率: {verification['migration_coverage']:.2f}%")
        
        return verification
    
    def cleanup_files_after_migration(self, keep_recent_days: int = 7) -> int:
        """
        在成功迁移后清理旧文件
        
        Args:
            keep_recent_days: 保留最近几天的文件
            
        Returns:
            删除的文件数量
        """
        self.logger.warning("注意：此操作将删除已迁移的文件，请确保数据库备份完整！")
        
        cutoff_time = datetime.now().timestamp() - (keep_recent_days * 24 * 3600)
        deleted_count = 0
        
        for html_file in self.output_dir.rglob("*.html"):
            try:
                if html_file.stat().st_mtime < cutoff_time:
                    # 检查对应的元数据文件
                    metadata_file = html_file.with_suffix('.json')
                    
                    # 删除HTML文件
                    html_file.unlink()
                    deleted_count += 1
                    
                    # 删除元数据文件（如果存在）
                    if metadata_file.exists():
                        metadata_file.unlink()
                        deleted_count += 1
                    
                    self.logger.debug(f"删除文件: {html_file}")
                    
            except Exception as e:
                self.logger.error(f"删除文件失败 {html_file}: {e}")
        
        self.logger.info(f"清理完成，删除了 {deleted_count} 个文件")
        return deleted_count


def main():
    """迁移脚本入口函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="数据迁移工具")
    parser.add_argument("--output-dir", default="output", help="输出目录路径")
    parser.add_argument("--db-path", default="data/crawler.db", help="数据库文件路径")
    parser.add_argument("--dry-run", action="store_true", help="试运行模式")
    parser.add_argument("--verify", action="store_true", help="验证迁移结果")
    parser.add_argument("--cleanup", action="store_true", help="清理已迁移的文件")
    parser.add_argument("--keep-days", type=int, default=7, help="清理时保留的天数")
    parser.add_argument("--verbose", action="store_true", help="详细输出")
    
    args = parser.parse_args()
    
    # 配置日志
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建迁移工具
    db_manager = DatabaseManager(args.db_path)
    migration_tool = DataMigrationTool(db_manager, args.output_dir)
    
    try:
        if args.verify:
            # 验证模式
            migration_tool.verify_migration()
        elif args.cleanup:
            # 清理模式
            migration_tool.cleanup_files_after_migration(args.keep_days)
        else:
            # 迁移模式
            migration_tool.migrate_all_files(dry_run=args.dry_run)
            
            if not args.dry_run:
                migration_tool.verify_migration()
                
    except KeyboardInterrupt:
        logging.info("迁移被用户中断")
    except Exception as e:
        logging.error(f"迁移过程中发生错误: {e}")
        raise
    finally:
        db_manager.close_connection()


if __name__ == "__main__":
    main() 