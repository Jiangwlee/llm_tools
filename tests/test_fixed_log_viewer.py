#!/usr/bin/env python3
"""
测试修复后的日志查看器
验证实时刷新功能是否正常工作
"""

import streamlit as st
import sys
import threading
import time
from pathlib import Path
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 配置页面
st.set_page_config(
    page_title="修复后的日志查看器测试",
    page_icon="🔧",
    layout="wide"
)

st.title("🔧 修复后的日志查看器测试")
st.markdown("验证实时刷新功能是否正常工作")

# 导入修复后的组件
try:
    from src.biddingcsg.ui.components.log_viewer_v2 import get_global_log_viewer
    
    # 获取全局日志查看器
    log_viewer = get_global_log_viewer()
    
    st.success("✅ 成功加载修复后的日志查看器组件")
    
    # 初始化时间模拟爬虫的session state
    if 'crawler_start_time' not in st.session_state:
        st.session_state.crawler_start_time = None
    if 'crawler_message_count' not in st.session_state:
        st.session_state.crawler_message_count = 0
    
    # 基于时间的模拟爬虫（在fragment中处理）
    @st.fragment(run_every=1)
    def time_based_crawler():
        """基于时间的模拟爬虫"""
        if st.session_state.crawler_start_time and st.session_state.get('real_crawler_running', False):
            elapsed = datetime.now() - st.session_state.crawler_start_time
            expected_messages = int(elapsed.total_seconds() // 2)  # 每2秒一条
            
            messages = [
                ("🚀 启动爬虫引擎", "SUCCESS"),
                ("🔧 初始化配置文件", "INFO"),
                ("⚙️ 设置ProactorEventLoop成功", "SUCCESS"),
                ("🌐 连接到目标网站", "INFO"),
                ("📄 解析页面结构", "INFO"),
                ("📊 提取数据字段", "INFO"),
                ("💾 保存到数据库", "SUCCESS"),
                ("✅ 第一页处理完成", "SUCCESS"),
                ("🔄 继续处理下一页", "INFO"),
                ("📈 更新统计信息", "INFO")
            ]
            
            # 发送新消息
            if expected_messages > st.session_state.crawler_message_count and st.session_state.crawler_message_count < len(messages):
                msg, level = messages[st.session_state.crawler_message_count]
                log_viewer.add_log_threadsafe(f"{msg} (第{st.session_state.crawler_message_count+1}步)", level)
                st.session_state.crawler_message_count += 1
                st.info(f"🔥 实时发送: {msg}")
            
            # 完成处理
            elif st.session_state.crawler_message_count >= len(messages):
                log_viewer.add_log_threadsafe("🎉 爬虫任务全部完成！", "SUCCESS")
                st.session_state.real_crawler_running = False
                st.session_state.crawler_start_time = None
                st.balloons()
            
            # 显示进度
            progress = st.session_state.crawler_message_count / len(messages)
            st.progress(progress, f"爬虫进度: {st.session_state.crawler_message_count}/{len(messages)}")
    
    # 运行基于时间的爬虫
    time_based_crawler()
    
    # 控制面板
    st.markdown("### 🎮 测试控制面板")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🚀 启动实时爬虫测试"):
            if not st.session_state.get('real_crawler_running', False):
                st.session_state.real_crawler_running = True
                st.session_state.crawler_start_time = datetime.now()
                st.session_state.crawler_message_count = 0
                log_viewer.add_log_threadsafe("🎯 用户启动实时爬虫测试（基于时间）", "INFO")
                st.success("✅ 已启动实时爬虫测试")
            else:
                st.warning("⚠️ 爬虫测试已在运行")
    
    with col2:
        if st.button("⏹️ 停止爬虫测试"):
            st.session_state.real_crawler_running = False
            log_viewer.add_log_threadsafe("🛑 用户停止爬虫测试", "WARNING")
            st.info("已停止爬虫测试")
    
    with col3:
        if st.button("📝 添加单条测试日志"):
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_viewer.add_log_threadsafe(f"🧪 [{timestamp}] 手动测试日志", "INFO")
            st.success("已添加测试日志")
    
    with col4:
        if st.button("🗑️ 清空所有日志"):
            log_viewer.clear_logs()
            st.success("已清空日志")
    
    # 批量测试按钮
    st.markdown("### 📦 批量测试")
    
    col5, col6, col7 = st.columns(3)
    
    with col5:
        if st.button("📦 批量添加5条日志"):
            for i in range(5):
                log_viewer.add_log_threadsafe(f"📋 批量测试日志 #{i+1}", "INFO")
            st.success("已批量添加5条日志")
    
    with col6:
        if st.button("🌟 添加各种级别日志"):
            levels = [
                ("这是信息日志", "INFO"),
                ("这是成功日志", "SUCCESS"),
                ("这是警告日志", "WARNING"),
                ("这是错误日志", "ERROR"),
                ("这是调试日志", "DEBUG")
            ]
            for msg, level in levels:
                log_viewer.add_log_threadsafe(msg, level)
            st.success("已添加各种级别的日志")
    
    with col7:
        # 显示爬虫状态
        if st.session_state.get('real_crawler_running', False):
            st.error("🔄 爬虫测试运行中...")
        else:
            st.success("⏹️ 爬虫测试已停止")
    
    st.markdown("---")
    
    # 渲染日志查看器
    st.markdown("### 📋 实时日志显示")
    st.markdown("**观察要点：新日志应该在1-2秒内自动显示**")
    
    log_viewer.render_modern(height=500, show_controls=True)
    
    # 使用说明
    st.markdown("---")
    st.markdown("### 📖 使用说明")
    
    st.info("""
    **测试步骤：**
    1. 点击 "🚀 启动实时爬虫测试" - 观察是否每2秒自动显示新日志
    2. 点击 "📝 添加单条测试日志" - 观察单条日志是否立即显示
    3. 点击 "📦 批量添加5条日志" - 观察批量日志是否立即显示
    
    **判断标准：**
    ✅ **成功** - 新日志在1-2秒内自动出现在界面上
    ❌ **失败** - 新日志需要手动刷新页面或点击按钮才显示
    
    **技术说明：**
    - 使用了 `st.rerun()` 强制刷新UI
    - 每秒自动检查队列和文件变化
    - 线程安全的日志添加机制
    """)
    
except ImportError as e:
    st.error(f"❌ 无法加载日志查看器组件: {e}")
    st.info("请确保 biddingcsg 包存在并且路径正确")
    
except Exception as e:
    st.error(f"❌ 发生错误: {e}")
    st.exception(e) 