#!/usr/bin/env python3
"""
简单的日志显示测试
"""

import streamlit as st
import sys
import time
import threading
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def main():
    st.set_page_config(
        page_title="简单日志测试",
        page_icon="📝",
        layout="wide"
    )
    
    st.title("📝 简单日志实时显示测试")
    
    # 导入日志相关组件
    try:
        from src.biddingcsg.ui.components.log_viewer import ModernLogViewer, get_global_log_viewer, global_log_queue
        st.success("✅ 日志组件导入成功")
    except Exception as e:
        st.error(f"❌ 日志组件导入失败: {e}")
        return
    
    # 获取日志查看器实例
    log_viewer = get_global_log_viewer()
    
    # 控制区域
    st.subheader("🎮 控制台")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📝 添加测试日志"):
            ModernLogViewer.add_log_background("🧪 这是一条测试日志", "INFO")
            st.success("已添加测试日志")
    
    with col2:
        if st.button("✅ 添加成功日志"):
            ModernLogViewer.add_log_background("✅ 操作成功！", "SUCCESS")
            st.success("已添加成功日志")
    
    with col3:
        if st.button("❌ 添加错误日志"):
            ModernLogViewer.add_log_background("❌ 出现错误！", "ERROR")
            st.error("已添加错误日志")
    
    # 状态信息
    st.subheader("📊 状态信息")
    
    col4, col5, col6 = st.columns(3)
    
    with col4:
        log_count = len(st.session_state.get('log_entries', []))
        st.metric("Session 日志数", log_count)
    
    with col5:
        queue_size = global_log_queue.qsize()
        st.metric("队列大小", queue_size)
    
    with col6:
        auto_refresh = st.session_state.get('log_auto_refresh', True)
        st.metric("自动刷新", "开启" if auto_refresh else "关闭")
    
    # 日志显示区域
    st.markdown("---")
    st.subheader("📝 实时日志")
    
    # 渲染日志查看器
    log_viewer.render_modern(height=300, show_controls=True)
    
    # 调试信息
    with st.expander("🔧 调试信息"):
        st.write("**Session State Keys:**")
        log_keys = [k for k in st.session_state.keys() if 'log' in k.lower()]
        for key in log_keys:
            st.write(f"- {key}: {type(st.session_state[key])}")
        
        st.write("**日志队列状态:**")
        st.write(f"- 队列大小: {global_log_queue.qsize()}")
        st.write(f"- 队列是否为空: {global_log_queue.empty()}")
        
        # 检查日志文件
        log_file = Path("logs/crawler_realtime.log")
        if log_file.exists():
            st.write(f"**日志文件:** 存在，大小 {log_file.stat().st_size} bytes")
        else:
            st.write("**日志文件:** 不存在")

if __name__ == "__main__":
    main() 