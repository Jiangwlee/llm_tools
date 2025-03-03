import requests
import json
import time
from llm_tools.logger import get_logger

logger = get_logger()

def chat_with_coze(bot_id, user_id, message, authorization):
    """
    与 Coze Bot 聊天。

    Args:
        bot_id (str): Bot ID.
        user_id (str): User ID.
        message (str): Message to send.
        authorization (str): Authorization token.

    Returns:
        dict: Response from Coze API.
    """
    logger.info(f"Coze chat: 发起新会话.")
    url = 'https://api.coze.cn/v3/chat?'
    headers = {
        "Authorization": f"Bearer {authorization}",
        "Content-Type": "application/json"
    }
    data = {
        "bot_id": bot_id,
        "user_id": user_id,
        "stream": False,
        "additional_messages": [
            {
                "content": message,
                "content_type": "text",
                "role": "user",
                "type": "question"
            }
        ]
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    return response.json()

    
def check_status(conversation_id, chat_id, authorization):
    """
    检查 Coze Bot 的状态。

    Args:
        conversation_id (str): Conversation ID.
        chat_id (str): Chat ID.
        authorization (str): Authorization token.

    Returns:
        str: Status from Coze API.
    """
    logger.info(f"Coze chat: 检查会话状态")
    url = f'https://api.coze.cn/v3/chat/retrieve?conversation_id={conversation_id}&chat_id={chat_id}&'
    headers = {
        "Authorization": f"Bearer {authorization}",
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    response_json = response.json()
    return response_json["data"]["status"]

def fetch_response(conversation_id, chat_id, authorization):
    """
    使用 requests 执行 curl 命令，从返回的内容中获取第一个 content。

    Args:
        authorization (str): Authorization token.

    Returns:
        str: 第一个 content，如果不存在则返回 None。
    """
    logger.info(f"Coze chat: 查询会话结果")
    url = f'https://api.coze.cn/v3/chat/message/list?conversation_id={conversation_id}&chat_id={chat_id}&'
    headers = {
        "Authorization": f"Bearer {authorization}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # 检查是否有 HTTP 错误
        data = response.json()
        if data and data.get("data") and isinstance(data["data"], list) and len(data["data"]) > 0:
            return data["data"][0].get("content")
        return None
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return None
    
def coze_chat(user_prompt: str, sys_prompt: str=""):
    # bot_id = "7457488016186392613" # 小微助理
    bot_id = "7477567540965752866"
    user_id = "bruce"
    authorization = "pat_pP0vf4fmuFQ9m8jxEVy4Nyc0tFm649zTsLxTKdeTtuShekQixhAoNwomw1nmnzwh"
    
    response = chat_with_coze(bot_id, user_id, f"{sys_prompt}\n\n{user_prompt}", authorization)
    # print(json.dumps(response, indent=2, ensure_ascii=False))

    conversation_id = response["data"]["conversation_id"]
    chat_id = response["data"]["id"]
    completed = False
    while not completed:
        time.sleep(5)
        status = check_status(conversation_id, chat_id, authorization)
        logger.info(f"Status: {status}")
        completed = True if status == 'completed' else False
    resp = fetch_response(conversation_id, chat_id, authorization)
    if resp:
        logger.info(f"Coze chat response: \n{resp}")
    else:
        logger.error("无法获取返回结果")
    return resp

if __name__ == '__main__':
    # 示例用法
    coze_chat("hello")