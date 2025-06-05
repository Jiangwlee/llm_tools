#!/usr/bin/env python3
"""
LLM重构测试脚本

测试重构后的LLMHelper类的功能，包括：
1. 统一模型调用接口
2. 动态模型切换
3. Web UI配置集成
4. 错误处理和降级方案
"""

import sys
import os

# 添加项目根目录到路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

from src.llm_tools.tools.bidding_csg import LLMHelper, UnifiedLLMClient
from src.llm_tools.logger import get_logger

logger = get_logger()

def test_unified_llm_client():
    """测试统一LLM客户端"""
    print("\n" + "="*60)
    print("🔧 测试 UnifiedLLMClient")
    print("="*60)
    
    # 测试默认配置
    client = UnifiedLLMClient()
    print(f"✅ 默认提供商: {client.provider}")
    print(f"✅ 默认模型: {client.model}")
    print(f"✅ 客户端可用性: {client.is_available()}")
    
    if client.is_available():
        # 测试简单对话
        print("\n📝 测试简单对话...")
        response = client.chat("你好，请回复'测试成功'")
        if response:
            print(f"✅ 模型回复: {response}")
        else:
            print("❌ 模型无回复")
    
    return client.is_available()

def test_llm_helper_basic():
    """测试LLMHelper基本功能"""
    print("\n" + "="*60)
    print("🔧 测试 LLMHelper 基本功能")
    print("="*60)
    
    # 测试基本信息提取
    print("\n1️⃣ 测试基本信息提取...")
    test_text = "南方电网广东汕头供电局2024年变电站设备检修项目招标公告"
    result = LLMHelper.llm_basic_info_extract(test_text)
    if result:
        print(f"✅ 信息提取成功: {result[:100]}...")
    else:
        print("❌ 信息提取失败")
    
    # 测试内容总结
    print("\n2️⃣ 测试内容总结...")
    summary_text = "本项目为南方电网汕头供电局2024年变电站设备检修项目，包含变压器检修、开关设备检修、保护装置检修等内容。项目预算1000万元，工期6个月。"
    result = LLMHelper.llm_summary(summary_text)
    if result:
        print(f"✅ 内容总结成功: {result[:100]}...")
    else:
        print("❌ 内容总结失败")
    
    # 测试价格提取
    print("\n3️⃣ 测试价格提取...")
    price_text = "中标单位：某电力公司，中标价格：980万元，投标限价：1000万元"
    result = LLMHelper.llm_price_extract(price_text)
    if result:
        print(f"✅ 价格提取成功: {result[:100]}...")
    else:
        print("❌ 价格提取失败")

def test_provider_switching():
    """测试模型提供商切换"""
    print("\n" + "="*60)
    print("🔧 测试模型提供商切换")
    print("="*60)
    
    # 获取当前提供商
    current_client = LLMHelper.get_llm_client()
    original_provider = current_client.provider
    print(f"🔄 当前提供商: {original_provider}")
    
    # 测试切换到不同提供商
    test_providers = ["DEEPSEEK", "DOUBAO", "SILICONFLOW"]
    
    for provider in test_providers:
        print(f"\n➡️  测试切换到: {provider}")
        LLMHelper.switch_provider(provider)
        new_client = LLMHelper.get_llm_client()
        print(f"✅ 切换后提供商: {new_client.provider}")
        print(f"✅ 模型可用性: {new_client.is_available()}")
    
    # 恢复原始提供商
    LLMHelper.switch_provider(original_provider)
    print(f"\n🔄 恢复到原始提供商: {original_provider}")

def test_web_ui_integration():
    """测试Web UI配置集成"""
    print("\n" + "="*60)
    print("🔧 测试 Web UI 配置集成")
    print("="*60)
    
    try:
        # 测试从Web UI配置管理器初始化
        print("📋 尝试从Web UI配置管理器初始化...")
        LLMHelper.initialize_from_config_manager()
        
        client = LLMHelper.get_llm_client()
        print(f"✅ 从Web UI配置的提供商: {client.provider}")
        print(f"✅ 从Web UI配置的模型: {client.model}")
        print(f"✅ 客户端可用性: {client.is_available()}")
        
    except Exception as e:
        print(f"⚠️  Web UI配置集成测试失败: {e}")

def test_error_handling():
    """测试错误处理和降级方案"""
    print("\n" + "="*60)
    print("🔧 测试错误处理和降级方案")
    print("="*60)
    
    # 创建一个无效配置的客户端
    print("1️⃣ 测试无效API密钥...")
    invalid_client = UnifiedLLMClient(provider="DEEPSEEK", api_key="invalid_key")
    print(f"✅ 无效客户端可用性: {invalid_client.is_available()}")
    
    # 测试在无可用模型情况下的降级
    print("\n2️⃣ 测试降级方案...")
    LLMHelper.set_llm_client(provider="DEEPSEEK", api_key="invalid_key")
    
    # 测试基本信息提取的降级行为
    test_text = "测试降级方案"
    result = LLMHelper.llm_basic_info_extract(test_text)
    if result:
        print(f"✅ 降级方案工作正常: {result[:50]}...")
    else:
        print("⚠️  降级方案也无法工作")

def main():
    """主测试函数"""
    print("🚀 开始 LLM 重构功能测试")
    print("=" * 80)
    
    try:
        # 1. 测试统一LLM客户端
        client_available = test_unified_llm_client()
        
        if client_available:
            # 2. 测试LLMHelper基本功能
            test_llm_helper_basic()
            
            # 3. 测试提供商切换
            test_provider_switching()
        
        # 4. 测试Web UI集成
        test_web_ui_integration()
        
        # 5. 测试错误处理
        test_error_handling()
        
        print("\n" + "="*80)
        print("🎉 LLM 重构功能测试完成")
        print("="*80)
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
        print(f"\n❌ 测试失败: {e}")

if __name__ == "__main__":
    main() 