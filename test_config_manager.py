#!/usr/bin/env python3
"""
配置管理器测试脚本

使用方法:
    python test_config_manager.py

功能:
    - 测试配置文件的创建和读写
    - 测试模型配置功能
    - 测试配置持久化
    - 测试默认值合并
"""

import sys
import os
import json
from pathlib import Path

# 添加项目根目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from src.llm_tools.web_ui.config_manager import ConfigManager

def test_config_creation():
    """测试配置文件创建"""
    print("🔧 测试配置文件创建...")
    
    try:
        # 使用临时配置文件
        config = ConfigManager("test_config.json")
        
        # 检查配置文件是否被创建
        if config.config_file.exists():
            print("  ✅ 配置文件创建成功")
            print(f"  📁 文件位置: {config.config_file}")
            return True
        else:
            print("  ❌ 配置文件创建失败")
            return False
            
    except Exception as e:
        print(f"  ❌ 配置创建测试失败: {str(e)}")
        return False

def test_config_read_write():
    """测试配置读写功能"""
    print("\n📖 测试配置读写功能...")
    
    try:
        config = ConfigManager("test_config.json")
        
        # 测试设置值
        config.set("test_key", "test_value")
        config.set("nested.key", "nested_value")
        
        # 测试获取值
        value1 = config.get("test_key")
        value2 = config.get("nested.key")
        value3 = config.get("nonexistent.key", "default_value")
        
        if value1 == "test_value" and value2 == "nested_value" and value3 == "default_value":
            print("  ✅ 配置读写测试成功")
            return True
        else:
            print(f"  ❌ 配置读写测试失败: {value1}, {value2}, {value3}")
            return False
            
    except Exception as e:
        print(f"  ❌ 配置读写测试失败: {str(e)}")
        return False

def test_model_configuration():
    """测试模型配置功能"""
    print("\n🤖 测试模型配置功能...")
    
    try:
        config = ConfigManager("test_config.json")
        
        # 获取可用模型
        models = config.get_available_models()
        print(f"  📋 可用模型提供商: {list(models.keys())}")
        
        # 测试模型切换
        config.set("default_model.provider", "DOUBAO")
        config.set("default_model.name", "doubao-1.5-pro-32k-250115")
        
        # 获取当前模型信息
        current_model = config.get_current_model_info()
        
        if (current_model["provider"] == "DOUBAO" and 
            current_model["model"] == "doubao-1.5-pro-32k-250115"):
            print("  ✅ 模型配置测试成功")
            print(f"  🔄 当前模型: {current_model['display_name']}")
            return True
        else:
            print(f"  ❌ 模型配置测试失败: {current_model}")
            return False
            
    except Exception as e:
        print(f"  ❌ 模型配置测试失败: {str(e)}")
        return False

def test_persistence():
    """测试配置持久化"""
    print("\n💾 测试配置持久化...")
    
    try:
        # 创建第一个配置实例并设置值
        config1 = ConfigManager("test_config.json")
        config1.set("persistence_test", "persistent_value")
        
        # 创建第二个配置实例，应该能读取到相同的值
        config2 = ConfigManager("test_config.json")
        value = config2.get("persistence_test")
        
        if value == "persistent_value":
            print("  ✅ 配置持久化测试成功")
            return True
        else:
            print(f"  ❌ 配置持久化测试失败: {value}")
            return False
            
    except Exception as e:
        print(f"  ❌ 配置持久化测试失败: {str(e)}")
        return False

def test_default_merge():
    """测试默认配置合并"""
    print("\n🔄 测试默认配置合并...")
    
    try:
        config = ConfigManager("test_config.json")
        
        # 检查默认配置是否存在
        default_provider = config.get("default_model.provider")
        default_max_pages = config.get("download_settings.default_max_pages")
        
        if default_provider and default_max_pages:
            print("  ✅ 默认配置合并测试成功")
            print(f"  📋 默认模型提供商: {default_provider}")
            print(f"  📄 默认最大页数: {default_max_pages}")
            return True
        else:
            print(f"  ❌ 默认配置合并测试失败: {default_provider}, {default_max_pages}")
            return False
            
    except Exception as e:
        print(f"  ❌ 默认配置合并测试失败: {str(e)}")
        return False

