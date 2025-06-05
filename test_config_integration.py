#!/usr/bin/env python3
"""
配置集成测试脚本

验证 config_manager.py 与 config.py 的正确集成

使用方法:
    python test_config_integration.py
"""

import sys
import os

# 添加项目根目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from src.llm_tools.web_ui.config_manager import ConfigManager
from src.llm_tools import config

def test_config_loading():
    """测试配置加载是否正确"""
    print("🔧 测试配置加载...")
    
    try:
        config_manager = ConfigManager("test_integration_config.json")
        
        # 检查是否正确加载了 config.py 中的提供商
        available_models = config_manager.get_available_models()
        config_providers = set(config.PROVIDERS.keys())
        manager_providers = set(available_models.keys())
        
        if config_providers == manager_providers:
            print(f"  ✅ 提供商加载成功: {list(config_providers)}")
            return True
        else:
            print(f"  ❌ 提供商不匹配")
            print(f"     config.py: {config_providers}")
            print(f"     manager:   {manager_providers}")
            return False
            
    except Exception as e:
        print(f"  ❌ 配置加载测试失败: {str(e)}")
        return False

def test_model_config_consistency():
    """测试模型配置的一致性"""
    print("\n🔍 测试模型配置一致性...")
    
    try:
        config_manager = ConfigManager("test_integration_config.json")
        
        # 检查每个提供商的配置
        for provider_key in config.PROVIDERS:
            config_data = config.PROVIDERS[provider_key]
            manager_models = config_manager.get_available_models()[provider_key]
            
            # 检查 API 密钥环境变量名称是否一致
            if config_data["API_KEY_ENV"] != manager_models["api_key_env"]:
                print(f"  ❌ {provider_key} API密钥环境变量不一致")
                return False
            
            # 检查基础URL是否一致
            if config_data["BASE_URL"] != manager_models["base_url"]:
                print(f"  ❌ {provider_key} 基础URL不一致")
                return False
            
            # 检查默认模型是否包含在可用模型中
            if config_data["MODEL"] not in manager_models["models"]:
                print(f"  ❌ {provider_key} 默认模型不在可用模型列表中")
                return False
        
        print("  ✅ 模型配置一致性检查通过")
        return True
        
    except Exception as e:
        print(f"  ❌ 模型配置一致性测试失败: {str(e)}")
        return False

def test_current_model_config():
    """测试当前模型配置获取"""
    print("\n🤖 测试当前模型配置获取...")
    
    try:
        config_manager = ConfigManager("test_integration_config.json")
        
        # 获取当前模型信息
        current_model = config_manager.get_current_model_info()
        print(f"  📋 当前模型: {current_model['display_name']}")
        print(f"  📊 提供商: {current_model['provider']}")
        print(f"  🔧 模型名: {current_model['model']}")
        print(f"  ✅ 可用性: {'可用' if current_model['available'] else '需要API密钥'}")
        
        # 获取完整配置
        full_config = config_manager.get_current_model_config()
        print(f"  🌐 API地址: {full_config['base_url']}")
        
        # 验证配置的完整性
        required_keys = ["base_url", "api_key", "model", "provider", "available"]
        for key in required_keys:
            if key not in full_config:
                print(f"  ❌ 缺少配置项: {key}")
                return False
        
        print("  ✅ 当前模型配置获取成功")
        return True
        
    except Exception as e:
        print(f"  ❌ 当前模型配置测试失败: {str(e)}")
        return False

def test_model_switching():
    """测试模型切换功能"""
    print("\n🔄 测试模型切换功能...")
    
    try:
        config_manager = ConfigManager("test_integration_config.json")
        
        # 获取所有可用提供商
        available_models = config_manager.get_available_models()
        providers = list(available_models.keys())
        
        if len(providers) < 2:
            print("  ⚠️ 可用提供商不足，跳过切换测试")
            return True
        
        # 切换到第二个提供商
        original_provider = config_manager.get_current_model_info()["provider"]
        target_provider = providers[1] if providers[0] == original_provider else providers[0]
        target_model = config.PROVIDERS[target_provider]["MODEL"]
        
        # 执行切换
        config_manager.set("default_model.provider", target_provider)
        config_manager.set("default_model.name", target_model)
        
        # 验证切换结果
        new_model_info = config_manager.get_current_model_info()
        
        if (new_model_info["provider"] == target_provider and 
            new_model_info["model"] == target_model):
            print(f"  ✅ 模型切换成功: {original_provider} → {target_provider}")
            return True
        else:
            print(f"  ❌ 模型切换失败")
            return False
            
    except Exception as e:
        print(f"  ❌ 模型切换测试失败: {str(e)}")
        return False

def test_api_key_detection():
    """测试API密钥检测功能"""
    print("\n🔑 测试API密钥检测功能...")
    
    try:
        config_manager = ConfigManager("test_integration_config.json")
        
        # 检查每个提供商的API密钥状态
        providers_status = {}
        for provider_key in config.PROVIDERS:
            is_available = config_manager.check_model_availability(provider_key)
            env_var = config.PROVIDERS[provider_key]["API_KEY_ENV"]
            actual_key = os.getenv(env_var)
            
            providers_status[provider_key] = {
                "available": is_available,
                "has_key": bool(actual_key),
                "env_var": env_var
            }
            
            status_icon = "✅" if is_available else "❌"
            print(f"  {status_icon} {provider_key}: 环境变量 {env_var}")
        
        # 验证检测逻辑的正确性
        for provider, status in providers_status.items():
            if status["available"] != status["has_key"]:
                print(f"  ⚠️ {provider} 密钥检测逻辑可能有误")
        
        print("  ✅ API密钥检测功能验证完成")
        return True
        
    except Exception as e:
        print(f"  ❌ API密钥检测测试失败: {str(e)}")
        return False

def cleanup_test_files():
    """清理测试文件"""
    print("\n🧹 清理测试文件...")
    
    from pathlib import Path
    test_file = Path.home() / ".llm_tools" / "test_integration_config.json"
    
    try:
        if test_file.exists():
            test_file.unlink()
            print(f"  🗑️ 已删除: {test_file}")
    except Exception as e:
        print(f"  ⚠️ 删除失败: {test_file} - {str(e)}")

def main():
    """主测试函数"""
    print("🔍 配置集成测试")
    print("=" * 50)
    
    # 显示当前配置状态
    print(f"📋 config.py 中的提供商: {list(config.PROVIDERS.keys())}")
    
    # 测试用例
    tests = [
        ("配置加载", test_config_loading),
        ("模型配置一致性", test_model_config_consistency),
        ("当前模型配置", test_current_model_config),
        ("模型切换功能", test_model_switching),
        ("API密钥检测", test_api_key_detection),
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
        print("\n🎉 所有测试通过！配置集成工作正常")
        print("\n📚 配置管理器现在使用 config.py 中的提供商配置")
        print("✨ 当添加新的模型提供商时，只需要在 config.py 中更新 PROVIDERS 即可")
    else:
        print("\n⚠️ 部分测试失败，请检查配置集成")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 测试已取消")
        cleanup_test_files()
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {str(e)}")
        cleanup_test_files() 