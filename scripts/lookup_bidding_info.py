import asyncio
import csv
import argparse
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from llm_tools_v1.services.bid_award_price_service import BidAwardPriceService, BidAwardPriceInfo

DATABASE_URL = "sqlite+aiosqlite:///data/db/llm_tools.db"

async def query_and_export(owner: str, output: str):
    engine = create_async_engine(DATABASE_URL, echo=False, future=True)
    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session_maker() as session:
        infos = await BidAwardPriceService.list_award_price_infos(session, owner=owner)
        if not infos:
            print(f"未找到招标单位为 '{owner}' 的中标信息。")
            return
        with open(output, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "招标编号", "项目名称", "标的名称", "标包名称", "价格类型",
                "价格数值", "投标下浮率", "招标价格", "最高限价", "招标单位", "中标公告URL", "招标公告URL"
            ])
            for info in infos:
                writer.writerow([
                    info.bidding_no, info.project, info.subject, info.package_name,
                    info.price_type, info.price_value, info.price_percent,
                    info.estimated_amount, info.max_bid_amount, info.owner, info.award_url, info.bidding_url
                ])
        print(f"已导出 {len(infos)} 条记录到 {output}")

def main():
    parser = argparse.ArgumentParser(description="按招标单位名称查询中标信息并导出CSV")
    parser.add_argument("--owner", required=True, help="招标单位名称")
    parser.add_argument("--output", default="data/output/award_info.csv", help="输出CSV文件名")
    args = parser.parse_args()
    asyncio.run(query_and_export(args.owner, args.output))

if __name__ == "__main__":
    main()
