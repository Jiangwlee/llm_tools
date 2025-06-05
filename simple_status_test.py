#!/usr/bin/env python3
"""
简单的状态显示测试
"""

import sys
import os

# 添加项目根目录到路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

def test_llm_direct():
    """直接测试LLM功能"""
    print("🧪 直接测试LLM功能")
    print("=" * 50)
    
    try:
        from src.llm_tools.tools.bidding_csg import LLMHelper, UnifiedLLMClient
        
        # 状态收集
        status_messages = []
        
        def test_callback(message):
            status_messages.append(message)
            print(f"📊 状态更新: {message}")
        
        # 测试统一客户端
        print("\n1️⃣ 测试UnifiedLLMClient...")
        client = UnifiedLLMClient()
        print(f"✅ 提供商: {client.provider}")
        print(f"✅ 模型: {client.model}")
        print(f"✅ 可用性: {client.is_available()}")
        
        if client.is_available():
            print("\n2️⃣ 测试chat方法...")
            response = client.chat(
                user_prompt="请说'测试成功'",
                system_prompt="你是测试助手",
                status_callback=test_callback
            )
            print(f"✅ 响应: {response}")
        
        print("\n3️⃣ 测试LLMHelper...")
        LLMHelper.set_global_status_callback(test_callback)
        
        try:
            result = LLMHelper.llm_summary("这是一个测试")
            print(f"✅ LLMHelper结果: {result}")
        finally:
            LLMHelper.clear_global_status_callback()
        
        print(f"\n📊 共收到 {len(status_messages)} 个状态更新")
        for i, msg in enumerate(status_messages, 1):
            print(f"  {i}. {msg}")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_llm_direct() 