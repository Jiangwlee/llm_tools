#!/usr/bin/env python3
"""
测试实时状态显示功能

验证修改后的wrapper是否能正确传递LLM状态
"""

import sys
import os
import time

# 添加项目根目录到路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

from src.llm_tools.web_ui.bidding_csg_wrapper import safe_get_price_info
from src.llm_tools.logger import get_logger

logger = get_logger()

def test_status_callback():
    """测试状态回调功能"""
    print("🧪 测试实时状态回调功能")
    print("=" * 80)
    
    # 收集状态更新
    page_updates = []
    llm_updates = []
    
    def status_callback(status_type, message):
        """状态回调函数"""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] {status_type.upper()}: {message}")
        
        if status_type == "page":
            page_updates.append(f"[{timestamp}] {message}")
        elif status_type == "llm":
            llm_updates.append(f"[{timestamp}] {message}")
    
    print("\n🚀 开始测试下载流程...")
    print("注意：这个测试会启动真实的下载流程，请确保网络连接正常")
    
    # 使用测试关键字
    test_keyword = "供电局"
    
    try:
        result = safe_get_price_info(
            keyword=test_keyword,
            bidding_type=1,  # 投标报价
            max_page=1,  # 只下载1页数据
            end_date=None,
            status_callback=status_callback
        )
        
        print(f"\n✅ 下载结果: {result}")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
    
    finally:
        print(f"\n📊 状态更新统计:")
        print(f"页面状态更新: {len(page_updates)} 次")
        print(f"LLM状态更新: {len(llm_updates)} 次")
        
        if page_updates:
            print(f"\n🌐 页面状态历史:")
            for update in page_updates:
                print(f"  {update}")
        
        if llm_updates:
            print(f"\n🤖 LLM状态历史:")
            for update in llm_updates:
                print(f"  {update}")
        
        if len(page_updates) > 0 and len(llm_updates) > 0:
            print("\n🎉 状态回调功能正常工作！")
        else:
            print("\n⚠️ 状态回调可能存在问题，请检查配置")

def test_simple_callback():
    """简单的回调测试"""
    print("\n🧪 简单回调测试")
    print("=" * 80)
    
    def simple_callback(status_type, message):
        print(f"📺 [{status_type}] {message}")
    
    # 这里可以添加更简单的测试逻辑
    print("回调函数定义成功！")

if __name__ == "__main__":
    print("🚀 开始实时状态显示测试")
    print("=" * 80)
    
    # 首先运行简单测试
    test_simple_callback()
    
    # 询问是否运行完整测试
    response = input("\n是否运行完整的下载测试？这会启动真实的爬虫进程 (y/N): ")
    
    if response.lower() in ['y', 'yes']:
        test_status_callback()
    else:
        print("跳过完整测试，仅运行基础功能验证")
    
    print("\n✅ 测试完成！") 