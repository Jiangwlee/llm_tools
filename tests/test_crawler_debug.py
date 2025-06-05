#!/usr/bin/env python3
"""
调试爬虫应用的实时日志显示问题
"""

import streamlit as st
import sys
import time
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.biddingcsg.ui.components.log_viewer import ModernLogViewer, get_global_log_viewer, global_log_queue

def main():
    st.set_page_config(
        page_title="爬虫日志调试",
        page_icon="🐛",
        layout="wide"
    )
    
    st.title("🐛 爬虫日志调试工具")
    
    # 获取全局日志查看器
    log_viewer = get_global_log_viewer()
    
    st.markdown("### 🔧 调试控制")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🧪 添加测试日志"):
            ModernLogViewer.add_log_background("🧪 测试日志消息", "INFO")
            st.success("已添加测试日志")
    
    with col2:
        if st.button("✅ 添加成功日志"):
            ModernLogViewer.add_log_background("✅ 成功操作完成", "SUCCESS")
            st.success("已添加成功日志")
    
    with col3:
        if st.button("⚠️ 添加警告日志"):
            ModernLogViewer.add_log_background("⚠️ 这是警告信息", "WARNING")
            st.warning("已添加警告日志")
    
    with col4:
        if st.button("🗑️ 清空日志"):
            log_viewer.clear_logs()
            st.success("已清空日志")
    
    st.markdown("---")
    
    # 状态信息
    st.subheader("📊 状态信息")
    
    col5, col6, col7 = st.columns(3)
    
    with col5:
        log_count = len(st.session_state.get('log_entries', []))
        st.metric("Session State 日志数", log_count)
    
    with col6:
        queue_size = global_log_queue.qsize()
        st.metric("全局队列大小", queue_size)
    
    with col7:
        auto_refresh = st.session_state.get('log_auto_refresh', True)
        status = "🟢 启用" if auto_refresh else "🔴 禁用"
        st.metric("自动刷新", status)
    
    # 显示session state中的日志条目详情
    with st.expander("🔍 Session State 调试信息"):
        st.write("**所有session state键：**")
        keys = [k for k in st.session_state.keys() if 'log' in k.lower()]
        for key in keys:
            value = st.session_state[key]
            if isinstance(value, list):
                st.write(f"- {key}: {type(value)} (长度: {len(value)})")
                if len(value) > 0:
                    st.write(f"  最新条目类型: {type(value[-1])}")
                    st.write(f"  最新条目内容: {value[-1]}")
            else:
                st.write(f"- {key}: {value}")
    
    st.markdown("---")
    
    # 使用简化的Fragment来测试
    test_fragment()
    
    # 日志显示区域
    st.subheader("📝 日志显示测试")
    
    # 使用日志查看器
    log_viewer.render_modern(height=400, show_controls=True)

@st.fragment(run_every=1)
def test_fragment():
    """测试Fragment是否正常工作"""
    if 'fragment_counter' not in st.session_state:
        st.session_state.fragment_counter = 0
    
    st.session_state.fragment_counter += 1
    
    # 每5秒自动添加一条测试日志
    if st.session_state.fragment_counter % 5 == 0:
        ModernLogViewer.add_log_background(f"🔄 自动测试日志 #{st.session_state.fragment_counter//5}", "INFO")
    
    # 显示Fragment工作状态（不能在Fragment中使用sidebar）
    st.write(f"🔄 Fragment 运行计数: {st.session_state.fragment_counter}")

if __name__ == "__main__":
    main() 