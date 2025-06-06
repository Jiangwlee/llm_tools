"""
信息提取服务测试

验证InfoExtractor的基本功能。
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_info_extractor_import():
    """测试信息提取器导入"""
    try:
        from src.biddingcsg.services.info_extractor import InfoExtractor, create_info_extractor
        print("✅ 信息提取器导入成功")
        return True
    except ImportError as e:
        print(f"❌ 信息提取器导入失败: {e}")
        return False

def test_create_extractor():
    """测试创建信息提取器"""
    try:
        from src.biddingcsg.services.info_extractor import create_info_extractor
        
        # 创建一个测试目录路径
        test_dir = "./test_html"
        extractor = create_info_extractor(test_dir)
        
        print(f"✅ 信息提取器创建成功: {type(extractor).__name__}")
        print(f"✅ HTML目录设置为: {extractor.html_directory}")
        return True
    except Exception as e:
        print(f"❌ 创建信息提取器失败: {e}")
        return False

def test_llm_helper_import():
    """测试LLM助手导入"""
    try:
        from src.biddingcsg.llm.chat import LLMHelper
        print("✅ LLMHelper导入成功")
        
        # 测试获取客户端
        client = LLMHelper.get_llm_client()
        print(f"✅ LLM客户端创建成功: {type(client).__name__}")
        print(f"✅ 提供商: {client.provider}")
        print(f"✅ 模型: {client.model}")
        print(f"✅ 是否可用: {client.is_available()}")
        
        return True
    except Exception as e:
        print(f"❌ LLMHelper导入失败: {e}")
        return False

def test_ui_integration():
    """测试UI集成"""
    try:
        from src.biddingcsg.ui.pages.crawler_config import CrawlerConfigPage
        print("✅ CrawlerConfigPage导入成功")
        
        # 检查新增的方法是否存在
        page = CrawlerConfigPage()
        methods = [
            '_start_price_extraction',
            '_extraction_status_fragment', 
            '_show_extraction_results'
        ]
        
        for method_name in methods:
            if hasattr(page, method_name):
                print(f"✅ 方法 {method_name} 存在")
            else:
                print(f"❌ 方法 {method_name} 不存在")
                return False
        
        return True
    except Exception as e:
        print(f"❌ UI集成测试失败: {e}")
        return False

def run_all_tests():
    """运行所有测试"""
    print("🧪 开始运行信息提取功能测试...\n")
    
    tests = [
        ("信息提取器导入", test_info_extractor_import),
        ("创建信息提取器", test_create_extractor),
        ("LLM助手导入", test_llm_helper_import),
        ("UI集成", test_ui_integration)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"🔍 测试: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
            print(f"{'✅' if result else '❌'} {test_name}: {'通过' if result else '失败'}\n")
        except Exception as e:
            print(f"❌ {test_name}: 异常 - {e}\n")
            results.append((test_name, False))
    
    # 总结
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print("📊 测试总结:")
    print(f"总测试数: {total}")
    print(f"通过: {passed}")
    print(f"失败: {total - passed}")
    print(f"成功率: {passed/total*100:.1f}%")
    
    if passed == total:
        print("\n🎉 所有测试通过！信息提取功能集成成功！")
    else:
        print(f"\n⚠️ {total - passed} 个测试失败，请检查相关配置")
    
    return passed == total

if __name__ == "__main__":
    run_all_tests() 