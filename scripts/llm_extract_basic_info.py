import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

import argparse
import asyncio
import json
from src.llm_tools_v1.core.config import set_current_llm
from src.llm_tools_v1.core.logging import setup_logging
from src.llm_tools_v1.ai.llm_parser import aextract_bidding_info
from src.llm_tools_v1.crawlers.biddingcsg import BiddingCsgCrawler
from src.llm_tools_v1.db.async_session import get_async_session
from src.llm_tools_v1.services.bidding_service import BiddingService, BiddingCreate
from src.llm_tools_v1.db.models import Bidding, BiddingPackage
from sqlmodel import select
from src.llm_tools_v1.utils.llm_mapping import map_llm_bidding_to_schema, map_llm_package_to_schema

async def list_all_biddings():
    async with get_async_session() as session:
        result = await session.execute(select(Bidding))
        biddings = result.scalars().all()
        print("数据库全部 Bidding 记录：")
        for b in biddings:
            print(b.id, b.bidding_no, b.project, b.url)

async def list_all_packages():
    async with get_async_session() as session:
        result = await session.execute(select(BiddingPackage))
        packages = result.scalars().all()
        print("数据库全部 BiddingPackage 记录：")
        for p in packages:
            print(p.bidding_id, p.package_name, p.estimated_amount)

def parse_args():
    parser = argparse.ArgumentParser(description="大模型命令行对话工具")
    parser.add_argument("--model", type=str, default="doubao", help="指定大模型名称（如 doubao、deepseek）")
    parser.add_argument("--test", type=str, default=None, help="信息提取测试")
    parser.add_argument("--crawl", type=int, default=3, help="爬取招标列表. 默认最多提取3页")
    parser.add_argument("--list", action="store_true", help="打印数据库中所有 bidding 记录并退出")
    parser.add_argument("--list-packages", action="store_true", help="打印数据库中所有标包记录并退出")
    return parser.parse_args()

def setup_env(args):
    setup_logging(logging_level="INFO")
    set_current_llm(args.model)

async def fetch_bidding_list(max_page: int = 3):
    crawler = BiddingCsgCrawler()
    return await crawler.asearch("广州供电局", max_page=max_page)

async def fetch_html(url: str) -> str:
    crawler = BiddingCsgCrawler()
    return await crawler.async_read_bidding_page(url)

async def extract_bidding_info_from_html(html_content: str):
    llm_result = await aextract_bidding_info(html_content)
    if llm_result.success:
        print("大模型抽取结果：", llm_result.content)
        return llm_result.content
    else:
        print("大模型抽取失败：", llm_result.error)
        return None

def parse_llm_result(llm_result):
    try:
        if isinstance(llm_result, str):
            return json.loads(llm_result)
        else:
            return llm_result
    except Exception as e:
        print(f"解析大模型结果失败: {e}")
        return None

def map_bidding_data(bidding_data_raw, url):
    try:
        bidding_data = map_llm_bidding_to_schema(bidding_data_raw, url=url)
        bidding_create = BiddingCreate(**bidding_data)
        return bidding_create
    except Exception as e:
        print(f"BiddingCreate 字段校验失败: {e}")
        return None

async def save_bidding_and_packages(bidding_create, bidding_data_raw):
    async with get_async_session() as session:
        try:
            bidding = await BiddingService.create_bidding(bidding_create, session)
            print("保存成功，数据库记录：", bidding)
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
                        print("标包保存成功：", pkg_obj)
                except Exception as e:
                    print(f"批量保存标包失败: {e}")
                    await session.rollback()
        except Exception as e:
            print(f"保存到数据库失败: {e}")

async def main():
    args = parse_args()
    setup_env(args)

    if args.list:
        await list_all_biddings()
        return
    if args.list_packages:
        await list_all_packages()
        return
    if args.test:
        print(f"信息提取测试：{args.test}")
        html_content = await fetch_html(args.test)
        llm_result = await extract_bidding_info_from_html(html_content)
        print(llm_result)
        if not llm_result:
            return
        bidding_data_raw = parse_llm_result(llm_result)
        print(bidding_data_raw)
        return

    if args.crawl:
        bidding_list = await fetch_bidding_list(max_page=args.crawl)
        print(f"共找到 {len(bidding_list)} 条标讯")
        async def process_bidding(bidding):
            print(f"开始处理标讯：{bidding['url']}")
            html_content = await fetch_html(bidding["url"])
            llm_result = await extract_bidding_info_from_html(html_content)
            if not llm_result:
                return
            bidding_data_raw = parse_llm_result(llm_result)
            if not bidding_data_raw:
                return
            bidding_create = map_bidding_data(bidding_data_raw, url=bidding["url"])
            if not bidding_create:
                return
            await save_bidding_and_packages(bidding_create, bidding_data_raw)
        
        # 使用 asyncio.gather 并行处理所有标讯
        await asyncio.gather(*[process_bidding(bidding) for bidding in bidding_list])

if __name__ == "__main__":
    asyncio.run(main())