from typing import Any, Dict, Optional
from llm_tools_v1.core.llm_service import LLMResult, chat, achat
from llm_tools_v1.core.config import get_settings
from llm_tools_v1.core.llm import LLMClient
from llm_tools_v1.ai.prompt_templates import SYS_BIDDING_INFO_PROMPT, SYS_BIDDING_PRICE_PROMPT
from llm_tools_v1.crawlers.biddingcsg import BiddingCsgCrawler
import asyncio

def build_bidding_info_prompt(html_content: str) -> str:
    """
    构建招标基本信息的 prompt。
    Args:
        html_content (str): 网页 HTML 内容
    Returns:
        str: 构建好的 prompt
    """
    return SYS_BIDDING_INFO_PROMPT.format(html_content=html_content)

def build_bidding_price_prompt(html_content: str, price_type: int = 1) -> str:
    """
    构建招标价格信息的 prompt。
    Args:
        html_content (str): 网页 HTML 内容
        price_type (int): 价格类型
    Returns:
        str: 构建好的 prompt
    """
    return SYS_BIDDING_PRICE_PROMPT.format(html_content=html_content)
    # if price_type == 1:
    #     return SYS_BIDDING_PRICE_TYPE_ONE_PROMPT.format(html_content=html_content)
    # else:
    #     return SYS_BIDDING_PRICE_TYPE_TWO_PROMPT.format(html_content=html_content)

def extract_bidding_info(html_content: str, llm_client: Optional[LLMClient] = None) -> LLMResult:
    """
    调用大模型总结 Bidding CSG 网页内容，提取招标基本信息。
    Args:
        html_content (str): 网页 HTML 内容
        llm_client (Optional[LLMClient]): 可注入的 LLMClient 实例
    Returns:
        LLMResult: 结构化返回内容、状态和错误信息
    """
    prompt = build_bidding_info_prompt(html_content)
    return chat(prompt, llm_client)

async def aextract_bidding_info(html_content: str, llm_client: Optional[LLMClient] = None) -> LLMResult:
    """
    调用大模型总结 Bidding CSG 网页内容，提取招标基本信息。
    Args:
        html_content (str): 网页 HTML 内容
        llm_client (Optional[LLMClient]): 可注入的 LLMClient 实例
    Returns:
        LLMResult: 结构化返回内容、状态和错误信息
    """
    prompt = build_bidding_info_prompt(html_content)
    return await achat(prompt, llm_client)

def extract_bidding_price(html_content: str, price_type: int = 1, llm_client: Optional[LLMClient] = None) -> LLMResult:
    """
    调用大模型总结 Bidding CSG 网页内容，提取招标价格信息。
    Args:
        html_content (str): 网页 HTML 内容
        price_type (int): 价格类型，1 或 2
        llm_client (Optional[LLMClient]): 可注入的 LLMClient 实例
    Returns:
        LLMResult: 结构化返回内容、状态和错误信息
    """
    prompt = build_bidding_price_prompt(html_content, price_type)
    return chat(prompt, llm_client)

async def aextract_bidding_price(html_content: str, price_type: int = 1, llm_client: Optional[LLMClient] = None) -> LLMResult:
    """
    调用大模型总结 Bidding CSG 网页内容，提取招标价格信息。
    Args:
        html_content (str): 网页 HTML 内容
        price_type (int): 价格类型，1 或 2
        llm_client (Optional[LLMClient]): 可注入的 LLMClient 实例
    Returns:
        LLMResult: 结构化返回内容、状态和错误信息
    """
    prompt = build_bidding_price_prompt(html_content, price_type)
    return await achat(prompt, llm_client)

if __name__ == "__main__":
    async def main():
        crawler = BiddingCsgCrawler()
        html_content = await crawler.async_read_bidding_page("https://www.bidding.csg.cn/zbhxrgs/1200395227.jhtml")
        result = await aextract_bidding_price(html_content)
        if result.success:
            print(result.content)
        else:
            print(f"调用失败: {result.error}")

    asyncio.run(main())