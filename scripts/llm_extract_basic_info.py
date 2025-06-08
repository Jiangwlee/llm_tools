import sys
import os
import argparse
import asyncio
import json
import logging
from typing import Any, Dict, Optional, List
from src.llm_tools_v1.core.config import set_current_llm
from src.llm_tools_v1.core.logging import setup_logging
from src.llm_tools_v1.ai.llm_parser import aextract_bidding_info
from src.llm_tools_v1.crawlers.biddingcsg import BiddingCsgCrawler
from src.llm_tools_v1.db.async_session import get_async_session
from src.llm_tools_v1.services.bidding_service import BiddingService, BiddingCreate
from src.llm_tools_v1.db.models import Bidding, BiddingPackage
from sqlmodel import select
from src.llm_tools_v1.utils.llm_mapping import map_llm_bidding_to_schema, map_llm_package_to_schema
from tenacity import retry, stop_after_attempt, wait_fixed

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

# ===================== 参数解析 =====================
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="大模型驱动的招标信息抽取与入库工具。支持单页测试、批量爬取、数据库查看等功能。"
    )
    parser.add_argument("--model", type=str, default="doubao", help="指定大模型名称（如 doubao、deepseek）。")
    parser.add_argument("--test", type=str, default=None, help="信息提取测试，传入招标详情页URL，仅抽取不入库。")
    parser.add_argument("--crawl", type=int, default=3, help="批量爬取招标列表，最大页数。默认3页。")
    parser.add_argument("--concurrency", type=int, default=5, help="并发处理标讯数量，防止资源耗尽。默认5。")
    parser.add_argument("--list", action="store_true", help="打印数据库中所有 bidding 记录并退出。")
    parser.add_argument("--list-packages", action="store_true", help="打印数据库中所有标包记录并退出。")
    return parser.parse_args()

# ===================== 环境初始化 =====================
def setup_env(args: argparse.Namespace) -> None:
    setup_logging(logging_level="INFO")
    set_current_llm(args.model)

# ===================== 数据库查询 =====================
async def list_all_biddings() -> None:
    async with get_async_session() as session:
        result = await session.execute(select(Bidding))
        biddings = result.scalars().all()
        logging.info("数据库全部 Bidding 记录：")
        for b in biddings:
            print(b.id, b.bidding_no, b.project, b.url)

async def list_all_packages() -> None:
    async with get_async_session() as session:
        result = await session.execute(select(BiddingPackage))
        packages = result.scalars().all()
        logging.info("数据库全部 BiddingPackage 记录：")
        for p in packages:
            print(p.bidding_id, p.package_name, p.estimated_amount)

# ===================== 业务主流程分层 =====================
class BiddingExtractor:
    def __init__(self, concurrency: int = 5) -> None:
        self.semaphore = asyncio.Semaphore(concurrency)

    async def fetch_bidding_list(self, max_page: int = 3) -> List[Dict[str, Any]]:
        crawler = BiddingCsgCrawler()
        return await crawler.asearch("广州供电局", max_page=max_page)

    async def fetch_html(self, url: str) -> str:
        crawler = BiddingCsgCrawler()
        return await crawler.async_read_bidding_page(url)

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    async def extract_bidding_info_from_html(self, html_content: str) -> Optional[str]:
        llm_result = await aextract_bidding_info(html_content)
        if llm_result.success:
            logging.info(f"大模型抽取结果：{llm_result.content}")
            return llm_result.content
        else:
            logging.error(f"大模型抽取失败：{llm_result.error}")
            return None

    def parse_llm_result(self, llm_result: Any) -> Optional[Dict[str, Any]]:
        try:
            if isinstance(llm_result, str):
                return json.loads(llm_result)
            else:
                return llm_result
        except Exception as e:
            logging.error(f"解析大模型结果失败: {e}")
            return None

    def map_bidding_data(self, bidding_data_raw: Dict[str, Any], url: str) -> Optional[BiddingCreate]:
        try:
            bidding_data = map_llm_bidding_to_schema(bidding_data_raw, url=url)
            bidding_create = BiddingCreate(**bidding_data)
            return bidding_create
        except Exception as e:
            logging.error(f"BiddingCreate 字段校验失败: {e}")
            return None

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    async def save_bidding_and_packages(self, bidding_create: BiddingCreate, bidding_data_raw: Dict[str, Any]) -> None:
        async with get_async_session() as session:
            try:
                bidding = await BiddingService.create_bidding(bidding_create, session)
                logging.info(f"保存成功，数据库记录：{bidding}")
                # 标包信息批量插入
                packages = bidding_data_raw.get("标包信息")
                if packages and isinstance(packages, list):
                    from src.llm_tools_v1.services.bidding_service import BiddingPackageService, BiddingPackageCreate
                    pkg_creates = [
                        BiddingPackageCreate(**{**map_llm_package_to_schema(pkg), "bidding_id": bidding.id})
                        for pkg in packages
                    ]
                    try:
                        pkg_objs = await BiddingPackageService.create_multi_packages(pkg_creates, session)
                        await session.commit()
                        for pkg_obj in pkg_objs:
                            logging.info(f"标包保存成功：{pkg_obj}")
                    except Exception as e:
                        logging.error(f"批量保存标包失败: {e}")
                        await session.rollback()
            except Exception as e:
                logging.error(f"保存到数据库失败: {e}")

    async def process_bidding(self, bidding: Dict[str, Any]) -> None:
        async with self.semaphore:
            try:
                logging.info(f"开始处理标讯：{bidding['url']}")
                html_content = await self.fetch_html(bidding["url"])
                llm_result = await self.extract_bidding_info_from_html(html_content)
                if not llm_result:
                    return
                bidding_data_raw = self.parse_llm_result(llm_result)
                if not bidding_data_raw:
                    return
                bidding_create = self.map_bidding_data(bidding_data_raw, url=bidding["url"])
                if not bidding_create:
                    return
                await self.save_bidding_and_packages(bidding_create, bidding_data_raw)
            except Exception as e:
                logging.error(f"处理标讯异常: {e}")

# ===================== 主入口 =====================
async def main() -> None:
    args = parse_args()
    setup_env(args)
    extractor = BiddingExtractor(concurrency=args.concurrency)

    if args.list:
        await list_all_biddings()
        return
    if args.list_packages:
        await list_all_packages()
        return
    if args.test:
        logging.info(f"信息提取测试：{args.test}")
        html_content = await extractor.fetch_html(args.test)
        llm_result = await extractor.extract_bidding_info_from_html(html_content)
        print(llm_result)
        if not llm_result:
            return
        bidding_data_raw = extractor.parse_llm_result(llm_result)
        print(bidding_data_raw)
        return
    if args.crawl:
        bidding_list = await extractor.fetch_bidding_list(max_page=args.crawl)
        logging.info(f"共找到 {len(bidding_list)} 条标讯")
        await asyncio.gather(*[extractor.process_bidding(bidding) for bidding in bidding_list])

if __name__ == "__main__":
    asyncio.run(main())