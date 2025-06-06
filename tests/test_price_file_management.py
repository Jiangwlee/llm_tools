"""测试价格文件管理功能"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
import sys

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.biddingcsg.ui.pages.crawler_config import CrawlerConfigPage


class TestPriceFileManagement:
    """测试价格文件管理功能"""
    
    def setup_method(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        self.config_page = CrawlerConfigPage()
    
    def teardown_method(self):
        """清理测试环境"""
        # 清理临时文件
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_price_file(self, filename: str, data: dict = None) -> Path:
        """创建测试价格文件"""
        if data is None:
            data = {
                "extraction_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "total_files": 10,
                "successful_extractions": 8,
                "results": [
                    {
                        "file_name": "test1.html",
                        "title": "测试标题1",
                        "price_info": "100万元"
                    },
                    {
                        "file_name": "test2.html", 
                        "title": "测试标题2",
                        "price_info": "200万元"
                    }
                ]
            }
        
        file_path = self.temp_path / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return file_path
    
    def test_scan_price_files_empty_directory(self):
        """测试扫描空目录"""
        files_info = self.config_page._scan_price_files(str(self.temp_path))
        assert files_info == []
    
    def test_scan_price_files_with_files(self):
        """测试扫描包含价格文件的目录"""
        # 创建测试文件
        self.create_test_price_file("price_extraction_test1_20240101.json")
        self.create_test_price_file("price_extraction_test2_20240102.json")
        
        # 创建非价格文件（应该被忽略）
        (self.temp_path / "other_file.json").write_text("test")
        
        files_info = self.config_page._scan_price_files(str(self.temp_path))
        
        assert len(files_info) == 2
        assert all('price_extraction_' in f['name'] for f in files_info)
        assert all('keyword' in f for f in files_info)
        assert all('success_rate' in f for f in files_info)
    
    def test_file_info_parsing(self):
        """测试文件信息解析"""
        test_data = {
            "extraction_time": "2024-01-01 12:00:00",
            "total_files": 15,
            "successful_extractions": 12,
            "results": []
        }
        
        file_path = self.create_test_price_file(
            "price_extraction_测试关键词_20240101_120000.json", 
            test_data
        )
        
        files_info = self.config_page._scan_price_files(str(self.temp_path))
        
        assert len(files_info) == 1
        file_info = files_info[0]
        
        assert file_info['total_files'] == 15
        assert file_info['successful_extractions'] == 12
        assert file_info['success_rate'] == 80.0  # 12/15 * 100
        assert file_info['keyword'] == '测试关键词'
    
    def test_file_sorting_by_time(self):
        """测试文件按时间排序"""
        # 创建不同时间的文件
        old_file = self.create_test_price_file("price_extraction_old_20240101.json")
        new_file = self.create_test_price_file("price_extraction_new_20240102.json")
        
        # 设置不同的修改时间
        import os
        old_time = datetime.now() - timedelta(days=2)
        new_time = datetime.now() - timedelta(days=1)
        
        os.utime(old_file, (old_time.timestamp(), old_time.timestamp()))
        os.utime(new_file, (new_time.timestamp(), new_time.timestamp()))
        
        files_info = self.config_page._scan_price_files(str(self.temp_path))
        
        assert len(files_info) == 2
        # 应该按时间倒序排列（新文件在前）
        assert 'new' in files_info[0]['name']
        assert 'old' in files_info[1]['name']
    
    def test_file_size_calculation(self):
        """测试文件大小计算"""
        # 创建一个相对较大的测试文件
        large_data = {
            "extraction_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "total_files": 100,
            "successful_extractions": 90,
            "results": [{"test": "data" * 1000} for _ in range(100)]  # 创建较大内容
        }
        
        self.create_test_price_file("price_extraction_large_20240101.json", large_data)
        
        files_info = self.config_page._scan_price_files(str(self.temp_path))
        
        assert len(files_info) == 1
        file_info = files_info[0]
        
        assert file_info['size'] > 0
        assert file_info['size_mb'] > 0
        assert file_info['size_mb'] == file_info['size'] / (1024 * 1024)


if __name__ == "__main__":
    # 运行测试
    test_instance = TestPriceFileManagement()
    test_instance.setup_method()
    
    try:
        print("🧪 开始测试价格文件管理功能...")
        
        # 运行各个测试
        test_instance.test_scan_price_files_empty_directory()
        print("✅ 测试空目录扫描 - 通过")
        
        test_instance.test_scan_price_files_with_files()
        print("✅ 测试文件扫描 - 通过")
        
        test_instance.test_file_info_parsing()
        print("✅ 测试文件信息解析 - 通过")
        
        test_instance.test_file_sorting_by_time()
        print("✅ 测试文件排序 - 通过")
        
        test_instance.test_file_size_calculation()
        print("✅ 测试文件大小计算 - 通过")
        
        print("\n🎉 所有测试通过！价格文件管理功能运行正常。")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        test_instance.teardown_method() 