#!/usr/bin/env python3
"""
测试日志实时显示功能
"""

import streamlit as st
import sys
import time
import threading
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.biddingcsg.ui.components.log_viewer import ModernLogViewer, get_global_log_viewer

def test_log_functionality():
    """测试日志功能的完整性"""
    st.title("🧪 日志显示功能测试")
    
    # 获取全局日志查看器
    log_viewer = get_global_log_viewer()
    
    # 测试按钮区域
    st.subheader("🎯 测试控制")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📝 添加测试日志"):
            ModernLogViewer.add_log_background("🧪 这是一条测试信息", "INFO")
            st.success("测试日志已添加")
    
    with col2:
        if st.button("✅ 添加成功日志"):
            ModernLogViewer.add_log_background("✅ 操作成功完成", "SUCCESS")
            st.success("成功日志已添加")
    
    with col3:
        if st.button("⚠️ 添加警告日志"):
            ModernLogViewer.add_log_background("⚠️ 这是一条警告信息", "WARNING")
            st.warning("警告日志已添加")
    
    with col4:
        if st.button("❌ 添加错误日志"):
            ModernLogViewer.add_log_background("❌ 这是一条错误信息", "ERROR")
            st.error("错误日志已添加")
    
    # 批量测试
    st.subheader("🚀 批量测试")
    
    col5, col6 = st.columns(2)
    
    with col5:
        if st.button("📦 批量添加日志"):
            for i in range(5):
                ModernLogViewer.add_log_background(f"📦 批量测试日志 #{i+1}", "INFO")
                time.sleep(0.1)  # 短暂延迟
            st.success("批量日志已添加")
    
    with col6:
        if st.button("🔄 模拟爬虫日志"):
            def simulate_crawler():
                messages = [
                    ("🚀 启动爬虫任务...", "SUCCESS"),
                    ("🌐 初始化浏览器...", "INFO"),
                    ("🔍 访问搜索页面...", "INFO"),
                    ("📝 输入搜索关键词...", "INFO"),
                    ("🔎 点击搜索按钮...", "INFO"),
                    ("📄 进入搜索结果页面...", "INFO"),
                    ("📊 找到 100 条记录，共 10 页", "SUCCESS"),
                    ("📖 处理第 1/10 页", "INFO"),
                    ("🔍 页面找到 10 个项目", "INFO"),
                    ("✅ 爬取任务完成！", "SUCCESS")
                ]
                
                for msg, level in messages:
                    ModernLogViewer.add_log_background(msg, level)
                    time.sleep(0.5)
            
            # 在线程中运行模拟
            thread = threading.Thread(target=simulate_crawler)
            thread.start()
            st.success("模拟爬虫日志启动")
    
    # 日志显示区域
    st.markdown("---")
    st.subheader("📝 实时日志显示")
    
    # 使用现代化日志查看器
    log_viewer.render_modern(height=400, show_controls=True)
    
    # 统计信息
    st.markdown("---")
    st.subheader("📊 统计信息")
    
    col7, col8, col9 = st.columns(3)
    
    with col7:
        log_count = len(st.session_state.get('log_entries', []))
        st.metric("Session 日志数", log_count)
    
    with col8:
        from src.biddingcsg.ui.components.log_viewer import global_log_queue
        queue_size = global_log_queue.qsize()
        st.metric("队列大小", queue_size)
    
    with col9:
        # 检查日志文件
        log_file = Path("logs/crawler_realtime.log")
        if log_file.exists():
            file_size = log_file.stat().st_size
            st.metric("日志文件大小", f"{file_size} bytes")
        else:
            st.metric("日志文件", "不存在")
    
    # 调试信息
    st.markdown("---")
    st.subheader("🔧 调试信息")
    
    # 显示session state信息
    with st.expander("Session State 内容"):
        relevant_keys = [k for k in st.session_state.keys() if 'log' in k.lower()]
        for key in relevant_keys:
            st.write(f"**{key}**: {type(st.session_state[key])}")
            if key == 'log_entries' and st.session_state[key]:
                st.write(f"  - 总数: {len(st.session_state[key])}")
                st.write(f"  - 最新: {st.session_state[key][-1]['formatted'] if st.session_state[key] else 'None'}")
    
    # 文件日志内容
    with st.expander("文件日志内容（最后10行）"):
        log_file = Path("logs/crawler_realtime.log")
        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    last_lines = lines[-10:] if len(lines) > 10 else lines
                    st.code('\n'.join(last_lines), language='text')
            except Exception as e:
                st.error(f"读取日志文件失败: {e}")
        else:
            st.info("日志文件不存在")

if __name__ == "__main__":
    st.set_page_config(
        page_title="日志测试",
        page_icon="🧪",
        layout="wide"
    )
    
    test_log_functionality() 