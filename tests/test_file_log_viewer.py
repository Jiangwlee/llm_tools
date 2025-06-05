#!/usr/bin/env python3
"""
文件日志查看器测试
模拟真实的爬虫写入日志文件的场景
"""

import streamlit as st
import time
import threading
from datetime import datetime
from pathlib import Path
import sys
import os

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 配置页面
st.set_page_config(
    page_title="文件日志测试",
    page_icon="📄",
    layout="wide"
)

st.title("📄 文件日志查看器测试")

# 日志文件路径
log_file = Path("test_crawler.log")

# 初始化
if 'file_writing' not in st.session_state:
    st.session_state.file_writing = False

# 模拟爬虫写入文件的函数
def write_log_file():
    """模拟爬虫持续写入日志文件"""
    try:
        # 清空现有文件
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write("")
        
        messages = [
            "[INFO] 🚀 启动爬虫引擎",
            "[INFO] 🔧 初始化配置", 
            "[SUCCESS] ⚙️ 设置ProactorEventLoop成功",
            "[INFO] 🌐 连接到目标网站",
            "[INFO] 📄 解析页面结构",
            "[INFO] 📊 提取数据字段",
            "[INFO] 💾 保存到数据库",
            "[SUCCESS] ✅ 处理完成一页",
            "[INFO] 🔄 继续下一页",
            "[INFO] 📈 统计信息更新"
        ]
        
        for i, msg in enumerate(messages):
            if st.session_state.file_writing:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log_line = f"[{timestamp}] {msg}\n"
                
                # 写入文件
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(log_line)
                
                time.sleep(2)  # 每2秒写入一条
            else:
                break
        
        # 写入完成消息
        if st.session_state.file_writing:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            final_line = f"[{timestamp}] [SUCCESS] ⏹️ 爬虫任务完成\n"
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(final_line)
        
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        error_line = f"[{timestamp}] [ERROR] ❌ 爬虫错误: {e}\n"
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(error_line)

# 控制面板
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("📝 开始写入日志文件"):
        if not st.session_state.file_writing:
            st.session_state.file_writing = True
            # 启动写入线程
            write_thread = threading.Thread(target=write_log_file, daemon=True)
            write_thread.start()
            st.success("✅ 开始写入日志文件")
        else:
            st.warning("⚠️ 已在写入中")

with col2:
    if st.button("⏹️ 停止写入"):
        st.session_state.file_writing = False
        st.info("已停止写入")

with col3:
    if st.button("🗑️ 清空日志文件"):
        if log_file.exists():
            log_file.unlink()
        st.success("已清空日志文件")

st.markdown("---")

# 使用原始日志查看器
try:
    from src.biddingcsg.ui.components.log_viewer_v2 import ModernLogViewer
    
    st.subheader("🔍 原始日志查看器测试")
    
    # 创建日志查看器实例
    if 'log_viewer' not in st.session_state:
        st.session_state.log_viewer = ModernLogViewer(log_file_path=log_file)
    
    log_viewer = st.session_state.log_viewer
    
    # 渲染日志查看器
    log_viewer.render_modern(height=400, show_controls=True)
    
except Exception as e:
    st.error(f"无法加载原始日志查看器: {e}")
    st.info("这可能是因为没有找到 biddingcsg 包")
    
    # 提供简单的文件显示
    st.subheader("📋 简单文件内容显示")
    
    if log_file.exists():
        content = log_file.read_text(encoding='utf-8')
        if content.strip():
            st.text_area("日志内容:", content, height=300)
        else:
            st.info("日志文件为空")
    else:
        st.info("日志文件不存在")

# 文件状态
st.markdown("---")
st.subheader("📊 文件状态")

col_stat1, col_stat2, col_stat3 = st.columns(3)

with col_stat1:
    exists = log_file.exists()
    st.metric("文件存在", "是" if exists else "否")

with col_stat2:
    if log_file.exists():
        size = log_file.stat().st_size
        st.metric("文件大小", f"{size} 字节")
    else:
        st.metric("文件大小", "0 字节")

with col_stat3:
    if log_file.exists():
        lines = len(log_file.read_text(encoding='utf-8').splitlines())
        st.metric("行数", lines)
    else:
        st.metric("行数", 0)

# 实时文件内容（简化版）
if st.checkbox("📺 实时显示文件内容"):
    @st.fragment(run_every=1)
    def show_file_content():
        if log_file.exists():
            content = log_file.read_text(encoding='utf-8')
            if content.strip():
                lines = content.strip().split('\n')
                st.markdown("**最新10行:**")
                for line in lines[-10:]:
                    st.text(line)
            else:
                st.info("文件为空")
        else:
            st.info("文件不存在")
    
    show_file_content() 