def test_model_availability():
    """测试模型可用性检查"""
    print("\n🔍 测试模型可用性检查...")
    
    try:
        config = ConfigManager("test_config.json")
        
        # 检查各个提供商的可用性
        providers = ["DEEPSEEK", "DOUBAO", "SILICONFLOW"]
        availability_results = {}
        
        for provider in providers:
            is_available = config.check_model_availability(provider)
            availability_results[provider] = is_available
            status = "✅ 可用" if is_available else "❌ 需要API密钥"
            print(f"  {provider}: {status}")
        
        print("  ✅ 模型可用性检查完成")
        return True
        
    except Exception as e:
        print(f"  ❌ 模型可用性检查失败: {str(e)}")
        return False

def test_export_import():
    """测试配置导出导入功能"""
    print("\n📤 测试配置导出导入功能...")
    
    try:
        config = ConfigManager("test_config.json")
        
        # 设置一些测试值
        config.set("export_test.key1", "value1")
        config.set("export_test.key2", "value2")
        
        # 导出配置
        exported = config.export_config()
        exported_data = json.loads(exported)
        
        # 创建新配置实例并导入
        config2 = ConfigManager("test_config2.json")
        success = config2.import_config(exported)
        
        if success:
            # 验证导入的值
            value1 = config2.get("export_test.key1")
            value2 = config2.get("export_test.key2")
            
            if value1 == "value1" and value2 == "value2":
                print("  ✅ 配置导出导入测试成功")
                return True
            else:
                print(f"  ❌ 配置导入验证失败: {value1}, {value2}")
                return False
        else:
            print("  ❌ 配置导入失败")
            return False
            
    except Exception as e:
        print(f"  ❌ 配置导出导入测试失败: {str(e)}")
        return False

def cleanup_test_files():
    """清理测试文件"""
    print("\n🧹 清理测试文件...")
    
    test_files = [
        Path.home() / ".llm_tools" / "test_config.json",
        Path.home() / ".llm_tools" / "test_config2.json"
    ]
    
    for file_path in test_files:
        try:
            if file_path.exists():
                file_path.unlink()
                print(f"  🗑️  已删除: {file_path}")
        except Exception as e:
            print(f"  ⚠️  删除失败: {file_path} - {str(e)}")

def main():
    """主测试函数"""
    print("🔍 配置管理器功能测试")
    print("=" * 50)
    
    # 测试用例
    tests = [
        ("配置文件创建", test_config_creation),
        ("配置读写功能", test_config_read_write),
        ("模型配置功能", test_model_configuration),
        ("配置持久化", test_persistence),
        ("默认配置合并", test_default_merge),
        ("模型可用性检查", test_model_availability),
        ("配置导出导入", test_export_import),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ❌ 测试异常: {str(e)}")
            failed += 1
    
    # 清理测试文件
    cleanup_test_files()
    
    # 显示测试结果
    print("\n" + "=" * 50)
    print("📊 测试结果总结:")
    print(f"  ✅ 通过: {passed} 项")
    print(f"  ❌ 失败: {failed} 项")
    print(f"  📈 成功率: {passed/(passed+failed)*100:.1f}%")
    
    if passed == len(tests):
        print("\n🎉 所有测试通过！配置管理器工作正常")
        print("\n📚 使用示例:")
        print("```python")
        print("from src.llm_tools.web_ui.config_manager import get_config_manager")
        print("config = get_config_manager()")
        print("config.set('default_model.provider', 'DOUBAO')")
        print("provider = config.get('default_model.provider')")
        print("```")
    else:
        print("\n⚠️ 部分测试失败，请检查配置管理器实现")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 测试已取消")
        cleanup_test_files()
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {str(e)}")
        cleanup_test_files() 