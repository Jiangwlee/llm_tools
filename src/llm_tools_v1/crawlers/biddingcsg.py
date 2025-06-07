import re
from typing import Optional, List, Dict
from ..core.logging import get_logger
from .common import PlaywrightCrawler
from bs4 import BeautifulSoup

logger = get_logger()

class BiddingCsgCrawler:
    """
    南方电网招标公告爬虫，仅负责页面爬取和结构化数据提取。
    """
    SEARCH_URL = "https://www.bidding.csg.cn/dbsearch.jspx?q="
    LIST_SELECTOR = "div.List2"
    NEXT_PAGE_SELECTOR = "text=下一页"
    PAGE_INFO_PATTERN = r"共(\d+)条记录\s+(\d+)/(\d+)页"

    def __init__(self, verbose: bool = True):
        """
        初始化 Playwright 和浏览器实例
        """
        self.playwright = PlaywrightCrawler()
        self.prev_page = None
        self.bidding_list: List[Dict] = []
        self.end_date: Optional[str] = None
        self.stop_crawl = True

    def search(self, keyword: str, max_page: int = 65535, end_date: Optional[str] = None) -> List[Dict]:
        """
        检索公告。
        Args:
            keyword: 检索关键字
            max_page: 最大爬取页数
            end_date: 结束日期 (YYYY-MM-DD)
        Returns:
            招标公告列表
        """
        self.bidding_list.clear()
        self.stop_crawl = False
        self.end_date = end_date
        self.playwright.start()
        try:
            self.playwright.goto(self.SEARCH_URL)
            self.playwright.fill("input[id='txtKey']", keyword)
            self.playwright.page.select_option('#types', value='服务')
            with self.playwright.page.expect_popup() as popup_info:
                self.playwright.click("input[class='seachBtn']")
            self.prev_page = self.playwright.page
            self.playwright.page = popup_info.value
            self.playwright.page.locator(self.LIST_SELECTOR).wait_for(state='visible')
            logger.info(self.playwright.page.title())
            logger.info(self.playwright.page.url)
            match = re.search(self.PAGE_INFO_PATTERN, self.playwright.page.content())
            if match:
                total_records = match.group(1)
                current_page = match.group(2)
                total_pages = match.group(3)
                logger.info(f"总记录数: {total_records}")
                logger.info(f"当前页: {current_page}")
                logger.info(f"总页数: {total_pages}")
            else:
                logger.warning("未找到匹配的内容")
            self.parse(self.playwright.page.content())
            count = 1
            while count < max_page:
                logger.info(f"正在处理第【{count}】页")
                self.next_page()
                next_page_tag = self.playwright.page.locator(self.NEXT_PAGE_SELECTOR)
                if next_page_tag.get_attribute('disabled') == 'disabled':
                    logger.info("已处理完全部页面")
                    break
                if self.stop_crawl:
                    logger.info("爬取结束")
                    break
                count += 1
            return self.bidding_list
        finally:
            self.playwright.close()

    def next_page(self) -> None:
        """
        打开下一页。
        """
        self.playwright.click(self.NEXT_PAGE_SELECTOR)
        self.playwright.page.wait_for_load_state('load')
        self.playwright.page.locator(self.LIST_SELECTOR).wait_for(state='visible')
        self.parse(self.playwright.page.content())

    def parse(self, content_text: str) -> None:
        """
        解析搜索结果页面的HTML内容，提取招标公告的信息。
        Args:
            content_text: 包含搜索结果的HTML文本
        Returns:
            None
        """
        try:
            soup = BeautifulSoup(content_text, 'html.parser')
            content_div = soup.find('div', class_='List2')
            if content_div:
                for item in content_div.find_all("li"):
                    links = item.find_all("a")
                    logger.info(f"类型：{links[0].text}, 招标方: {links[1].text}, 项目名称: {links[2].text}, 链接：https://www.bidding.csg.cn/{links[2].get('href')}")
                    create_date = item.find('span', class_='Black14 Gray')
                    logger.info(f"日期: {create_date.text if create_date else ''}")
                    if create_date and create_date.text and self.end_date and create_date.text < self.end_date:
                        self.stop_crawl = True
                    else:
                        self.bidding_list.append({
                            "type": links[0].text,
                            "part_a": links[1].text,
                            "project": links[2].text,
                            "date": create_date.text if create_date else '',
                            "url": f"https://www.bidding.csg.cn{links[2].get('href')}"
                        })
            else:
                logger.warning("未找到正文内容")
        except Exception as e:
            logger.error(f"读取内容失败: {e}")

    def read_bidding_page(self, url):
        """
        阅读标讯。

        该方法用于读取单个招标公告的详细信息。

        参数：
            url (str): 招标公告的URL。

        返回值：
            dict: 包含招标公告的标题、日期和正文内容的字典。
                  字典的结构如下：
                  {
                      "title": str,    # 招标公告的标题
                      "date": str,     # 招标公告的日期
                      "content": str   # 招标公告的正文内容
                  }
        """
        try:
            logger.info(f"开始访问链接: {url}")
            self.playwright.start()
            self.playwright.goto(url, wait_until='load')
            self.playwright.page.locator('div.s-content').wait_for(state='visible')
            soup = BeautifulSoup(self.playwright.page.content(), 'html.parser')

            title_tag = soup.find('h1', class_='s-title')
            date_tag = soup.find('div', class_='s-date')
            content_div = soup.find('div', class_='Content')
            return {
                "title": title_tag.text,
                "date": date_tag.text,
                "content": content_div.text
            }
        except Exception as e:
            logger.error(f"访问链接时发生错误: {url}。 错误信息: {e}")
            return None
        finally:
            self.playwright.close()

if __name__ == "__main__":
    crawler = BiddingCsgCrawler()
    # result = crawler.search("广州供电局", max_page=3)
    # for item in result:
    #     print(item)

    print(crawler.read_bidding_page("https://www.bidding.csg.cn/zbhxrgs/1200395227.jhtml"))