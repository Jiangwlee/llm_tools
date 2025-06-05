#!/usr/bin/env python3
"""
Streamlit状态更新测试页面
"""

import streamlit as st
import sys
import os
import time
from queue import Queue, Empty

# 添加项目根目录到路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

def init_session_state():
    """初始化session state"""
    if "page_url_status" not in st.session_state:
        st.session_state.page_url_status = "未开始"
    if "llm_inference_status" not in st.session_state:
        st.session_state.llm_inference_status = "未开始"
    if "status_queue" not in st.session_state:
        st.session_state.status_queue = Queue()
    if "llm_queue" not in st.session_state:
        st.session_state.llm_queue = Queue()

def update_page_status(message):
    """更新页面状态"""
    st.session_state.page_url_status = message
    print(f"页面状态更新: {message}")

def update_llm_status(message):
    """更新LLM状态"""
    st.session_state.llm_inference_status = message
    print(f"LLM状态更新: {message}")

def show_status_panel():
    """显示状态面板"""
    st.markdown("### 📊 实时状态监控")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🌐 页面状态")
        status = st.session_state.page_url_status
        if status == "未开始":
            st.info("🟡 等待开始...")
        elif any(word in status for word in ["完成", "成功"]):
            st.success(f"✅ {status}")
        elif any(word in status for word in ["错误", "失败"]):
            st.error(f"❌ {status}")
        else:
            st.info(f"🔄 {status}")
    
    with col2:
        st.markdown("#### 🤖 AI状态")
        status = st.session_state.llm_inference_status
        if status == "未开始":
            st.info("🟡 等待推理...")
        elif any(word in status for word in ["推理中", "分析", "处理中"]):
            st.warning(f"🟠 {status}")
        elif any(word in status for word in ["完成", "成功"]):
            st.success(f"✅ {status}")
        elif any(word in status for word in ["错误", "失败"]):
            st.error(f"❌ {status}")
        else:
            st.info(f"🔄 {status}")

def test_basic_status_update():
    """测试基本状态更新"""
    st.markdown("### 🧪 基本状态更新测试")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📄 更新页面状态"):
            update_page_status("🔍 测试页面访问...")
            st.success("页面状态已更新")
    
    with col2:
        if st.button("🤖 更新AI状态"):
            update_llm_status("💭 AI推理中...")
            st.success("AI状态已更新")
    
    with col3:
        if st.button("🔄 重置状态"):
            update_page_status("未开始")
            update_llm_status("未开始")
            st.success("状态已重置")

def test_llm_function():
    """测试LLM功能"""
    st.markdown("### 🤖 LLM功能测试")
    
    if st.button("🚀 测试LLM"):
        try:
            from src.llm_tools.tools.bidding_csg import LLMHelper
            
            # 状态回调
            def callback(message):
                update_llm_status(message)
                st.info(f"🤖 状态更新: {message}")
            
            update_page_status("🧪 开始LLM测试...")
            update_llm_status("🚀 准备测试...")
            
            LLMHelper.set_global_status_callback(callback)
            
            try:
                result = LLMHelper.llm_summary("这是一个测试")
                
                if result:
                    st.success("✅ LLM测试成功!")
                    st.text_area("LLM回复:", result, height=100)
                    update_page_status("✅ 测试完成")
                    update_llm_status("✅ 推理成功")
                else:
                    st.warning("⚠️ LLM返回空结果")
                    update_llm_status("⚠️ 返回空结果")
                    
            finally:
                LLMHelper.clear_global_status_callback()
                
        except Exception as e:
            st.error(f"❌ LLM测试失败: {e}")
            update_page_status("❌ 测试失败")
            update_llm_status("❌ 推理失败")

def test_streaming():
    """测试streaming效果"""
    st.markdown("### 🌊 模拟Streaming测试")
    
    if st.button("🎬 开始Streaming测试"):
        progress_area = st.empty()
        
        steps = [
            ("🌐 连接服务器...", "🚀 初始化模型..."),
            ("📄 处理第1页...", "💭 分析内容..."),
            ("📄 处理第2页...", "📝 提取信息..."),
            ("💾 保存数据...", "✅ 处理完成!")
        ]
        
        for i, (page_msg, llm_msg) in enumerate(steps):
            update_page_status(page_msg)
            update_llm_status(llm_msg)
            
            with progress_area.container():
                st.progress((i + 1) / len(steps))
                st.info(f"步骤 {i + 1}/{len(steps)}: {page_msg}")
            
            time.sleep(1)
        
        progress_area.empty()
        st.success("🎉 Streaming测试完成!")

def main():
    st.set_page_config(
        page_title="状态更新测试",
        page_icon="🧪",
        layout="wide"
    )
    
    st.title("🧪 状态更新功能测试")
    st.markdown("测试页面状态和LLM状态的实时更新功能")
    
    # 初始化session state
    init_session_state()
    
    # 显示状态面板
    show_status_panel()
    
    st.markdown("---")
    
    # 测试基本状态更新
    test_basic_status_update()
    
    st.markdown("---")
    
    # 测试LLM功能
    test_llm_function()
    
    st.markdown("---")
    
    # 测试streaming
    test_streaming()
    
    # 调试信息
    with st.expander("🐛 调试信息"):
        st.write("Session State:")
        st.json({
            "page_url_status": st.session_state.page_url_status,
            "llm_inference_status": st.session_state.llm_inference_status
        })

if __name__ == "__main__":
    main() 