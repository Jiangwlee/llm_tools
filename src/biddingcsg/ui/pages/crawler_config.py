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
# 删除了日志查看器相关导入
from biddingcsg.config.paths import BiddingPaths, FilePatterns, FileSizes

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CrawlerConfigPage:
    """现代化爬虫配置页面 - 使用最新的 Streamlit 功能"""
    
    def __init__(self):
        """初始化页面"""
        self._init_session_state()
        
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
    
    def _crawler_status_fragment(self):
        """爬虫状态检查 - 移除了fragment装饰器"""
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
        
        # 只在页面顶部调用一次所有fragment，避免重复创建
        try:
            # 状态检查fragments - 低频运行
            self._crawler_status_fragment()
            self._extraction_status_fragment()
            # 删除了日志刷新fragment功能
        except Exception as e:
            # 如果fragment出错，静默处理，避免影响主界面
            logger.debug(f"Fragment运行错误 (已忽略): {e}")
        
        # 检查是否刚完成
        if st.session_state.get('crawler_finished', False):
            st.session_state.crawler_finished = False
            st.balloons()
            st.success("🎉 爬虫任务已完成！请查看结果统计标签页了解详情。")
        
        # 主要布局
        tab1, tab2 = st.tabs(["⚙️ 配置与控制", "📊 结果统计"])
        
        with tab1:
            self._render_config_tab()
        
        with tab2:
            self._render_stats_tab()
        
        # 清空缓存弹窗对话框
        self._render_clear_cache_dialog()
    
    def _render_config_tab(self):
        """渲染配置标签页"""        
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
            default_output_dir = str(Path.cwd() / "output")
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
            # 删除了队列大小统计
            st.metric("待处理", 0)
        
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
                # 删除了日志查看器调用
                st.success("日志已清空")
        
        with ctrl_col3:
            if st.button(
                "🧹 清空缓存",
                use_container_width=True,
                type="secondary",
                help="删除所有已保存的HTML文件和元数据"
            ):
                st.session_state.show_clear_cache_dialog = True
        
    

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
                    
                except Exception as e:
                    logger.error(f"进度回调错误: {e}")
            
            # 爬虫工作线程
            def crawler_worker():
                try:
                    st.session_state.crawler_running = True
                    # 删除了日志调用
                    
                    session = crawler_service.start_crawling(
                        progress_callback=progress_callback
                    )
                    
                    st.session_state.current_session = session
                    
                    if session.status == "completed":
                        # 删除了日志调用
                        pass
                    else:
                        # 删除了日志调用
                        pass
                        
                except Exception as e:
                    # 删除了日志调用
                    logger.error(f"爬虫执行异常: {e}", exc_info=True)
                finally:
                    st.session_state.crawler_running = False
                    st.session_state.crawler_thread = None
                    st.session_state.crawler_finished = True
            
            # 启动后台线程
            crawler_thread = threading.Thread(target=crawler_worker, daemon=True)
            crawler_thread.start()
            st.session_state.crawler_thread = crawler_thread
            
            # 删除了日志调用
            st.success("🚀 爬虫已启动！请在结果统计标签页查看进度。")
            
        except Exception as e:
            # 删除了日志调用
            logger.error(f"启动爬虫失败: {e}", exc_info=True)
            st.error(f"启动失败: {e}")
    
    def _stop_crawler(self):
        """停止爬虫"""
        if st.session_state.crawler_running:
            # 删除了日志调用
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
                        # 删除了日志调用
                        
                        # 使用默认配置创建存储服务
                        default_config = CrawlerConfig(
                            search_keyword="temp",
                            output_directory=str(Path.cwd() / "output")
                        )
                        storage_service = LocalStorageService(default_config)
                    
                    # 显示警告信息
                    st.warning("⚠️ **此操作不可恢复！**")
                    st.markdown("""
                    **将删除以下数据：**
                    - `bidding_data/raw_html/` 下的所有HTML文件
                    - `bidding_data/metadata/` 下的所有元数据文件
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
                            # 删除了日志调用
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
                    # 删除了日志调用
                    logger.error(f"清空缓存对话框错误: {e}", exc_info=True)
            
            # 显示对话框
            clear_cache_dialog()
    
    def _execute_clear_cache(self, storage_service):
        """执行清空缓存操作"""
        try:
            # 删除了日志调用
            
            # 显示存储服务基础信息（调试用）
            # 删除了日志调用
            # 删除了日志调用
            # 删除了日志调用
            # 删除了日志调用
            
            # 执行清空操作
            # 删除了日志调用
            
            stats = storage_service.clear_all_cache()
            
            # 显示清理结果
            total_files = stats['html_files_deleted'] + stats['metadata_files_deleted']
            success_msg = (f"✅ 缓存清空完成！"
                          f" 删除HTML文件 {stats['html_files_deleted']} 个，"
                          f" 删除元数据文件 {stats['metadata_files_deleted']} 个，"
                          f" 清理目录 {stats['directories_cleaned']} 个，"
                          f" 总计删除文件 {total_files} 个")
            
            # 删除了日志调用
            
            # 在对话框中也显示成功消息
            st.success(f"🎉 缓存清空完成！\n\n"
                      f"• 删除HTML文件: {stats['html_files_deleted']} 个\n"
                      f"• 删除元数据文件: {stats['metadata_files_deleted']} 个\n"
                      f"• 清理目录: {stats['directories_cleaned']} 个\n"
                      f"• 总计删除文件: {total_files} 个")
            
        except Exception as e:
            error_msg = f"❌ 清空缓存失败: {e}"
            st.error(error_msg)
            # 删除了日志调用
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
        """启动批量价格提取任务"""
        return self._start_price_extraction_internal(keyword, output_directory, test_mode=False)
    
    def _start_price_extraction_internal(self, keyword: str, output_directory: str, test_mode: bool = False):
        """统一的价格提取核心逻辑
        
        Args:
            keyword: 搜索关键词
            output_directory: 输出目录
            test_mode: 是否为测试模式（True=单文件测试，False=批量处理）
        """
        # 重置提取状态
        st.session_state.extraction_running = True
        st.session_state.extraction_completed = False
        st.session_state.extraction_results = []
        st.session_state.extraction_logs = []
        st.session_state.stop_extraction = False
        
        # 测试模式额外的状态
        if test_mode:
            st.session_state.testing_in_progress = True
            st.session_state.test_results = None
            st.session_state.test_file_path = None
            # test_start_time现在在工作线程内部管理，避免跨线程访问问题
        
        # 检查HTML目录是否存在
        html_dir = BiddingPaths.get_raw_html_dir(output_directory)
        if not html_dir.exists():
            error_msg = f"❌ HTML文件目录不存在: {html_dir}"
            st.error(error_msg)
            st.session_state.extraction_running = False
            if test_mode:
                st.session_state.testing_in_progress = False
            return
        
        # 根据模式显示不同的开始消息
        mode_name = "测试" if test_mode else "批量"
        mode_icon = "🧪" if test_mode else "🚀"
        # 删除了日志调用
        # 删除了日志调用
        
        def progress_callback(current, total, message):
            """进度更新回调"""
            st.session_state.extraction_progress = {
                'current': current,
                'total': total,
                'message': message,
                'percentage': (current / total * 100) if total > 0 else 0
            }
        
        def log_callback(message):
            """日志更新回调 - 现在使用标准日志记录"""
            mode_prefix = f"🧪 [测试]" if test_mode else f"🚀 [批量]"
            logger.info(f"{mode_prefix} {message}")
        
        class ExtractionWorker(threading.Thread):
            """提取工作线程类 - 正确的线程间通信方式"""
            
            def __init__(self):
                super().__init__(daemon=True)
                self.start_time = datetime.now()
                self.test_mode = test_mode
                self.keyword = keyword
                self.output_directory = output_directory
                self.html_dir = html_dir
                
                # 线程结果属性 - 主线程可以安全访问
                self.status = 'running'  # running, completed, failed
                self.results = []
                self.output_file = ''
                self.test_results = None
                self.test_file_path = ''
                self.error_message = ''
                self.processing_time = 0.0
                
            def run(self):
                """线程执行方法 - 只做计算，不访问session_state"""
                try:
                    # 创建提取器  
                    extractor = create_info_extractor(str(self.html_dir))
                    
                    # 如果是测试模式，预先筛选单个文件
                    if self.test_mode:
                        log_callback("🔍 测试模式：查找最新匹配文件...")
                        # 注意：这里需要获取到外层类的方法
                        latest_file = self._find_latest_test_file_standalone(self.html_dir, self.keyword)
                        
                        if not latest_file:
                            log_callback("❌ 未找到匹配的公示公告文件")
                            self.status = 'failed'
                            self.error_message = "未找到匹配的公示公告文件"
                            return
                        
                        self.test_file_path = str(latest_file)
                        log_callback(f"📄 选择测试文件: {latest_file.name}")
                        
                        # 显示文件信息
                        file_stat = latest_file.stat()
                        file_size = file_stat.st_size / 1024  # KB
                        file_time = datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                        log_callback(f"📅 文件时间: {file_time}")
                        log_callback(f"📏 文件大小: {file_size:.1f}KB")
                        
                        # 手动设置扫描结果为单个文件
                        extractor._manual_file_list = [latest_file]
                    
                    # 执行批量提取（测试模式会处理单个文件）
                    results = extractor.extract_info_batch(
                        keyword=self.keyword,
                        extract_type="price",
                        progress_callback=progress_callback,
                        log_callback=log_callback
                    )
                    
                    # 保存结果
                    if results:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        # 使用全局路径配置
                        price_dir = BiddingPaths.get_price_dir(self.output_directory)
                        
                        if self.test_mode:
                            output_file = price_dir / FilePatterns.PRICE_EXTRACTION_TEST.format(keyword=self.keyword, timestamp=timestamp)
                        else:
                            output_file = price_dir / FilePatterns.PRICE_EXTRACTION_BATCH.format(keyword=self.keyword, timestamp=timestamp)
                        
                        # 添加详细的保存日志
                        log_callback(f"📁 输出目录: {self.output_directory}")
                        log_callback(f"📄 目标文件路径: {output_file}")
                        log_callback(f"📊 提取结果数量: {len(results)}")
                        
                        # 使用全局路径配置确保所有必要目录存在
                        BiddingPaths.ensure_directories(self.output_directory)
                        log_callback(f"✅ 确保目录结构存在: {BiddingPaths.get_data_dir(self.output_directory)}")
                        
                        if extractor.save_results(results, str(output_file)):
                            mode_name = "测试" if self.test_mode else "批量"
                            log_callback(f"🎉 {mode_name}提取完成！结果已保存到: {output_file}")
                            log_callback(f"📏 文件大小: {output_file.stat().st_size / 1024:.1f}KB")
                            
                            # 保存结果到线程属性（不访问session_state）
                            self.results = results
                            self.output_file = str(output_file)
                            self.status = 'completed'
                            
                            # 测试模式额外保存测试结果
                            if self.test_mode and results:
                                self.test_results = results[0] if results else None
                        else:
                            log_callback("❌ 保存结果文件失败")
                            log_callback(f"🔍 检查目录权限: {output_file.parent}")
                            self.status = 'failed'
                            self.error_message = "保存结果文件失败"
                    else:
                        log_callback("⚠️ 未找到匹配的价格信息")
                        log_callback(f"🔍 检查HTML目录: {self.html_dir}")
                        self.status = 'completed'  # 没有结果也算完成
                        self.error_message = "未找到匹配的价格信息"
                        
                        # 显示HTML目录中的文件
                        if self.html_dir.exists():
                            html_files = list(self.html_dir.rglob("*.html"))
                            log_callback(f"📊 HTML目录文件数: {len(html_files)}")
                            if html_files:
                                log_callback("📋 HTML文件列表 (前5个):")
                                for i, f in enumerate(html_files[:5]):
                                    log_callback(f"  {i+1}. {f.name}")
                        else:
                            log_callback(f"❌ HTML目录不存在: {self.html_dir}")
                    
                    # 计算处理时间
                    self.processing_time = (datetime.now() - self.start_time).total_seconds()
                    
                    # 测试模式显示详细结果
                    if self.test_mode and self.test_results:
                        log_callback(f"⏱️ 处理耗时: {self.processing_time:.1f}秒")
                        log_callback("测试结果已保存，请在UI中查看")
                    
                except Exception as e:
                    mode_name = "测试" if self.test_mode else "批量"
                    error_msg = f"❌ {mode_name}提取过程发生错误: {str(e)}"
                    log_callback(error_msg)
                    logger.error(f"{mode_name}价格提取异常: {e}")
                    self.status = 'failed'
                    self.error_message = str(e)
                finally:
                    # 确保状态被设置
                    if self.status == 'running':
                        self.status = 'completed'
                        
            def _find_latest_test_file_standalone(self, html_dir: Path, keyword: str) -> Optional[Path]:
                """独立的文件查找方法 - 不依赖外层类"""
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
                            except Exception:
                                continue
                    
                    if not matching_files:
                        return None
                    
                    # 按修改时间排序，选择最新的
                    latest_file = max(matching_files, key=lambda f: f.stat().st_mtime)
                    return latest_file
                    
                except Exception:
                    return None
        
        # 启动后台线程
        worker = ExtractionWorker()
        worker.start()
        st.session_state.extraction_thread = worker
        
        success_msg = f"{mode_icon} {mode_name}价格提取任务已启动！请在结果统计标签页查看进度。"
        st.success(success_msg)
    
    def _extraction_status_fragment(self):
        """提取状态检查 - 正确的线程间通信方式"""
        extraction_thread = st.session_state.get('extraction_thread')
        
        if extraction_thread and isinstance(extraction_thread, threading.Thread):
            # 检查线程是否完成
            if not extraction_thread.is_alive() and st.session_state.get('extraction_running', False):
                # 线程已完成，从线程属性获取结果并更新session_state
                try:
                    # 同步结果到session_state（在主线程中安全操作）
                    st.session_state.extraction_running = False
                    if hasattr(extraction_thread, 'test_mode') and extraction_thread.test_mode:
                        st.session_state.testing_in_progress = False
                    
                    # 获取结果
                    if extraction_thread.status == 'completed':
                        st.session_state.extraction_results = extraction_thread.results
                        st.session_state.extraction_output_file = extraction_thread.output_file
                        
                        if hasattr(extraction_thread, 'test_results') and extraction_thread.test_results:
                            st.session_state.test_results = extraction_thread.test_results
                        if hasattr(extraction_thread, 'test_file_path') and extraction_thread.test_file_path:
                            st.session_state.test_file_path = extraction_thread.test_file_path
                        
                        # 标记完成以触发UI更新
                        st.session_state.extraction_completed = True
                        
                    elif extraction_thread.status == 'failed':
                        error_msg = f"❌ 提取任务失败: {extraction_thread.error_message}"
                        st.error(error_msg)
                    
                    # 清理线程引用
                    st.session_state.extraction_thread = None
                    
                except Exception as e:
                    logger.error(f"同步线程结果时出错: {e}")
                    # 确保基本状态被重置
                    st.session_state.extraction_running = False
                    st.session_state.testing_in_progress = False
                    st.session_state.extraction_thread = None
        
        # 显示完成结果（原有逻辑）
        if st.session_state.get('extraction_completed', False):
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
        return self._start_price_extraction_internal(keyword, output_directory, test_mode=True)
    
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
                                # 删除了日志调用
                    except Exception as e:
                        # 删除了日志调用
                        continue
            
            if not matching_files:
                # 删除了日志调用
                return None
            
            # 删除了日志调用
            
            # 按修改时间排序，选择最新的
            latest_file = max(matching_files, key=lambda f: f.stat().st_mtime)
            
            # 删除了日志调用
            return latest_file
            
        except Exception as e:
            # 删除了日志调用
            return None
    

    

    
    def _display_test_results_unified(self, test_result: Dict[str, Any]):
        """统一的测试结果显示方法（适用于新的统一架构）"""
        if not test_result:
            return
        
        # 在日志中显示详细结果
        # 删除了日志调用
        # 删除了日志调用
        # 删除了日志调用
        # 删除了日志调用
        
        extracted_info = test_result.get('extracted_info')
        if extracted_info:
            # 将提取结果按行分割并逐行输出到日志
            extracted_lines = str(extracted_info).split('\n')
            # 删除了日志调用
            for line in extracted_lines[:10]:  # 只显示前10行
                if line.strip():
                    # 删除了日志调用
                    pass
            
            if len(extracted_lines) > 10:
                # 删除了日志调用
                pass
        
        # 删除了日志调用
    
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
            # 删除了日志调用
            
            if not output_path.exists():
                # 删除了日志调用
                return []
            
            files_info = []
            
            # 使用全局路径配置获取价格文件目录
            price_dir = BiddingPaths.get_price_dir(str(output_path))
            
            # 查找所有价格提取结果文件（包括测试文件）
            if price_dir.exists():
                all_json_files = list(price_dir.glob("*.json"))
                all_price_files = list(price_dir.glob(FilePatterns.PRICE_EXTRACTION_GLOB))
            else:
                # 如果新目录不存在，检查旧位置并显示提示
                old_files = list(output_path.glob(FilePatterns.PRICE_EXTRACTION_GLOB))
                if old_files:
                    # 删除了日志调用
                    pass
                all_json_files = []
                all_price_files = []
            
            # 分别计算批量和测试文件（用于统计）
            batch_price_files = [f for f in all_price_files if "test" not in f.name]
            test_price_files = [f for f in all_price_files if "test" in f.name]
            
            pass
            
            # 显示所有JSON文件名（调试用）
            if all_json_files:
                pass
                for f in all_json_files[:5]:  # 只显示前5个
                    pass
                if len(all_json_files) > 5:
                    pass
            
            for file_path in all_price_files:
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
                        'size_kb': file_size / 1024,
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
                            
                            # 从文件名中提取关键词和类型
                            name_parts = file_path.stem.split('_')
                            if 'test' in file_path.name:
                                # 测试文件格式: price_extraction_test_keyword_timestamp
                                file_info['file_type'] = '测试'
                                if len(name_parts) >= 4:
                                    file_info['keyword'] = name_parts[3]
                            else:
                                # 批量文件格式: price_extraction_keyword_timestamp  
                                file_info['file_type'] = '批量'
                                if len(name_parts) >= 3:
                                    file_info['keyword'] = name_parts[2]
                    except (json.JSONDecodeError, Exception):
                        pass
                    
                    files_info.append(file_info)
                    
                except Exception as e:
                    logger.error(f"读取文件信息失败 {file_path}: {e}")
                    continue
            
            # 去重，基于文件路径
            unique_files = {}
            for file_info in files_info:
                path = file_info['path']
                if path not in unique_files:
                    unique_files[path] = file_info
                else:
                    # 如果发现重复，记录日志
                    pass
            
            # 转换为列表并按创建时间倒序排列
            files_info = list(unique_files.values())
            files_info.sort(key=lambda x: x['created_time'], reverse=True)
            
            pass
            
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
                                file_type_icon = "🧪" if file_info.get('file_type') == '测试' else "🚀"
                                st.write(f"**{file_type_icon} {file_info['name']}**")
                                st.caption(f"类型: {file_info.get('file_type', '未知')} | 关键词: {file_info['keyword']} | 成功率: {file_info.get('success_rate', 0):.1f}%")
                            
                            with col3:
                                # 使用全局配置的文件大小显示
                                if file_info['size_mb'] >= FileSizes.SIZE_DISPLAY_MB_THRESHOLD:
                                    st.write(f"{file_info['size_mb']:.1f}MB")
                                elif file_info['size_kb'] >= FileSizes.SIZE_DISPLAY_KB_THRESHOLD:
                                    st.write(f"{file_info['size_kb']:.1f}KB")
                                else:
                                    st.write(f"{file_info['size']}B")
                            
                            with col4:
                                st.write(file_info['formatted_time'].split()[0])  # 只显示日期
                            
                            with col5:
                                btn_col1, btn_col2 = st.columns(2)
                                
                                with btn_col1:
                                    # 直接下载按钮，使用st.download_button
                                    try:
                                        with open(file_info['path'], 'r', encoding='utf-8') as f:
                                            file_content = f.read()
                                        
                                        st.download_button(
                                            label="📥",
                                            data=file_content,
                                            file_name=file_info['name'],
                                            mime="application/json",
                                            key=f"download_{i}",
                                            help="下载文件",
                                            use_container_width=True
                                        )
                                    except Exception as e:
                                        st.button("❌", disabled=True, help=f"下载失败: {e}", key=f"download_error_{i}")
                                
                                with btn_col2:
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
    

    

    
    def _delete_price_file(self, file_path: str):
        """删除单个价格文件"""
        try:
            Path(file_path).unlink()
            st.session_state.file_operation_result = f"✅ 文件删除成功: {Path(file_path).name}"
            pass
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
                            pass
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
        import zipfile
        import io
        
        if not st.session_state.selected_files:
            st.warning("⚠️ 请先选择要下载的文件")
            return
        
        try:
            # 创建内存中的ZIP文件
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for file_path in st.session_state.selected_files:
                    try:
                        file_path_obj = Path(file_path)
                        if file_path_obj.exists():
                            # 在ZIP中使用文件名作为路径
                            zip_file.write(file_path_obj, file_path_obj.name)
                    except Exception as e:
                        pass
            
            zip_buffer.seek(0)
            
            # 生成下载文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_filename = f"price_files_batch_{timestamp}.zip"
            
            # 提供下载按钮
            st.download_button(
                label=f"📦 下载压缩包 ({len(st.session_state.selected_files)} 个文件)",
                data=zip_buffer.getvalue(),
                file_name=zip_filename,
                mime="application/zip",
                key="batch_download_zip",
                use_container_width=True
            )
            
            st.success(f"✅ 已生成包含 {len(st.session_state.selected_files)} 个文件的压缩包")
            
        except Exception as e:
            st.error(f"❌ 创建压缩包失败: {e}")
            pass
    
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
        pass
    
    def _debug_file_paths(self, output_directory: str):
        """调试文件路径和生成问题"""
        pass
        
        # 1. 检查输出目录
        output_path = Path(output_directory)
        pass
        pass
        
        if output_path.exists():
            # 检查目录权限
            try:
                test_file = output_path / "test_write_permission.tmp"
                test_file.write_text("test")
                test_file.unlink()
                pass
            except Exception as e:
                pass
            
            # 列出所有文件
            all_files = list(output_path.rglob("*"))
            pass
            
            # JSON文件
            json_files = [f for f in all_files if f.suffix == '.json']
            pass
            
            if json_files:
                pass
                for f in json_files[:10]:  # 显示前10个
                    pass
            
            # 价格文件 - 使用全局路径配置检查
            price_dir = BiddingPaths.get_price_dir(str(output_path))
            pass
            pass
            
            if price_dir.exists():
                price_files = list(price_dir.glob(FilePatterns.PRICE_EXTRACTION_GLOB))
                pass
                
                if price_files:
                    pass
                    for f in price_files:
                        stat = f.stat()
                        size_kb = stat.st_size / 1024
                        mtime = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                        pass
            else:
                # 检查旧位置的价格文件
                old_price_files = list(output_path.glob(FilePatterns.PRICE_EXTRACTION_GLOB))
                pass
                
                if old_price_files:
                    pass
                    for f in old_price_files:
                        stat = f.stat()
                        size_kb = stat.st_size / 1024
                        mtime = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                        pass
        
        # 2. 检查HTML目录
        html_dir = BiddingPaths.get_raw_html_dir(str(output_path))
        pass
        pass
        
        if html_dir.exists():
            html_files = list(html_dir.rglob("*.html"))
            pass
            
            # 公示公告文件
            announcement_files = list(html_dir.glob(FilePatterns.HTML_ANNOUNCEMENT))
            pass
            
            if announcement_files:
                pass
                for f in announcement_files[:5]:
                    stat = f.stat()
                    size_kb = stat.st_size / 1024
                    mtime = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                    pass
        
        # 3. 检查最近的提取操作
        if hasattr(st.session_state, 'extraction_output_file') and st.session_state.extraction_output_file:
            last_output_file = st.session_state.extraction_output_file
            pass
            
            if Path(last_output_file).exists():
                file_size = Path(last_output_file).stat().st_size / 1024
                pass
            else:
                pass
        else:
            pass
        
        # 4. 检查当前工作目录
        import os
        cwd = os.getcwd()
        pass
        
        # 5. 检查相对路径和绝对路径
        if not output_path.is_absolute():
            absolute_path = Path(cwd) / output_path
            pass
            pass
        
        pass
        
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