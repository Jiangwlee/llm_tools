import argparse
import asyncio
import logging
import json
import os
from typing import List, Dict, Any, Set
from src.llm_tools_v1.crawlers.biddingcsg import BiddingCsgCrawler
from src.llm_tools_v1.ai.llm_parser import aextract_bidding_info, aextract_bidding_price
from src.llm_tools_v1.db.async_session import get_async_session
# from src.llm_tools_v1.services.bidding_service import BiddingService, BiddingCreate
# from src.llm_tools_v1.services.bid_award_price_service import BidAwardPriceService, BidAwardPriceCreate

FAILED_URLS_FILE = "failed_urls.json"
PROCESSED_URLS_FILE = "processed_urls.json"

# ========== 工具函数 ==========
def load_json_set(filename: str) -> Set[str]:
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_json_set(filename: str, s: Set[str]) -> None:
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(list(s), f, ensure_ascii=False, indent=2)

def load_json_dict(filename: str) -> Dict[str, Any]:
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json_dict(filename: str, d: Dict[str, Any]) -> None:
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

# ========== 参数解析 ==========
def parse_args():
    parser = argparse.ArgumentParser(description="自动爬取并入库招标/中标公告信息，支持断点续跑和失败记录")
    parser.add_argument("--keyword", type=str, default="广州供电局", help="检索关键词")
    parser.add_argument("--max_page", type=int, default=3, help="最大爬取页数")
    parser.add_argument("--test_url", type=str, default=None, help="测试模式，指定单个公告URL")
    parser.add_argument("--concurrency", type=int, default=5, help="并发处理数")
    parser.add_argument("--type", type=str, default="all", choices=["all", "bidding", "award"], help="公告类型")
    return parser.parse_args()

# ========== 主体类 ==========
class BiddingInfoExtractor:
    def __init__(self, concurrency: int = 5):
        self.semaphore = asyncio.Semaphore(concurrency)
        self.processed_urls: Set[str] = load_json_set(PROCESSED_URLS_FILE)
        self.failed_urls: Dict[str, Any] = load_json_dict(FAILED_URLS_FILE)

    async def fetch_list(self, keyword: str, max_page: int) -> List[Dict[str, Any]]:
        crawler = BiddingCsgCrawler()
        return await crawler.asearch(keyword, max_page=max_page)

    async def fetch_html(self, url: str) -> str:
        crawler = BiddingCsgCrawler()
        return await crawler.async_read_bidding_page(url)

    async def process_bidding(self, bidding: Dict[str, Any], session, info_type: str):
        url = bidding["url"]
        async with self.semaphore:
            if url in self.processed_urls:
                logging.info(f"已处理，跳过: {url}")
                return
            try:
                html_content = await self.fetch_html(url)
                # TODO: 根据公告类型选择不同的提取和入库逻辑
                if info_type in ("all", "bidding") and "招标公告" in bidding.get("title", ""):
                    llm_result = await aextract_bidding_info(html_content)
                    # TODO: 解析和入库 Bidding 信息
                if info_type in ("all", "award") and "中标公告" in bidding.get("title", ""):
                    llm_result = await aextract_bidding_price(html_content)
                    # TODO: 解析和入库 BidAwardPrice 信息
                # 处理成功，记录到 processed_urls
                self.processed_urls.add(url)
                save_json_set(PROCESSED_URLS_FILE, self.processed_urls)
                logging.info(f"处理成功: {url}")
            except Exception as e:
                # 记录失败的 url 和错误信息
                self.failed_urls[url] = str(e)
                save_json_dict(FAILED_URLS_FILE, self.failed_urls)
                logging.error(f"处理失败: {url}, 错误: {e}")

# ========== 主入口 ==========
async def main():
    args = parse_args()
    logging.basicConfig(level=logging.INFO)
    extractor = BiddingInfoExtractor(concurrency=args.concurrency)

    if args.test_url:
        html_content = await extractor.fetch_html(args.test_url)
        # TODO: 根据 URL 类型自动选择提取方式并打印结果
        print(html_content[:500])  # 仅打印前500字符做示例
        return

    bidding_list = await extractor.fetch_list(args.keyword, args.max_page)
    logging.info(f"共获取到 {len(bidding_list)} 条公告")
    # 跳过已处理的 url
    to_process = [b for b in bidding_list if b["url"] not in extractor.processed_urls]
    async with get_async_session() as session:
        await asyncio.gather(*[
            extractor.process_bidding(bidding, session, args.type)
            for bidding in to_process
        ])
    logging.info("全部处理完成！")


async def test_fetch_list():
    """测试 fetch_list 功能"""
    extractor = BiddingInfoExtractor(concurrency=5)
    try:
        # 测试搜索关键词
        keyword = "广州供电局"
        max_page = 2
        
        print(f"开始测试 fetch_list，关键词: {keyword}, 最大页数: {max_page}")
        bidding_list = await extractor.fetch_list(keyword, max_page)
        
        # 打印结果统计
        print(f"获取到 {len(bidding_list)} 条公告")
        
        # 打印前3条记录详情
        for i, bidding in enumerate(bidding_list[:3], 1):
            print(f"\n第 {i} 条公告:")
            print(f"{bidding}")
            
        return bidding_list
        
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        raise

if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_fetch_list())
