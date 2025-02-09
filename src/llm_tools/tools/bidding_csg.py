import re
import csv
import random
import json
import time
from openai import OpenAI
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from llm_tools.connector import getConnection
from llm_tools.logger import get_logger
from llm_tools.config import LLM_API_KEY, LLM_BASE_URL
from llm_tools.utils.number_util import is_number

logger = get_logger()

class BiddingParser:
    def __init__(self, html: str):
        self.html_text = html

    def parse_announcement(self):
        soup = BeautifulSoup(self.html_text, 'html.parser')
        tables = soup.findAll('table') # 找到内容部分

        all_table_data = []
        for t in tables:
            rows = t.findAll('tr')
            table_data = []
            # parse <td>
            prev_row = None
            for r in rows:
                columns = r.findAll('td')
                col_text = [c.text for c in columns]
                if prev_row is not None and len(prev_row) > len(col_text):
                    leading = prev_row[:(len(prev_row) - len(col_text))]
                    leading.extend(col_text)
                    col_text = leading
                table_data.append(col_text)
                prev_row = col_text
                print(', '.join(col_text))
            all_table_data.append(table_data)
        return {
            "tables": all_table_data
        }

    def parse_bid_price(self):
        announcement = self.parse_announcement()
        result = []
        for table in announcement['tables']:
            subject_index = None
            package_index = None
            price_index = None
            header = table[0]
            for i in range(0, len(header)):
                if self.is_subject(header[i]):
                    subject_index = i
                    continue
                if self.is_package(header[i]):
                    package_index = i
                    continue
                if self.is_max_price(header[i]):
                    price_index = i
            if subject_index is None or package_index is None or price_index is None:
                subject_index = None
                package_index = None
                price_index = None
                continue
            # 找到了中标信息表
            logger.info(table)
            for i in range(1, len(table)):
                print(i)
                row = table[i]
                result.append({
                    "subject": row[subject_index],
                    "package": row[package_index],
                    'price': row[price_index]
                })
        return result
            

    def is_subject(self, text: str):
        return text.startswith('标的')

    def is_package(self, text: str):
        return text.startswith('标包名称')

    def is_max_price(self, text: str):
        return text.startswith('最高限价')

