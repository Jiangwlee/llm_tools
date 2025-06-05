import streamlit as st
import threading
from datetime import date, datetime
from pathlib import Path
import logging

from ...models.config import CrawlerConfig
from ...services.storage import LocalStorageService  
from ...services.crawler import BiddingCrawlerService
from ..components.log_viewer import LogViewer, ProgressViewer

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CrawlerConfigPage:
    """爬虫配置页面"""
    
    def __init__(self):
        """初始化页面"""
        # 先初始化session state
        self._init_session_state()
        
        # 再初始化组件
        self.log_viewer = LogViewer(max_lines=150)
        self.progress_viewer = ProgressViewer()
    
    def _init_session_state(self):
        """初始化session state"""
        if 'crawler_running' not in st.session_state:
            st.session_state.crawler_running = False
        if 'crawler_thread' not in st.session_state:
            st.session_state.crawler_thread = None
        if 'current_session' not in st.session_state:
            st.session_state.current_session = None
        if 'log_buffer' not in st.session_state:
            st.session_state.log_buffer = []
        if 'progress_info' not in st.session_state:
            st.session_state.progress_info = {
                'current': 0,
                'total': 0,
                'message': '',
                'percentage': 0.0
            }
    
    def render(self):
        """渲染页面"""
        st.title("🕷️ 招标公告数据下载器")
        st.markdown("---")
        
        # 主要布局：左侧配置，右侧日志
        col1, col2 = st.columns([1, 1], gap="large")
        
        with col1:
            self._render_config_section()
        
        with col2:
            self._render_log_section()
        
        # 底部状态栏
        self._render_status_section()
    
    def _render_config_section(self):
        """渲染配置区域"""
        st.subheader("⚙️ 爬虫配置")
        
        with st.form("crawler_config_form", clear_on_submit=False):
            # 基本配置
            st.markdown("#### 🔍 搜索参数")
            
            col1, col2 = st.columns(2)
            
            with col1:
                search_keyword = st.text_input(
                    "搜索关键词",
                    placeholder="例如：汕头供电局",
                    help="输入要搜索的关键词，支持公司名称、项目名称等",
                    key="search_keyword"
                )
                
                max_pages = st.number_input(
                    "最大爬取页数",
                    min_value=1,
                    max_value=1000,
                    value=10,
                    help="限制爬取的最大页数，避免过度爬取",
                    key="max_pages"
                )
            
            with col2:
                announcement_type = st.selectbox(
                    "公告类型",
                    ["服务", "招标公告", "公示公告"],
                    help="选择要爬取的公告类型",
                    key="announcement_type"
                )
                
                earliest_date = st.date_input(
                    "最早日期",
                    value=None,
                    help="只爬取此日期之后的公告，留空表示不限制",
                    key="earliest_date"
                )
            
            # 输出配置
            st.markdown("#### 📁 输出设置")
            
            default_output_dir = str(Path.cwd() / "output" / "bidding_data")
            output_directory = st.text_input(
                "输出目录",
                value=default_output_dir,
                help="爬取结果的保存目录",
                key="output_directory"
            )
            
            # 高级设置（可折叠）
            with st.expander("🔧 高级设置"):
                col3, col4 = st.columns(2)
                
                with col3:
                    request_delay = st.slider(
                        "请求间隔（秒）",
                        min_value=0.5,
                        max_value=10.0,
                        value=2.0,
                        step=0.5,
                        help="两次请求之间的等待时间，避免被封IP",
                        key="request_delay"
                    )
                    
                    enable_dedup = st.checkbox(
                        "启用去重",
                        value=True,
                        help="跳过已经爬取过的URL",
                        key="enable_dedup"
                    )
                
                with col4:
                    headless_mode = st.checkbox(
                        "无头模式",
                        value=True,
                        help="浏览器是否在后台运行（推荐开启）",
                        key="headless_mode"
                    )
                    
                    timeout = st.number_input(
                        "页面超时（秒）",
                        min_value=10,
                        max_value=120,
                        value=30,
                        help="页面加载的最大等待时间",
                        key="timeout"
                    )
            
            # 提交按钮
            col5, col6, col7 = st.columns(3)
            
            with col5:
                submitted = st.form_submit_button(
                    "🚀 开始爬取",
                    type="primary",
                    disabled=st.session_state.crawler_running,
                    use_container_width=True
                )
            
            with col6:
                if st.form_submit_button(
                    "🛑 停止爬取",
                    disabled=not st.session_state.crawler_running,
                    use_container_width=True
                ):
                    self._stop_crawler()
            
            with col7:
                if st.form_submit_button(
                    "🗑️ 清空日志",
                    use_container_width=True
                ):
                    self.log_viewer.clear_logs()
                    self.progress_viewer.reset()
                    st.rerun()
        
        # 处理表单提交
        if submitted and not st.session_state.crawler_running:
            if self._validate_config(search_keyword, output_directory):
                config = self._create_config(
                    search_keyword, max_pages, announcement_type,
                    earliest_date, output_directory, request_delay,
                    enable_dedup, headless_mode, timeout
                )
                self._start_crawler(config)
    
    def _render_log_section(self):
        """渲染日志区域"""
        st.subheader("📝 实时日志")
        
        # 进度显示
        if st.session_state.crawler_running:
            self.progress_viewer.render()
            st.markdown("---")
        
        # 日志显示
        self.log_viewer.render(height=400, title="", auto_scroll=True)
        
        # 导出按钮
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📥 导出日志", use_container_width=True):
                self.log_viewer.export_logs()
        
        with col2:
            # 显示存储统计
            if hasattr(st.session_state, 'storage_service') and st.session_state.storage_service:
                if st.button("📊 存储统计", use_container_width=True):
                    self._show_storage_stats()
    
    def _render_status_section(self):
        """渲染状态栏"""
        st.markdown("---")
        
        if st.session_state.crawler_running:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.success("🔄 爬虫运行中...")
            
            with col2:
                if st.session_state.current_session:
                    session = st.session_state.current_session
                    st.info(f"📄 已爬取: {session.total_items_found} 条记录")
            
            with col3:
                if st.button("🔄 刷新状态"):
                    st.rerun()
        else:
            st.info("⏳ 爬虫待机中，请配置参数后启动")
    
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
        """创建爬虫配置对象"""
        earliest_date_str = earliest_date.strftime("%Y-%m-%d") if earliest_date else None
        
        config = CrawlerConfig(
            search_keyword=search_keyword,
            max_pages=max_pages,
            announcement_type=announcement_type,
            earliest_date=earliest_date_str,
            output_directory=output_directory,
            request_delay=request_delay,
            enable_dedup=enable_dedup,
            headless_mode=headless_mode,
            timeout=timeout
        )
        
        return config
    
    def _safe_add_log(self, message: str, level: str = "INFO"):
        """线程安全的添加日志函数"""
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%H:%M:%S")
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
        
        # 直接操作session_state，避免调用Streamlit组件
        if 'log_buffer' in st.session_state:
            st.session_state.log_buffer.append(log_entry)
            # 限制缓冲区大小
            if len(st.session_state.log_buffer) > 150:
                st.session_state.log_buffer.pop(0)
    
    def _safe_update_progress(self, current: int, total: int, message: str = ""):
        """线程安全的更新进度函数"""
        percentage = (current / total * 100) if total > 0 else 0
        if 'progress_info' in st.session_state:
            st.session_state.progress_info.update({
                'current': current,
                'total': total,
                'message': message,
                'percentage': percentage
            })
    
    def _start_crawler(self, config: CrawlerConfig):
        """启动爬虫"""
        try:
            # 创建存储服务
            storage_service = LocalStorageService(config)
            st.session_state.storage_service = storage_service
            
            # 创建爬虫服务
            crawler_service = BiddingCrawlerService(config, storage_service)
            
            # 设置回调函数
            def log_callback(message):
                self._safe_add_log(message, "INFO")
            
            def progress_callback(current, total, message):
                self._safe_update_progress(current, total, message)
            
            # 在后台线程中启动爬虫
            def crawler_worker():
                try:
                    st.session_state.crawler_running = True
                    self._safe_add_log("🚀 启动爬虫任务...", "INFO")
                    
                    session = crawler_service.start_crawling(
                        progress_callback=progress_callback,
                        log_callback=log_callback
                    )
                    
                    st.session_state.current_session = session
                    
                    if session.status == "completed":
                        self._safe_add_log(
                            f"✅ 爬取完成！共获取 {session.total_items_found} 条记录", 
                            "SUCCESS"
                        )
                    else:
                        self._safe_add_log(
                            f"❌ 爬取失败: {session.error_message}", 
                            "ERROR"
                        )
                        
                except Exception as e:
                    self._safe_add_log(f"❌ 爬虫执行异常: {e}", "ERROR")
                    logger.error(f"爬虫执行异常: {e}", exc_info=True)
                finally:
                    st.session_state.crawler_running = False
                    st.session_state.crawler_thread = None
            
            # 启动后台线程
            crawler_thread = threading.Thread(target=crawler_worker, daemon=True)
            crawler_thread.start()
            st.session_state.crawler_thread = crawler_thread
            
            self._safe_add_log("✅ 爬虫已启动", "SUCCESS")
            st.rerun()
            
        except Exception as e:
            self._safe_add_log(f"❌ 启动爬虫失败: {e}", "ERROR")
            logger.error(f"启动爬虫失败: {e}", exc_info=True)
    
    def _stop_crawler(self):
        """停止爬虫"""
        if st.session_state.crawler_running:
            self._safe_add_log("🛑 正在停止爬虫...", "WARNING")
            st.session_state.crawler_running = False
            
            # 注意：实际的停止逻辑需要在爬虫服务中实现
            # 这里只是更新状态
            
            st.rerun()
    
    def _show_storage_stats(self):
        """显示存储统计信息"""
        if hasattr(st.session_state, 'storage_service') and st.session_state.storage_service:
            try:
                stats = st.session_state.storage_service.get_storage_stats()
                
                with st.container():
                    st.subheader("📊 存储统计")
                    
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
                        st.info(f"最近爬取时间: {stats['latest_crawl_date']}")
                        
            except Exception as e:
                st.error(f"获取统计信息失败: {e}")

def main():
    """主函数"""
    try:
        page = CrawlerConfigPage()
        page.render()
    except Exception as e:
        st.error(f"页面加载失败: {e}")
        logger.error(f"页面加载失败: {e}", exc_info=True)

if __name__ == "__main__":
    main() 