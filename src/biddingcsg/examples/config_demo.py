"""
BiddingCSG 配置管理器使用演示
展示如何使用配置管理器进行模型配置和管理
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from src.biddingcsg.config import get_biddingcsg_config_manager
from src.biddingcsg.llm.chat import LLMHelper


def demo_config_manager():
    """演示配置管理器的基本功能"""
    print("=" * 60)
    print("BiddingCSG 配置管理器演示")
    print("=" * 60)
    
    # 获取配置管理器实例
    config_manager = get_biddingcsg_config_manager()
    print(f"✅ 配置管理器初始化成功")
    print(f"📁 配置文件位置: {config_manager.config_file}")
    
    # 获取当前模型信息
    current_model = config_manager.get_current_model_info()
    print(f"\n🤖 当前模型配置:")
    print(f"   提供商: {current_model['provider']}")
    print(f"   模型: {current_model['model']}")
    print(f"   显示名称: {current_model['display_name']}")
    print(f"   可用性: {'✅ 可用' if current_model['available'] else '❌ 不可用'}")
    
    # 显示配置数据
    print(f"\n📋 完整配置数据:")
    import json
    print(json.dumps(config_manager.config_data, ensure_ascii=False, indent=2))
    
    return config_manager


def demo_llm_integration():
    """演示与 LLM 客户端的集成"""
    print("\n" + "=" * 60)
    print("LLM 客户端集成演示")
    print("=" * 60)
    
    try:
        # 初始化 LLM 客户端（使用配置管理器）
        LLMHelper.initialize_from_config_manager()
        print("✅ LLM 客户端初始化成功")
        
        # 获取客户端实例
        llm_client = LLMHelper.get_llm_client()
        print(f"🔧 LLM 客户端: {llm_client}")
        print(f"   提供商: {llm_client.provider}")
        print(f"   模型: {llm_client.model}")
        print(f"   可用性: {'✅ 可用' if llm_client.is_available() else '❌ 不可用'}")
        
        # 如果客户端可用，尝试简单的聊天测试
        if llm_client.is_available():
            print("\n🧪 尝试模型测试调用...")
            def status_callback(status):
                print(f"   状态: {status}")
            
            try:
                response = llm_client.chat(
                    user_prompt="你好，请简单介绍一下自己",
                    system_prompt="你是一个AI助手",
                    max_tokens=100,
                    status_callback=status_callback
                )
                
                if response:
                    print(f"✅ 测试成功！模型回复:")
                    print(f"   {response[:200]}{'...' if len(response) > 200 else ''}")
                else:
                    print("❌ 测试失败：无响应")
                    
            except Exception as e:
                print(f"❌ 测试异常: {e}")
        else:
            print("⚠️  客户端不可用，跳过测试调用")
            
    except Exception as e:
        print(f"❌ LLM 客户端初始化失败: {e}")


def demo_config_operations():
    """演示配置操作功能"""
    print("\n" + "=" * 60)
    print("配置操作演示")
    print("=" * 60)
    
    config_manager = get_biddingcsg_config_manager()
    
    # 显示可用的提供商
    from src.biddingcsg.config import global_config
    print("📡 可用的模型提供商:")
    for provider, config in global_config.PROVIDERS.items():
        has_key = bool(config.get("API_KEY"))
        status = "✅ 已配置" if has_key else "❌ 未配置"
        print(f"   {provider}: {config['MODEL']} - {status}")
    
    # 尝试切换提供商（如果有多个可用）
    available_providers = [p for p, c in global_config.PROVIDERS.items() if c.get("API_KEY")]
    if len(available_providers) > 1:
        print(f"\n🔄 尝试切换提供商演示...")
        original_provider = config_manager.get_current_model_info()["provider"]
        
        # 找一个不同的提供商
        new_provider = None
        for provider in available_providers:
            if provider != original_provider:
                new_provider = provider
                break
        
        if new_provider:
            print(f"   原提供商: {original_provider}")
            print(f"   新提供商: {new_provider}")
            
            # 这里只是演示，实际不修改配置
            print("   (演示模式，不实际修改配置)")
        else:
            print("   只有一个可用提供商，无法演示切换")
    else:
        print(f"\n⚠️  只有 {len(available_providers)} 个可用提供商，无法演示切换")


def main():
    """主函数"""
    try:
        # 基础配置管理器功能演示
        config_manager = demo_config_manager()
        
        # LLM 集成演示
        demo_llm_integration()
        
        # 配置操作演示
        demo_config_operations()
        
        print("\n" + "=" * 60)
        print("✅ 演示完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 演示过程中出现异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 