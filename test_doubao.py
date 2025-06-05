#!/usr/bin/env python3
"""
豆包大模型测试脚本

使用方法:
    python test_doubao.py

功能:
    - 测试豆包大模型的可用性
    - 测试普通对话功能
    - 测试流式对话功能
    - 测试批量对话功能
"""

import sys
import os

# 添加项目根目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from src.llm_tools.tools.bytedance import (
    check_doubao_availability,
    doubao_chat,
    doubao_chat_stream,
    doubao_batch_chat,
    DOUBAO_API_KEY
)

def test_api_key():
    """测试 API 密钥是否配置"""
    print("🔑 检查 API 密钥配置...")
    if DOUBAO_API_KEY:
        masked_key = DOUBAO_API_KEY[:8] + "*" * (len(DOUBAO_API_KEY) - 12) + DOUBAO_API_KEY[-4:]
        print(f"  ✅ DOUBAO_API_KEY 已配置: {masked_key}")
        return True
    else:
        print("  ❌ DOUBAO_API_KEY 未配置")
        print("  💡 请设置环境变量: export DOUBAO_API_KEY=your_api_key")
        return False

def test_basic_chat():
    """测试基本对话功能"""
    print("\n💬 测试基本对话功能...")
    try:
        response = doubao_chat("你好，请用一句话介绍下你自己")
        if response:
            print(f"  ✅ 豆包回复: {response}")
            return True
        else:
            print("  ❌ 豆包返回空回复")
            return False
    except Exception as e:
        print(f"  ❌ 基本对话测试失败: {str(e)}")
        return False

def test_stream_chat():
    """测试流式对话功能"""
    print("\n🌊 测试流式对话功能...")
    try:
        print("  豆包流式回复: ", end="")
        response_parts = []
        for chunk in doubao_chat_stream("用20个字以内介绍人工智能"):
            print(chunk, end="", flush=True)
            response_parts.append(chunk)
        
        full_response = "".join(response_parts)
        print()
        
        if full_response.strip():
            print(f"  ✅ 流式对话成功，共接收 {len(response_parts)} 个片段")
            return True
        else:
            print("  ❌ 流式对话返回空内容")
            return False
    except Exception as e:
        print(f"\n  ❌ 流式对话测试失败: {str(e)}")
        return False

def test_batch_chat():
    """测试批量对话功能"""
    print("\n📦 测试批量对话功能...")
    try:
        prompts = [
            "什么是Python？（一句话）",
            "推荐一本编程书（书名即可）",
            "机器学习的核心是什么？（一句话）"
        ]
        
        responses = doubao_batch_chat(prompts)
        
        success_count = 0
        for i, (prompt, response) in enumerate(zip(prompts, responses)):
            if response:
                print(f"  {i+1}. 问: {prompt}")
                print(f"     答: {response}")
                success_count += 1
            else:
                print(f"  {i+1}. 问: {prompt}")
                print(f"     答: ❌ 无回复")
        
        if success_count == len(prompts):
            print(f"  ✅ 批量对话成功，{success_count}/{len(prompts)} 个问题获得回复")
            return True
        else:
            print(f"  ⚠️ 批量对话部分成功，{success_count}/{len(prompts)} 个问题获得回复")
            return success_count > 0
            
    except Exception as e:
        print(f"  ❌ 批量对话测试失败: {str(e)}")
        return False

def test_custom_parameters():
    """测试自定义参数功能"""
    print("\n⚙️ 测试自定义参数功能...")
    try:
        # 测试高温度参数
        response_creative = doubao_chat(
            "用一个词形容编程",
            system_prompt="你是一个富有创意的助手",
            temperature=0.9
        )
        
        # 测试低温度参数
        response_precise = doubao_chat(
            "用一个词形容编程",
            system_prompt="你是一个严谨精确的助手",
            temperature=0.1
        )
        
        if response_creative and response_precise:
            print(f"  高温度回复(0.9): {response_creative}")
            print(f"  低温度回复(0.1): {response_precise}")
            print("  ✅ 自定义参数测试成功")
            return True
        else:
            print("  ❌ 自定义参数测试失败，有回复为空")
            return False
            
    except Exception as e:
        print(f"  ❌ 自定义参数测试失败: {str(e)}")
        return False

def main():
    """主测试函数"""
    print("🔍 豆包大模型功能测试")
    print("=" * 50)
    
    # 测试结果统计
    tests = [
        ("API密钥配置", test_api_key),
        ("模型可用性", check_doubao_availability),
        ("基本对话", test_basic_chat),
        ("流式对话", test_stream_chat),
        ("批量对话", test_batch_chat),
        ("自定义参数", test_custom_parameters),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n🧪 执行测试: {test_name}")
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ❌ 测试异常: {str(e)}")
            failed += 1
    
    # 显示测试结果
    print("\n" + "=" * 50)
    print("📊 测试结果总结:")
    print(f"  ✅ 通过: {passed} 项")
    print(f"  ❌ 失败: {failed} 项")
    print(f"  📈 成功率: {passed/(passed+failed)*100:.1f}%")
    
    if passed == len(tests):
        print("\n🎉 所有测试通过！豆包大模型集成成功")
        print("\n📚 使用示例:")
        print("```python")
        print("from src.llm_tools.tools.bytedance import doubao_chat")
        print("response = doubao_chat('你的问题')")
        print("print(response)")
        print("```")
    else:
        print("\n⚠️ 部分测试失败，请检查配置和网络连接")
        
        if not DOUBAO_API_KEY:
            print("\n💡 首先确保设置了环境变量:")
            print("export DOUBAO_API_KEY=your_doubao_api_key")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 测试已取消")
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {str(e)}")
        print("请检查网络连接和环境配置") 