import asyncio
from typing import Optional

from llm_tools_v1.ai.prompt_templates import (
    SYS_BIDDING_INFO_PROMPT,
    SYS_BIDDING_JUDGE_PROMPT,
    SYS_BIDDING_PRICE_PROMPT,
)
from llm_tools_v1.core.llm import LLMClient
from llm_tools_v1.core.llm_service import LLMResult, achat, chat


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

def build_bidding_judge_prompt(markdown_content: str) -> str:
    """
    构建招标判断的 prompt。
    Args:
        markdown_content (str): 网页 Markdown 内容
    Returns:
        str: 构建好的 prompt
    """
    return SYS_BIDDING_JUDGE_PROMPT.format(markdown_content=markdown_content)

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

async def aextract_bidding_judge(markdown_content: str, llm_client: Optional[LLMClient] = None) -> LLMResult:
    """
    调用大模型判断招标是否适合。
    Args:
        markdown_content (str): 网页 Markdown 内容
        llm_client (Optional[LLMClient]): 可注入的 LLMClient 实例
    Returns:    
        LLMResult: 结构化返回内容、状态和错误信息
    """
    prompt = build_bidding_judge_prompt(markdown_content)
    return await achat(prompt, llm_client)

if __name__ == "__main__":
    # async def main():
    #     crawler = BiddingCsgCrawler()
    #     html_content = await crawler.async_read_bidding_page("https://www.bidding.csg.cn/zbhxrgs/1200395227.jhtml")
    #     result = await aextract_bidding_price(html_content)
    #     if result.success:
    #         print(result.content)
    #     else:
    #         print(f"调用失败: {result.error}")

    
    async def main():
        from llm_tools_v1.db.async_session import get_async_session
        from llm_tools_v1.services.bidding_service import (
            BiddingPackageService,
            BiddingService,
        )
        async with get_async_session() as session:
            bidding_list = await BiddingService.get_bidding_by_date("2025-07-07", session)
            tasks = []
            for bidding in bidding_list:
                async def build_and_judge(bidding=bidding):
                    markdown_content = ""
                    markdown_content += f"# {bidding.project}\n\n"
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
            for item in results:
                print("--------------------------------")
                if item["result"].success:
                    print(item["result"].content)
                else:
                    print(f"调用失败: {item['result'].error}")

    asyncio.run(main())