import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

import argparse
from src.llm_tools_v1.core.config import set_current_llm
from src.llm_tools_v1.core.logging import setup_logging
from src.llm_tools_v1.ai.llm_parser import extract_bidding_price
from src.llm_tools_v1.crawlers.biddingcsg import BiddingCsgCrawler

def main():
    parser = argparse.ArgumentParser(description="大模型命令行对话工具")
    parser.add_argument("--model", type=str, default="doubao", help="指定大模型名称（如 doubao、deepseek）")
    parser.add_argument("--url", type=str, default="https://www.bidding.csg.cn/zbhxrgs/1200395227.jhtml", help="招标页面URL")
    parser.add_argument("--price_type", type=int, default=1, help="招标价格类型")
    args = parser.parse_args()

    set_current_llm(args.model)
    setup_logging(logging_level="INFO")

    crawler = BiddingCsgCrawler()
    html_content = crawler.read_bidding_page(args.url)
    print(extract_bidding_price(html_content, args.price_type))

if __name__ == "__main__":
    main() 