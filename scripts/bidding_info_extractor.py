import argparse
import asyncio
import json
import os
from typing import List, Dict, Any, Set, Optional
from llm_tools_v1.crawlers.biddingcsg import BiddingCsgCrawler, BiddingListItem, BiddingType, BiddingPageDetail
from llm_tools_v1.ai.llm_parser import aextract_bidding_info, aextract_bidding_price
from llm_tools_v1.db.async_session import get_async_session
from llm_tools_v1.utils.llm_mapping import map_llm_bidding_to_schema, map_llm_package_to_schema, map_llm_bid_award_price_to_schema
from llm_tools_v1.services.bidding_service import BiddingService, BiddingPackageService, BiddingCreate, BiddingPackageCreate
from llm_tools_v1.services.bid_award_price_service import BidAwardPriceService, BidAwardPriceCreate
from llm_tools_v1.core.logging import get_logger, setup_logging

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

def map_bidding_package_data(bidding_package_data_raw: Dict[str, Any], bidding_id: int) -> Optional[BiddingPackageCreate]:
    try:
        bidding_package_data = map_llm_package_to_schema(bidding_package_data_raw, bidding_id=bidding_id)
        bidding_package_create = BiddingPackageCreate(**bidding_package_data)
        return bidding_package_create
    except Exception as e:
        logger.error(f"BiddingPackageCreate 字段校验失败: {e}")
        return None
    
def map_bid_award_price_data(bid_award_price_data_raw: Dict[str, Any], url: str, bid_no: str) -> Optional[BidAwardPriceCreate]:
    try:
        bid_award_price_data = map_llm_bid_award_price_to_schema(bid_award_price_data_raw, url=url, bid_no=bid_no)
        bid_award_price_create = BidAwardPriceCreate(**bid_award_price_data)
        return bid_award_price_create
    except Exception as e:
        logger.error(f"BidAwardPriceCreate 字段校验失败: {e}")
    
async def save_bidding_and_packages(bidding_data_raw: Dict[str, Any], url: str) -> None:
    async with get_async_session() as session:
        try:
            # 保存招标公告
            bidding_create = map_bidding_data(bidding_data_raw, url=url)
            bidding_info = await BiddingService.create_bidding(bidding_create, session)
            logger.info(f"【招标公告】保存成功，url：{url}, bidding_id：{bidding_info.id}")
            # 保存标包信息
            packages = bidding_data_raw.get("标包信息")
            if packages and isinstance(packages, list):
                pkg_creates = []
                for pkg in packages:
                    pkg_create = map_bidding_package_data(pkg, bidding_id=bidding_info.id)
                    if not pkg_create:
                        continue
                    pkg_creates.append(pkg_create)
                try:
                    await BiddingPackageService.create_multi_packages(pkg_creates, session)
                    await session.commit()
                    logger.info(f"【标包】保存成功，url：{url}")
                except Exception as e:
                    logger.error(f"【标包】批量保存失败: {e}")
                    await session.rollback()
        except Exception as e:
            logger.error(f"【招标公告】保存到数据库失败: {e}")

