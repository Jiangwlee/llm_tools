"""
数据库功能测试

测试数据库模型、管理器和存储服务的基本功能
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import json

import sys
sys.path.append(str(Path(__file__).parent.parent / "src"))

from biddingcsg.models.config import CrawlerConfig

from biddingcsg.models.database import (
    CrawlItem, LLMAnalysis, LLMSummary, LLMSession, 
    AnalysisError, CrawlStatus, AnalysisStatus
)
from biddingcsg.services.database_manager import DatabaseManager
from biddingcsg.services.database_storage import DatabaseStorageService


class TestDatabaseModels(unittest.TestCase):
    """测试数据库模型"""
    
    def test_crawl_item_creation(self):
        """测试CrawlItem创建和MD5计算"""
        item = CrawlItem(
            url="https://www.bidding.csg.cn/zbhxrgs/1200396189.jhtml",
            title="测试页面",
            content_html="<html><body>测试内容</body></html>",
            page_type="detail"
        )
        
        # 测试MD5计算
        md5_hash = item.calculate_content_md5()
        self.assertTrue(md5_hash)
        self.assertEqual(len(md5_hash), 32)  # MD5长度为32字符
        
        # 测试元数据处理
        item.metadata_dict = {"test": "value", "number": 123}
        metadata = item.metadata_dict
        self.assertEqual(metadata["test"], "value")
        self.assertEqual(metadata["number"], 123)
    
    def test_llm_analysis_creation(self):
        """测试LLMAnalysis创建"""
        analysis = LLMAnalysis(
            crawl_item_id=1,
            project_name="测试项目",
            budget_amount="100万元",
            llm_model="gpt-4",
            confidence_score=0.85
        )
        
        self.assertEqual(analysis.crawl_item_id, 1)
        self.assertEqual(analysis.project_name, "测试项目")
        self.assertEqual(analysis.confidence_score, 0.85)
    
    def test_llm_summary_key_points(self):
        """测试LLMSummary关键点处理"""
        summary = LLMSummary(
            crawl_item_id=1,
            summary_text="这是一个测试摘要"
        )
        
        # 测试关键点列表
        summary.key_points_list = ["关键点1", "关键点2", "关键点3"]
        points = summary.key_points_list
        self.assertEqual(len(points), 3)
        self.assertEqual(points[0], "关键点1")
    
    def test_llm_session_progress(self):
        """测试LLMSession进度计算"""
        session = LLMSession(
            session_name="测试会话",
            total_items=100,
            processed_items=50,
            success_items=45
        )
        
        self.assertEqual(session.progress_percentage, 50.0)
        self.assertEqual(session.success_rate, 90.0)


class TestDatabaseManager(unittest.TestCase):
    """测试数据库管理器"""
    
    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"
        self.db_manager = DatabaseManager(self.db_path)
    
    def tearDown(self):
        """清理测试环境"""
        self.db_manager.close_connection()
        shutil.rmtree(self.temp_dir)
    
    def test_database_initialization(self):
        """测试数据库初始化"""
        # 数据库文件应该存在
        self.assertTrue(self.db_path.exists())
        
        # 应该能够获取统计信息
        stats = self.db_manager.get_database_stats()
        self.assertIn('total_crawl_items', stats)
        self.assertEqual(stats['total_crawl_items'], 0)
    
    def test_crawl_item_operations(self):
        """测试爬虫数据项的CRUD操作"""
        # 创建测试数据
        item = CrawlItem(
            url="https://example.com/test1",
            title="测试页面1",
            content_html="<html><body>测试内容1</body></html>",
            page_type="detail",
            status=CrawlStatus.COMPLETED
        )
        
        # 插入数据
        item_id = self.db_manager.insert_crawl_item(item)
        self.assertIsNotNone(item_id)
        self.assertGreater(item_id, 0)
        
        # 根据ID查询
        retrieved_item = self.db_manager.get_crawl_item_by_id(item_id)
        self.assertIsNotNone(retrieved_item)
        self.assertEqual(retrieved_item.url, item.url)
        self.assertEqual(retrieved_item.title, item.title)
        
        # 根据URL查询
        retrieved_item2 = self.db_manager.get_crawl_item_by_url(item.url)
        self.assertIsNotNone(retrieved_item2)
        self.assertEqual(retrieved_item2.id, item_id)
        
        # 更新数据
        retrieved_item.title = "更新后的标题"
        success = self.db_manager.update_crawl_item(retrieved_item)
        self.assertTrue(success)
        
        # 验证更新
        updated_item = self.db_manager.get_crawl_item_by_id(item_id)
        self.assertEqual(updated_item.title, "更新后的标题")
    
    def test_llm_analysis_operations(self):
        """测试LLM分析的操作"""
        # 先创建一个爬虫数据项
        item = CrawlItem(
            url="https://example.com/test2",
            title="测试页面2",
            content_html="<html><body>测试内容2</body></html>"
        )
        item_id = self.db_manager.insert_crawl_item(item)
        
        # 创建分析结果
        analysis = LLMAnalysis(
            crawl_item_id=item_id,
            project_name="测试项目分析",
            budget_amount="200万元",
            llm_model="gpt-4",
            confidence_score=0.92
        )
        
        # 插入分析结果
        analysis_id = self.db_manager.insert_llm_analysis(analysis)
        self.assertIsNotNone(analysis_id)
        
        # 查询分析结果
        retrieved_analysis = self.db_manager.get_llm_analysis_by_crawl_item_id(item_id)
        self.assertIsNotNone(retrieved_analysis)
        self.assertEqual(retrieved_analysis.project_name, "测试项目分析")
        self.assertEqual(retrieved_analysis.confidence_score, 0.92)
    
    def test_llm_session_operations(self):
        """测试LLM会话操作"""
        # 创建会话
        session_id = self.db_manager.create_llm_session(
            session_name="测试会话",
            description="这是一个测试会话",
            llm_model="gpt-4"
        )
        self.assertIsNotNone(session_id)
        
        # 更新会话进度
        self.db_manager.update_session_progress(
            session_id,
            total_items=10,
            processed_items=5,
            success_items=4,
            status=AnalysisStatus.ANALYZING
        )
        
        # 查询会话
        session = self.db_manager.get_llm_session_by_id(session_id)
        self.assertIsNotNone(session)
        self.assertEqual(session.total_items, 10)
        self.assertEqual(session.processed_items, 5)
        self.assertEqual(session.progress_percentage, 50.0)
        self.assertEqual(session.success_rate, 80.0)
    
    def test_paginated_queries(self):
        """测试分页查询"""
        # 插入多条测试数据
        for i in range(15):
            item = CrawlItem(
                url=f"https://example.com/test{i}",
                title=f"测试页面{i}",
                content_html=f"<html><body>测试内容{i}</body></html>"
            )
            self.db_manager.insert_crawl_item(item)
        
        # 测试分页查询
        items, total_count = self.db_manager.get_crawl_items_paginated(page=1, page_size=10)
        self.assertEqual(len(items), 10)
        self.assertEqual(total_count, 15)
        
        # 第二页
        items2, total_count2 = self.db_manager.get_crawl_items_paginated(page=2, page_size=10)
        self.assertEqual(len(items2), 5)
        self.assertEqual(total_count2, 15)


class TestDatabaseStorageService(unittest.TestCase):
    """测试数据库存储服务"""
    
    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        
        # 创建测试配置
        self.config = CrawlerConfig(
            search_keyword="测试关键词",
            output_directory=self.temp_dir
        )
        
        # 创建存储服务
        db_path = Path(self.temp_dir) / "test_storage.db"
        self.storage = DatabaseStorageService(self.config, str(db_path))
    
    def tearDown(self):
        """清理测试环境"""
        self.storage.close()
        shutil.rmtree(self.temp_dir)
    
    def test_save_and_load_html(self):
        """测试HTML内容保存和加载"""
        url = "https://example.com/test"
        content = "<html><body><h1>测试页面</h1><p>这是测试内容</p></body></html>"
        metadata = {"title": "测试页面", "type": "detail"}
        
        # 保存HTML内容
        item_id = self.storage.save_html_content(url, content, metadata)
        self.assertIsNotNone(item_id)
        
        # 通过URL加载
        loaded_content = self.storage.load_html_content(url)
        self.assertEqual(loaded_content, content)
        
        # 通过ID加载
        loaded_content2 = self.storage.load_html_content(item_id)
        self.assertEqual(loaded_content2, content)
    
    def test_save_and_load_metadata(self):
        """测试元数据保存和加载"""
        url = "https://example.com/metadata_test"
        metadata = {
            "title": "元数据测试页面",
            "author": "测试作者",
            "tags": ["测试", "元数据"],
            "score": 95
        }
        
        # 保存元数据
        item_id = self.storage.save_metadata(url, metadata)
        self.assertIsNotNone(item_id)
        
        # 加载元数据
        loaded_metadata = self.storage.load_metadata(url)
        self.assertIsNotNone(loaded_metadata)
        self.assertEqual(loaded_metadata["title"], "元数据测试页面")
        self.assertEqual(loaded_metadata["score"], 95)
        self.assertIn("测试", loaded_metadata["tags"])
    
    def test_storage_statistics(self):
        """测试存储统计功能"""
        # 保存一些测试数据
        for i in range(5):
            url = f"https://example.com/stats_test{i}"
            content = f"<html><body>统计测试{i}</body></html>"
            self.storage.save_html_content(url, content)
        
        # 获取统计信息
        stats = self.storage.get_storage_stats()
        self.assertIn('total_crawl_items', stats)
        self.assertEqual(stats['total_crawl_items'], 5)
        
        # 获取文件数量
        file_count = self.storage.get_file_count()
        self.assertEqual(file_count, 5)
        
        # 获取URL列表
        urls = self.storage.get_saved_urls()
        self.assertEqual(len(urls), 5)
    
    def test_paginated_items(self):
        """测试分页获取数据项"""
        # 保存测试数据
        for i in range(12):
            url = f"https://example.com/page_test{i}"
            content = f"<html><body>分页测试{i}</body></html>"
            metadata = {"page_index": i}
            self.storage.save_html_content(url, content, metadata)
        
        # 获取第一页
        items, total = self.storage.get_crawl_items_paginated(page=1, page_size=5)
        self.assertEqual(len(items), 5)
        self.assertEqual(total, 12)
        
        # 检查数据项格式
        item = items[0]
        self.assertIn('id', item)
        self.assertIn('url', item)
        self.assertIn('title', item)
        self.assertIn('content_size', item)
        self.assertIn('has_content', item)


def main():
    """运行测试"""
    # 配置日志
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 运行测试
    unittest.main(verbosity=2)


if __name__ == "__main__":
    main()