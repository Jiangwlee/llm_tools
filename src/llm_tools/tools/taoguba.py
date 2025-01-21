import csv
import time
import json
import re
import random
import requests
import datetime
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from playwright.sync_api import sync_playwright
from llm_tools.config import TGB_USERNAME, TGB_PASSWORD, TGB_BASEURL
from llm_tools.logger import get_logger

logger = get_logger()

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
        self.page.wait_for_load_state("networkidle")
        self.page.click("#userLoginBtn")

        # 填写用户名和密码
        self.page.fill("input[id='userName']", TGB_USERNAME)
        self.page.fill("input[id='password1']", TGB_PASSWORD)

        # 点击登录按钮
        self.page.click("#loginbtn1")

        # 等待页面跳转或验证登录状态
        # self.page.wait_for_timeout(3000)  # 等待 3 秒，可根据需要调整

        # 检查是否登录成功 (假设页面会包含某些用户标识元素)
        if TGB_USERNAME in self.page.locator(".header-user-content").text_content():
        # if "我的主页" in self.page.content():
            print("登录成功")
        else:
            print("登录失败，请检查用户名和密码")

    def crawl_blog(self, url: str):
        """爬取用户的全部博客和回帖信息

        ## Arguments:
        - url: 个人博客入口链接. 比如: https://www.tgb.cn/user/blog/moreTopic?userID=1116585
        """
        # 第一步: 从入口获取所有帖子链接
        self.page.goto(url)
        soup = BeautifulSoup(self.page.content(), "html.parser")
        form_tag = soup.find('form', {'name': 'main'})
        links = form_tag.findAll('a', {'target': '_blank'})
        blogs = [
            {
                'url': f"{TGB_BASEURL}{x['href']}",
                'title': x['title']
            } for x in links
        ]

        # 第二步: 顺序访问每个帖子，获取作者发言和回帖
        results = []
        for blog in blogs:
            print("-" * 50)
            print(f"【标题】{blog['title']}")
            results.append(self.crawl_article(blog['url']))
        return results

    def crawl_article(self, url: str):
        article = {}
        self.page.goto(url)
        soup = BeautifulSoup(self.page.content(), "html.parser")

        # 读取标题
        title_div = soup.find(id='gioMsg')
        title = title_div['subject']
        username = title_div['username'].strip()
        article['title'] = title
        article['username'] = username

        # 提取页数
        pc_fpag_div = soup.find('div', class_='pc_fpag')
        pattern = r"/(\d+)页"
        match = re.search(pattern, pc_fpag_div.text)
        total_page = 0
        if match:
            page_number = match.group(1)  # 提取捕获组中的内容
            total_page = int(page_number)
            print("总页数：", total_page)
        else:
            print("未找到匹配的页数")

        # 读取正文
        content_div = soup.find(id='first')
        article['content'] =content_div.text

        # 读取评论
        comments = self.read_comments(username)
        
        page_count = 2
        while page_count <= total_page:
            try:
                self.page.goto(f"{url}-{str(page_count)}")
                comments_of_page = self.read_comments(username)
                comments.extend(comments_of_page)
            except Exception as e:
                logger.error(f"异常: {e}")
            page_count += 1
        article['comments'] = comments
        self.save_comments_to_csv(comments, 'a')
        return article

    def read_comments(self, username: str):
        comments = []
        soup = BeautifulSoup(self.page.content(), "html.parser")
        for comment in soup.find_all('div', attrs={"subject": True, "username": True}):
            subject_attr = BeautifulSoup(comment['subject'], 'html.parser')
            # 提取正文内容（去除所有 HTML 标签）
            subject = subject_attr.get_text(separator='').strip()
            # subject = comment['subject']
            user = comment['username'].strip()
            
            # print(f"【{user}】{subject}")
            if user.strip() == username and len(subject) > 50:
                userid = comment['userid']
                user_comment_data = soup.find('div', class_=f"comment-data user_{userid}")
                comment_time = user_comment_data.find('span', class_='pcyclspan').text
                print(comment_time)
                comments.append({
                    "subject": subject,
                    "username": user,
                    "comment_time": comment_time
                })
                print(f"subject: {subject}")
                print(f"username: {user}")
        return comments

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

    def random_wait(self):
        # 生成 1 到 3 秒之间的随机等待时间，防止被反爬虫机制检测到
        wait_time = random.uniform(1, 3)
        # 打印等待时间
        logger.info(f"等待时间: {wait_time:.2f} 秒")
        # 等待
        time.sleep(wait_time)

    def save_comments_to_csv(self, comments, mode='w'):
        if len(comments) == 0:
            return
        csv_list = [['author', 'comments', 'comment_time']]
        filename = f"tgb_comments_{comments[0]['username']}.csv"
        with open(filename, 'r', encoding='utf-8') as infile:
            if len(infile.readline()) > 0 and 'a' in mode:
                csv_list = []
                logger.info("CSV 文件为追加模式, 不添加表头.")
        for item in comments:
            csv_list.append([item['username'], item['subject'], item['comment_time']])
        with open(filename, mode, encoding='utf-8', newline="") as outfile:
                writer = csv.writer(outfile)
                writer.writerows(csv_list)


ARTICLE_TEMPLATE = """
## 标题: {title} 

**作者: **{author}

{content}

"""
# 测试代码
if __name__ == "__main__":
    # print(ARTICLE_TEMPLATE.format(title="标题A", author="zuozhe", content="content"))
    
    import os
    tgb = Taoguba()
    tgb.login()
    result = tgb.crawl_blog("https://www.tgb.cn/user/blog/moreTopic?userID=1116585")
    # result = tgb.crawl_article("https://www.tgb.cn/a/1ykDEq6OT9h")
    # tgb.save_comments_to_csv(result['comments'], mode='a')
    articles = []
    for blog in result:
        username = blog['username']
        title = blog['title']
        content = blog['content']
        articles.append(ARTICLE_TEMPLATE.format(title=title, author=username, content=content))
        # tgb.save_comments_to_csv(blog['comments'], 'a')

    with open(f"淘股吧_{result[0]['username']}.md", 'w', encoding='utf-8') as outfile:
        outfile.write('\n'.join(articles))
    # hot_articles = tgb.get_tgb_hot_articles()
    # for article in hot_articles:
    #     print(f"用户: {article['userName']}, 标题: {article['subject']}")
    #     print(f"内容: {article['content'][:100]}...")  # 仅打印前100字符
    
    # print(hot_articles[0])
    # print(tgb.get_hot_articles())
    # resp = requests.get("http://home.justdofun.top:12345/tgb/hot-articles")
    # print(resp.text)