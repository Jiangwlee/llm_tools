from playwright.sync_api import sync_playwright, Page, Browser, Playwright
from typing import Optional

class PlaywrightCrawler:
    """
    只负责页面加载、表单操作、页面跳转和HTML源码获取，不做任何业务数据解析和存储。
    """
    def __init__(self, headless: bool = True):
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context = None
        self.page: Optional[Page] = None
        self.headless = headless

    def start(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless, args=["--disable-blink-features=AutomationControlled"])
        self.context = self.browser.new_context()
        self.page = self.context.new_page()

    def goto(self, url: str, wait_until: str = 'load'):
        """跳转到指定URL"""
        if not self.page:
            raise RuntimeError("Crawler未启动，请先调用start()方法")
        self.page.goto(url, wait_until=wait_until)

    def fill(self, selector: str, value: str):
        """填充表单字段"""
        if not self.page:
            raise RuntimeError("Crawler未启动，请先调用start()方法")
        self.page.fill(selector, value)

    def click(self, selector: str):
        """点击页面元素"""
        if not self.page:
            raise RuntimeError("Crawler未启动，请先调用start()方法")
        self.page.click(selector)

    def get_html(self) -> str:
        """获取当前页面HTML源码"""
        if not self.page:
            raise RuntimeError("Crawler未启动，请先调用start()方法")
        return self.page.content()

    def close(self):
        if self.page:
            self.page.close()
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop() 