class BiddingCSG:
    """
    不要使用 requests, 目标网站有爬虫检测, 简单爬虫容易被检测到, 导致封 IP.
    """
    def __init__(self, verbose=True):
        """初始化 Playwright 和浏览器实例"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=not verbose, args=["--disable-blink-features=AutomationControlled"])  # 设置为 False 以便调试
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        self.prev_page = None
        self.bidding_list = []
        self.filtered_list = []
        self.end_date = None
        self.stop_crawl = True

    def search(self, keyword, max_page=65535, end_date=None, query_url=None):
        """
        检索公告。

        该方法用于在南方电网的招标网站上搜索招标公告。

        参数：
            keyword (str): 检索关键字。
            max_page (int, 可选): 最大爬取页数，默认为 65535。
            end_date (str, 可选): 要爬取公告的结束日期，格式为 "YYYY-MM-DD"，默认为 None。
            query_url (str, 可选): 检索页面地址，默认为 "https://www.bidding.csg.cn/dbsearch.jspx?q="。

        返回值：
            None
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
        """
        打开下一页。

        该方法用于在招标网站上打开下一页搜索结果。

        参数：
            无

        返回值：
            None
        """
        # 打开下一页
        self.page.click('text=下一页')
        self.page.wait_for_load_state('load')
        self.page.locator('div.List2').wait_for(state='visible')
        self.parse(self.page.content())

    def parse(self, content_text):
        """
        解析搜索结果页面的HTML内容，提取招标公告的信息。

        该方法用于解析搜索结果页面的HTML内容，提取招标公告的类型、甲方、项目名称、日期和链接等信息，
        并将信息存储在 self.bidding_list 列表中。

        参数：
            content_text (str): 包含搜索结果的HTML文本。

        返回值：
            str: 如果解析成功，则返回空字符串 ""。如果未找到正文内容或发生异常，则返回空字符串 ""。
        """
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
                    if create_date and create_date.text and self.end_date and create_date.text < self.end_date:
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

    def filter(self, keyword, bidding_type=None, max_items: int = None):
        """
        过滤出包含特定关键字的公告。

        该方法用于从数据库中查找相关的招标公告，并过滤出包含特定关键字（例如 "投标报价"）的公告。

        参数：
            keyword (str): 过滤关键字。
            bidding_type (int, 可选): 公告类型，1=投标报价，2=投标费率。默认为 None。
            max_items (int, 可选): 最大处理公告数量，默认为 None 表示处理所有公告。

        返回值：
            None
        """
        bidding_list = self.lookup(keyword)
        update_list = []
        total_items = len(bidding_list)
        max_items = min(total_items, max_items) if max_items is not None else total_items
        logger.info(f"开始处理公告列表，共 {total_items} 条记录，最大处理数量: {max_items}")
        
        for i, item in enumerate(bidding_list):
            if i >= max_items:
                logger.info(f"已达到最大处理数量 {max_items}，停止处理")
                break
                
            logger.info(f"正在处理第 {i+1}/{max_items} 条公告: {item['url']}")
            try:
                self.page.goto(item['url'], wait_until='load')
                soup = BeautifulSoup(self.page.content(), 'html.parser')
                content_div = soup.find('div', class_='Content')

                title_tag = soup.find('h1', class_='s-title')
                item['project'] = title_tag.text

                if bidding_type == 1 or bidding_type is None:
                    found_elements = content_div.find_all(lambda tag: '>投标报价<' in str(tag))
                    if found_elements:
                        logger.info("找到包含 '>投标报价<' 的标签：")
                        logger.info(content_div.text)
                        result = LLMHelper.llm_summary(content_div)
                        logger.info(result)
                        item['summary'] = result
                        update_list.append(item)
                        # break
                if bidding_type == 2 or bidding_type is None:
                    found_elements = content_div.find_all(lambda tag: '>投标费率<' in str(tag))
                    if found_elements:
                        logger.info(f"找到投标费率, 尝试使用大模型提取投标费率. URL: {item['url']}")
                        result = LLMHelper.llm_price_extract(self.page.content())
                        logger.info(f"大模型解读结果: \n{json.dumps(result, indent=2, ensure_ascii=False)}")
                        item['summary'] = result
                        update_list.append(item)
                if (bidding_type == 1 and not content_div.find_all(lambda tag: '>投标报价<' in str(tag))) or (bidding_type == 2 and not content_div.find_all(lambda tag: '>投标费率<' in str(tag))):
                    logger.warning(f"无投标报价和投标费率，跳过此公告.")
            except Exception as e:
                logger.error(f"访问链接时发生错误: {item['url']}")

            self.random_wait()
        logger.info(f"更新数据库，共 {len(update_list)} 条记录, {update_list}")
        self.update(update_list)

    def save_to_db(self):
        """
        将爬取的招标信息保存到数据库中。

        该方法用于将爬取的招标信息保存到数据库中，避免重复爬取相同的信息。

        参数：
            无

        返回值：
            None
        """
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
            logger.info(f"数据库 Update 错误: {e}")

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
                logger.info(f"正在处理第 {len(update_list) + 1}/{len(results_with_summary)} 条记录")
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