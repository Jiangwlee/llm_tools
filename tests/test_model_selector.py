"""
模型选择器组件测试

验证模型选择器的基本功能。
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_model_selector_import():
    """测试模型选择器导入"""
    try:
        from src.biddingcsg.ui.components.model_selector import ModelSelector, get_model_selector
        print("✅ 模型选择器导入成功")
        return True
    except ImportError as e:
        print(f"❌ 模型选择器导入失败: {e}")
        return False

def test_config_manager():
    """测试配置管理器"""
    try:
        from src.biddingcsg.config import get_biddingcsg_config_manager
        
        config_manager = get_biddingcsg_config_manager()
        print("✅ 配置管理器创建成功")
        
        # 测试获取当前模型信息
        current_model = config_manager.get_current_model_info()
        print(f"✅ 当前模型: {current_model}")
        
        return True
    except Exception as e:
        print(f"❌ 配置管理器测试失败: {e}")
        return False

def test_model_selector_creation():
    """测试模型选择器创建"""
    try:
        from src.biddingcsg.ui.components.model_selector import get_model_selector
        
        selector = get_model_selector()
        print("✅ 模型选择器创建成功")
        
        # 测试获取当前模型信息
        model_info = selector.get_current_model_info()
        print(f"✅ 模型信息: {model_info}")
        
        return True
    except Exception as e:
        print(f"❌ 模型选择器创建失败: {e}")
        return False

def test_global_config():
    """测试全局配置"""
    try:
        from src.biddingcsg.config import global_config
        
        print(f"✅ 找到 {len(global_config.PROVIDERS)} 个模型提供商:")
        for provider, config in global_config.PROVIDERS.items():
            has_key = bool(config.get("API_KEY"))
            status = "✅ 已配置" if has_key else "❌ 未配置"
            print(f"   {provider}: {config.get('MODEL', 'unknown')} - {status}")
        
        return True
    except Exception as e:
        print(f"❌ 全局配置测试失败: {e}")
        return False

def main():
    """运行所有测试"""
    print("🧪 开始测试模型选择器功能...")
    print("=" * 50)
    
    tests = [
        ("导入测试", test_model_selector_import),
        ("配置管理器测试", test_config_manager),
        ("模型选择器创建测试", test_model_selector_creation),
        ("全局配置测试", test_global_config),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 {test_name}...")
        try:
            if test_func():
                passed += 1
            else:
                print(f"   测试失败")
        except Exception as e:
            print(f"   测试异常: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！模型选择器功能正常。")
    else:
        print("⚠️ 部分测试失败，请检查相关配置。")

if __name__ == "__main__":
    main() 