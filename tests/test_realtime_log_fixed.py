#!/usr/bin/env python3
"""
基于 streamlit_realtime_log_solution.md 方案的测试
验证修复后的实时日志显示功能
"""

import streamlit as st
import sys
import time
import queue
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.biddingcsg.ui.components.log_viewer import ModernLogViewer, get_global_log_viewer, global_log_queue

def main():
    st.set_page_config(
        page_title="实时日志修复测试",
        page_icon="🔧",
        layout="wide"
    )
    
    st.title("🔧 实时日志显示修复测试")
    st.markdown("基于 `streamlit_realtime_log_solution.md` 方案的验证测试")
    
    # 状态初始化
    if 'test_start_time' not in st.session_state:
        st.session_state.test_start_time = time.time()
    if 'test_running' not in st.session_state:
        st.session_state.test_running = False
    
    # 获取日志查看器实例
    log_viewer = get_global_log_viewer()
    
    # 控制面板
    st.subheader("🎮 测试控制面板")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🚀 开始模拟爬虫"):
            st.session_state.test_running = True
            st.session_state.test_start_time = time.time()
            st.session_state.simulated_log_count = 0  # 重置计数器
            ModernLogViewer.add_log_background("🚀 启动爬虫测试...", "SUCCESS")
            st.success("开始模拟爬虫运行")
    
    with col2:
        if st.button("🛑 停止模拟"):
            st.session_state.test_running = False
            ModernLogViewer.add_log_background("🛑 停止爬虫测试", "WARNING")
            st.warning("已停止模拟")
    
    with col3:
        if st.button("📝 添加测试日志"):
            ModernLogViewer.add_log_background("🧪 手动测试日志", "INFO")
            st.info("已添加测试日志")
    
    with col4:
        if st.button("🗑️ 清空所有日志"):
            log_viewer.clear_logs()
            st.success("已清空日志")
    
    # 状态显示
    st.subheader("📊 运行状态")
    
    col5, col6, col7, col8 = st.columns(4)
    
    with col5:
        status = "🟢 运行中" if st.session_state.test_running else "🔴 已停止"
        st.metric("模拟状态", status)
    
    with col6:
        elapsed = time.time() - st.session_state.test_start_time
        st.metric("运行时间", f"{elapsed:.0f}秒")
    
    with col7:
        log_count = len(st.session_state.get('log_entries', []))
        st.metric("日志条数", log_count)
    
    with col8:
        queue_size = global_log_queue.qsize()
        st.metric("队列大小", queue_size)
    
    # 模拟爬虫日志生成
    simulate_crawler_logs()
    
    # 日志显示区域
    st.markdown("---")
    st.subheader("📝 实时日志显示（修复后）")
    
    # 使用修复后的日志查看器
    log_viewer.render_modern(height=400, show_controls=True)
    
    # 测试结果分析
    st.markdown("---")
    st.subheader("📋 测试验证要点")
    
    with st.expander("✅ 修复效果验证清单"):
        st.markdown("""
        **按照 streamlit_realtime_log_solution.md 文档方案，应该验证以下功能：**
        
        1. **实时更新** ✅
           - 日志应该在1-2秒内显示到界面上
           - 不需要手动刷新页面
        
        2. **日志顺序** ✅
           - 最新日志显示在文本框的上方
           - 便于阅读最新内容
        
        3. **UI强制刷新** ✅
           - 使用 `st.rerun()` 强制更新界面
           - Fragment 每秒检查一次
        
        4. **队列机制** ✅
           - 使用线程安全的 queue.Queue
           - 生产者消费者模式
        
        5. **导出功能** ✅
           - 导出时保持原始时间顺序
           - 界面显示最新在上，导出保持时间顺序
        
        6. **性能控制** ✅
           - 限制刷新频率（最少1秒间隔）
           - 限制每次处理的日志数量
        """)
    
    # 调试信息
    with st.expander("🔧 调试信息"):
        st.write("**Session State 相关键:**")
        debug_keys = [k for k in st.session_state.keys() if 'log' in k.lower() or 'test' in k.lower()]
        for key in debug_keys:
            value = st.session_state[key]
            if isinstance(value, list):
                st.write(f"- {key}: {type(value)} (长度: {len(value)})")
            else:
                st.write(f"- {key}: {value}")

@st.fragment(run_every=1)  # 每秒检查一次
def simulate_crawler_logs():
    """模拟爬虫日志生成 - 按文档方案实现"""
    if st.session_state.get('test_running', False):
        # 初始化模拟相关状态
        if 'simulated_log_count' not in st.session_state:
            st.session_state.simulated_log_count = 0
        
        elapsed = time.time() - st.session_state.get('test_start_time', time.time())
        expected_count = int(elapsed / 2)  # 每2秒一条日志（更快的测试节奏）
        
        # 预定义的爬虫日志消息
        messages = [
            "🌐 初始化浏览器...",
            "🔍 访问搜索页面...",
            "📝 输入搜索关键词...",
            "🔎 点击搜索按钮...",
            "📄 进入搜索结果页面...",
            "📊 找到 100 条记录，共 10 页",
            "📖 处理第 1/10 页",
            "🔍 页面找到 15 个项目",
            "🔗 访问详细页面...",
            "✅ 成功解析项目信息",
            "📖 处理第 2/10 页",
            "⚠️ 跳过重复项目",
            "📖 处理第 3/10 页",
            "💾 保存数据到本地",
            "✅ 爬取任务完成！"
        ]
        
        # 检查是否需要添加新日志
        if (expected_count > st.session_state.simulated_log_count and 
            st.session_state.simulated_log_count < len(messages)):
            
            message = messages[st.session_state.simulated_log_count]
            level = "SUCCESS" if "✅" in message else ("WARNING" if "⚠️" in message else "INFO")
            
            ModernLogViewer.add_log_background(message, level)
            st.session_state.simulated_log_count += 1
            
            # 如果完成所有日志，自动停止
            if st.session_state.simulated_log_count >= len(messages):
                st.session_state.test_running = False
                ModernLogViewer.add_log_background("🎉 模拟测试完成！", "SUCCESS")

if __name__ == "__main__":
    main() 