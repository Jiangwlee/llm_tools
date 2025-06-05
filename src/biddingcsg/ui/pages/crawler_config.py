import streamlit as st
import threading
import os
import time
import queue
from datetime import date, datetime
from pathlib import Path
import logging
import sys

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from biddingcsg.models.config import CrawlerConfig
from biddingcsg.services.storage import LocalStorageService  
from biddingcsg.services.crawler import BiddingCrawlerService
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
            'show_clear_cache_dialog': False
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
            submitted = st.form_submit_button(
                "🚀 开始爬取",
                type="primary",
                disabled=st.session_state.crawler_running,
                use_container_width=True
            )
            
            # 处理表单提交
            if submitted and not st.session_state.crawler_running:
                if self._validate_config(search_keyword, output_directory):
                    config = self._create_config(
                        search_keyword, max_pages, announcement_type,
                        earliest_date, output_directory, request_delay,
                        enable_dedup, headless_mode, timeout
                    )
                    self._start_crawler(config)
    
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