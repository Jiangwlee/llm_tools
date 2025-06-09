import argparse
import asyncio
import json
import os
from typing import List, Dict, Any, Set, Optional
from llm_tools_v1.crawlers.biddingcsg import BiddingCsgCrawler, BiddingListItem, BiddingType, BiddingPageDetail
from llm_tools_v1.ai.llm_parser import aextract_bidding_info, aextract_bidding_price
from llm_tools_v1.db.async_session import get_async_session
from llm_tools_v1.utils.llm_mapping import map_llm_bidding_to_schema, map_llm_package_to_schema
from llm_tools_v1.services.bidding_service import BiddingService, BiddingPackageService, BiddingCreate, BiddingPackageCreate
from llm_tools_v1.core.logging import get_logger
# from src.llm_tools_v1.services.bidding_service import BiddingService, BiddingCreate
# from src.llm_tools_v1.services.bid_award_price_service import BidAwardPriceService, BidAwardPriceCreate

logger = get_logger()

FAILED_URLS_FILE = "data/cache/failed_urls.json"
PROCESSED_URLS_FILE = "data/cache/processed_urls.json"

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

def type_to_bidding_type(type: str) -> BiddingType:
    if type == "bidding":
        return BiddingType.BIDDING
    elif type == "award":
        return BiddingType.AWARD
    elif type == "all":
        return BiddingType.ALL
    else:
        raise ValueError(f"无效的公告类型: {type}")
    
def parse_llm_result(llm_result: Any) -> Optional[Dict[str, Any]]:
    """
    解析大模型结果
    Args:
        llm_result (Any): 大模型结果

    Returns:
        Optional[Dict[str, Any]]: 解析后的结果
    """
    try:
        if isinstance(llm_result, str):
            return json.loads(llm_result)
        else:
            return llm_result
    except Exception as e:
        logger.error(f"解析大模型结果失败: {e}")
        return None
    
def map_bidding_data(bidding_data_raw: Dict[str, Any], url: str) -> Optional[BiddingCreate]:
    try:
        bidding_data = map_llm_bidding_to_schema(bidding_data_raw, url=url)
        bidding_create = BiddingCreate(**bidding_data)
        return bidding_create
    except Exception as e:
        logger.error(f"BiddingCreate 字段校验失败: {e}")
        return None

def map_bidding_package_data(bidding_package_data_raw: Dict[str, Any]) -> Optional[BiddingPackageCreate]:
    try:
        bidding_package_data = map_llm_package_to_schema(bidding_package_data_raw)
        bidding_package_create = BiddingPackageCreate(**bidding_package_data)
        return bidding_package_create
    except Exception as e:
        logger.error(f"BiddingPackageCreate 字段校验失败: {e}")
        return None
    
async def save_bidding_and_packages(bidding_data_raw: Dict[str, Any], url: str) -> None:
    async with get_async_session() as session:
        try:
            # 保存招标公告
            bidding_create = map_bidding_data(bidding_data_raw, url=url)
            bidding = await BiddingService.create_bidding(bidding_create, session)
            logger.info(f"【招标公告】保存成功，数据库记录：{bidding}")
            # 保存标包信息
            packages = bidding_data_raw.get("标包信息")
            if packages and isinstance(packages, list):
                pkg_creates = []
                for pkg in packages:
                    pkg_create = map_bidding_package_data(pkg)
                    if not pkg_create:
                        continue
                    pkg_creates.append(pkg_create)
                try:
                    pkg_objs = await BiddingPackageService.create_multi_packages(pkg_creates, session)
                    await session.commit()
                    for pkg_obj in pkg_objs:
                        logger.info(f"【标包】保存成功：{pkg_obj}")
                except Exception as e:
                    logger.error(f"【标包】批量保存失败: {e}")
                    await session.rollback()
        except Exception as e:
            logger.error(f"【招标公告】保存到数据库失败: {e}")

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

    async def fetch_list(self, keyword: str, max_page: int) -> List[BiddingListItem]:
        crawler = BiddingCsgCrawler()
        return await crawler.asearch(keyword, max_page=max_page)

    async def fetch_html(self, url: str) -> BiddingPageDetail:
        crawler = BiddingCsgCrawler()
        return await crawler.async_read_bidding_page(url)

    async def process_bidding(self, bidding: BiddingListItem, session):
        print(f"开始处理: {bidding}")
        url = bidding.url
        async with self.semaphore:
            if url in self.processed_urls:
                print(f"已处理，跳过: {url}")
                return
            try:
                bidding_detail = await self.fetch_html(url)
                logger.debug(f"html_content: {bidding_detail}")
                type = bidding_detail.type
                html_content = bidding_detail.content
                # TODO: 根据公告类型选择不同的提取和入库逻辑
                if type == BiddingType.BIDDING:
                    llm_result = await aextract_bidding_info(html_content)
                    print("--------------------------------")
                    if llm_result.success:
                        print("成功解析招标公告：")
                        content = llm_result.content
                        print(f"content: {content}")
                        bidding_data_raw = parse_llm_result(content)
                        print(f"bidding_data: {bidding_data_raw}")
                        # TODO: 解析和入库 Bidding 信息
                        if not bidding_data_raw:
                            return
                        await save_bidding_and_packages(bidding_data_raw, url=url)
                    else:
                        print(f"解析失败: {llm_result.error}")
                if type == BiddingType.AWARD:
                    llm_result = await aextract_bidding_price(html_content)
                    print("--------------------------------")
                    if llm_result.success:
                        print("成功解析中标公示：")
                        content = llm_result.content
                        print(f"content: {content}")
                        bidding_data_raw = parse_llm_result(content)
                        print(f"bidding_data: {bidding_data_raw}")
                    else:
                        print(f"解析失败: {llm_result.error}")

                    # TODO: 解析和入库 BidAwardPrice 信息
                else:
                    print(f"其他类型公告，不处理, url: {url}")
                # 处理成功，记录到 processed_urls
                self.processed_urls.add(url)
                save_json_set(PROCESSED_URLS_FILE, self.processed_urls)
                print(f"处理成功: {url}")
            except Exception as e:
                # 记录失败的 url 和错误信息
                self.failed_urls[url] = str(e)
                save_json_dict(FAILED_URLS_FILE, self.failed_urls)
                logger.error(f"处理失败: {url}, 错误: {e}")

# ========== 主入口 ==========
async def main():
    args = parse_args()
    extractor = BiddingInfoExtractor(concurrency=args.concurrency)

    if args.test_url:
        html_content = await extractor.fetch_html(args.test_url)
        # TODO: 根据 URL 类型自动选择提取方式并打印结果
        print(html_content[:500])  # 仅打印前500字符做示例
        return

    print(args.keyword)
    print(args.max_page)
    print(args.type)
    bidding_list = await extractor.fetch_list(args.keyword, args.max_page)
    print(f"共获取到 {len(bidding_list)} 条公告")
    print(f"已处理的url: {extractor.processed_urls}")
    # 跳过已处理的 url
    to_process = [b for b in bidding_list if b.url not in extractor.processed_urls]
    print(f"共需要处理 {len(to_process)} 条公告")
    print(to_process)
    async with get_async_session() as session:
        await asyncio.gather(*[
            extractor.process_bidding(bidding, session)
            for bidding in to_process
        ])
    print("全部处理完成！")


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
        for i, bidding in enumerate(bidding_list, 1):
            print(f"\n第 {i} 条公告:")
            print(f"{bidding}")
            
        return bidding_list
        
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        raise

if __name__ == "__main__":
    # 运行测试
    # asyncio.run(test_fetch_list())
    asyncio.run(main())
