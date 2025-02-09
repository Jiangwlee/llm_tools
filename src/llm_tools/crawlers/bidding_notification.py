"""
招标公告爬虫.
"""

import os
import re
import json
import argparse
from datetime import date, datetime
from llm_tools.tools.bidding_csg import BiddingCSG
from llm_tools.connector import getConnection, get_logger
from llm_tools.config import BIDDING_DIR

logger = get_logger()

def format_date(date_str):
    return datetime.strptime(date_str, "%Y%m%d").strftime("%Y-%m-%d")

class BiddingCrawler:
    def __init__(self, end_date: str):
        """
        ## Parameter:
        end_date: 结束日期，格式为：20250102 形式
        """
        self.start_url = "https://www.bidding.csg.cn/dbsearch.jspx?channelId=309&types=%E6%9C%8D%E5%8A%A1&org=&q="
        self.bidding_notices = []
        self.end_date = format_date(end_date)

    def crawl(self):
        crawler = BiddingCSG()
        crawler.search("", end_date=self.end_date, query_url=self.start_url)
        for item in crawler.bidding_list:
            if item['type'] == '招标公告':
                print(item['project'], ':', item['url'])
                result = crawler.read_bidding_page(item['url'])
                print(f"    title: {result['title']}")
                print(f"    date: {result['date']}")
                print(f"    content: {result['content']}")
                print('-' * 50)
                self.bidding_notices.append({
                    'title': result['title'],
                    'content': result['content'],
                    'notice_time': self.filter_time(result['date']),
                    'company': item['part_a'],
                    'url': item['url'],
                    'type': item['type']
                })
                logger.info(self.bidding_notices)

    def filter_time(self, text):
        pattern = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'
        # 使用 re.search 函数在文本中查找匹配的时间
        match = re.search(pattern, text)
        # 获取当前时间
        current_time = datetime.now()

        # 将当前时间格式化为 "2025-02-08 14:19:56" 形式
        time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
        logger.info(time_str)

        if match:
            # 如果找到匹配项，提取匹配的时间字符串
            time_str = match.group()
            print("提取到的时间为:", time_str)
        else:
            print("未找到时间信息。")

        return time_str
    
    def save(self, date_str: str):
        with open(os.path.join(BIDDING_DIR, f"bidding_notice_{date_str}.json"), 'w', encoding='utf-8') as outfile:
            json.dump(self.bidding_notices, outfile, indent=2, ensure_ascii=False)
        return len(self.bidding_notices)

    def save_to_db(self):
        # 插入数据的 SQL 语句
        insert_query = """
        INSERT INTO bidding_notice (title, content, notice_time, company, url, type)
        VALUES (%s, %s, %s, %s, %s, %s)
        """

        # 检查 URL 是否存在的 SQL 语句
        check_url_query = """
        SELECT url FROM bidding_notice WHERE url = %s
        """

        try:
            # 连接数据库
            connection = getConnection()
            if connection is None:
                logger.warning("数据库未启用")
                return
            cursor = connection.cursor()

            # 用于存储唯一的数据
            unique_data_to_insert = []

            for item in self.bidding_notices:
                url = item["url"]
                # 检查 URL 是否已存在
                cursor.execute(check_url_query, (url,))
                result = cursor.fetchone()

                if not result:  # 如果 URL 不存在
                    unique_data_to_insert.append((item["title"], item["content"], item["notice_time"], item["company"], item["url"], item["type"]))
                else:
                    logger.info(f"URL 已存在，跳过: {url}")

            # 执行批量插入
            if unique_data_to_insert:
                cursor.executemany(insert_query, unique_data_to_insert)
                connection.commit()
                logger.info(f"成功插入 {cursor.rowcount} 条数据")
                return cursor.rowcount
            else:
                logger.info("没有新数据需要插入")
                return 0

        except Exception as e:
            logger.error(f"数据库错误: {e}")

        finally:
            # 关闭连接
            if connection.is_connected():
                cursor.close()
                connection.close()
                logger.info("数据库连接已关闭")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Bidding Crawler Script")
    parser.add_argument('--date', type=str, default=date.today().strftime('%Y%m%d'),
                        help="Specify the date in YYYYMMDD format (default: today's date)")

    args = parser.parse_args()
    date_str = args.date  # 使用命令行参数中的日期

    crawler = BiddingCrawler(date_str)
    crawler.crawl()
    crawler.save(date_str) 