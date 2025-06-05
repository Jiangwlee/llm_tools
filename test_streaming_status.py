#!/usr/bin/env python3
"""
测试 LLM Streaming 状态显示功能

这个脚本用于测试重构后的LLM系统中的streaming状态显示功能
"""

import sys
import os
import time

# 添加项目根目录到路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

from src.llm_tools.tools.bidding_csg import LLMHelper, UnifiedLLMClient
from src.llm_tools.logger import get_logger

logger = get_logger()

def test_streaming_callback():
    """测试streaming回调功能"""
    print("\n" + "="*80)
    print("🧪 测试 LLM Streaming 状态显示功能")
    print("="*80)
    
    # 状态记录
    status_updates = []
    
    def status_callback(message):
        """状态回调函数"""
        timestamp = time.strftime("%H:%M:%S")
        status_updates.append(f"[{timestamp}] {message}")
        print(f"📊 [{timestamp}] {message}")
    
    # 测试统一客户端
    print("\n1️⃣ 测试统一LLM客户端的streaming功能...")
    
    client = UnifiedLLMClient()
    print(f"✅ 使用提供商: {client.provider}")
    print(f"✅ 使用模型: {client.model}")
    print(f"✅ 客户端可用: {client.is_available()}")
    
    if client.is_available():
        print("\n🚀 开始streaming测试...")
        
        test_prompt = "请简要介绍一下人工智能的发展历程，大概200字左右。"
        
        response = client.chat(
            user_prompt=test_prompt,
            system_prompt="你是一个专业的AI助手，请提供准确简洁的回答。",
            temperature=0.7,
            max_tokens=500,
            status_callback=status_callback
        )
        
        print(f"\n✅ 模型最终回复:\n{response}\n")
        print(f"📊 共收到 {len(status_updates)} 个状态更新")
    else:
        print("❌ 客户端不可用，跳过streaming测试")
    
    return len(status_updates)

def test_llm_helper_with_callback():
    """测试LLMHelper的全局回调功能"""
    print("\n" + "="*80)
    print("🧪 测试 LLMHelper 全局回调功能")
    print("="*80)
    
    status_updates = []
    
    def global_callback(message):
        """全局状态回调"""
        timestamp = time.strftime("%H:%M:%S")
        status_updates.append(f"[{timestamp}] {message}")
        print(f"🌐 [{timestamp}] {message}")
    
    # 设置全局回调
    LLMHelper.set_global_status_callback(global_callback)
    
    try:
        print("\n1️⃣ 测试基本信息提取...")
        test_text = "南方电网广东汕头供电局2024年变电站设备检修项目招标公告，预算1000万元，工期6个月。"
        result = LLMHelper.llm_basic_info_extract(test_text)
        if result:
            print(f"✅ 提取结果: {result[:100]}...")
        
        print("\n2️⃣ 测试内容总结...")
        summary_text = "本项目为电力设备检修，包含变压器检修、开关设备检修等内容。"
        result = LLMHelper.llm_summary(summary_text)
        if result:
            print(f"✅ 总结结果: {result[:100]}...")
        
        print("\n3️⃣ 测试价格提取...")
        price_text = "中标单位：某电力公司，中标价格：980万元，投标限价：1000万元"
        result = LLMHelper.llm_price_extract(price_text)
        if result:
            print(f"✅ 价格提取: {result[:100]}...")
            
    finally:
        # 清除全局回调
        LLMHelper.clear_global_status_callback()
    
    print(f"\n📊 全局回调共收到 {len(status_updates)} 个状态更新")
    return len(status_updates)

def test_callback_priority():
    """测试回调优先级（局部回调 vs 全局回调）"""
    print("\n" + "="*80)
    print("🧪 测试回调优先级功能")
    print("="*80)
    
    global_updates = []
    local_updates = []
    
    def global_callback(message):
        global_updates.append(f"GLOBAL: {message}")
        print(f"🌐 GLOBAL: {message}")
    
    def local_callback(message):
        local_updates.append(f"LOCAL: {message}")
        print(f"📱 LOCAL: {message}")
    
    # 设置全局回调
    LLMHelper.set_global_status_callback(global_callback)
    
    try:
        print("\n1️⃣ 测试只有全局回调...")
        result1 = LLMHelper.llm_summary("测试全局回调")
        
        print("\n2️⃣ 测试局部回调覆盖全局回调...")
        result2 = LLMHelper.llm_summary("测试局部回调", status_callback=local_callback)
        
    finally:
        LLMHelper.clear_global_status_callback()
    
    print(f"\n📊 全局回调收到: {len(global_updates)} 个更新")
    print(f"📊 局部回调收到: {len(local_updates)} 个更新")
    
    return len(global_updates), len(local_updates)

def main():
    """主测试函数"""
    print("🚀 开始 LLM Streaming 状态显示测试")
    print("=" * 80)
    
    total_tests = 0
    passed_tests = 0
    
    try:
        # 测试1: 基本streaming功能
        print("\n🧪 测试 1: 基本 Streaming 功能")
        updates1 = test_streaming_callback()
        total_tests += 1
        if updates1 > 0:
            passed_tests += 1
            print("✅ 测试1通过")
        else:
            print("❌ 测试1失败")
        
        # 测试2: LLMHelper全局回调
        print("\n🧪 测试 2: LLMHelper 全局回调")
        updates2 = test_llm_helper_with_callback()
        total_tests += 1
        if updates2 > 0:
            passed_tests += 1
            print("✅ 测试2通过")
        else:
            print("❌ 测试2失败")
        
        # 测试3: 回调优先级
        print("\n🧪 测试 3: 回调优先级")
        global_count, local_count = test_callback_priority()
        total_tests += 1
        if global_count > 0 and local_count > 0:
            passed_tests += 1
            print("✅ 测试3通过")
        else:
            print("❌ 测试3失败")
        
        # 总结
        print("\n" + "="*80)
        print("📊 测试结果总结")
        print("="*80)
        print(f"总测试数: {total_tests}")
        print(f"通过测试: {passed_tests}")
        print(f"通过率: {passed_tests/total_tests*100:.1f}%")
        
        if passed_tests == total_tests:
            print("🎉 所有测试通过！Streaming状态显示功能正常工作。")
        else:
            print("⚠️ 部分测试失败，请检查配置和网络连接。")
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
        print(f"\n❌ 测试失败: {e}")

if __name__ == "__main__":
    main() 