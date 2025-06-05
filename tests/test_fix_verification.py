#!/usr/bin/env python3
"""
验证实时日志修复是否成功
运行真实的爬虫应用并检查Fragment和UI刷新机制
"""

import streamlit as st
import sys
import subprocess
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def main():
    st.set_page_config(
        page_title="修复验证",
        page_icon="✅",
        layout="wide"
    )
    
    st.title("✅ 实时日志修复验证")
    
    st.markdown("""
    ## 修复内容摘要
    
    参考 `tests/test_realtime_log_fixed.py` 的成功经验，对 `src/biddingcsg/ui/pages/crawler_config.py` 进行了以下修复：
    
    ### 🔧 关键修复点
    
    1. **添加实时刷新Fragment**
       - 新增 `_log_refresh_fragment()` 方法
       - 使用 `@st.fragment(run_every=1)` 每秒检查一次
       - 强制调用 `st.rerun()` 刷新UI
    
    2. **队列处理优化**
       - 新增 `_get_new_logs_from_queue()` 方法
       - 非阻塞队列读取，性能控制（最多50条/次）
       - 正确的异常处理
    
    3. **导入修复**
       - 添加缺少的 `import queue` 和 `time`
       - 修复模块导入路径为正确的 `src.biddingcsg.*`
    
    ### 📋 验证步骤
    
    1. 点击下方按钮启动真实的爬虫应用
    2. 在爬虫应用中：
       - 填写搜索参数（如："汕头供电局"）
       - 点击"开始爬取"
       - 切换到"📝 实时日志"标签
       - 观察日志是否在1-2秒内实时显示
    
    3. 期望结果：
       - ✅ 日志实时显示，无需手动刷新
       - ✅ 最新日志显示在上方
       - ✅ UI响应迅速，Fragment正常工作
    """)
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🚀 启动真实爬虫应用", type="primary", use_container_width=True):
            st.info("正在启动爬虫应用...")
            
            try:
                # 构建启动命令
                cmd = [
                    sys.executable, "-m", "streamlit", "run",
                    str(project_root / "src" / "biddingcsg" / "ui" / "app.py"),
                    "--server.port", "8502",  # 使用不同端口避免冲突
                    "--server.address", "localhost",
                    "--server.headless", "false"
                ]
                
                # 启动应用
                subprocess.Popen(cmd, cwd=project_root)
                
                st.success("✅ 爬虫应用已启动！")
                st.markdown("🌐 访问地址: http://localhost:8502")
                
            except Exception as e:
                st.error(f"❌ 启动失败: {e}")
    
    with col2:
        if st.button("🧪 重新运行测试文件", use_container_width=True):
            st.info("正在启动测试文件...")
            
            try:
                cmd = [
                    sys.executable, "-m", "streamlit", "run",
                    str(project_root / "tests" / "test_realtime_log_fixed.py"),
                    "--server.port", "8503",
                    "--server.address", "localhost"
                ]
                
                subprocess.Popen(cmd, cwd=project_root)
                
                st.success("✅ 测试文件已启动！")
                st.markdown("🌐 访问地址: http://localhost:8503")
                
            except Exception as e:
                st.error(f"❌ 启动失败: {e}")
    
    st.markdown("---")
    
    with st.expander("📝 修复代码对比"):
        st.markdown("""
        ### 添加的核心Fragment代码：
        
        ```python
        @st.fragment(run_every=1)  # 每1秒刷新一次
        def _log_refresh_fragment(self):
            '''实时日志刷新Fragment - 基于streamlit_realtime_log_solution.md文档方案'''
            try:
                # 初始化刷新控制
                if 'last_log_refresh' not in st.session_state:
                    st.session_state.last_log_refresh = time.time()
                    
                current_time = time.time()
                
                # 控制最小刷新间隔（1秒），避免过度刷新
                if current_time - st.session_state.last_log_refresh >= 1.0:
                    # 处理队列中的新日志
                    new_logs_added = self._get_new_logs_from_queue()
                    
                    # 如果有新日志或爬虫正在运行，强制刷新UI
                    if new_logs_added or st.session_state.get('crawler_running', False):
                        st.session_state.last_log_refresh = current_time
                        # 强制UI刷新 - 这是关键！
                        st.rerun()
                        
            except Exception as e:
                logger.error(f"日志刷新Fragment错误: {e}")
        ```
        
        ### 修改的日志标签页：
        
        ```python
        def _render_log_tab(self):
            '''渲染日志标签页'''
            st.markdown("### 📝 实时日志监控")
            
            # 启动实时日志刷新Fragment - 参考测试文件的成功方案
            self._log_refresh_fragment()  # <-- 新增这一行
            
            # 使用现代化日志查看器
            self.log_viewer.render_modern(height=500, show_controls=True)
            # ... 其余代码不变
        ```
        """)

if __name__ == "__main__":
    main() 