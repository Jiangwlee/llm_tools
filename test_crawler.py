#!/usr/bin/env python3
"""
招标公告爬虫测试脚本

测试第一阶段功能:
1. 配置模型创建和验证
2. 存储服务基本功能
3. 爬虫服务基本功能
4. UI组件基本功能
"""

import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """测试所有模块导入"""
    print("🔍 测试模块导入...")
    
    try:
        # 测试数据模型
        from src.biddingcsg.models.config import CrawlerConfig, CrawlResult, CrawlSession
        print("✅ 数据模型导入成功")
        
        # 测试服务层
        from src.biddingcsg.services.storage import LocalStorageService
        from src.biddingcsg.services.crawler import BiddingCrawlerService
        print("✅ 服务层导入成功")
        
        # 测试UI组件
        from src.biddingcsg.ui.components.log_viewer import LogViewer, ProgressViewer
        from src.biddingcsg.ui.pages.crawler_config import CrawlerConfigPage
        print("✅ UI组件导入成功")
        
        # 测试包级别导入
        from src.biddingcsg import (
            create_default_config, 
            get_version_info,
            CrawlerConfig,
            LocalStorageService
        )
        print("✅ 包级别导入成功")
        
        return True
        
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False

def test_config_model():
    """测试配置模型"""
    print("\n🔧 测试配置模型...")
    
    try:
        from src.biddingcsg.models.config import CrawlerConfig
        
        # 测试默认配置
        config = CrawlerConfig(search_keyword="测试关键词")
        print(f"✅ 默认配置创建成功: {config.search_keyword}")
        
        # 测试配置验证
        try:
            invalid_config = CrawlerConfig(search_keyword="")
            print("❌ 配置验证失败 - 应该拒绝空关键词")
            return False
        except ValueError:
            print("✅ 配置验证正常 - 正确拒绝了空关键词")
        
        # 测试配置属性
        assert config.max_pages == 10
        assert config.announcement_type == "服务"
        assert config.enable_dedup == True
        assert config.headless_mode == True
        print("✅ 配置属性默认值正确")
        
        # 测试目录属性
        html_dir = config.html_output_dir
        metadata_dir = config.metadata_output_dir
        assert html_dir.name == "raw_html"
        assert metadata_dir.name == "metadata"
        print("✅ 目录属性正确")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置模型测试失败: {e}")
        return False

def test_storage_service():
    """测试存储服务"""
    print("\n💾 测试存储服务...")
    
    try:
        from src.biddingcsg.models.config import CrawlerConfig
        from src.biddingcsg.services.storage import LocalStorageService
        
        # 创建测试配置
        test_dir = project_root / "test_output"
        config = CrawlerConfig(
            search_keyword="测试",
            output_directory=str(test_dir)
        )
        
        # 创建存储服务
        storage = LocalStorageService(config)
        print("✅ 存储服务创建成功")
        
        # 检查目录创建
        assert test_dir.exists()
        assert (test_dir / "raw_html").exists()
        assert (test_dir / "metadata").exists()
        print("✅ 目录结构创建正确")
        
        # 测试文件名生成
        test_url = "https://example.com/test"
        test_metadata = {"project_name": "测试项目"}
        filename = storage.generate_filename(test_url, test_metadata)
        assert filename.endswith(".html")
        assert "example_com" in filename
        print(f"✅ 文件名生成正确: {filename}")
        
        # 测试去重检查
        assert not storage.check_duplicate(test_url)
        print("✅ 去重检查功能正常")
        
        # 清理测试目录
        import shutil
        if test_dir.exists():
            shutil.rmtree(test_dir)
        
        return True
        
    except Exception as e:
        print(f"❌ 存储服务测试失败: {e}")
        return False

def test_ui_components():
    """测试UI组件"""
    print("\n🖥️ 测试UI组件...")
    
    try:
        from src.biddingcsg.ui.components.log_viewer import LogViewer, ProgressViewer
        
        # 测试日志查看器
        log_viewer = LogViewer(max_lines=10)
        print("✅ 日志查看器创建成功")
        
        # 测试进度查看器
        progress_viewer = ProgressViewer()
        print("✅ 进度查看器创建成功")
        
        return True
        
    except Exception as e:
        print(f"❌ UI组件测试失败: {e}")
        return False

def test_package_functions():
    """测试包级别函数"""
    print("\n📦 测试包级别函数...")
    
    try:
        from src.biddingcsg import create_default_config, get_version_info
        
        # 测试默认配置创建
        config = create_default_config("测试关键词")
        assert config.search_keyword == "测试关键词"
        print("✅ 默认配置创建函数正常")
        
        # 测试版本信息
        version_info = get_version_info()
        assert "version" in version_info
        assert "features" in version_info
        print(f"✅ 版本信息正常: v{version_info['version']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 包级别函数测试失败: {e}")
        return False

def test_dependencies():
    """测试依赖包"""
    print("\n📋 检查依赖包...")
    
    required_packages = [
        ("streamlit", "Streamlit Web框架"),
        ("playwright", "浏览器自动化"),
        ("bs4", "BeautifulSoup HTML解析"),
        ("pathlib", "路径处理"),
        ("threading", "多线程支持"),
        ("json", "JSON处理"),
        ("hashlib", "哈希计算"),
        ("datetime", "日期时间处理")
    ]
    
    missing_packages = []
    
    for package, description in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} - {description}")
        except ImportError:
            print(f"❌ {package} - {description} (缺失)")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️ 缺少依赖包: {', '.join(missing_packages)}")
        print("请运行: pip install streamlit playwright beautifulsoup4")
        print("然后运行: playwright install chromium")
        return False
    
    print("✅ 所有依赖包已安装")
    return True

def run_all_tests():
    """运行所有测试"""
    print("🧪 开始运行第一阶段功能测试...")
    print("=" * 50)
    
    tests = [
        ("依赖检查", test_dependencies),
        ("模块导入", test_imports),
        ("配置模型", test_config_model),
        ("存储服务", test_storage_service),
        ("UI组件", test_ui_components),
        ("包函数", test_package_functions)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n📝 运行测试: {test_name}")
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ 测试异常: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"🎯 测试结果: {passed} 通过, {failed} 失败")
    
    if failed == 0:
        print("🎉 所有测试通过！第一阶段功能已就绪")
        print("\n🚀 下一步操作:")
        print("1. 运行 'python run_crawler.py' 启动Web应用")
        print("2. 在浏览器中访问 http://localhost:8501")
        print("3. 配置爬虫参数并开始数据下载")
    else:
        print("⚠️ 部分测试失败，请检查错误信息并修复")
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1) 