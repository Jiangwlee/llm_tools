from src.llm_tools_v1.ai.llm_parser import aextract_bidding_judge
from .bidding_info_extractor import BiddingInfoExtractor
import os
import asyncio
import argparse
from datetime import datetime, timedelta
from llm_tools_v1.db.async_session import get_async_session
from llm_tools_v1.core.logging import get_logger
from llm_tools_v1.core.config import LlmToolsDirs
logger = get_logger()


def today_date():
    return datetime.now().strftime("%Y-%m-%d")

def yesterday_date():
    return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

async def extract_bidding_info(end_date: str):
    extractor = BiddingInfoExtractor(concurrency=5)
    bidding_list = await extractor.fetch_list(keyword="", max_page=65535, end_date=end_date)
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
    logger.info(f"已处理 {len(extractor.processed_urls)} 条公告")

async def summarize_bidding_info(date: str):
    from llm_tools_v1.services.bidding_service import BiddingService, BiddingPackageService
    async with get_async_session() as session:
        bidding_list = await BiddingService.get_bidding_by_date(date, session)
        tasks = []
        for index, bidding in enumerate(bidding_list):
            async def build_and_judge(bidding=bidding):
                markdown_content = ""
                markdown_content += f"# {index+1}.{bidding.project}\n\n"
                markdown_content += f"招标编号：{bidding.bidding_no}\n"
                markdown_content += f"招标公告：{bidding.url}\n"
                markdown_content += f"招标人：{bidding.owner}\n"
                markdown_content += f"招标代理机构：{bidding.agent}\n"
                markdown_content += f"招标项目：{bidding.project}\n"
                markdown_content += f"招标文件获取开始时间：{bidding.doc_start_time}\n"
                markdown_content += f"招标文件获取结束时间：{bidding.doc_end_time}\n"
                markdown_content += f"投标文件递交截止时间：{bidding.submit_deadline}\n"
                markdown_content += f"开标时间：{bidding.open_time}\n"
                markdown_content += f"开标地点：{bidding.open_location}\n"
                markdown_content += "\n"
                package_list = await BiddingPackageService.get_bidding_package_by_bidding_id(bidding.id, session)
                for package in package_list:
                    markdown_content += f"## {package.subject}\n"
                    markdown_content += f"标包名称：{package.package_name}\n"
                    markdown_content += f"标包概述：{package.subject_desc}\n"
                    markdown_content += f"预计采购金额：{package.estimated_amount} 万元\n"
                    markdown_content += f"最高投标限价：{package.max_bid_amount} 万元\n"
                    markdown_content += "\n"
                markdown_content += "\n"
                result = await aextract_bidding_judge(markdown_content)
                return {"bidding": bidding, "result": result}
            tasks.append(build_and_judge())
        results = await asyncio.gather(*tasks)
        with open(os.path.join(LlmToolsDirs.get_cache_dir(), f"bidding_info_{date}.md"), "w", encoding="utf-8") as f:
            for item in results:
                if item["result"].success:
                    f.write(item["result"].content)
                    f.write("\n\n---\n\n")


# ========== 参数解析 ==========
def parse_args():
    parser = argparse.ArgumentParser(description="每日定期任务")
    parser.add_argument("--task", type=str, default="summarize_bidding_info", help="任务名称")
    parser.add_argument("--date", type=str, default=None, help="日期")
    return parser.parse_args()

if __name__ == "__main__":
    # async def main():
    #     crawler = BiddingCsgCrawler()
    #     html_content = await crawler.async_read_bidding_page("https://www.bidding.csg.cn/zbhxrgs/1200395227.jhtml")
    #     result = await aextract_bidding_price(html_content)
    #     if result.success:
    #         print(result.content)
    #     else:
    #         print(f"调用失败: {result.error}")

    
    args = parse_args()
    if args.task == "extract_bidding_info":
        print("开始提取招标信息")
        asyncio.run(extract_bidding_info(args.date or yesterday_date()))
    elif args.task == "summarize_bidding_info":
        print("开始总结招标信息")
        asyncio.run(summarize_bidding_info(args.date or today_date()))
    else:
        print(f"任务名称错误: {args.task}")