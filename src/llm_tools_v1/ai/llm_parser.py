from ..core.logging import get_logger
from ..core.config import get_settings
from ..core.llm import LLMClient
from ..ai.prompt_templates import SYS_BIDDING_SUMMARY_PROMPT
from ..crawlers.biddingcsg import BiddingCsgCrawler

logger = get_logger()

def summary(html_content):
    """调用大模型总结Bidding CSG网页的内容, 提取关键信息.
    
    
    Args:
        user_prompt: 用户输入的提示词
        
    Returns:
        大模型返回的总结结果
        
    """
    try:
        messages = [
            {"role": "system", "content": SYS_BIDDING_SUMMARY_PROMPT.format(html_content=html_content)},
        ]

        resp = LLMClient(model_name="doubao").chat(messages, temperature=0.1)
        return resp["choices"][0]["message"]["content"]
    except Exception as ex:
        logger.warning(f"llm_summary 调用大模型出错, 错误信息: {ex}")

if __name__ == "__main__":
    crawler = BiddingCsgCrawler()
    html_content = crawler.read_bidding_page("https://www.bidding.csg.cn/zbhxrgs/1200395227.jhtml")
    print(summary(html_content))