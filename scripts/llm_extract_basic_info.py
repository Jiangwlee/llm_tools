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
            print(b.bidding_no, b.project)

async def list_all_packages():
    async with get_async_session() as session:
        result = await session.execute(select(BiddingPackage))
        packages = result.scalars().all()
        print("数据库全部 BiddingPackage 记录：")
        for p in packages:
            print(p.package_name, p.estimated_amount)

async def main():
    parser = argparse.ArgumentParser(description="大模型命令行对话工具")
    parser.add_argument("--model", type=str, default="doubao", help="指定大模型名称（如 doubao、deepseek）")
    parser.add_argument("--url", type=str, default="https://www.bidding.csg.cn/zbgg/1200395704.jhtml", help="招标页面URL")
    parser.add_argument("--list", action="store_true", help="打印数据库中所有 bidding 记录并退出")
    parser.add_argument("--list-packages", action="store_true", help="打印数据库中所有标包记录并退出")
    args = parser.parse_args()

    setup_logging(logging_level="INFO")
    set_current_llm(args.model)

    if args.list:
        await list_all_biddings()
        return
    if args.list_packages:
        await list_all_packages()
        return

    crawler = BiddingCsgCrawler()
    html_content = await crawler.async_read_bidding_page(args.url)
    # print(html_content)
    llm_result = await aextract_bidding_info(html_content)
    if llm_result.success:
        llm_result = llm_result.content
        print("大模型抽取结果：", llm_result)
    else:
        print("大模型抽取失败：", llm_result.error)
        return

    # 假设 llm_result 是 JSON 字符串或结构化文本，需解析为 dict
    try:
        if isinstance(llm_result, str):
            bidding_data_raw = json.loads(llm_result)
        else:
            bidding_data_raw = llm_result
    except Exception as e:
        print(f"解析大模型结果失败: {e}")
        return

    # 字段映射，确保符合 BiddingCreate schema
    try:
        bidding_data = map_llm_bidding_to_schema(bidding_data_raw, url=args.url)
        bidding_create = BiddingCreate(**bidding_data)
    except Exception as e:
        print(f"BiddingCreate 字段校验失败: {e}")
        return

    # 保存到数据库，并处理标包信息
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

if __name__ == "__main__":
    asyncio.run(main())