import streamlit as st
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
import queue
import time

# 全局日志队列（线程安全，后台线程写，主线程读）
global_log_queue = queue.Queue()

class ModernLogViewer:
    """现代化日志查看器 - 推荐方案：全局队列+主线程同步session_state"""
    def __init__(self, max_lines: int = 200):
        self.max_lines = max_lines
        self.log_file_path = Path("logs/crawler_realtime.log")
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_session_state()
        self.last_file_size = 0
        self.last_check_time = 0
        # 添加文件监控状态
        self.last_file_mtime = 0

    def _init_session_state(self):
        if 'log_entries' not in st.session_state:
            st.session_state.log_entries = []
        if 'log_auto_refresh' not in st.session_state:
            st.session_state.log_auto_refresh = True
        if 'log_last_update' not in st.session_state:
            st.session_state.log_last_update = datetime.now()
        # 添加强制刷新计数器
        if 'log_force_refresh_count' not in st.session_state:
            st.session_state.log_force_refresh_count = 0

    @staticmethod
    def add_log_background(message: str, level: str = "INFO"):
        """后台线程安全写入全局队列和文件"""
        try:
            # 添加到全局队列
            global_log_queue.put((message, level))
            
            # 同时写入日志文件，确保日志不丢失
            import os
            from datetime import datetime
            
            log_dir = Path("logs")
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / "crawler_realtime.log"
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            level_icons = {
                "INFO": "ℹ️", "WARNING": "⚠️", "ERROR": "❌", 
                "SUCCESS": "✅", "DEBUG": "🔍"
            }
            icon = level_icons.get(level, "ℹ️")
            
            formatted_line = f"[{timestamp}] {icon} {message}\n"
            
            # 追加写入日志文件
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(formatted_line)
                f.flush()  # 强制刷新到磁盘
                
            # 尝试更新session state（如果在主线程上下文中）
            try:
                if hasattr(st, 'session_state'):
                    # 触发强制刷新
                    if 'log_force_refresh_count' in st.session_state:
                        st.session_state.log_force_refresh_count += 1
            except:
                pass
                
        except Exception as e:
            # 如果出错，至少保证队列写入
            try:
                global_log_queue.put((message, level))
            except:
                pass

    def _process_global_log_queue(self):
        """主线程/fragment定时同步全局队列到session_state"""
        processed_count = 0
        max_process = 50  # 限制每次处理的最大数量，防止界面卡顿
        
        while not global_log_queue.empty() and processed_count < max_process:
            try:
                message, level = global_log_queue.get_nowait()
                self._add_log_to_session(message, level)
                processed_count += 1
            except queue.Empty:
                break
        return processed_count

    def _add_log_to_session(self, message: str, level: str = "INFO"):
        timestamp = datetime.now()
        level_config = {
            "INFO": {"icon": "ℹ️", "color": "#0066cc"},
            "WARNING": {"icon": "⚠️", "color": "#ff8c00"},
            "ERROR": {"icon": "❌", "color": "#dc3545"},
            "SUCCESS": {"icon": "✅", "color": "#28a745"},
            "DEBUG": {"icon": "🔍", "color": "#6c757d"}
        }
        config = level_config.get(level, level_config["INFO"])
        log_entry = {
            'timestamp': timestamp,
            'level': level,
            'message': message,
            'icon': config['icon'],
            'color': config['color'],
            'formatted': f"[{timestamp.strftime('%H:%M:%S')}] {config['icon']} {message}"
        }
        st.session_state.log_entries.append(log_entry)
        if len(st.session_state.log_entries) > self.max_lines:
            st.session_state.log_entries.pop(0)
        st.session_state.log_last_update = datetime.now()

    def _check_log_file(self):
        """增强的文件监控功能"""
        if not self.log_file_path.exists():
            return 0
        try:
            file_stat = self.log_file_path.stat()
            current_size = file_stat.st_size
            current_mtime = file_stat.st_mtime
            
            # 检查文件是否有更新
            if current_size != self.last_file_size or current_mtime != self.last_file_mtime:
                with open(self.log_file_path, 'r', encoding='utf-8') as f:
                    if current_size < self.last_file_size:
                        # 文件被重置，重新读取
                        content = f.read()
                        st.session_state.log_entries = []
                        self.last_file_size = 0
                    else:
                        # 读取新增内容
                        f.seek(self.last_file_size)
                        content = f.read()
                
                self.last_file_size = current_size
                self.last_file_mtime = current_mtime
                
                if content.strip():
                    lines = content.strip().split('\n')
                    processed_lines = 0
                    for line in lines:
                        line = line.strip()
                        if line:
                            self._parse_log_line(line)
                            processed_lines += 1
                    if processed_lines > 0:
                        st.session_state.log_last_update = datetime.now()
                    return processed_lines
        except Exception as e:
            self._add_log_to_session(f"读取日志文件错误: {e}", "ERROR")
        return 0

    def _parse_log_line(self, line: str):
        """解析日志文件中的行"""
        if "ERROR" in line or "❌" in line:
            level = "ERROR"
        elif "WARNING" in line or "⚠️" in line:
            level = "WARNING"
        elif "SUCCESS" in line or "✅" in line:
            level = "SUCCESS"
        elif "DEBUG" in line or "🔍" in line:
            level = "DEBUG"
        else:
            level = "INFO"
        message = line
        if "] " in line:
            parts = line.split("] ", 1)
            if len(parts) > 1:
                message = parts[1]
        self._add_log_to_session(message, level)

    @st.fragment(run_every=1)  # 每秒检查一次
    def _log_refresh_fragment(self):
        """基于文档方案的实时日志更新机制"""
        try:
            self._init_session_state()
            
            if not st.session_state.get('log_auto_refresh', True):
                return
            
            current_time = datetime.now().strftime("%H:%M:%S")
            
            # 处理队列中的新日志
            new_logs_from_queue = self._get_new_logs_from_queue()
            
            # 检查文件更新
            file_logs_count = self._check_log_file()
            
            # 如果有新日志，添加并强制刷新UI
            total_new_logs = len(new_logs_from_queue) + file_logs_count
            
            if total_new_logs > 0:
                st.session_state.log_last_update = datetime.now()
                
                # 显示更新状态
                st.success(f"🔄 **{current_time}** - 新增 {total_new_logs} 条日志")
                
                # 控制刷新频率（避免过于频繁）
                last_rerun = st.session_state.get('last_rerun_time', 0)
                current_timestamp = time.time()
                
                if current_timestamp - last_rerun > 1:  # 最少间隔1秒
                    st.session_state.last_rerun_time = current_timestamp
                    st.rerun()  # 强制刷新UI
            else:
                # 显示静态状态
                queue_size = global_log_queue.qsize()
                if queue_size > 0:
                    st.info(f"🔄 **{current_time}** - 队列中有 {queue_size} 条日志待处理")
                else:
                    st.markdown(f"🔄 **自动刷新中** - {current_time}")
                
        except Exception as e:
            st.error(f"日志刷新异常: {e}")
    
    def _get_new_logs_from_queue(self):
        """从队列获取新日志 - 按文档方案实现"""
        new_logs = []
        max_process = 50  # 限制每次处理数量
        
        processed = 0
        while not global_log_queue.empty() and processed < max_process:
            try:
                message, level = global_log_queue.get_nowait()
                self._add_log_to_session(message, level)
                new_logs.append((message, level))
                processed += 1
            except queue.Empty:
                break
        
        return new_logs

    def _force_log_update(self):
        if 'log_force_update_counter' not in st.session_state:
            st.session_state.log_force_update_counter = 0
        st.session_state.log_force_update_counter += 1

    def render_modern(self, height: int = 400, show_controls: bool = True, disable_auto_refresh: bool = False):
        self._init_session_state()
        if show_controls:
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            with col1:
                st.markdown("**📝 实时日志**")
            with col2:
                auto_refresh = st.checkbox(
                    "自动刷新", 
                    value=st.session_state.get('log_auto_refresh', True),
                    key="log_auto_refresh_checkbox"
                )
                st.session_state.log_auto_refresh = auto_refresh
            with col3:
                if st.button("🔄 刷新", key="manual_refresh_btn"):
                    # 手动强制刷新
                    self._get_new_logs_from_queue()
                    self._check_log_file()
                    st.rerun()
            with col4:
                if st.button("🗑️ 清空", key="clear_logs_btn"):
                    self.clear_logs()
        log_count = len(st.session_state.log_entries)
        last_update = st.session_state.get('log_last_update', datetime.now())
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        with col_stat1:
            st.metric("日志条数", log_count)
        with col_stat2:
            st.metric("队列大小", global_log_queue.qsize())
        with col_stat3:
            update_ago = (datetime.now() - last_update).total_seconds()
            st.metric("上次更新", f"{update_ago:.0f}秒前")
        if st.session_state.get('log_auto_refresh', True) and not disable_auto_refresh:
            self._log_refresh_fragment()
        # 手动处理已在 fragment 中完成，这里注释掉避免重复处理
        # manual_queue_count = self._process_global_log_queue()
        # manual_file_count = self._check_log_file()
        if st.session_state.log_entries:
            # 按文档方案：最新日志显示在上方
            display_logs = list(reversed(st.session_state.log_entries))
            
            # 安全的日志格式处理
            log_lines = []
            for entry in display_logs:
                try:
                    if isinstance(entry, dict) and 'formatted' in entry:
                        log_lines.append(entry['formatted'])
                    elif isinstance(entry, (tuple, list)) and len(entry) >= 2:
                        # 处理元组格式的日志条目 (message, level)
                        message, level = entry[0], entry[1]
                        timestamp = datetime.now().strftime('%H:%M:%S')
                        level_config = {
                            "INFO": "ℹ️", "WARNING": "⚠️", "ERROR": "❌", 
                            "SUCCESS": "✅", "DEBUG": "🔍"
                        }
                        icon = level_config.get(level, "ℹ️")
                        log_lines.append(f"[{timestamp}] {icon} {message}")
                    else:
                        # 回退处理
                        log_lines.append(str(entry))
                except Exception as e:
                    log_lines.append(f"[Error] 日志格式错误: {entry}")
            
            log_text = '\n'.join(log_lines)
            
            st.text_area(
                "日志内容",
                value=log_text,
                height=height,
                disabled=True,
                key="modern_log_display",
                help="实时显示的日志内容（最新日志在上方），支持自动刷新",
                label_visibility="collapsed"
            )
            if st.session_state.get('log_auto_refresh', True):
                st.markdown("""
                <script>
                setTimeout(function() {
                    const textAreas = window.parent.document.querySelectorAll('textarea[aria-label=\"日志内容\"]');
                    textAreas.forEach(function(textarea) {
                        if (textarea) {
                            textarea.scrollTop = 0;
                        }
                    });
                }, 100);
                </script>
                """, unsafe_allow_html=True)
        else:
            st.info("📝 等待日志输出...")
            if st.session_state.get('log_auto_refresh', True):
                st.markdown("🔄 **自动刷新已启用** - 每1秒检查新日志")
            else:
                st.markdown("⏸️ **自动刷新已暂停** - 点击刷新按钮手动更新")

    def render_compact(self, max_display: int = 5):
        self._init_session_state()
        self._process_global_log_queue()
        self._check_log_file()
        if st.session_state.log_entries:
            recent_entries = st.session_state.log_entries[-max_display:]
            for entry in reversed(recent_entries):
                try:
                    if isinstance(entry, dict):
                        level = entry.get('level', 'INFO')
                        message = entry.get('message', str(entry))
                        timestamp = entry.get('timestamp', datetime.now()).strftime('%H:%M:%S')
                    elif isinstance(entry, (tuple, list)) and len(entry) >= 2:
                        message, level = entry[0], entry[1]
                        timestamp = datetime.now().strftime('%H:%M:%S')
                    else:
                        level = "INFO"
                        message = str(entry)
                        timestamp = datetime.now().strftime('%H:%M:%S')
                    
                    if level == "ERROR":
                        st.error(f"[{timestamp}] {message}")
                    elif level == "WARNING":
                        st.warning(f"[{timestamp}] {message}")
                    elif level == "SUCCESS":
                        st.success(f"[{timestamp}] {message}")
                    else:
                        st.info(f"[{timestamp}] {message}")
                except Exception as e:
                    st.error(f"[Error] 日志显示错误: {entry}")
        else:
            st.info("🔄 等待日志输出...")

    def clear_logs(self):
        self._init_session_state()
        st.session_state.log_entries = []
        while not global_log_queue.empty():
            try:
                global_log_queue.get_nowait()
            except queue.Empty:
                break
        try:
            with open(self.log_file_path, 'w', encoding='utf-8') as f:
                f.write("")
            self.last_file_size = 0
        except Exception as e:
            st.error(f"清空日志文件失败: {e}")

    def export_logs(self) -> Optional[str]:
        """导出日志到文件 - 按文档方案保持时间顺序"""
        self._init_session_state()
        if not st.session_state.log_entries:
            st.warning("没有日志可以导出")
            return None
        
        # 按文档方案：导出时保持原始时间顺序（不反转）
        original_order_logs = st.session_state.log_entries
        
        # 生成导出内容
        export_content = []
        export_content.append(f"# 爬虫日志导出")
        export_content.append(f"# 导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        export_content.append(f"# 总日志数: {len(original_order_logs)}")
        export_content.append("")
        
        # 安全的导出格式处理
        for entry in original_order_logs:
            try:
                if isinstance(entry, dict) and 'formatted' in entry:
                    export_content.append(entry['formatted'])
                elif isinstance(entry, (tuple, list)) and len(entry) >= 2:
                    # 处理元组格式的日志条目
                    message, level = entry[0], entry[1]
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    level_config = {
                        "INFO": "ℹ️", "WARNING": "⚠️", "ERROR": "❌", 
                        "SUCCESS": "✅", "DEBUG": "🔍"
                    }
                    icon = level_config.get(level, "ℹ️")
                    export_content.append(f"[{timestamp}] {icon} {message}")
                else:
                    export_content.append(str(entry))
            except Exception as e:
                export_content.append(f"[Error] 导出格式错误: {entry}")
        
        final_content = '\n'.join(export_content)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"crawler_logs_{timestamp}.txt"
        
        st.download_button(
            label="📥 下载日志文件",
            data=final_content,
            file_name=filename,
            mime="text/plain",
            key="download_modern_logs"
        )
        
        st.success(f"✅ 日志导出成功！文件名: {filename}")
        return final_content

_global_log_viewer = None

def get_global_log_viewer() -> ModernLogViewer:
    global _global_log_viewer
    if _global_log_viewer is None:
        _global_log_viewer = ModernLogViewer()
    return _global_log_viewer

def add_log(message: str, level: str = "INFO"):
    ModernLogViewer.add_log_background(message, level)

LogViewer = ModernLogViewer

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