async def save_bid_award_price(bid_award_price_data_raw: Dict[str, Any], url: str) -> None:
    async with get_async_session() as session:
        try:
            bid_no = bid_award_price_data_raw.get("招标编号")
            if not bid_no:
                logger.error(f"【中标价格】招标编号为空，不保存: {bid_award_price_data_raw}")
                return
            
            price_list = bid_award_price_data_raw.get("评标情况")
            if not price_list:
                logger.error(f"【中标价格】评标情况为空，不保存: {bid_award_price_data_raw}")
                return
            
            bid_award_price_creates = []
            for price in price_list:
                bid_award_price_create = map_bid_award_price_data(price, url=url, bid_no=bid_no)
                if not bid_award_price_create:
                    continue
                bid_award_price_creates.append(bid_award_price_create)
            try:
                await BidAwardPriceService.create_multi_prices(bid_award_price_creates, session)
                await session.commit()
                logger.info(f"【中标价格】保存成功，url：{url}")
            except Exception as e:
                logger.error(f"【中标价格】批量保存失败: {e}")
                await session.rollback()
        except Exception as e:
            logger.error(f"【中标价格】保存到数据库失败: {e}")

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
                if type == BiddingType.BIDDING:
                    llm_result = await aextract_bidding_info(html_content)
                    logger.debug("--------------------------------")
                    if llm_result.success:
                        logger.info("成功解析招标公告：")
                        content = llm_result.content
                        logger.debug(f"content: {content}")
                        bidding_data_raw = parse_llm_result(content)
                        logger.debug(f"bidding_data: {bidding_data_raw}")
                        if not bidding_data_raw:
                            return
                        await save_bidding_and_packages(bidding_data_raw, url=url)
                    else:
                        logger.error(f"解析失败: {llm_result.error}")
                if type == BiddingType.AWARD:
                    llm_result = await aextract_bidding_price(html_content)
                    logger.debug("--------------------------------")
                    if llm_result.success:
                        logger.info("成功解析中标公示：")
                        content = llm_result.content
                        logger.debug(f"content: {content}")
                        bidding_data_raw = parse_llm_result(content)
                        # bidding_data_raw example: [{'标的': '标的1.广州供电局2025年基于柔性直流技术的配网台区低电压治理技术服务框架', '标包': '标包1.广州供电局2025年基于柔性直流技术的配网台区低电压治理技术服务框架', '候选人': '广州电能电力工程有限公司', '价格类型': '百分比', '中标价格': 12}]
                        logger.debug(f"bidding_data: {bidding_data_raw}")
                        if not bidding_data_raw:
                            return
                        await save_bid_award_price(bidding_data_raw, url=url)
                    else:
                        logger.error(f"解析失败: {llm_result.error}")
                else:
                    logger.info(f"其他类型公告，不处理, url: {url}")
                # 处理成功，记录到 processed_urls
                self.processed_urls.add(url)
                save_json_set(PROCESSED_URLS_FILE, self.processed_urls)
                logger.info(f"处理成功: {url}")
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
        logger.debug(html_content[:500])  # 仅打印前500字符做示例
        return

    logger.debug(args.keyword)
    logger.debug(args.max_page)
    logger.debug(args.type)
    bidding_list = await extractor.fetch_list(args.keyword, args.max_page)
    logger.info(f"共获取到 {len(bidding_list)} 条公告")
    logger.info(f"已处理的url: {extractor.processed_urls}")
    # 跳过已处理的 url
    to_process = [b for b in bidding_list if b.url not in extractor.processed_urls]
    logger.info(f"共需要处理 {len(to_process)} 条公告")
    logger.debug(to_process)
    async with get_async_session() as session:
        await asyncio.gather(*[
            extractor.process_bidding(bidding, session)
            for bidding in to_process
        ])
    logger.info("全部处理完成！")


async def test_fetch_list():
    """测试 fetch_list 功能"""
    extractor = BiddingInfoExtractor(concurrency=5)
    try:
        # 测试搜索关键词
        keyword = "广州供电局"
        max_page = 2
        
        logger.info(f"开始测试 fetch_list，关键词: {keyword}, 最大页数: {max_page}")
        bidding_list = await extractor.fetch_list(keyword, max_page)
        
        # 打印结果统计
        logger.info(f"获取到 {len(bidding_list)} 条公告")
        
        # 打印前3条记录详情
        for i, bidding in enumerate(bidding_list, 1):
            logger.info(f"\n第 {i} 条公告:")
            logger.info(f"{bidding}")
            
        return bidding_list
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
        raise

if __name__ == "__main__":
    # 运行测试
    # asyncio.run(test_fetch_list())
    setup_logging(logging_level="INFO")
    asyncio.run(main())
