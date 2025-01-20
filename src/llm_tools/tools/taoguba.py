import os
import json
import requests
import datetime
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from playwright.sync_api import sync_playwright
from llm_tools.config import TGB_USERNAME, TGB_PASSWORD

def get_tgb_hot_articles():
    tgb = Taoguba()
    return tgb.get_hot_articles()

class Taoguba:
    def __init__(self):
        """初始化 Playwright 和浏览器实例"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])  # 设置为 False 以便调试
        self.context = self.browser.new_context()
        self.page = self.context.new_page()

    def login(self):
        """
        使用 Playwright 自动登录淘股吧
        :param username: 用户名
        :param password: 密码
        """
        login_url = "https://sso.tgb.cn/web/login/index"
        self.page.goto(login_url)

        # 等待页面加载
        # self.page.wait_for_load_state("networkidle")
        self.page.click("#userLoginBtn")

        # 填写用户名和密码
        self.page.fill("input[id='userName']", TGB_USERNAME)
        self.page.fill("input[id='password1']", TGB_PASSWORD)

        # 点击登录按钮
        self.page.click("#loginbtn1")

        # 等待页面跳转或验证登录状态
        self.page.wait_for_timeout(3000)  # 等待 3 秒，可根据需要调整

        # 检查是否登录成功 (假设页面会包含某些用户标识元素)
        if self.username in self.page.locator(".header-user-content").text_content():
        # if "我的主页" in self.page.content():
            print("登录成功")
        else:
            print("登录失败，请检查用户名和密码")

    def __del__(self):
        """在类实例销毁时，关闭浏览器和 Playwright"""
        print("正在关闭浏览器...")
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def read_article(self, url: str):
        try:
            # 发送HTTP请求获取网页内容
            response = requests.get(url, timeout=10)
            response.encoding = 'utf-8'  # 设置编码

            # 解析网页内容
            soup = BeautifulSoup(response.text, 'html.parser')

            # 查找包含正文内容的 <div> 标签
            content_div = soup.find('div', class_='article-text p_coten')

            # 提取正文内容
            if content_div:
                # 移除隐藏的内容（如 style="display:none;" 的部分）
                for hidden in content_div.find_all(style="display:none;"):
                    hidden.decompose()  # 彻底移除标签

                # 提取文本内容，并去除多余的空格和换行
                content = content_div.get_text(separator="\n", strip=True)
                return content
            else:
                print(f"未找到正文内容: {url}")
                return ""
        except Exception as e:
            print(f"读取文章失败: {url}, 错误: {e}")
            return ""

    def get_hot_articles(self):
        """获取精华热帖"""
        # 目标URL
        url = 'https://www.tgb.cn/jinghua/1-1'

        # 发送GET请求
        response = requests.get(url, timeout=10)
        response.encoding = 'utf-8'

         # 解析网页内容
        soup = BeautifulSoup(response.text, 'html.parser')

        # 查找包含正文内容的 <div> 标签
        div_list = soup.findAll('div', class_='Nbbs-tiezi-lists')
        article_list = []
        max_date = None
        for article in div_list:
            info = article.find('a', class_='overhide mw300')
            user = article.find('a', class_='mw100 overhide')
            create_time = article.find('div', class_='left middle-list-post')
            create_date = create_time.text.split(' ')[0]

            if max_date == None or create_date >= max_date:
                max_date = create_date

            article_list.append(
                {
                    'userName': user.text,
                    'subject': info.get('title'),
                    'url': f"https://www.tgb.cn/{info.get('href')}",
                    'date': create_date
                }
            )
        article_list = [x for x in article_list if x['date'] == max_date]
        return self.get_articles(article_list)
        
    def get_recommend_articles(self):
        """获取推荐帖子"""
        # 目标URL
        url = 'https://www.tgb.cn/newIndex/getNowRecommend?pageNo=1'

        # 发送GET请求
        response = requests.get(url)

        # 检查请求是否成功
        if response.status_code == 200:
            # 打印获取到的内容
            resp = json.loads(response.text)
            articles = [
                {
                    'userName': x['userName'],
                    'subject': x['subject'],
                    'url': f"https://www.tgb.cn/a/{x['newTopicID']}?sy_jrtj"
                } for x in resp['dto']['list']
            ]
            return self.get_articles(articles)
        else:
            print(f"请求失败，状态码: {response.status_code}")
            return []

    def get_articles(self, articles):
        if not articles:
            return []

        # 使用 ThreadPoolExecutor 并行化读取文章内容
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_article = {executor.submit(self.read_article, a['url']): a for a in articles}

            for future in as_completed(future_to_article):
                article = future_to_article[future]
                try:
                    article['content'] = future.result()
                except Exception as e:
                    print(f"处理文章时出错: {article['url']}, 错误: {e}")
                    article['content'] = ""

        return articles


# 测试代码
if __name__ == "__main__":
    import os
    tgb = Taoguba()
    tgb.login()
    # hot_articles = tgb.get_tgb_hot_articles()
    # for article in hot_articles:
    #     print(f"用户: {article['userName']}, 标题: {article['subject']}")
    #     print(f"内容: {article['content'][:100]}...")  # 仅打印前100字符
    
    # print(hot_articles[0])
    # print(tgb.get_hot_articles())
    # resp = requests.get("http://home.justdofun.top:12345/tgb/hot-articles")
    # print(resp.text)