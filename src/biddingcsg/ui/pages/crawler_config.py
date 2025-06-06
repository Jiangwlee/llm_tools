import streamlit as st
import threading
import os
import time
import queue
import json
from datetime import date, datetime, timedelta
from pathlib import Path
import logging
import sys
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from biddingcsg.models.config import CrawlerConfig
from biddingcsg.services.storage import LocalStorageService  
from biddingcsg.services.crawler import BiddingCrawlerService
from biddingcsg.services.info_extractor import create_info_extractor
from biddingcsg.ui.components.log_viewer import ModernLogViewer, get_global_log_viewer, global_log_queue

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CrawlerConfigPage:
    """现代化爬虫配置页面 - 使用最新的 Streamlit 功能"""
    
    def __init__(self):
        """初始化页面"""
        self._init_session_state()
        
        # 使用全局日志查看器实例
        self.log_viewer = get_global_log_viewer()
        
        # 进度相关
        self._init_progress_state()
    
    def _init_session_state(self):
        """初始化session state"""
        defaults = {
            'crawler_running': False,
            'crawler_thread': None,
            'current_session': None,
            'crawler_finished': False,
            'storage_service': None,
            'show_clear_cache_dialog': False,
            # 价格提取相关状态
            'extraction_running': False,
            'extraction_thread': None,
            'extraction_completed': False,
            'extraction_results': [],
            'extraction_logs': [],
            'stop_extraction': False,
            # 测试功能相关状态
            'testing_in_progress': False,
            'test_results': None,
            'test_file_path': None,
            'test_start_time': None,
            # 文件管理相关状态
            'show_price_files_dialog': False,
            'show_cleanup_dialog': False,
            'selected_files': [],
            'file_operation_result': None,
            'last_scan_time': None,
            'price_files_info': []
        }
        
        for key, default_value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = default_value
    
    def _init_progress_state(self):
        """初始化进度状态"""
        if 'progress_info' not in st.session_state:
            st.session_state.progress_info = {
                'current': 0,
                'total': 0,
                'message': '准备中...',
                'percentage': 0.0
            }
    
    @st.fragment(run_every=3)  # 每3秒检查爬虫状态
    def _crawler_status_fragment(self):
        """爬虫状态检查片段"""
        if st.session_state.crawler_running:
            # 检查线程是否还活着
            if st.session_state.crawler_thread and not st.session_state.crawler_thread.is_alive():
                st.session_state.crawler_running = False
                st.session_state.crawler_thread = None
                st.session_state.crawler_finished = True
    
    def render(self):
        """渲染页面"""
        st.title("🕷️ 招标公告数据下载器 v2.0")
        st.markdown("---")
        
        # 启动状态检查片段
        self._crawler_status_fragment()
        
        # 启动提取状态检查片段
        self._extraction_status_fragment()
        
        # 检查是否刚完成
        if st.session_state.get('crawler_finished', False):
            st.session_state.crawler_finished = False
            st.balloons()
            st.success("🎉 爬虫任务已完成！请查看下方日志了解详情。")
        
        # 主要布局
        tab1, tab2, tab3 = st.tabs(["⚙️ 配置与控制", "📝 实时日志", "📊 结果统计"])
        
        with tab1:
            self._render_config_tab()
        
        with tab2:
            self._render_log_tab()
        
        with tab3:
            self._render_stats_tab()
        
        # 清空缓存弹窗对话框
        self._render_clear_cache_dialog()
    
    def _render_config_tab(self):
        """渲染配置标签页"""
        # 启动Fragment刷新，确保实时状态信息更新
        self._log_refresh_fragment()
        
        # 左右分栏，各占一半空间
        col1, col2 = st.columns([1, 1])
        
        with col1:
            self._render_config_form()
        
        with col2:
            self._render_realtime_status()
    
    def _render_config_form(self):
        """渲染配置表单"""
        st.subheader("⚙️ 爬虫配置")
        
        with st.form("modern_crawler_config", clear_on_submit=False):
            # 基本配置
            st.markdown("#### 🔍 搜索参数")
            
            col1, col2 = st.columns(2)
            with col1:
                search_keyword = st.text_input(
                    "搜索关键词",
                    placeholder="例如：汕头供电局",
                    help="输入要搜索的关键词",
                    key="modern_search_keyword"
                )
                
                max_pages = st.number_input(
                    "最大爬取页数",
                    min_value=1,
                    max_value=1000,
                    value=10,
                    key="modern_max_pages"
                )
            
            with col2:
                announcement_type = st.selectbox(
                    "公告类型",
                    ["服务", "货物", "工程", "全部类型"],
                    key="modern_announcement_type"
                )
                
                earliest_date = st.date_input(
                    "最早日期",
                    value=None,
                    help="只爬取此日期之后的公告",
                    key="modern_earliest_date"
                )
            
            # 输出配置
            st.markdown("#### 📁 输出设置")
            default_output_dir = str(Path.cwd() / "output" / "bidding_data")
            output_directory = st.text_input(
                "输出目录",
                value=default_output_dir,
                key="modern_output_directory"
            )
            
            # 高级设置
            with st.expander("🔧 高级设置", expanded=False):
                col3, col4 = st.columns(2)
                
                with col3:
                    request_delay = st.slider(
                        "请求间隔（秒）",
                        0.5, 10.0, 2.0, 0.5,
                        key="modern_request_delay"
                    )
                    
                    enable_dedup = st.checkbox(
                        "启用去重",
                        value=True,
                        key="modern_enable_dedup"
                    )
                
                with col4:
                    headless_mode = st.checkbox(
                        "无头模式",
                        value=True,
                        key="modern_headless_mode"
                    )
                    
                    timeout = st.number_input(
                        "页面超时（秒）",
                        10, 120, 30,
                        key="modern_timeout"
                    )
            
            # 表单提交按钮
            col1, col2, col3 = st.columns(3)
            
            with col1:
                submitted = st.form_submit_button(
                    "🚀 开始爬取",
                    type="primary",
                    disabled=st.session_state.crawler_running,
                    use_container_width=True
                )
            
            with col2:
                extract_price = st.form_submit_button(
                    "💰 提取成交价",
                    disabled=st.session_state.crawler_running or st.session_state.get('extraction_running', False),
                    use_container_width=True,
                    help="从已下载的HTML文件中提取价格信息"
                )
            
            with col3:
                test_extraction = st.form_submit_button(
                    "🧪 测试价格提取",
                    disabled=st.session_state.crawler_running or st.session_state.get('extraction_running', False) or st.session_state.get('testing_in_progress', False),
                    use_container_width=True,
                    help="快速测试单个文件的价格提取效果"
                )
            
            # 处理爬虫启动
            if submitted and not st.session_state.crawler_running:
                if self._validate_config(search_keyword, output_directory):
                    config = self._create_config(
                        search_keyword, max_pages, announcement_type,
                        earliest_date, output_directory, request_delay,
                        enable_dedup, headless_mode, timeout
                    )
                    self._start_crawler(config)
            
            # 处理价格提取
            if extract_price and not st.session_state.get('extraction_running', False):
                if self._validate_config(search_keyword, output_directory):
                    self._start_price_extraction(search_keyword, output_directory)
            
            # 处理测试价格提取
            if test_extraction and not st.session_state.get('testing_in_progress', False):
                if self._validate_config(search_keyword, output_directory):
                    self._start_test_price_extraction(search_keyword, output_directory)
        
        # 文件管理区域
        self._render_file_management_section(output_directory)
    
    def _render_realtime_status(self):
        """渲染实时状态组件"""
        st.subheader("📊 实时状态")
        
        # 爬虫状态显示
        if st.session_state.crawler_running:
            st.success("🔄 爬虫运行中...")
            
            # 进度信息
            progress_data = st.session_state.progress_info
            progress_value = max(0, min(1, progress_data['percentage'] / 100))
            
            st.progress(progress_value)
            
            prog_col1, prog_col2 = st.columns(2)
            with prog_col1:
                st.metric(
                    "进度",
                    f"{progress_data['current']}/{progress_data['total']}"
                )
            with prog_col2:
                st.metric(
                    "完成度",
                    f"{progress_data['percentage']:.1f}%"
                )
            
            if progress_data['message']:
                st.info(progress_data['message'])
        else:
            if st.session_state.current_session:
                session = st.session_state.current_session
                if session.status == "completed":
                    st.success(f"✅ 上次爬取完成！\n共获取 {session.total_items_found} 条记录")
                elif session.status == "failed":
                    st.error(f"❌ 上次爬取失败:\n{session.error_message}")
                else:
                    st.info("⏳ 爬虫待机中")
            else:
                st.info("⏳ 爬虫待机中，请配置参数后启动")
        
        # 实时统计信息
        st.markdown("#### 📈 实时统计")
        
        stat_col1, stat_col2 = st.columns(2)
        
        with stat_col1:
            log_count = len(st.session_state.get('log_entries', []))
            st.metric("日志条数", log_count)
        
        with stat_col2:
            queue_size = global_log_queue.qsize()
            st.metric("待处理", queue_size)
        
        # 控制按钮
        st.markdown("#### 🎮 控制操作")
        
        ctrl_col1, ctrl_col2, ctrl_col3 = st.columns(3)
        
        with ctrl_col1:
            if st.button(
                "🛑 停止爬取",
                disabled=not st.session_state.crawler_running,
                use_container_width=True,
                type="secondary"
            ):
                self._stop_crawler()
        
        with ctrl_col2:
            if st.button(
                "🗑️ 清空日志",
                use_container_width=True
            ):
                self.log_viewer.clear_logs()
                st.success("日志已清空")
        
        with ctrl_col3:
            if st.button(
                "🧹 清空缓存",
                use_container_width=True,
                type="secondary",
                help="删除所有已保存的HTML文件和元数据"
            ):
                st.session_state.show_clear_cache_dialog = True
        
        # 实时日志显示区域
        st.markdown("#### 📝 实时日志输出")
        
        if st.session_state.get('log_entries'):
            # 显示最新的日志，最新的在上方
            display_logs = list(reversed(st.session_state.log_entries[-15:]))  # 显示最近15条
            
            # 安全的日志格式处理
            log_lines = []
            for entry in display_logs:
                try:
                    if isinstance(entry, dict) and 'formatted' in entry:
                        log_lines.append(entry['formatted'])
                    elif isinstance(entry, (tuple, list)) and len(entry) >= 2:
                        # 处理元组格式的日志条目
                        message, level = entry[0], entry[1]
                        # 使用日志条目的实际时间戳或当前时间
                        if isinstance(entry, dict) and 'timestamp' in entry:
                            timestamp = entry['timestamp'].strftime('%H:%M:%S')
                        else:
                            timestamp = datetime.now().strftime('%H:%M:%S')
                        
                        level_config = {
                            "INFO": "ℹ️", "WARNING": "⚠️", "ERROR": "❌", 
                            "SUCCESS": "✅", "DEBUG": "🔍"
                        }
                        icon = level_config.get(level, "ℹ️")
                        log_lines.append(f"[{timestamp}] {icon} {message}")
                    else:
                        log_lines.append(str(entry))
                except Exception:
                    log_lines.append(f"[Error] 日志格式错误")
            
            log_text = '\n'.join(log_lines)
            
            # 设置白色背景
            st.markdown("""
            <style>
            /* 实时日志输出区域白色背景 */
            div[data-testid="stTextArea"] textarea {
                background-color: #ffffff !important;
            }
            </style>
            """, unsafe_allow_html=True)
            
            st.text_area(
                "实时日志",
                value=log_text,
                height=350,
                disabled=True,
                key="realtime_log_display",
                help="显示最近15条日志（最新在上方）",
                label_visibility="collapsed"
            )
            
            # 实时统计和提示
            log_total = len(st.session_state.log_entries)
            st.caption(f"📊 显示最近 15 条日志，总计 {log_total} 条 | 💡 查看完整日志请切换到 '📝 实时日志' 标签页")
        else:
            # 空日志状态也设置白色背景
            st.markdown("""
            <style>
            /* 空日志显示区域白色背景 */
            div[data-testid="stTextArea"] textarea {
                background-color: #ffffff !important;
            }
            </style>
            """, unsafe_allow_html=True)
            
            st.text_area(
                "实时日志",
                value="📝 等待日志输出...\n\n🔄 启动爬虫后日志将在此处实时显示\n📋 最新的日志会显示在最上方\n⏱️ 日志将每秒自动刷新",
                height=350,
                disabled=True,
                key="empty_log_display",
                label_visibility="collapsed"
            )
    
    def _render_log_tab(self):
        """渲染日志标签页"""
        st.markdown("### 📝 实时日志监控")
        
        # 显示调试信息
        st.info(f"🔧 调试信息: Fragment刷新计数 = {st.session_state.get('fragment_counter', 0)}, 队列大小 = {global_log_queue.qsize()}, 日志条数 = {len(st.session_state.get('log_entries', []))}")
        
        # 启动实时日志刷新Fragment - 参考测试文件的成功方案
        self._log_refresh_fragment()
        
        # 添加手动测试按钮
        if st.button("🧪 添加测试日志到队列"):
            ModernLogViewer.add_log_background("🧪 手动测试日志", "INFO")
            st.success("已添加测试日志")
        
        # 使用现代化日志查看器，禁用内部的自动刷新避免重复
        self.log_viewer.render_modern(height=500, show_controls=True, disable_auto_refresh=True)
        
        # 额外的日志操作
        st.markdown("---")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📥 导出日志", use_container_width=True):
                self.log_viewer.export_logs()
        
        with col2:
            # 紧凑显示开关
            if st.button("📋 紧凑显示", use_container_width=True):
                st.markdown("#### 最近日志（紧凑模式）")
                self.log_viewer.render_compact(max_display=5)
        
        with col3:
            # 刷新统计
            log_count = len(st.session_state.get('log_entries', []))
            queue_size = global_log_queue.qsize()
            st.metric("总日志/队列", f"{log_count}/{queue_size}")
        
        # 显示最近的几条日志预览
        if st.session_state.get('log_entries'):
            st.markdown("#### 📋 最近日志预览")
            recent_logs = st.session_state.log_entries[-3:]  # 显示最近3条
            for entry in reversed(recent_logs):  # 最新的在上面
                try:
                    if isinstance(entry, dict) and 'formatted' in entry:
                        st.text(entry['formatted'])
                    elif isinstance(entry, (tuple, list)) and len(entry) >= 2:
                        message, level = entry[0], entry[1]
                        timestamp = datetime.now().strftime('%H:%M:%S')
                        level_config = {
                            "INFO": "ℹ️", "WARNING": "⚠️", "ERROR": "❌", 
                            "SUCCESS": "✅", "DEBUG": "🔍"
                        }
                        icon = level_config.get(level, "ℹ️")
                        st.text(f"[{timestamp}] {icon} {message}")
                    else:
                        st.text(str(entry))
                except Exception:
                    st.text(f"[Error] 无法显示日志: {entry}")
            
            st.markdown("💡 **提示**: 切换到 '📝 实时日志' 标签查看完整日志")
    
    @st.fragment(run_every=1)  # 每1秒刷新一次 - 直接参考测试文件的成功经验
    def _log_refresh_fragment(self):
        """实时日志刷新Fragment - 直接处理，避免委托调用"""
        try:
            # 添加Fragment计数器用于调试
            if 'fragment_counter' not in st.session_state:
                st.session_state.fragment_counter = 0
            st.session_state.fragment_counter += 1
            
            # 初始化刷新控制
            if 'last_log_refresh' not in st.session_state:
                st.session_state.last_log_refresh = time.time()
                
            current_time = time.time()
            
            # 控制最小刷新间隔（1秒），避免过度刷新
            if current_time - st.session_state.last_log_refresh >= 1.0:
                # 确保日志查看器的session state已初始化
                self.log_viewer._init_session_state()
                
                # 处理队列中的新日志
                new_logs_added = self._get_new_logs_from_queue()
                
                # 如果有新日志或爬虫正在运行，强制刷新UI
                if new_logs_added or st.session_state.get('crawler_running', False):
                    st.session_state.last_log_refresh = current_time
                    # 强制UI刷新 - 这是关键！
                    st.rerun()
                    
        except Exception as e:
            logger.error(f"日志刷新Fragment错误: {e}")
    
    def _get_new_logs_from_queue(self) -> bool:
        """从队列获取新日志 - 直接实现，参考测试文件"""
        new_logs_added = False
        max_logs_per_cycle = 50  # 性能控制
        
        try:
            for _ in range(max_logs_per_cycle):
                try:
                    # 非阻塞获取
                    message, level = global_log_queue.get_nowait()
                    
                    # 使用日志查看器的方法添加到session state
                    self.log_viewer._add_log_to_session(message, level)
                    new_logs_added = True
                    
                except queue.Empty:
                    break
                    
        except Exception as e:
            logger.error(f"处理日志队列时出错: {e}")
            
        return new_logs_added
    
    def _render_stats_tab(self):
        """渲染统计标签页"""
        st.markdown("### 📊 爬取结果统计")
        
        if st.session_state.current_session:
            session = st.session_state.current_session
            
            # 基本统计
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("总记录数", session.total_items_found)
            
            with col2:
                st.metric("成功下载", session.successful_downloads)
            
            with col3:
                st.metric("失败数量", session.failed_downloads)
            
            with col4:
                success_rate = 0
                if session.total_items_found > 0:
                    success_rate = (session.successful_downloads / session.total_items_found) * 100
                st.metric("成功率", f"{success_rate:.1f}%")
            
            # 会话信息
            st.markdown("#### 📋 会话详情")
            
            info_data = {
                "会话ID": session.session_id,
                "开始时间": session.start_time.strftime("%Y-%m-%d %H:%M:%S"),
                "状态": session.status,
                "搜索关键词": session.config.search_keyword if session.config else "未知",
            }
            
            if session.end_time:
                info_data["结束时间"] = session.end_time.strftime("%Y-%m-%d %H:%M:%S")
                duration = session.end_time - session.start_time
                info_data["持续时间"] = str(duration)
            
            if session.error_message:
                info_data["错误信息"] = session.error_message
            
            for key, value in info_data.items():
                st.text(f"**{key}**: {value}")
        
        else:
            st.info("📭 暂无爬取记录")
        
        # 存储统计
        if st.session_state.get('storage_service'):
            st.markdown("---")
            st.markdown("#### 💾 存储统计")
            
            if st.button("🔄 刷新存储统计"):
                self._show_storage_stats()
    
    def _validate_config(self, search_keyword: str, output_directory: str) -> bool:
        """验证配置参数"""
        if not search_keyword.strip():
            st.error("❌ 搜索关键词不能为空")
            return False
        
        if not output_directory.strip():
            st.error("❌ 输出目录不能为空")
            return False
        
        try:
            Path(output_directory).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            st.error(f"❌ 无法创建输出目录: {e}")
            return False
        
        return True
    
    def _create_config(self, search_keyword: str, max_pages: int, 
                      announcement_type: str, earliest_date: date,
                      output_directory: str, request_delay: float,
                      enable_dedup: bool, headless_mode: bool, timeout: int) -> CrawlerConfig:
        """创建爬虫配置"""
        
        # 处理公告类型
        type_mapping = {
            "服务": "service",
            "货物": "goods", 
            "工程": "engineering",
            "全部类型": "all"
        }
        processed_announcement_type = type_mapping.get(announcement_type, "all")
        
        # 处理日期
        earliest_date_str = earliest_date.isoformat() if earliest_date else None
        
        config = CrawlerConfig(
            search_keyword=search_keyword,
            max_pages=max_pages,
            announcement_type=processed_announcement_type,
            earliest_date=earliest_date_str,
            output_directory=output_directory,
            request_delay=request_delay,
            enable_dedup=enable_dedup,
            headless_mode=headless_mode,
            timeout=timeout
        )
        
        return config
    
    def _start_crawler(self, config: CrawlerConfig):
        """启动爬虫"""
        try:
            # 创建存储服务
            storage_service = LocalStorageService(config)
            st.session_state.storage_service = storage_service
            
            # 创建爬虫服务
            crawler_service = BiddingCrawlerService(config, storage_service)
            
            # 日志回调函数
            def log_callback(message):
                try:
                    ModernLogViewer.add_log_background(message, "INFO")
                except Exception as e:
                    logger.error(f"日志回调错误: {e}")
            
            # 进度回调函数
            def progress_callback(current, total, message):
                try:
                    percentage = (current / total * 100) if total > 0 else 0
                    st.session_state.progress_info.update({
                        'current': current,
                        'total': total,
                        'message': message,
                        'percentage': percentage
                    })
                    
                    # 也记录到日志
                    ModernLogViewer.add_log_background(
                        f"📊 进度更新: {current}/{total} ({percentage:.1f}%) - {message}",
                        "INFO"
                    )
                except Exception as e:
                    logger.error(f"进度回调错误: {e}")
            
            # 爬虫工作线程
            def crawler_worker():
                try:
                    st.session_state.crawler_running = True
                    ModernLogViewer.add_log_background("🚀 启动爬虫任务...", "SUCCESS")
                    
                    session = crawler_service.start_crawling(
                        progress_callback=progress_callback,
                        log_callback=log_callback
                    )
                    
                    st.session_state.current_session = session
                    
                    if session.status == "completed":
                        ModernLogViewer.add_log_background(
                            f"✅ 爬取完成！共获取 {session.total_items_found} 条记录", 
                            "SUCCESS"
                        )
                    else:
                        ModernLogViewer.add_log_background(
                            f"❌ 爬取失败: {session.error_message}", 
                            "ERROR"
                        )
                        
                except Exception as e:
                    ModernLogViewer.add_log_background(f"❌ 爬虫执行异常: {e}", "ERROR")
                    logger.error(f"爬虫执行异常: {e}", exc_info=True)
                finally:
                    st.session_state.crawler_running = False
                    st.session_state.crawler_thread = None
                    st.session_state.crawler_finished = True
            
            # 启动后台线程
            crawler_thread = threading.Thread(target=crawler_worker, daemon=True)
            crawler_thread.start()
            st.session_state.crawler_thread = crawler_thread
            
            ModernLogViewer.add_log_background("✅ 爬虫线程已启动", "SUCCESS")
            st.success("🚀 爬虫已启动！请切换到日志标签页查看实时进度。")
            
        except Exception as e:
            ModernLogViewer.add_log_background(f"❌ 启动爬虫失败: {e}", "ERROR")
            logger.error(f"启动爬虫失败: {e}", exc_info=True)
            st.error(f"启动失败: {e}")
    
    def _stop_crawler(self):
        """停止爬虫"""
        if st.session_state.crawler_running:
            ModernLogViewer.add_log_background("🛑 正在停止爬虫...", "WARNING")
            st.session_state.crawler_running = False
            st.warning("停止信号已发送，爬虫将在安全点停止")
    
    def _render_clear_cache_dialog(self):
        """渲染清空缓存弹窗对话框"""
        if st.session_state.get('show_clear_cache_dialog'):
            @st.dialog("🧹 清空缓存确认", width="large")
            def clear_cache_dialog():
                try:
                    # 获取或创建存储服务实例
                    storage_service = st.session_state.get('storage_service')
                    
                    if not storage_service:
                        # 如果没有存储服务实例，创建一个默认的
                        ModernLogViewer.add_log_background("🔧 创建临时存储服务实例用于清空缓存", "INFO")
                        
                        # 使用默认配置创建存储服务
                        default_config = CrawlerConfig(
                            search_keyword="temp",
                            output_directory=str(Path.cwd() / "output" / "bidding_data")
                        )
                        storage_service = LocalStorageService(default_config)
                    
                    # 显示警告信息
                    st.warning("⚠️ **此操作不可恢复！**")
                    st.markdown("""
                    **将删除以下数据：**
                    - `output/bidding_data/raw_html/` 下的所有HTML文件
                    - `output/bidding_data/metadata/` 下的所有元数据文件
                    - 所有已爬取URL记录
                    """)
                    
                    # 显示当前文件统计
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if storage_service.html_dir.exists():
                            html_files = list(storage_service.html_dir.rglob('*.html'))
                            st.metric("📄 HTML文件", f"{len(html_files)} 个")
                        else:
                            st.metric("📄 HTML文件", "0 个")
                    
                    with col2:
                        if storage_service.metadata_dir.exists():
                            metadata_files = list(storage_service.metadata_dir.glob('*_metadata.json'))
                            st.metric("📋 元数据文件", f"{len(metadata_files)} 个")
                        else:
                            st.metric("📋 元数据文件", "0 个")
                    
                    st.markdown("---")
                    
                    # 确认按钮
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button("❌ 取消", use_container_width=True):
                            ModernLogViewer.add_log_background("📝 用户取消清空操作", "INFO")
                            st.session_state.show_clear_cache_dialog = False
                            st.rerun()
                    
                    with col2:
                        if st.button("✅ 确认清空", type="primary", use_container_width=True):
                            # 执行清空操作
                            self._execute_clear_cache(storage_service)
                            st.session_state.show_clear_cache_dialog = False
                            st.rerun()
                            
                except Exception as e:
                    error_msg = f"❌ 对话框错误: {e}"
                    st.error(error_msg)
                    ModernLogViewer.add_log_background(error_msg, "ERROR")
                    logger.error(f"清空缓存对话框错误: {e}", exc_info=True)
            
            # 显示对话框
            clear_cache_dialog()
    
    def _execute_clear_cache(self, storage_service):
        """执行清空缓存操作"""
        try:
            ModernLogViewer.add_log_background("✅ 用户确认清空缓存，开始执行...", "INFO")
            
            # 显示存储服务基础信息（调试用）
            ModernLogViewer.add_log_background(f"🔍 存储服务实例: {type(storage_service).__name__}", "DEBUG")
            ModernLogViewer.add_log_background(f"🔍 基础目录: {storage_service.base_dir}", "DEBUG")
            ModernLogViewer.add_log_background(f"🔍 HTML目录: {storage_service.html_dir}", "DEBUG")
            ModernLogViewer.add_log_background(f"🔍 元数据目录: {storage_service.metadata_dir}", "DEBUG")
            
            # 执行清空操作
            ModernLogViewer.add_log_background("🧹 正在执行清空缓存操作...", "WARNING")
            
            stats = storage_service.clear_all_cache()
            
            # 显示清理结果
            total_files = stats['html_files_deleted'] + stats['metadata_files_deleted']
            success_msg = (f"✅ 缓存清空完成！"
                          f" 删除HTML文件 {stats['html_files_deleted']} 个，"
                          f" 删除元数据文件 {stats['metadata_files_deleted']} 个，"
                          f" 清理目录 {stats['directories_cleaned']} 个，"
                          f" 总计删除文件 {total_files} 个")
            
            ModernLogViewer.add_log_background(success_msg, "SUCCESS")
            
            # 在对话框中也显示成功消息
            st.success(f"🎉 缓存清空完成！\n\n"
                      f"• 删除HTML文件: {stats['html_files_deleted']} 个\n"
                      f"• 删除元数据文件: {stats['metadata_files_deleted']} 个\n"
                      f"• 清理目录: {stats['directories_cleaned']} 个\n"
                      f"• 总计删除文件: {total_files} 个")
            
        except Exception as e:
            error_msg = f"❌ 清空缓存失败: {e}"
            st.error(error_msg)
            ModernLogViewer.add_log_background(error_msg, "ERROR")
            logger.error(f"清空缓存失败: {e}", exc_info=True)
    
    def _show_storage_stats(self):
        """显示存储统计信息"""
        if st.session_state.get('storage_service'):
            try:
                stats = st.session_state.storage_service.get_storage_stats()
                
                st.markdown("#### 💾 详细存储统计")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("已爬取URL", stats.get('total_crawled_urls', 0))
                
                with col2:
                    st.metric("HTML文件", stats.get('html_files_count', 0))
                
                with col3:
                    storage_size = stats.get('total_storage_size', 0)
                    size_mb = storage_size / (1024 * 1024) if storage_size > 0 else 0
                    st.metric("存储大小", f"{size_mb:.2f} MB")
                
                if stats.get('latest_crawl_date'):
                    st.info(f"📅 最近爬取时间: {stats['latest_crawl_date']}")
                    
            except Exception as e:
                st.error(f"获取统计信息失败: {e}")
    
    def _start_price_extraction(self, keyword: str, output_directory: str):
        """启动价格提取任务"""
        # 重置提取状态
        st.session_state.extraction_running = True
        st.session_state.extraction_completed = False
        st.session_state.extraction_results = []
        st.session_state.extraction_logs = []
        st.session_state.stop_extraction = False
        
        # 检查HTML目录是否存在
        html_dir = Path(output_directory) / "raw_html"
        if not html_dir.exists():
            st.error(f"❌ HTML文件目录不存在: {html_dir}")
            st.session_state.extraction_running = False
            return
        
        ModernLogViewer.add_log_background(f"🚀 开始从 {html_dir} 中提取 '{keyword}' 相关的价格信息...", "INFO")
        
        def progress_callback(current, total, message):
            """进度更新回调"""
            # 通过session state共享进度信息
            st.session_state.extraction_progress = {
                'current': current,
                'total': total,
                'message': message,
                'percentage': (current / total * 100) if total > 0 else 0
            }
        
        def log_callback(message):
            """日志更新回调"""
            ModernLogViewer.add_log_background(message, "INFO")
        
        def extraction_worker():
            """后台提取工作线程"""
            try:
                # 创建提取器
                extractor = create_info_extractor(str(html_dir))
                
                # 执行批量提取
                results = extractor.extract_info_batch(
                    keyword=keyword,
                    extract_type="price",
                    progress_callback=progress_callback,
                    log_callback=log_callback
                )
                
                # 保存结果
                if results:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_file = Path(output_directory) / f"price_extraction_{keyword}_{timestamp}.json"
                    
                    # 添加详细的保存日志
                    ModernLogViewer.add_log_background(f"📁 输出目录: {output_directory}", "INFO")
                    ModernLogViewer.add_log_background(f"📄 目标文件路径: {output_file}", "INFO")
                    ModernLogViewer.add_log_background(f"📊 提取结果数量: {len(results)}", "INFO")
                    
                    # 确保输出目录存在
                    output_file.parent.mkdir(parents=True, exist_ok=True)
                    ModernLogViewer.add_log_background(f"✅ 确保目录存在: {output_file.parent}", "INFO")
                    
                    if extractor.save_results(results, str(output_file)):
                        ModernLogViewer.add_log_background(f"🎉 提取完成！结果已保存到: {output_file}", "SUCCESS")
                        ModernLogViewer.add_log_background(f"📏 文件大小: {output_file.stat().st_size / 1024:.1f}KB", "INFO")
                        st.session_state.extraction_results = results
                        st.session_state.extraction_output_file = str(output_file)
                    else:
                        ModernLogViewer.add_log_background("❌ 保存结果文件失败", "ERROR")
                        ModernLogViewer.add_log_background(f"🔍 检查目录权限: {output_file.parent}", "ERROR")
                else:
                    ModernLogViewer.add_log_background("⚠️ 未找到匹配的价格信息", "WARNING")
                    ModernLogViewer.add_log_background(f"🔍 检查HTML目录: {html_dir}", "INFO")
                    
                    # 显示HTML目录中的文件
                    if html_dir.exists():
                        html_files = list(html_dir.rglob("*.html"))
                        ModernLogViewer.add_log_background(f"📊 HTML目录文件数: {len(html_files)}", "INFO")
                        if html_files:
                            ModernLogViewer.add_log_background("📋 HTML文件列表 (前5个):", "INFO")
                            for i, f in enumerate(html_files[:5]):
                                ModernLogViewer.add_log_background(f"  {i+1}. {f.name}", "INFO")
                    else:
                        ModernLogViewer.add_log_background(f"❌ HTML目录不存在: {html_dir}", "ERROR")
                
                # 标记完成
                st.session_state.extraction_completed = True
                
            except Exception as e:
                error_msg = f"❌ 提取过程发生错误: {str(e)}"
                ModernLogViewer.add_log_background(error_msg, "ERROR")
                logger.error(f"价格提取异常: {e}")
            finally:
                st.session_state.extraction_running = False
        
        # 启动后台线程
        import threading
        thread = threading.Thread(target=extraction_worker)
        thread.daemon = True
        st.session_state.extraction_thread = thread
        thread.start()
        
        st.success("🚀 价格提取任务已启动！请查看日志标签页了解实时进度。")
    
    @st.fragment(run_every=2)  # 每2秒检查一次提取状态
    def _extraction_status_fragment(self):
        """提取状态检查片段"""
        if st.session_state.get('extraction_completed', False):
            # 显示完成结果
            self._show_extraction_results()
            # 重置完成状态，避免重复显示
            st.session_state.extraction_completed = False
    
    def _show_extraction_results(self):
        """显示提取完成的结果"""
        results = st.session_state.get('extraction_results', [])
        output_file = st.session_state.get('extraction_output_file', '')
        
        if results:
            st.success("🎉 价格提取任务完成！")
            
            # 显示统计信息
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("处理文件数", len(results))
            with col2:
                success_count = len([r for r in results if r.get('success', False)])
                st.metric("成功提取", success_count)
            with col3:
                success_rate = (success_count / len(results) * 100) if results else 0
                st.metric("成功率", f"{success_rate:.1f}%")
            
            # 显示下载链接
            if output_file and Path(output_file).exists():
                with open(output_file, 'r', encoding='utf-8') as f:
                    json_data = f.read()
                
                st.download_button(
                    label="📥 下载提取结果",
                    data=json_data,
                    file_name=Path(output_file).name,
                    mime="application/json",
                    use_container_width=True
                )
    
    def _start_test_price_extraction(self, keyword: str, output_directory: str):
        """启动测试价格提取功能"""
        from datetime import datetime
        
        # 重置测试状态
        st.session_state.testing_in_progress = True
        st.session_state.test_results = None
        st.session_state.test_file_path = None
        st.session_state.test_start_time = datetime.now()
        
        # 检查HTML目录是否存在
        html_dir = Path(output_directory) / "raw_html"
        if not html_dir.exists():
            st.error(f"❌ HTML文件目录不存在: {html_dir}")
            st.session_state.testing_in_progress = False
            return
        
        try:
            ModernLogViewer.add_log_background("🧪 开始测试价格提取功能...", "INFO")
            
            # 第1步：文件发现
            ModernLogViewer.add_log_background(f"📁 扫描目录: {html_dir}", "INFO")
            ModernLogViewer.add_log_background(f"🔍 搜索关键词: {keyword}", "INFO")
            
            test_file = self._find_latest_test_file(html_dir, keyword)
            
            if not test_file:
                ModernLogViewer.add_log_background("❌ 未找到匹配的公示公告文件", "ERROR")
                st.session_state.testing_in_progress = False
                return
            
            st.session_state.test_file_path = str(test_file)
            ModernLogViewer.add_log_background(f"📄 选择测试文件: {test_file.name}", "SUCCESS")
            
            # 第2步：文件信息展示
            file_stat = test_file.stat()
            file_size = file_stat.st_size / 1024  # KB
            file_time = datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            
            ModernLogViewer.add_log_background(f"📅 文件时间: {file_time}", "INFO")
            ModernLogViewer.add_log_background(f"📏 文件大小: {file_size:.1f}KB", "INFO")
            
            # 第3步：文件处理
            ModernLogViewer.add_log_background("📝 开始解析HTML文件...", "INFO")
            
            test_result = self._process_test_file(test_file, "price", keyword)
            
            if test_result:
                st.session_state.test_results = test_result
                
                # 计算处理时间
                processing_time = (datetime.now() - st.session_state.test_start_time).total_seconds()
                
                ModernLogViewer.add_log_background(f"⏱️ 处理耗时: {processing_time:.1f}秒", "INFO")
                ModernLogViewer.add_log_background("🎉 测试完成！", "SUCCESS")
                
                # 显示结果
                self._display_test_results(test_result)
            else:
                ModernLogViewer.add_log_background("❌ 测试处理失败", "ERROR")
                
        except Exception as e:
            error_msg = f"❌ 测试过程发生错误: {str(e)}"
            ModernLogViewer.add_log_background(error_msg, "ERROR")
            logger.error(f"测试价格提取异常: {e}")
        finally:
            st.session_state.testing_in_progress = False
    
    def _find_latest_test_file(self, html_dir: Path, keyword: str) -> Optional[Path]:
        """找到最新的匹配测试文件"""
        try:
            matching_files = []
            
            # 递归查找所有HTML文件
            for html_file in html_dir.rglob("*.html"):
                # 检查文件名是否以"公示公告"开头
                if html_file.name.startswith("公示公告"):
                    try:
                        # 检查文件内容是否包含关键词
                        with open(html_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if keyword.lower() in content.lower():
                                matching_files.append(html_file)
                                ModernLogViewer.add_log_background(f"  ✅ 找到匹配文件: {html_file.name}", "DEBUG")
                    except Exception as e:
                        ModernLogViewer.add_log_background(f"  ❌ 读取文件失败 {html_file.name}: {e}", "WARNING")
                        continue
            
            if not matching_files:
                ModernLogViewer.add_log_background("⚠️ 未找到包含关键词的公示公告文件", "WARNING")
                return None
            
            ModernLogViewer.add_log_background(f"📊 找到 {len(matching_files)} 个匹配的公示公告文件", "INFO")
            
            # 按修改时间排序，选择最新的
            latest_file = max(matching_files, key=lambda f: f.stat().st_mtime)
            
            ModernLogViewer.add_log_background(f"🎯 选择最新文件: {latest_file.name}", "SUCCESS")
            return latest_file
            
        except Exception as e:
            ModernLogViewer.add_log_background(f"❌ 文件扫描失败: {e}", "ERROR")
            return None
    
    def _process_test_file(self, file_path: Path, extract_type: str, keyword: str) -> Optional[Dict[str, Any]]:
        """处理单个测试文件"""
        try:
            # 读取HTML文件
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # 解析HTML
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 提取基本信息
            title = self._extract_title_from_soup(soup)
            date = self._extract_date_from_soup(soup)
            
            ModernLogViewer.add_log_background(f"📝 文件标题: {title}", "INFO")
            ModernLogViewer.add_log_background(f"📅 公告日期: {date}", "INFO")
            
            # 查找内容区域
            content_div = soup.find('div', class_='Content')
            if not content_div:
                content_div = soup.find('body') or soup
            
            # 检查是否包含价格信息
            has_price_info = self._check_price_info(content_div)
            
            if has_price_info:
                ModernLogViewer.add_log_background("✅ 检测到价格相关信息", "SUCCESS")
            else:
                ModernLogViewer.add_log_background("⚠️ 未检测到明显的价格信息", "WARNING")
            
            # 调用LLM进行提取
            ModernLogViewer.add_log_background("🤖 调用LLM进行价格信息提取...", "INFO")
            
            from biddingcsg.llm.chat import LLMHelper
            
            extracted_info = None
            if extract_type == "price":
                extracted_info = LLMHelper.llm_summary(str(content_div))
            
            if extracted_info:
                ModernLogViewer.add_log_background("✅ LLM提取完成", "SUCCESS")
                # 显示提取结果的前200个字符
                preview = extracted_info[:200] + "..." if len(extracted_info) > 200 else extracted_info
                ModernLogViewer.add_log_background(f"💰 提取结果预览: {preview}", "INFO")
            else:
                ModernLogViewer.add_log_background("❌ LLM提取失败或返回空结果", "ERROR")
            
            # 构建结果
            result = {
                "file_path": str(file_path),
                "file_name": file_path.name,
                "title": title,
                "date": date,
                "keyword": keyword,
                "extract_type": extract_type,
                "has_price_info": has_price_info,
                "success": extracted_info is not None,
                "extracted_info": extracted_info,
                "processed_at": datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            ModernLogViewer.add_log_background(f"❌ 文件处理失败: {e}", "ERROR")
            return None
    
    def _extract_title_from_soup(self, soup: BeautifulSoup) -> str:
        """从BeautifulSoup对象中提取标题"""
        title_selectors = ['h1.s-title', 'h1', 'title', '.title', '.article-title']
        
        for selector in title_selectors:
            title_tag = soup.select_one(selector)
            if title_tag and title_tag.get_text(strip=True):
                return title_tag.get_text(strip=True)
        
        return "未找到标题"
    
    def _extract_date_from_soup(self, soup: BeautifulSoup) -> str:
        """从BeautifulSoup对象中提取日期"""
        date_selectors = ['div.s-date', '.date', '.publish-date', '.article-date']
        
        for selector in date_selectors:
            date_tag = soup.select_one(selector)
            if date_tag and date_tag.get_text(strip=True):
                return date_tag.get_text(strip=True)
        
        # 尝试从文本中提取日期
        import re
        date_pattern = r'\d{4}[-年]\d{1,2}[-月]\d{1,2}[日]?'
        text_content = soup.get_text()
        date_match = re.search(date_pattern, text_content)
        if date_match:
            return date_match.group()
        
        return "未找到日期"
    
    def _check_price_info(self, content_div) -> bool:
        """检查内容是否包含价格信息"""
        try:
            # 检查是否包含投标报价相关关键词
            price_keywords = ['>投标报价<', '投标报价', '中标价', '成交价', '金额', '万元', '元整']
            content_text = str(content_div)
            
            for keyword in price_keywords:
                if keyword in content_text:
                    return True
            return False
        except Exception:
            return False
    
    def _display_test_results(self, test_result: Dict[str, Any]):
        """在UI中显示测试结果"""
        if not test_result:
            return
        
        # 在日志中显示详细结果
        ModernLogViewer.add_log_background("📊 === 测试结果详情 ===", "INFO")
        ModernLogViewer.add_log_background(f"📁 文件: {test_result['file_name']}", "INFO")
        ModernLogViewer.add_log_background(f"📝 标题: {test_result['title']}", "INFO")
        ModernLogViewer.add_log_background(f"📅 日期: {test_result['date']}", "INFO")
        ModernLogViewer.add_log_background(f"🎯 关键词: {test_result['keyword']}", "INFO")
        ModernLogViewer.add_log_background(f"✅ 成功: {'是' if test_result['success'] else '否'}", "INFO")
        ModernLogViewer.add_log_background(f"🔍 包含价格信息: {'是' if test_result['has_price_info'] else '否'}", "INFO")
        
        if test_result['extracted_info']:
            # 将提取结果按行分割并逐行输出到日志
            extracted_lines = test_result['extracted_info'].split('\n')
            ModernLogViewer.add_log_background("💰 === LLM提取结果 ===", "SUCCESS")
            for line in extracted_lines[:10]:  # 只显示前10行
                if line.strip():
                    ModernLogViewer.add_log_background(f"  {line.strip()}", "INFO")
            
            if len(extracted_lines) > 10:
                ModernLogViewer.add_log_background(f"  ... (还有 {len(extracted_lines) - 10} 行)", "INFO")
        
        ModernLogViewer.add_log_background("📊 === 测试结果结束 ===", "INFO")
    
    def _render_file_management_section(self, output_directory: str):
        """渲染文件管理区域"""
        st.markdown("---")
        st.subheader("📁 文件管理")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button(
                "📁 查看价格文件",
                use_container_width=True,
                help="查看和管理已生成的价格提取结果文件"
            ):
                st.session_state.show_price_files_dialog = True
        
        with col2:
            if st.button(
                "📊 文件统计",
                use_container_width=True,
                help="显示价格文件的统计信息"
            ):
                self._show_file_statistics(output_directory)
        
        with col3:
            if st.button(
                "🔄 刷新列表",
                use_container_width=True,
                help="重新扫描价格文件"
            ):
                self._refresh_price_files(output_directory)
        
        with col4:
            if st.button(
                "🔍 调试检查",
                use_container_width=True,
                help="检查文件生成和路径问题"
            ):
                self._debug_file_paths(output_directory)
        
        # 第二行按钮
        st.markdown("")  # 添加一些间距
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button(
                "🗑️ 清理文件",
                use_container_width=True,
                help="批量删除旧的价格文件",
                type="secondary"
            ):
                st.session_state.show_cleanup_dialog = True
        
        # 显示操作结果
        if st.session_state.file_operation_result:
            st.success(st.session_state.file_operation_result)
            st.session_state.file_operation_result = None
        
        # 渲染价格文件管理弹窗
        self._render_price_files_dialog(output_directory)
        
        # 渲染清理文件弹窗
        self._render_cleanup_dialog(output_directory)
    
    def _scan_price_files(self, output_directory: str) -> list:
        """扫描价格文件"""
        try:
            output_path = Path(output_directory)
            
            # 添加调试信息
            ModernLogViewer.add_log_background(f"🔍 扫描价格文件目录: {output_path}", "DEBUG")
            
            if not output_path.exists():
                ModernLogViewer.add_log_background(f"❌ 目录不存在: {output_path}", "WARNING")
                return []
            
            files_info = []
            
            # 查找所有价格提取结果文件
            all_json_files = list(output_path.glob("*.json"))
            price_files = list(output_path.glob("price_extraction_*.json"))
            
            ModernLogViewer.add_log_background(f"📊 目录统计 - 总JSON文件: {len(all_json_files)}, 价格文件: {len(price_files)}", "DEBUG")
            
            # 显示所有JSON文件名（调试用）
            if all_json_files:
                ModernLogViewer.add_log_background("📁 找到的JSON文件:", "DEBUG")
                for f in all_json_files[:5]:  # 只显示前5个
                    ModernLogViewer.add_log_background(f"  - {f.name}", "DEBUG")
                if len(all_json_files) > 5:
                    ModernLogViewer.add_log_background(f"  ... 还有 {len(all_json_files) - 5} 个文件", "DEBUG")
            
            for file_path in price_files:
                try:
                    stat = file_path.stat()
                    file_size = stat.st_size
                    file_time = datetime.fromtimestamp(stat.st_mtime)
                    
                    # 尝试读取文件内容获取更多信息
                    file_info = {
                        'path': str(file_path),
                        'name': file_path.name,
                        'size': file_size,
                        'size_mb': file_size / (1024 * 1024),
                        'created_time': file_time,
                        'formatted_time': file_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'total_files': 0,
                        'successful_extractions': 0,
                        'keyword': 'unknown'
                    }
                    
                    # 解析JSON文件获取详细信息
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            file_info.update({
                                'total_files': data.get('total_files', 0),
                                'successful_extractions': data.get('successful_extractions', 0),
                                'extraction_time': data.get('extraction_time', ''),
                                'success_rate': (data.get('successful_extractions', 0) / max(data.get('total_files', 1), 1)) * 100
                            })
                            
                            # 从文件名中提取关键词
                            name_parts = file_path.stem.split('_')
                            if len(name_parts) >= 3:
                                file_info['keyword'] = name_parts[2]
                    except (json.JSONDecodeError, Exception):
                        pass
                    
                    files_info.append(file_info)
                    
                except Exception as e:
                    logger.error(f"读取文件信息失败 {file_path}: {e}")
                    continue
            
            # 按创建时间倒序排列
            files_info.sort(key=lambda x: x['created_time'], reverse=True)
            
            st.session_state.price_files_info = files_info
            st.session_state.last_scan_time = datetime.now()
            
            return files_info
            
        except Exception as e:
            logger.error(f"扫描价格文件失败: {e}")
            return []
    
    def _render_price_files_dialog(self, output_directory: str):
        """渲染价格文件管理弹窗"""
        if st.session_state.get('show_price_files_dialog', False):
            
            @st.dialog("📁 价格文件管理", width="large")
            def price_files_dialog():
                try:
                    # 扫描文件
                    files_info = self._scan_price_files(output_directory)
                    
                    if not files_info:
                        st.warning("📭 未找到任何价格提取结果文件")
                        st.info("💡 提示：请先执行价格提取操作生成结果文件")
                        
                        if st.button("关闭", use_container_width=True):
                            st.session_state.show_price_files_dialog = False
                            st.rerun()
                        return
                    
                    # 显示统计信息
                    total_files = len(files_info)
                    total_size = sum(f['size'] for f in files_info)
                    latest_file = files_info[0]['formatted_time'] if files_info else "无"
                    
                    st.markdown("#### 📊 统计信息")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("总文件数", f"{total_files} 个")
                    with col2:
                        st.metric("总大小", f"{total_size / (1024*1024):.1f} MB")
                    with col3:
                        st.metric("最新文件", latest_file.split()[0])  # 只显示日期
                    
                    st.markdown("#### 📋 文件列表")
                    
                    # 文件列表表格
                    for i, file_info in enumerate(files_info):
                        with st.container():
                            col1, col2, col3, col4, col5 = st.columns([0.5, 3, 1, 1.5, 2])
                            
                            with col1:
                                selected = st.checkbox("", key=f"file_select_{i}", label_visibility="collapsed")
                                if selected and file_info['path'] not in st.session_state.selected_files:
                                    st.session_state.selected_files.append(file_info['path'])
                                elif not selected and file_info['path'] in st.session_state.selected_files:
                                    st.session_state.selected_files.remove(file_info['path'])
                            
                            with col2:
                                st.write(f"**{file_info['name']}**")
                                st.caption(f"关键词: {file_info['keyword']} | 成功率: {file_info.get('success_rate', 0):.1f}%")
                            
                            with col3:
                                st.write(f"{file_info['size_mb']:.1f}MB")
                            
                            with col4:
                                st.write(file_info['formatted_time'].split()[0])  # 只显示日期
                            
                            with col5:
                                btn_col1, btn_col2, btn_col3 = st.columns(3)
                                
                                with btn_col1:
                                    if st.button("📥", key=f"download_{i}", help="下载"):
                                        self._download_price_file(file_info)
                                
                                with btn_col2:
                                    if st.button("👁️", key=f"preview_{i}", help="预览"):
                                        self._preview_price_file(file_info)
                                
                                with btn_col3:
                                    if st.button("🗑️", key=f"delete_{i}", help="删除"):
                                        if st.button(f"确认删除 {file_info['name']}?", key=f"confirm_delete_{i}"):
                                            self._delete_price_file(file_info['path'])
                                            st.rerun()
                    
                    st.markdown("---")
                    
                    # 批量操作
                    st.markdown("#### 🔧 批量操作")
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        if st.button("全选", use_container_width=True):
                            st.session_state.selected_files = [f['path'] for f in files_info]
                            st.rerun()
                    
                    with col2:
                        if st.button("清空选择", use_container_width=True):
                            st.session_state.selected_files = []
                            st.rerun()
                    
                    with col3:
                        selected_count = len(st.session_state.selected_files)
                        if st.button(f"下载选中({selected_count})", disabled=selected_count == 0, use_container_width=True):
                            self._download_selected_files()
                    
                    with col4:
                        if st.button(f"删除选中({selected_count})", disabled=selected_count == 0, use_container_width=True, type="secondary"):
                            if st.button("确认删除选中的文件?", key="confirm_batch_delete"):
                                self._delete_selected_files()
                                st.rerun()
                    
                    # 关闭按钮
                    if st.button("关闭", use_container_width=True):
                        st.session_state.show_price_files_dialog = False
                        st.session_state.selected_files = []
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"文件管理出错: {e}")
                    logger.error(f"文件管理异常: {e}")
            
            # 显示弹窗
            price_files_dialog()
    
    def _download_price_file(self, file_info: dict):
        """下载单个价格文件"""
        try:
            with open(file_info['path'], 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            st.download_button(
                label=f"📥 下载 {file_info['name']}",
                data=file_content,
                file_name=file_info['name'],
                mime="application/json",
                key=f"download_btn_{file_info['name']}",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"下载文件失败: {e}")
    
    def _preview_price_file(self, file_info: dict):
        """预览价格文件内容"""
        try:
            with open(file_info['path'], 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            st.markdown(f"#### 📄 文件预览: {file_info['name']}")
            
            # 基本信息
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("处理文件数", data.get('total_files', 0))
            with col2:
                st.metric("成功提取", data.get('successful_extractions', 0))
            with col3:
                success_rate = (data.get('successful_extractions', 0) / max(data.get('total_files', 1), 1)) * 100
                st.metric("成功率", f"{success_rate:.1f}%")
            
            # JSON内容预览
            st.markdown("**JSON内容预览:**")
            preview_data = {
                "extraction_time": data.get("extraction_time", ""),
                "total_files": data.get("total_files", 0),
                "successful_extractions": data.get("successful_extractions", 0),
                "results_preview": data.get("results", [])[:3]  # 只显示前3个结果
            }
            st.json(preview_data)
            
            if len(data.get("results", [])) > 3:
                st.caption(f"... 还有 {len(data.get('results', [])) - 3} 个结果")
                
        except Exception as e:
            st.error(f"预览文件失败: {e}")
    
    def _delete_price_file(self, file_path: str):
        """删除单个价格文件"""
        try:
            Path(file_path).unlink()
            st.session_state.file_operation_result = f"✅ 文件删除成功: {Path(file_path).name}"
            ModernLogViewer.add_log_background(f"🗑️ 删除价格文件: {Path(file_path).name}", "INFO")
        except Exception as e:
            st.error(f"删除文件失败: {e}")
    
    def _show_file_statistics(self, output_directory: str):
        """显示文件统计信息"""
        with st.spinner("🔍 正在扫描价格文件..."):
            files_info = self._scan_price_files(output_directory)
        
        if not files_info:
            st.warning("📭 暂无价格文件统计信息")
            st.info("💡 提示：请先执行价格提取操作生成结果文件")
            return
        
        # 显示详细统计
        total_files = len(files_info)
        total_size = sum(f['size'] for f in files_info)
        total_extractions = sum(f.get('total_files', 0) for f in files_info)
        total_success = sum(f.get('successful_extractions', 0) for f in files_info)
        avg_success_rate = (total_success / max(total_extractions, 1)) * 100
        
        st.success("📊 价格文件统计信息")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("结果文件总数", f"{total_files} 个")
            st.metric("累计处理文件", f"{total_extractions} 个")
        
        with col2:
            st.metric("存储空间占用", f"{total_size / (1024*1024):.1f} MB")
            st.metric("平均成功率", f"{avg_success_rate:.1f}%")
        
        # 按关键词分组统计
        if files_info:
            keyword_stats = {}
            for file_info in files_info:
                keyword = file_info.get('keyword', 'unknown')
                if keyword not in keyword_stats:
                    keyword_stats[keyword] = {'count': 0, 'size': 0}
                keyword_stats[keyword]['count'] += 1
                keyword_stats[keyword]['size'] += file_info['size']
            
            st.markdown("**📈 按关键词分组统计:**")
            for keyword, stats in keyword_stats.items():
                st.write(f"• **{keyword}**: {stats['count']} 个文件, {stats['size']/(1024*1024):.1f}MB")
        
        # 显示文件列表预览
        st.markdown("**📋 最近文件预览:**")
        for i, file_info in enumerate(files_info[:3]):  # 只显示前3个
            with st.expander(f"📄 {file_info['name']}", expanded=False):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**大小**: {file_info['size_mb']:.1f}MB")
                    st.write(f"**关键词**: {file_info['keyword']}")
                with col2:
                    st.write(f"**处理文件数**: {file_info.get('total_files', 0)}")
                    st.write(f"**成功提取**: {file_info.get('successful_extractions', 0)}")
                with col3:
                    st.write(f"**成功率**: {file_info.get('success_rate', 0):.1f}%")
                    st.write(f"**创建时间**: {file_info['formatted_time']}")
        
        if len(files_info) > 3:
            st.caption(f"... 还有 {len(files_info) - 3} 个文件，点击'查看价格文件'查看完整列表")
    
    def _refresh_price_files(self, output_directory: str):
        """刷新价格文件列表"""
        with st.spinner("🔄 正在刷新价格文件列表..."):
            files_info = self._scan_price_files(output_directory)
        
        # 清理选中文件状态
        st.session_state.selected_files = []
        
        if files_info:
            st.session_state.file_operation_result = f"🔄 已刷新文件列表，找到 {len(files_info)} 个价格文件"
        else:
            st.session_state.file_operation_result = "🔄 已刷新文件列表，未找到价格文件"
    
    def _render_cleanup_dialog(self, output_directory: str):
        """渲染清理文件弹窗"""
        if st.session_state.get('show_cleanup_dialog', False):
            
            @st.dialog("🗑️ 批量清理价格文件", width="large")
            def cleanup_dialog():
                st.warning("⚠️ **此操作将永久删除选中的价格文件！**")
                
                files_info = self._scan_price_files(output_directory)
                if not files_info:
                    st.info("📭 没有可清理的价格文件")
                    if st.button("关闭"):
                        st.session_state.show_cleanup_dialog = False
                        st.rerun()
                    return
                
                # 按时间分组显示
                st.markdown("#### 🗂️ 选择要清理的文件")
                
                # 提供快速选择选项
                col1, col2, col3 = st.columns(3)
                with col1:
                    days_7 = st.button("清理7天前", use_container_width=True)
                with col2:
                    days_30 = st.button("清理30天前", use_container_width=True)
                with col3:
                    all_files = st.button("全部清理", use_container_width=True)
                
                # 文件列表
                selected_for_cleanup = []
                cutoff_date = None
                
                if days_7:
                    cutoff_date = datetime.now() - timedelta(days=7)
                elif days_30:
                    cutoff_date = datetime.now() - timedelta(days=30)
                elif all_files:
                    cutoff_date = datetime.now()
                
                for i, file_info in enumerate(files_info):
                    should_select = cutoff_date and file_info['created_time'] < cutoff_date
                    
                    if st.checkbox(
                        f"{file_info['name']} ({file_info['formatted_time']}, {file_info['size_mb']:.1f}MB)",
                        value=should_select,
                        key=f"cleanup_select_{i}"
                    ):
                        selected_for_cleanup.append(file_info['path'])
                
                st.markdown("---")
                
                # 确认清理
                if selected_for_cleanup:
                    st.warning(f"将删除 {len(selected_for_cleanup)} 个文件")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("确认删除", type="primary", use_container_width=True):
                            deleted_count = 0
                            for file_path in selected_for_cleanup:
                                try:
                                    Path(file_path).unlink()
                                    deleted_count += 1
                                except Exception as e:
                                    st.error(f"删除 {Path(file_path).name} 失败: {e}")
                            
                            st.success(f"✅ 成功删除 {deleted_count} 个文件")
                            ModernLogViewer.add_log_background(f"🗑️ 批量删除 {deleted_count} 个价格文件", "INFO")
                            st.session_state.show_cleanup_dialog = False
                            st.rerun()
                    
                    with col2:
                        if st.button("取消", use_container_width=True):
                            st.session_state.show_cleanup_dialog = False
                            st.rerun()
                else:
                    if st.button("关闭", use_container_width=True):
                        st.session_state.show_cleanup_dialog = False
                        st.rerun()
            
            cleanup_dialog()
    
    def _download_selected_files(self):
        """下载选中的文件"""
        # 这里可以实现打包下载或逐个下载
        st.info("📦 批量下载功能开发中，请使用单文件下载")
    
    def _delete_selected_files(self):
        """删除选中的文件"""
        deleted_count = 0
        for file_path in st.session_state.selected_files:
            try:
                Path(file_path).unlink()
                deleted_count += 1
            except Exception as e:
                st.error(f"删除文件失败: {e}")
        
        st.session_state.file_operation_result = f"✅ 成功删除 {deleted_count} 个文件"
        st.session_state.selected_files = []
        ModernLogViewer.add_log_background(f"🗑️ 批量删除 {deleted_count} 个价格文件", "INFO")
    
    def _debug_file_paths(self, output_directory: str):
        """调试文件路径和生成问题"""
        ModernLogViewer.add_log_background("🔍 === 开始调试检查 ===", "INFO")
        
        # 1. 检查输出目录
        output_path = Path(output_directory)
        ModernLogViewer.add_log_background(f"📁 配置的输出目录: {output_path}", "INFO")
        ModernLogViewer.add_log_background(f"📂 目录是否存在: {'是' if output_path.exists() else '否'}", "INFO")
        
        if output_path.exists():
            # 检查目录权限
            try:
                test_file = output_path / "test_write_permission.tmp"
                test_file.write_text("test")
                test_file.unlink()
                ModernLogViewer.add_log_background("✅ 目录写入权限: 正常", "INFO")
            except Exception as e:
                ModernLogViewer.add_log_background(f"❌ 目录写入权限: 异常 - {e}", "ERROR")
            
            # 列出所有文件
            all_files = list(output_path.rglob("*"))
            ModernLogViewer.add_log_background(f"📊 目录总文件数: {len(all_files)}", "INFO")
            
            # JSON文件
            json_files = [f for f in all_files if f.suffix == '.json']
            ModernLogViewer.add_log_background(f"📄 JSON文件数: {len(json_files)}", "INFO")
            
            if json_files:
                ModernLogViewer.add_log_background("📋 JSON文件列表:", "INFO")
                for f in json_files[:10]:  # 显示前10个
                    ModernLogViewer.add_log_background(f"  - {f.name} ({f.stat().st_size / 1024:.1f}KB)", "INFO")
            
            # 价格文件
            price_files = [f for f in json_files if f.name.startswith('price_extraction_')]
            ModernLogViewer.add_log_background(f"💰 价格文件数: {len(price_files)}", "INFO")
            
            if price_files:
                ModernLogViewer.add_log_background("📋 价格文件列表:", "INFO")
                for f in price_files:
                    stat = f.stat()
                    size_kb = stat.st_size / 1024
                    mtime = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                    ModernLogViewer.add_log_background(f"  - {f.name} ({size_kb:.1f}KB, {mtime})", "INFO")
        
        # 2. 检查HTML目录
        html_dir = output_path / "raw_html"
        ModernLogViewer.add_log_background(f"📁 HTML目录: {html_dir}", "INFO")
        ModernLogViewer.add_log_background(f"📂 HTML目录是否存在: {'是' if html_dir.exists() else '否'}", "INFO")
        
        if html_dir.exists():
            html_files = list(html_dir.rglob("*.html"))
            ModernLogViewer.add_log_background(f"📄 HTML文件数: {len(html_files)}", "INFO")
            
            # 公示公告文件
            announcement_files = [f for f in html_files if f.name.startswith('公示公告')]
            ModernLogViewer.add_log_background(f"📋 公示公告文件数: {len(announcement_files)}", "INFO")
            
            if announcement_files:
                ModernLogViewer.add_log_background("📋 公示公告文件列表 (前5个):", "INFO")
                for f in announcement_files[:5]:
                    stat = f.stat()
                    size_kb = stat.st_size / 1024
                    mtime = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                    ModernLogViewer.add_log_background(f"  - {f.name} ({size_kb:.1f}KB, {mtime})", "INFO")
        
        # 3. 检查最近的提取操作
        if hasattr(st.session_state, 'extraction_output_file') and st.session_state.extraction_output_file:
            last_output_file = st.session_state.extraction_output_file
            ModernLogViewer.add_log_background(f"📄 最近的输出文件: {last_output_file}", "INFO")
            
            if Path(last_output_file).exists():
                file_size = Path(last_output_file).stat().st_size / 1024
                ModernLogViewer.add_log_background(f"✅ 文件存在，大小: {file_size:.1f}KB", "INFO")
            else:
                ModernLogViewer.add_log_background("❌ 文件不存在", "ERROR")
        else:
            ModernLogViewer.add_log_background("ℹ️ 尚未进行过价格提取操作", "INFO")
        
        # 4. 检查当前工作目录
        import os
        cwd = os.getcwd()
        ModernLogViewer.add_log_background(f"🗂️ 当前工作目录: {cwd}", "INFO")
        
        # 5. 检查相对路径和绝对路径
        if not output_path.is_absolute():
            absolute_path = Path(cwd) / output_path
            ModernLogViewer.add_log_background(f"📍 绝对路径: {absolute_path}", "INFO")
            ModernLogViewer.add_log_background(f"📂 绝对路径是否存在: {'是' if absolute_path.exists() else '否'}", "INFO")
        
        ModernLogViewer.add_log_background("🔍 === 调试检查完成 ===", "INFO")
        
        # 显示结果提示
        st.session_state.file_operation_result = "🔍 已完成调试检查，请查看日志了解详情"

def main():
    """主函数"""
    try:
        # 确保页面实例在session中保持一致
        if 'modern_page_instance' not in st.session_state:
            st.session_state.modern_page_instance = CrawlerConfigPage()
        
        page = st.session_state.modern_page_instance
        page.render()
        
    except Exception as e:
        st.error(f"页面加载失败: {e}")
        logger.error(f"页面加载失败: {e}", exc_info=True)
        
        # 提供重置选项
        if st.button("🔄 重置页面"):
            if 'modern_page_instance' in st.session_state:
                del st.session_state.modern_page_instance
            st.rerun()

if __name__ == "__main__":
    main() 