class BiddingCSG:
    """
    不要使用 requests, 目标网站有爬虫检测, 简单爬虫容易被检测到, 导致封 IP.
    """
    def __init__(self):
        """初始化 Playwright 和浏览器实例"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])  # 设置为 False 以便调试
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        self.prev_page = None
        self.bidding_list = []
        self.filtered_list = []
        self.end_date = None
        self.stop_crawl = True

    def search(self, keyword, max_page=65535, end_date=None, query_url=None):
        """检索公告
        ## 参数
        - keyword: 检索关键字
        - max_page: 最大爬取页数
        - end_date: 要爬取公告的结束日期。取值为 None 或者 “2024-12-06” 格式的的日期字符串。
        - query_url: 检索页面地址，默认为：https://www.bidding.csg.cn/dbsearch.jspx?q=
        """
        self.stop_crawl = False
        self.end_date = end_date
        start_url = f"https://www.bidding.csg.cn/dbsearch.jspx?q=" if query_url is None else query_url
        self.page.goto(start_url, wait_until='load')

        # 填入搜索关键字
        self.page.fill("input[id='txtKey']", keyword)
        # 选择公告类型
        self.page.select_option('#types', value='服务')
        
        # 假设点击一个按钮会打开新标签页
        with self.page.expect_popup() as popup_info:
            self.page.click("input[class='seachBtn']")

        self.prev_page = self.page
        self.page = popup_info.value
        self.page.locator('div.List2').wait_for(state='visible')

        # 在新标签页中操作
        logger.info(self.page.title())
        logger.info(self.page.url)
        
        # 过滤页数信息, 正则表达式
        pattern = r"共(\d+)条记录\s+(\d+)/(\d+)页"

        # 匹配内容
        match = re.search(pattern, self.page.content())

        if match:
            total_records = match.group(1)  # 总记录数
            current_page = match.group(2)   # 当前页
            total_pages = match.group(3)    # 总页数
            logger.info(f"总记录数: {total_records}")
            logger.info(f"当前页: {current_page}")
            logger.info(f"总页数: {total_pages}")
        else:
            print("未找到匹配的内容")

        # 解析页面
        self.parse(self.page.content())
        count = 1
        while count < max_page:
            logger.info(f"正在处理第【{count}】页")
            self.next_page()
            next_page_tag = self.page.locator('text=下一页')
            if next_page_tag.get_attribute('disabled') == 'disabled':
                logger.info("已处理完全部页面")
                break
            if self.stop_crawl:
                logger.info("爬取结束")
                break
            count += 1

    def next_page(self):
        # 打开下一页
        self.page.click('text=下一页')
        self.page.wait_for_load_state('load')
        self.page.locator('div.List2').wait_for(state='visible')
        self.parse(self.page.content())

    def parse(self, content_text):
        try:
            # 解析网页内容
            soup = BeautifulSoup(content_text, 'html.parser')

            # 查找包含正文内容的 <div> 标签
            content_div = soup.find('div', class_='List2')

            # 提取正文内容
            if content_div:
                for item in content_div.find_all("li"):
                    # print(item)
                    links = item.find_all("a")
                    # print(f"类型：{links[0].text}, 招标方: {links[1].text}, 项目名称: {links[2].text}, 链接：https://www.bidding.csg.cn/{links[2].get('href')}")
                    create_date = item.find('span', class_='Black14 Gray')
                    # print(f"日期: {create_date.text}")
                    if create_date.text < self.end_date:
                        self.stop_crawl = True
                    else:
                        self.bidding_list.append({
                            "type": links[0].text,
                            "part_a": links[1].text,
                            "project": links[2].text,
                            "date": create_date.text,
                            "url": f"https://www.bidding.csg.cn{links[2].get('href')}"
                        })
            else:
                print(f"未找到正文内容")
                return ""
        except Exception as e:
            print(f"读取内容失败: {e}")
            return ""

    def read_bidding_page(self, url):
        """阅读标讯.
        """
        try:
            self.page.goto(url, wait_until='load')
            self.page.locator('div.s-content').wait_for(state='visible')
            soup = BeautifulSoup(self.page.content(), 'html.parser')

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

        self.random_wait()

    def filter(self, keyword):
        """过滤出包含【投标报价】的公告. 例子: https://www.bidding.csg.cn/zbhxrgs/1200383714.jhtml
        """
        bidding_list = self.lookup(keyword)
        update_list = []
        for item in bidding_list:
            try:
                self.page.goto(item['url'], wait_until='load')
                soup = BeautifulSoup(self.page.content(), 'html.parser')
                content_div = soup.find('div', class_='Content')

                title_tag = soup.find('h1', class_='s-title')
                item['project'] = title_tag.text

                found_elements = content_div.find_all(lambda tag: '>投标报价<' in str(tag))

                # 输出结果
                if found_elements:
                    logger.info("找到包含 '>投标报价<' 的标签：")
                    logger.info(content_div.text)
                    result = self.llm_summary(content_div)
                    logger.info(result)
                    item['summary'] = result
                    update_list.append(item)
                    # break

                # if content_div.text.find('投标报价') > 0:
                #     self.filtered_list.append(item)
            except Exception as e:
                logger.error(f"访问链接时发生错误: {item['url']}")

            self.random_wait()
        self.update(update_list)

    def save_to_db(self):
        # 插入数据的 SQL 语句
        insert_query = """
        INSERT INTO bidding_csg (type, part_a, project, create_date, url)
        VALUES (%s, %s, %s, %s, %s)
        """

        # 检查 URL 是否存在的 SQL 语句
        check_url_query = """
        SELECT url FROM bidding_csg WHERE url = %s
        """

        try:
            # 连接数据库
            connection = getConnection()
            cursor = connection.cursor()

            # 用于存储唯一的数据
            unique_data_to_insert = []

            for item in self.bidding_list:
                url = item["url"]
                # 检查 URL 是否已存在
                cursor.execute(check_url_query, (url,))
                result = cursor.fetchone()

                if not result:  # 如果 URL 不存在
                    unique_data_to_insert.append((item["type"], item["part_a"], item["project"], item["date"], item["url"]))
                else:
                    logger.info(f"URL 已存在，跳过: {url}")

            # 执行批量插入
            if unique_data_to_insert:
                cursor.executemany(insert_query, unique_data_to_insert)
                connection.commit()
                logger.info(f"成功插入 {cursor.rowcount} 条数据")
            else:
                logger.info("没有新数据需要插入")

        except Exception as e:
            logger.error(f"数据库错误: {e}")

        finally:
            # 关闭连接
            if connection.is_connected():
                cursor.close()
                connection.close()
                logger.info("数据库连接已关闭")

    def lookup(self, keyword):
        """
        从数据库中查询相关信息.
        """
        # 查询 SQL 语句
        query = """
        SELECT * FROM llm_tools.bidding_csg
        WHERE project LIKE %s
        """

        result = []
        try:
            # 连接数据库
            connection = getConnection()
            cursor = connection.cursor()

            # 执行查询
            cursor.execute(query, (f"%{keyword}%",))  # 使用 % 通配符匹配关键字

            # 获取查询结果
            results = cursor.fetchall()

            # 输出结果
            if results:
                logger.info(f"找到 {len(results)} 条包含关键字 '{keyword}' 的记录：")
                for row in results:
                    result.append({
                        "type": row[2],
                        "part_a": row[1],
                        "project": row[0],
                        "date": row[3],
                        "url": row[4],
                        "summary": row[5],
                        "price": row[6]
                    })
            else:
                logger.info(f"未找到包含关键字 '{keyword}' 的记录。")
            return result
        except Exception as e:
            logger.info(f"数据库错误: {e}")

        finally:
            # 关闭连接
            if connection.is_connected():
                cursor.close()
                connection.close()
                logger.info("数据库连接已关闭")

    def update(self, update_list):
        """更新数据库
        """
        # 更新 SQL 语句
        update_query = """
        UPDATE llm_tools.bidding_csg
        SET summary = %s, project = %s, price = %s
        WHERE url = %s
        """

        try:
            # 连接数据库
            connection = getConnection()
            cursor = connection.cursor()

            data_to_update = [(item["summary"], item["project"], item["price"], item["url"]) for item in update_list]
            
            # 执行更新
            cursor.executemany(update_query, data_to_update)
            connection.commit()

        except Exception as e:
            logger.info(f"数据库错误: {e}")

        finally:
            # 关闭连接
            if connection.is_connected():
                cursor.close()
                connection.close()
                print("数据库连接已关闭")

    def dump(self):
        with open('bidding_list.json', 'w', encoding='utf-8') as outfile:
            json.dump(self.bidding_list, outfile, indent=2)
        with open('filtered.json', 'w', encoding='utf-8') as outfile:
            json.dump(self.filtered_list, outfile, indent=2)

    def load(self):
        with open('bidding_list.json', 'r', encoding='utf-8') as infile:
            self.bidding_list = json.load(infile)

        print(f"加载了 {len(self.bidding_list)} 条记录")

    def llm_summary(self, user_prompt):
        """调用大模型总结内容.
        """
        client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)

        SYSTEM_PROMPT = """
        请仔细阅读用户提供的 HTML 内容, 提取信息, 以 JSON 格式输出。只输出 JSON 字符串, 不得输出其他内容, 也不得输出 Markdown 标记.

        以下是一个输出的例子:
        {
            "招标编号": 招标编号,
            "评标情况": [
                {
                    "标的": 标的1,
                    "标包": 标包1,
                    "候选人": 中标候选人名称,
                    "投标报价": 285
                },
                {
                    "标的": 标的1,
                    "标包": 标包2,
                    "候选人": 中标候选人名称,
                    "投标报价": 112.58
                },
            ]
        }

        """

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": str(user_prompt)},
            ],
            stream=False
        )

        resp = response.choices[0].message.content
        # print(resp)
        return resp

    def llm_price_extract(self, user_prompt):
        """调用大模型提取价格信息.
        """
        client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)

        SYSTEM_PROMPT = """
        请仔细阅读用户提供的 HTML 内容, 提取信息, 以 JSON 格式输出。只输出 JSON 字符串, 不得输出其他内容, 也不得输出 Markdown 标记.

        以下是一个输出的例子:
        {
            "招标编号": 招标编号,
            "招标情况": [
                {
                    "标的": 标的1,
                    "标包": 标包1,
                    "最高限价": 332
                },
                {
                    "标的": 标的1,
                    "标包": 标包2,
                    "最高限价": 177.42
                },
            ]
        }

        """

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": str(user_prompt)},
            ],
            stream=False
        )

        resp = response.choices[0].message.content
        # print(resp)
        return resp
    
    def analyze(self, keyword):
        """分析中标价格和招标价格
        """
        # 查询 SQL 语句
        query_final_price = """
        SELECT * FROM llm_tools.bidding_csg
        WHERE summary IS NOT NULL AND project LIKE %s
        """

        results_with_summary = []
        update_list = []
        try:
            # 连接数据库
            connection = getConnection()
            cursor = connection.cursor()

            # 执行查询
            cursor.execute(query_final_price, (f"%{keyword}%",))

            # 获取查询结果
            results = cursor.fetchall()

            # 输出结果
            if results:
                logger.info(f"找到 {len(results)} 条关于 '{keyword}' 的有价格中标记录.")
                for row in results:
                    results_with_summary.append({
                        "type": row[2],
                        "part_a": row[1],
                        "project": row[0],
                        "date": row[3],
                        "url": row[4],
                        "summary": row[5],
                        "price": row[6]
                    })
            else:
                logger.info(f"未找到包含关键字 '{keyword}' 的记录。")
            
            # 过滤出对应的招标公告，并调用大模型来提取招标金额等信息
            for item in results_with_summary:
                project_key = item['project'][:30]
                query = """
                SELECT * FROM llm_tools.bidding_csg
                WHERE project LIKE %s AND type="招标公告"
                """
                logger.info(f"Project key: {project_key}")
                cursor.execute(query, (f"%{project_key}%",))
                result = cursor.fetchall()
                if len(result) > 0:
                    url = result[0][4]
                    logger.info(f"查询招标公告 url: {url}")
                    self.page.goto(url, wait_until='load')
                    soup = BeautifulSoup(self.page.content(), 'html.parser')
                    content_div = soup.find('div', class_='Content') # 找到内容部分
                    bid_parser = BiddingParser(str(content_div))
                    price_info = bid_parser.parse_bid_price()
                    logger.info(f"项目【{item['project']}】的报价信息：{price_info}")
                    # logger.info(f"中标公告: {item['url']}")
                    # logger.info(f"中标金额: {item['summary']}")
                    item['price'] = json.dumps(price_info)
                    update_list.append(item)
                    # self.random_wait()
            self.update(update_list)
            return result
        except Exception as e:
            logger.info(f"数据库错误: {e}")

        finally:
            # 关闭连接
            if connection.is_connected():
                cursor.close()
                connection.close()
                logger.info("数据库连接已关闭")

    def random_wait(self):
        # 生成 1 到 3 秒之间的随机等待时间，防止被反爬虫机制检测到
        wait_time = random.uniform(1, 3)
        # 打印等待时间
        logger.info(f"等待时间: {wait_time:.2f} 秒")
        # 等待
        time.sleep(wait_time)

class BiddingCsgAnalyzer:
    def output_as_csv(self):
        # 以 csv 格式输出对比结果
        query = """
        SELECT * FROM llm_tools.bidding_csg bc 
        WHERE summary is not NULL AND price is not NULL;
        """

        csv_list = []
        try:
            # 连接数据库
            connection = getConnection()
            cursor = connection.cursor()

            # 执行查询
            cursor.execute(query)

            # 获取查询结果
            results = cursor.fetchall()

            # 输出结果
            if results:
                logger.info(f"找到 {len(results)} 条关于 '{keyword}' 的有价格中标记录.")
                header = ["招标编号", "甲方", "项目名称", "公告日期", "公告链接", "标的名称", "标包名称", "最高限价(万元)", "中标公司", "中标价格(万元)"]
                csv_list.append(header)
                for row in results:
                    project = row[0]
                    part_a = row[1]
                    annoce_date = row[3].strftime("%Y-%m-%d")
                    url = row[4]
                    summary = row[5]
                    price = row[6]
                    summary_obj = json.loads(summary)
                    price_obj = json.loads(price)
                    code = summary_obj["招标编号"]
                    for r in summary_obj["评标情况"]:
                        subject = r["标的"]
                        package = r["标包"]
                        company = r["候选人"]
                        price = r["投标报价"]
                        for item in price_obj:
                            if is_number(str(price)) and is_number(item['price']) and item['package'] == package:
                                data = [code, part_a, project, annoce_date, url, subject, package, item['price'], company, str(price)]
                                csv_list.append(data)
                    # break
            else:
                logger.info(f"未找到包含关键字 '{keyword}' 的记录。")
            
            with open('bidding_csg.csv', 'w', encoding='utf-8', newline="") as outfile:
                writer = csv.writer(outfile)
                writer.writerows(csv_list)
            return csv_list
        except Exception as e:
            logger.info(f"数据库错误: {e}")

        finally:
            # 关闭连接
            if connection.is_connected():
                cursor.close()
                connection.close()
                logger.info("数据库连接已关闭")

if __name__ == '__main__':
    keyword = "南方电网数字平台科技"
    csg = BiddingCsgAnalyzer()
    # csg.search("南方电网数字平台科技")
    # csg.save_to_db()
    # csg.filter(keyword)
    # csg.analyze(keyword)
    csg.output_as_csv()

