import os
from openai import OpenAI
from llm_tools.logger import get_logger

logger = get_logger()

# 豆包大模型配置
DOUBAO_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
DOUBAO_MODEL = "doubao-1.5-pro-32k-250115"
DOUBAO_API_KEY = os.environ.get("DOUBAO_API_KEY")

def check_doubao_availability():
    """检查豆包大模型的可用性"""
    if not DOUBAO_API_KEY:
        logger.warning("豆包 API_KEY 未设置, 请配置环境变量 DOUBAO_API_KEY")
        return False
    
    try:
        client = OpenAI(
            api_key=DOUBAO_API_KEY,
            base_url=DOUBAO_BASE_URL
        )
        
        resp = client.chat.completions.create(
            model=DOUBAO_MODEL,
            messages=[
                {"role": "system", "content": "你是人工智能助手"},
                {"role": "user", "content": "你好"}
            ]
        )
        
        if not resp.choices:
            logger.error(f"❌豆包大模型返回空的响应：{resp}")
            return False
            
        resp_text = resp.choices[0].message.content
        logger.info(f"🤖豆包大模型应答: {resp_text}")
        logger.info("👍豆包大模型可以正常使用!")
        return True
        
    except Exception as ex:
        logger.error(f"❌豆包大模型不可用，错误原因：{ex}")
        return False

def doubao_chat(user_prompt: str, 
                system_prompt="你是人工智能助手", 
                api_key=None,
                base_url=None,
                model=None,
                temperature=0.3,
                timeout=30):
    """
    调用豆包大模型完成任务
    
    Args:
        user_prompt (str): 用户输入的提示词
        system_prompt (str): 系统提示词，默认为"你是人工智能助手"
        api_key (str): API密钥，默认从环境变量获取
        base_url (str): API基础URL，默认使用豆包的URL
        model (str): 模型名称，默认使用豆包1.5-pro-32k
        temperature (float): 生成温度，默认0.3
        timeout (int): 请求超时时间，默认30秒
    
    Returns:
        str: 模型生成的回复文本，如果出错返回None
    """
    # 使用默认值或传入的参数
    api_key = api_key or DOUBAO_API_KEY
    base_url = base_url or DOUBAO_BASE_URL
    model = model or DOUBAO_MODEL
    
    if not api_key:
        logger.error("❌豆包 API_KEY 未设置")
        return None
    
    try:
        client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            stream=False,
            timeout=timeout
        )
        
        if not response.choices:
            logger.error(f"❌豆包大模型返回空的响应：{response}")
            return None
            
        resp = response.choices[0].message.content
        return resp
        
    except Exception as ex:
        logger.error(f"❌豆包大模型调用异常：{ex}")
        return None

def doubao_chat_stream(user_prompt: str, 
                       system_prompt="你是人工智能助手",
                       api_key=None,
                       base_url=None,
                       model=None,
                       temperature=0.3,
                       timeout=30):
    """
    调用豆包大模型完成任务（流式返回）
    
    Args:
        user_prompt (str): 用户输入的提示词
        system_prompt (str): 系统提示词
        api_key (str): API密钥
        base_url (str): API基础URL
        model (str): 模型名称
        temperature (float): 生成温度
        timeout (int): 请求超时时间
    
    Yields:
        str: 模型生成的回复文本片段
    """
    # 使用默认值或传入的参数
    api_key = api_key or DOUBAO_API_KEY
    base_url = base_url or DOUBAO_BASE_URL
    model = model or DOUBAO_MODEL
    
    if not api_key:
        logger.error("❌豆包 API_KEY 未设置")
        return
    
    try:
        client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        stream = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            stream=True,
            timeout=timeout
        )
        
        for chunk in stream:
            if not chunk.choices:
                continue
            content = chunk.choices[0].delta.content
            if content:
                yield content
                
    except Exception as ex:
        logger.error(f"❌豆包大模型流式调用异常：{ex}")

def doubao_batch_chat(prompts: list, 
                      system_prompt="你是人工智能助手",
                      temperature=0.3):
    """
    批量调用豆包大模型
    
    Args:
        prompts (list): 用户提示词列表
        system_prompt (str): 系统提示词
        temperature (float): 生成温度
    
    Returns:
        list: 模型回复列表
    """
    results = []
    for prompt in prompts:
        result = doubao_chat(prompt, system_prompt, temperature=temperature)
        results.append(result)
    return results

if __name__ == '__main__':
    # 测试豆包大模型可用性
    print("🔍 测试豆包大模型可用性...")
    if check_doubao_availability():
        print("\n📝 测试普通对话:")
        response = doubao_chat("介绍下你自己")
        print(f"豆包回复: {response}")
        
        print("\n🌊 测试流式对话:")
        print("豆包流式回复: ", end="")
        for chunk in doubao_chat_stream("用一句话介绍人工智能"):
            print(chunk, end="")
        print()
        
        print("\n📦 测试批量对话:")
        prompts = ["今天天气怎么样？", "推荐一本好书", "什么是机器学习？"]
        responses = doubao_batch_chat(prompts)
        for i, (prompt, response) in enumerate(zip(prompts, responses)):
            print(f"{i+1}. 问题: {prompt}")
            print(f"   回答: {response}\n")
    else:
        print("❌ 豆包大模型不可用，请检查配置") 