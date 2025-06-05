from ollama import chat
from ollama import ChatResponse
from pydantic import BaseModel
from llm_tools.logger import logger
from llm_tools.tools.model import BiddingNoticeInfo
    
def ollama_chat(user_prompt: str, system_prompt='You are a helpful AI assistant', model='qwen2.5:7b', format: BaseModel=None):
    response_content = None
    try:
        response: ChatResponse = chat(model=model, messages=[
                {
                    'role': 'system',
                    'content': system_prompt
                },
                {
                    'role': 'user',
                    'content': user_prompt,
                },
            ],
            format=format.model_json_schema()
        )

        response_content = response.message.content
    except Exception as ex:
        logger.error(f"❌ Ollama {model} 调用异常：{ex}")
    finally:
        return response_content

from llm_tools.tools.model import BiddingNoticeInfo
EXTRAC_BIDDIND_INFO_SYS_PROMPT = """你是一个认真负责的招投标助理. 你背负着巨额的房贷,上有老下有小,不能出现任何的工作闪失,导致失去工作.
<工作任务>
仔细阅读用户提供的招标公告,从中准确地提取相关信息:
- 项目名称: 来自于招标条件
- 项目编号: 来自于正文内容
- 招标人: 来自于招标条件

<输出格式>
以JSON格式输出:
{{
    "project": "项目名称",
    "project_code": "项目编号",
    "bidding_inviter": "招标人"
}}
"""
def extract_bidding_info(notification: str):
    try:
        return ollama_chat(
            user_prompt=notification,
            system_prompt=EXTRAC_BIDDIND_INFO_SYS_PROMPT,
            format=BiddingNoticeInfo
        )
    except Exception as ex:
        logger.error(f"捕获到异常: {ex}")
    
if __name__ == '__main__':
    print(ollama_chat('hello'))
