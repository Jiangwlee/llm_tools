#!/usr/bin/env python3
"""
测试日志显示顺序
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime
import time

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

st.set_page_config(page_title="日志顺序测试", page_icon="📄", layout="wide")
st.title("📄 日志显示顺序测试")

try:
    from src.biddingcsg.ui.components.log_viewer_v2 import get_global_log_viewer
    log_viewer = get_global_log_viewer()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📝 添加时间戳日志"):
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_viewer.add_log_threadsafe(f"时间戳: {timestamp}", "INFO")
    
    with col2:
        if st.button("📦 批量添加5条日志"):
            for i in range(5):
                timestamp = datetime.now().strftime("%H:%M:%S")
                log_viewer.add_log_threadsafe(f"批量日志 #{i+1} - {timestamp}", "INFO")
                time.sleep(0.2)
    
    with col3:
        if st.button("🗑️ 清空日志"):
            log_viewer.clear_logs()
    
    st.markdown("---")
    st.markdown("### 📋 日志显示（最新日志应该在上方）")
    log_viewer.render_modern(height=400, show_controls=True)
    
    st.info("✅ 验证要点：新添加的日志应该出现在日志区域的最上方")

except Exception as e:
    st.error(f"错误: {e}") 