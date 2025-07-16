import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Optional

from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CacheMode,
    CrawlerRunConfig,
    JsonCssExtractionStrategy,
)

BIDDINGCSG_URL_TEMPLATE = "https://www.bidding.csg.cn/dbsearch.jspx?pageNo={page_no}&channelId=309&q={q}&org=&types=%E6%9C%8D%E5%8A%A1"

CSG_SCHEMA = {
  "name": "BiddingCSGExtractor",
  "baseSelector": ".List2 > ul > li",
  "fields": [
    {
      "name": "type",
      "selector": "a.Black14",
      "type": "text"
    },
    {
      "name": "date",
      "selector": "span.Right > span",
      "type": "text"
    },
    {
      "name": "owner",
      "selector": "a.Blue",
      "type": "text"
    },
    {
      "name": "link",
      "selector": "a:nth-child(4)",
      "type": "attribute",
      "attribute": "href"
    },
    {
      "name": "title",
      "selector": "a:nth-child(4)",
      "type": "text"
    }
  ]
}

def parse_date(date_str: str) -> datetime:
    """解析日期字符串为datetime对象，支持多种格式。"""
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(date_str, fmt)
        except Exception:
            continue
    raise ValueError(f"未知日期格式: {date_str}")

async def fetch_page(crawler, run_config, page_no: int, q: str, sem: asyncio.Semaphore) -> List[dict]:
    async with sem:
        url = BIDDINGCSG_URL_TEMPLATE.format(page_no=page_no, q=q)
        result = await crawler.arun(
            url=url,
            config=run_config,
        )
        extracted_data = json.loads(result.extracted_content)
        return extracted_data

async def crawl_pages(page_count: int = 1, q: str = "", end_date: str = "") -> List[dict]:
    browser_config = BrowserConfig()  # 默认浏览器配置
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        extraction_strategy=JsonCssExtractionStrategy(CSG_SCHEMA)
    )   # 默认爬取配置

    sem = asyncio.Semaphore(10)  # 最大并发数为10
    results = []
    if page_count > 1:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            tasks = [fetch_page(crawler, run_config, page_no, q, sem) for page_no in range(1, page_count + 1)]
            all_results = await asyncio.gather(*tasks)
            merged_results = []
            for page_data in all_results:
                merged_results.extend(page_data)
            # 过滤出end_date之后的
            if end_date:
                try:
                    end_dt = parse_date(end_date)
                    filtered_results = [result for result in merged_results if 'date' in result and parse_date(result['date']) > end_dt]
                except Exception as e:
                    print(f"[警告] 日期过滤失败: {e}, 返回全部结果")
                    filtered_results = merged_results
            else:
                filtered_results = merged_results
            results = filtered_results
    else:
        if not end_date:
            end_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        filtered_results = []
        async with AsyncWebCrawler(config=browser_config) as crawler:
            page_no = 1
            try:
                end_dt = parse_date(end_date)
            except Exception as e:
                print(f"[警告] 结束日期格式错误: {e}, 不做日期过滤")
                end_dt = None
            while True:
                result = await fetch_page(crawler, run_config, page_no, q, sem)
                # 过滤出end_date之后的
                for item in result:
                    try:
                        if end_dt is None or ('date' in item and parse_date(item['date']) > end_dt):
                            filtered_results.append(item)
                        else:
                            return filtered_results
                    except Exception as e:
                        print(f"[警告] 单条数据日期解析失败: {e}, 跳过该条")
                        continue
                page_no += 1
        results = filtered_results
    return results

if __name__ == "__main__":
    import sys
    import argparse
    parser = argparse.ArgumentParser(description="抓取中标信息（多页并发）")
    parser.add_argument("--page_count", type=int, default=1, help="抓取页数，默认为1")
    parser.add_argument("--q", type=str, default="", help="搜索关键词q，默认为空")
    parser.add_argument("--end_date", type=str, default="", help="结束日期，默认为空")
    args = parser.parse_args()
    results = asyncio.run(crawl_pages(page_count=args.page_count, q=args.q, end_date=args.end_date))
    print("抓取结果：")
    for idx, item in enumerate(results, 1):
        print(f"[{idx}] {json.dumps(item, ensure_ascii=False)}")
