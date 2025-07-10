import pytest
import asyncio
from llm_tools_v1.crawlers.biddingcsg import BiddingCsgCrawler

# 可用真实页面或 mock URL，推荐用官方公开页面
TEST_URL = "https://www.bidding.csg.cn/zbgg/1200395704.jhtml"

@pytest.mark.asyncio
async def test_async_read_bidding_page():
    """
    测试异步爬虫接口能抓取并解析页面结构
    """
    crawler = BiddingCsgCrawler()
    result = await crawler.async_read_bidding_page(TEST_URL)
    assert isinstance(result, dict)
    assert "title" in result and result["title"]
    assert "date" in result and result["date"]
    assert "content" in result and result["content"]
    print("抓取结果：", result) 