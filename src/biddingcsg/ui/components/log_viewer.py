import streamlit as st
from datetime import datetime
from typing import List, Dict

class LogViewer:
    """日志查看器组件"""
    
    def __init__(self, max_lines: int = 100):
        """
        初始化日志查看器
        
        Args:
            max_lines: 最大显示行数
        """
        self.max_lines = max_lines
        
        # 初始化session state中的日志缓冲区
        if 'log_buffer' not in st.session_state:
            st.session_state.log_buffer = []
    
    def add_log(self, message: str, level: str = "INFO"):
        """
        添加日志消息
        
        Args:
            message: 日志消息
            level: 日志级别 (INFO, WARNING, ERROR, SUCCESS)
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # 根据级别添加颜色和图标
        level_config = {
            "INFO": {"icon": "ℹ️", "color": "#333333"},
            "WARNING": {"icon": "⚠️", "color": "#ff8c00"},
            "ERROR": {"icon": "❌", "color": "#ff4444"},
            "SUCCESS": {"icon": "✅", "color": "#00aa00"},
            "DEBUG": {"icon": "🔍", "color": "#888888"}
        }
        
        config = level_config.get(level, level_config["INFO"])
        log_entry = {
            'timestamp': timestamp,
            'level': level,
            'message': message,
            'icon': config['icon'],
            'color': config['color'],
            'full_text': f"[{timestamp}] {config['icon']} {message}"
        }
        
        # 添加到缓冲区
        st.session_state.log_buffer.append(log_entry)
        
        # 限制缓冲区大小
        if len(st.session_state.log_buffer) > self.max_lines:
            st.session_state.log_buffer.pop(0)
    
    def clear_logs(self):
        """清空日志"""
        st.session_state.log_buffer = []
    
    def render(self, height: int = 400, title: str = "📝 实时日志", auto_scroll: bool = True):
        """
        渲染日志显示区域
        
        Args:
            height: 显示区域高度
            title: 标题
            auto_scroll: 是否自动滚动到底部
        """
        with st.container():
            # 标题栏
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.subheader(title)
            
            with col2:
                if st.button("🗑️ 清空日志", key="clear_logs_btn"):
                    self.clear_logs()
                    st.rerun()
            
            with col3:
                log_count = len(st.session_state.log_buffer)
                st.metric("日志条数", log_count)
            
            # 日志显示区域
            if st.session_state.log_buffer:
                # 生成日志文本
                log_text = "\n".join([entry['full_text'] for entry in st.session_state.log_buffer])
                
                # 使用text_area显示日志
                st.text_area(
                    "日志内容",
                    value=log_text,
                    height=height,
                    disabled=True,
                    key="log_display_area",
                    help="实时显示爬虫运行日志",
                    label_visibility="collapsed"
                )
                
                # 如果启用自动滚动，添加JavaScript实现
                if auto_scroll:
                    st.markdown(
                        """
                        <script>
                        // 自动滚动到底部
                        setTimeout(function() {
                            const logArea = window.parent.document.querySelector('[data-testid="stTextArea"] textarea');
                            if (logArea) {
                                logArea.scrollTop = logArea.scrollHeight;
                            }
                        }, 100);
                        </script>
                        """,
                        unsafe_allow_html=True
                    )
            else:
                st.info("🔄 等待日志输出...")
    
    def render_compact(self, max_display_lines: int = 10):
        """
        渲染紧凑型日志显示
        
        Args:
            max_display_lines: 最大显示行数
        """
        if st.session_state.log_buffer:
            # 只显示最新的几条日志
            recent_logs = st.session_state.log_buffer[-max_display_lines:]
            
            for log_entry in recent_logs:
                # 根据日志级别使用不同的显示方式
                if log_entry['level'] == "ERROR":
                    st.error(f"{log_entry['timestamp']} - {log_entry['message']}")
                elif log_entry['level'] == "WARNING":
                    st.warning(f"{log_entry['timestamp']} - {log_entry['message']}")
                elif log_entry['level'] == "SUCCESS":
                    st.success(f"{log_entry['timestamp']} - {log_entry['message']}")
                else:
                    st.info(f"{log_entry['timestamp']} - {log_entry['message']}")
        else:
            st.info("🔄 等待日志输出...")
    
    def render_with_filter(self, height: int = 400, show_levels: List[str] = None):
        """
        渲染带过滤功能的日志显示
        
        Args:
            height: 显示区域高度
            show_levels: 要显示的日志级别列表，None表示显示所有
        """
        with st.container():
            # 过滤器
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.subheader("📝 日志查看器")
            
            with col2:
                available_levels = ["INFO", "WARNING", "ERROR", "SUCCESS", "DEBUG"]
                if show_levels is None:
                    show_levels = available_levels
                
                selected_levels = st.multiselect(
                    "日志级别过滤",
                    available_levels,
                    default=show_levels,
                    key="log_level_filter"
                )
            
            # 过滤日志
            filtered_logs = [
                entry for entry in st.session_state.log_buffer 
                if entry['level'] in selected_levels
            ]
            
            # 显示过滤后的日志
            if filtered_logs:
                log_text = "\n".join([entry['full_text'] for entry in filtered_logs])
                st.text_area(
                    "过滤后的日志",
                    value=log_text,
                    height=height,
                    disabled=True,
                    key="filtered_log_display_area",
                    label_visibility="collapsed"
                )
            else:
                st.info("🔍 没有符合过滤条件的日志")
    
    def get_logs_as_text(self) -> str:
        """
        获取所有日志的文本格式
        
        Returns:
            str: 格式化的日志文本
        """
        if not st.session_state.log_buffer:
            return "暂无日志记录"
        
        return "\n".join([entry['full_text'] for entry in st.session_state.log_buffer])
    
    def export_logs(self, filename: str = None) -> str:
        """
        导出日志到文件
        
        Args:
            filename: 文件名，如果为None则自动生成
            
        Returns:
            str: 导出的文件路径
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"crawler_logs_{timestamp}.txt"
        
        log_content = self.get_logs_as_text()
        
        # 在Streamlit中提供下载
        st.download_button(
            label="📥 下载日志文件",
            data=log_content,
            file_name=filename,
            mime="text/plain",
            key="download_logs_btn"
        )
        
        return filename

class ProgressViewer:
    """进度查看器组件"""
    
    def __init__(self):
        """初始化进度查看器"""
        # 不需要在这里初始化，使用CrawlerConfigPage中的progress_info
        pass
    
    def update_progress(self, current: int, total: int, message: str = ""):
        """
        更新进度
        
        Args:
            current: 当前进度
            total: 总数
            message: 进度消息
        """
        percentage = (current / total * 100) if total > 0 else 0
        
        if 'progress_info' in st.session_state:
            st.session_state.progress_info.update({
                'current': current,
                'total': total,
                'message': message,
                'percentage': percentage
            })
    
    def render(self, show_details: bool = True):
        """
        渲染进度显示
        
        Args:
            show_details: 是否显示详细信息
        """
        if 'progress_info' not in st.session_state:
            return
            
        data = st.session_state.progress_info
        
        # 进度条
        progress_value = max(0, min(1, data['percentage'] / 100))
        st.progress(progress_value)
        
        if show_details:
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(
                    "进度",
                    f"{data['current']}/{data['total']}",
                    f"{data['percentage']:.1f}%"
                )
            
            with col2:
                if data['message']:
                    st.info(data['message'])
    
    def reset(self):
        """重置进度"""
        if 'progress_info' in st.session_state:
            st.session_state.progress_info.update({
                'current': 0,
                'total': 0,
                'message': '准备中...',
                'percentage': 0.0
            }) 