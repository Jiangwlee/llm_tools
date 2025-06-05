import uuid
import time
import random
import logging
from datetime import datetime
from typing import Callable, Optional, List
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, Page, Browser

from ..models.config import CrawlerConfig, CrawlResult, CrawlSession
from .storage import LocalStorageService

logger = logging.getLogger(__name__)

class BiddingCrawlerService:
    """招标公告爬虫服务"""
    
    def __init__(self, config: CrawlerConfig, storage: LocalStorageService):
        """
        初始化爬虫服务
        
        Args:
            config: 爬虫配置对象
            storage: 存储服务对象
        """
        self.config = config
        self.storage = storage
        self.session: Optional[CrawlSession] = None
        
        # Playwright相关
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.prev_page: Optional[Page] = None
        
        # 爬取状态
        self.stop_crawl = False
        self.current_page_num = 0
        
        # 回调函数
        self.progress_callback: Optional[Callable] = None
        self.log_callback: Optional[Callable] = None
    
    def start_crawling(self, progress_callback: Optional[Callable] = None, 
                      log_callback: Optional[Callable] = None) -> CrawlSession:
        """
        开始爬取任务
        
        Args:
            progress_callback: 进度回调函数，参数为 (current, total, message)
            log_callback: 日志回调函数，参数为 (message)
            
        Returns:
            CrawlSession: 爬取会话对象
        """
        # 设置回调函数
        self.progress_callback = progress_callback
        self.log_callback = log_callback
        
        # 创建爬取会话
        session_id = str(uuid.uuid4())
        self.session = CrawlSession(
            session_id=session_id,
            config=self.config
        )
        
        try:
            self._log("🚀 开始爬取任务...")
            self._log(f"会话ID: {session_id}")
            self._log(f"搜索关键词: {self.config.search_keyword}")
            self._log(f"最大页数: {self.config.max_pages}")
            self._log(f"输出目录: {self.config.output_directory}")
            
            # 初始化浏览器
            self._init_browser()
            
            # 执行搜索
            self._execute_search()
            
            # 标记完成
            self.session.mark_completed()
            self._log(f"✅ 爬取任务完成！共爬取 {self.session.total_items_found} 条记录")
            
        except Exception as e:
            error_msg = f"爬取任务失败: {str(e)}"
            self._log(f"❌ {error_msg}")
            logger.error(error_msg, exc_info=True)
            self.session.mark_failed(error_msg)
            
        finally:
            # 清理资源
            self._cleanup_browser()
            
            # 保存会话信息
            self.storage.save_session(self.session)
        
        return self.session
    
    def _init_browser(self):
        """初始化浏览器"""
        try:
            self._log("🌐 初始化浏览器...")
            
            # 根据搜索结果，在Windows线程中设置正确的事件循环策略
            import asyncio
            import sys
            import threading
            import os
            
            # 检查是否在主线程中
            is_main_thread = threading.current_thread() is threading.main_thread()
            
            # 对于Windows平台和线程环境的特殊处理
            if sys.platform.startswith('win') and not is_main_thread:
                try:
                    # 方案1: 清理现有事件循环并设置ProactorEventLoop
                    try:
                        current_loop = asyncio.get_event_loop()
                        if not current_loop.is_closed():
                            current_loop.close()
                    except:
                        pass
                    
                    # 设置WindowsProactorEventLoopPolicy
                    if hasattr(asyncio, 'WindowsProactorEventLoopPolicy'):
                        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
                        self._log("✅ 设置WindowsProactorEventLoopPolicy成功")
                    
                    # 创建新的ProactorEventLoop
                    if hasattr(asyncio, 'ProactorEventLoop'):
                        loop = asyncio.ProactorEventLoop()
                        asyncio.set_event_loop(loop)
                        self._log("✅ 设置ProactorEventLoop成功")
                    else:
                        # 备用方案：WindowsSelectorEventLoopPolicy
                        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        self._log("✅ 使用WindowsSelectorEventLoopPolicy")
                        
                    # 设置环境变量以禁用某些功能
                    os.environ['PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD'] = '0'
                    
                except Exception as e:
                    self._log(f"⚠️ 事件循环设置失败，继续尝试: {e}")
            
            # 启动Playwright - 使用更兼容的设置
            try:
                self.playwright = sync_playwright().start()
                
                # 使用更保守的浏览器启动参数
                browser_args = [
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding",
                    "--disable-ipc-flooding-protection"
                ]
                
                # 如果在线程中运行，使用单进程模式
                if not is_main_thread:
                    browser_args.append("--single-process")
                    self._log("🔧 使用单进程模式避免子进程问题")
                
                self.browser = self.playwright.chromium.launch(
                    headless=self.config.headless_mode,
                    args=browser_args
                )
                
                context = self.browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                )
                self.page = context.new_page()
                
                # 设置超时
                self.page.set_default_timeout(self.config.timeout * 1000)
                
                self._log("✅ 浏览器初始化完成")
                
            except Exception as chrome_error:
                self._log(f"❌ Chrome启动失败: {chrome_error}")
                
                # 尝试使用Firefox作为备选
                try:
                    self._log("🔄 尝试使用Firefox引擎...")
                    self.browser = self.playwright.firefox.launch(
                        headless=self.config.headless_mode
                    )
                    context = self.browser.new_context()
                    self.page = context.new_page()
                    self.page.set_default_timeout(self.config.timeout * 1000)
                    self._log("✅ Firefox浏览器初始化完成")
                    
                except Exception as firefox_error:
                    self._log(f"❌ Firefox也失败: {firefox_error}")
                    
                    # 尝试使用WebKit作为最后选择
                    try:
                        self._log("🔄 尝试使用WebKit引擎...")
                        self.browser = self.playwright.webkit.launch(
                            headless=self.config.headless_mode
                        )
                        context = self.browser.new_context()
                        self.page = context.new_page()
                        self.page.set_default_timeout(self.config.timeout * 1000)
                        self._log("✅ WebKit浏览器初始化完成")
                        
                    except Exception as webkit_error:
                        self._log(f"❌ WebKit也失败: {webkit_error}")
                        raise RuntimeError(f"所有浏览器引擎初始化失败:\nChrome: {chrome_error}\nFirefox: {firefox_error}\nWebKit: {webkit_error}")
            
        except Exception as e:
            self._log(f"❌ 浏览器初始化失败: {e}")
            raise RuntimeError(f"浏览器初始化失败: {e}")
    
    def _execute_search(self):
        """执行搜索流程"""
        try:
            # 构建查询URL（基于现有实现）
            # 使用bidding_notification.py中的完整URL格式
            import urllib.parse
            
            # URL编码公告类型
            types_encoded = urllib.parse.quote(self.config.announcement_type)
            start_url = f"https://www.bidding.csg.cn/dbsearch.jspx?channelId=309&types={types_encoded}&org=&q="
            
            self._log(f"🔍 访问搜索页面: {start_url}")
            self.page.goto(start_url, wait_until='load')
            
            # 填入搜索关键字
            self._log(f"📝 输入搜索关键词: {self.config.search_keyword}")
            self.page.fill("input[id='txtKey']", self.config.search_keyword)
            
            # 公告类型已经在URL中设置，无需再次选择
            # self.page.select_option('#types', value=self.config.announcement_type)
            
            # 点击搜索按钮，处理弹出新页面
            self._log("🔎 点击搜索按钮...")
            with self.page.expect_popup() as popup_info:
                self.page.click("input[class='seachBtn']")
            
            # 切换到新页面
            self.prev_page = self.page
            self.page = popup_info.value
            self.page.locator('div.List2').wait_for(state='visible')
            
            self._log(f"📄 进入搜索结果页面: {self.page.title()}")
            
            # 获取总页数信息
            total_pages = self._get_total_pages()
            self._log(f"📊 预计总页数: {total_pages}")
            
            # 开始爬取页面
            self._crawl_pages(total_pages)
            
        except Exception as e:
            raise RuntimeError(f"搜索执行失败: {e}")
    
    def _get_total_pages(self) -> int:
        """获取总页数"""
        try:
            import re
            
            content = self.page.content()
            pattern = r"共(\d+)条记录\s+(\d+)/(\d+)页"
            match = re.search(pattern, content)
            
            if match:
                total_records = int(match.group(1))
                current_page = int(match.group(2))
                total_pages = int(match.group(3))
                
                self._log(f"📈 找到 {total_records} 条记录，共 {total_pages} 页")
                return min(total_pages, self.config.max_pages)
            else:
                self._log("⚠️ 无法解析页面信息，使用默认值")
                return self.config.max_pages
                
        except Exception as e:
            self._log(f"⚠️ 获取页面信息失败: {e}")
            return self.config.max_pages
    
    def _crawl_pages(self, total_pages: int):
        """爬取所有页面"""
        self.current_page_num = 1
        
        while self.current_page_num <= total_pages and not self.stop_crawl:
            try:
                self._log(f"📖 处理第 {self.current_page_num}/{total_pages} 页")
                
                # 更新进度
                if self.progress_callback:
                    self.progress_callback(self.current_page_num, total_pages, 
                                         f"正在处理第 {self.current_page_num} 页")
                
                # 解析当前页面
                page_results = self._parse_current_page()
                
                # 保存结果
                for result in page_results:
                    if result:  # 跳过重复项
                        self.session.add_result(result)
                
                self.session.total_pages_crawled = self.current_page_num
                
                # 检查是否需要停止（基于日期限制）
                if self._should_stop_crawling(page_results):
                    self._log("📅 达到日期限制，停止爬取")
                    break
                
                # 尝试翻到下一页
                if self.current_page_num < total_pages:
                    if not self._go_to_next_page():
                        self._log("❌ 无法翻到下一页，结束爬取")
                        break
                
                # 随机延迟
                self._random_wait()
                
            except Exception as e:
                self._log(f"❌ 处理第 {self.current_page_num} 页时出错: {e}")
                logger.error(f"页面处理错误: {e}", exc_info=True)
            
            finally:
                self.current_page_num += 1
    
    def _parse_current_page(self) -> List[CrawlResult]:
        """解析当前页面内容"""
        try:
            content = self.page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # 查找内容列表
            content_div = soup.find('div', class_='List2')
            if not content_div:
                self._log("⚠️ 未找到内容区域")
                return []
            
            results = []
            items = content_div.find_all("li")
            
            self._log(f"🔍 页面找到 {len(items)} 个项目")
            
            for item in items:
                try:
                    result = self._parse_item(item)
                    if result:
                        results.append(result)
                        self._log(f"✅ 成功解析: {result.title[:50]}...")
                    else:
                        self._log("⚠️ 跳过重复项目")
                        
                except Exception as e:
                    self._log(f"❌ 解析项目失败: {e}")
                    continue
            
            return results
            
        except Exception as e:
            self._log(f"❌ 解析页面失败: {e}")
            return []
    
    def _parse_item(self, item) -> Optional[CrawlResult]:
        """解析单个项目"""
        try:
            links = item.find_all("a")
            if len(links) < 3:
                return None
            
            # 提取基本信息
            announcement_type = links[0].text.strip()
            company = links[1].text.strip()
            project_name = links[2].text.strip()
            url = f"https://www.bidding.csg.cn{links[2].get('href')}"
            
            # 提取日期
            date_span = item.find('span', class_='Black14 Gray')
            date_str = date_span.text.strip() if date_span else ""
            
            # 检查日期限制
            if self.config.earliest_date and date_str:
                if date_str < self.config.earliest_date:
                    self.stop_crawl = True
                    return None
            
            # 获取详细内容
            detail_content = self._get_detail_content(url)
            
            # 构建元数据
            metadata = {
                'title': detail_content.get('title', project_name),
                'content_text': detail_content.get('content', ''),
                'date': detail_content.get('date', date_str),
                'announcement_type': announcement_type,
                'company': company,
                'project_name': project_name
            }
            
            # 保存到本地文件
            result = self.storage.save_html_content(
                url=url,
                content=detail_content.get('raw_html', ''),
                metadata=metadata
            )
            
            return result
            
        except Exception as e:
            logger.error(f"解析项目失败: {e}")
            return None
    
    def _get_detail_content(self, url: str) -> dict:
        """获取详细页面内容"""
        try:
            self._log(f"🔗 访问详细页面: {url}")
            
            # 访问详细页面
            self.page.goto(url, wait_until='load')
            self.page.locator('div.s-content').wait_for(state='visible')
            
            # 解析页面内容
            soup = BeautifulSoup(self.page.content(), 'html.parser')
            
            # 提取标题
            title_tag = soup.find('h1', class_='s-title')
            title = title_tag.text.strip() if title_tag else ""
            
            # 提取日期
            date_tag = soup.find('div', class_='s-date')
            date = date_tag.text.strip() if date_tag else ""
            
            # 提取正文内容
            content_div = soup.find('div', class_='Content')
            content_text = content_div.text.strip() if content_div else ""
            
            return {
                'title': title,
                'date': date,
                'content': content_text,
                'raw_html': self.page.content()
            }
            
        except Exception as e:
            self._log(f"❌ 获取详细内容失败: {e}")
            return {
                'title': '',
                'date': '',
                'content': '',
                'raw_html': ''
            }
    
    def _should_stop_crawling(self, results: List[CrawlResult]) -> bool:
        """检查是否应该停止爬取"""
        if not self.config.earliest_date or not results:
            return False
        
        # 检查是否有项目的日期早于限制日期
        for result in results:
            if result and result.date and result.date < self.config.earliest_date:
                return True
        
        return False
    
    def _go_to_next_page(self) -> bool:
        """翻到下一页"""
        try:
            # 检查下一页按钮是否可用
            next_page_locator = self.page.locator('text=下一页')
            if next_page_locator.get_attribute('disabled') == 'disabled':
                return False
            
            # 点击下一页
            self.page.click('text=下一页')
            self.page.wait_for_load_state('load')
            self.page.locator('div.List2').wait_for(state='visible')
            
            return True
            
        except Exception as e:
            self._log(f"❌ 翻页失败: {e}")
            return False
    
    def _random_wait(self):
        """随机等待，避免被反爬虫检测"""
        wait_time = random.uniform(
            max(0.5, self.config.request_delay - 1),
            self.config.request_delay + 1
        )
        self._log(f"⏳ 等待 {wait_time:.1f} 秒...")
        time.sleep(wait_time)
    
    def _cleanup_browser(self):
        """清理浏览器资源"""
        try:
            if self.page:
                self.page.close()
            if self.prev_page:
                self.prev_page.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            
            self._log("🧹 浏览器资源清理完成")
            
        except Exception as e:
            logger.warning(f"清理浏览器资源时出错: {e}")
    
    def _log(self, message: str):
        """统一的日志输出"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        # 输出到系统日志
        logger.info(message)
        
        # 调用回调函数，忽略ScriptRunContext警告
        if self.log_callback:
            try:
                # 直接调用回调函数，即使在线程中也让它正常工作
                # ScriptRunContext警告可以安全忽略
                self.log_callback(formatted_message)
            except Exception as e:
                # 如果回调函数调用失败，只记录到系统日志
                logger.warning(f"日志回调失败: {e}")
                pass
    
    def stop(self):
        """停止爬取任务"""
        self.stop_crawl = True
        self._log("🛑 收到停止信号，正在停止爬取...")
    
    def get_current_status(self) -> dict:
        """获取当前状态"""
        if not self.session:
            return {'status': 'not_started'}
        
        return {
            'status': self.session.status,
            'session_id': self.session.session_id,
            'current_page': self.current_page_num,
            'total_items': self.session.total_items_found,
            'pages_crawled': self.session.total_pages_crawled,
            'start_time': self.session.start_time,
            'end_time': self.session.end_time,
            'error_message': self.session.error_message
        } 