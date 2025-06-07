import llm_tools.config as config
from openai import OpenAI
from llm_tools.logger import get_logger

logger = get_logger()

def check_providers():
    # 找一个可用的API
    for key, item in config.PROVIDERS.items():
        logger.info(f"测试大模型接口可用性: {key}, 参数: {item}")
        if item['API_KEY'] is None:
            logger.warning(f"大模型 API_KEY 未设置, 请配置环境变量 {item['API_KEY_ENV']}")
            continue
        try:
            client = OpenAI(api_key=item['API_KEY'], base_url=item['BASE_URL'])
            resp = client.chat.completions.create(
                model=item['MODEL'],
                messages=[{"role": "system", "content": "You are a helpful assistant"}, {"role": "user", "content": "hello"}]
            )
            if not resp.choices:
                logger.error(f"❌大模型供应商 {key} 返回空的响应：{resp}")
                continue
            resp_text = resp.choices[0].message.content

            logger.info(f"🤖大模型应答: {resp_text}")
            logger.info(f"👍大模型供应商 {key} 可以正常使用! 设置为当前大模型参数.")
            config.BASE_URL = item["BASE_URL"]
            config.API_KEY = item["API_KEY"]
            config.MODEL = item['MODEL']
            break
        except Exception as ex:
            logger.error(f"❌大模型供应商 {key} 不可用，错误原因：{ex}")

# check_providers()
config.BASE_URL = config.PROVIDERS[config.DOUBAO]["BASE_URL"]
config.API_KEY = config.PROVIDERS[config.DOUBAO]["API_KEY"]
config.MODEL = config.PROVIDERS[config.DOUBAO]["MODEL"]

def deepseek_chat(user_prompt: str, 
                  system_prompt="You are a helpful assistant.", 
                  api_key=config.API_KEY, 
                  base_url=config.BASE_URL,
                  model=config.MODEL,
                  temperature=0.3,
                  timeout=30):
        """调用 Deepseek 大模型完成任务.
        """
        # print(LLM_API_KEY)
        # print(LLM_BASE_URL)
        client = OpenAI(api_key=api_key, base_url=base_url)

        try:
            response = client.chat.completions.create(
                #model="deepseek-chat",
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
                logger.error(f"❌大模型 {config.MODEL} 返回空的响应：{response}")
                return ""
            resp = response.choices[0].message.content
            return resp
        except Exception as ex:
            logger.error(f"❌大模型 {config.MODEL} 调用异常：{ex}")
        finally:
            return None

def doubao_chat(user_prompt: str, 
                system_prompt="You are a helpful assistant.", 
                api_key=config.API_KEY, 
                base_url=config.BASE_URL,
                model=config.MODEL,
                temperature=0.3,
                timeout=30):
    """调用豆包大模型完成任务.
    """
    client = OpenAI(api_key=api_key, base_url=base_url)
    # logger.info(f"调用豆包大模型，参数如下：")
    # logger.info(f"user_prompt: {user_prompt}")
    # logger.info(f"system_prompt: {system_prompt}")
    # logger.info(f"api_key: {api_key[:8]}...")
    # logger.info(f"base_url: {base_url}")
    # logger.info(f"model: {model}")
    # logger.info(f"temperature: {temperature}")
    # logger.info(f"timeout: {timeout}")

    try:
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
            logger.error(f"❌大模型 {config.MODEL} 返回空的响应：{response}")
            return ""
        resp = response.choices[0].message.content
        logger.info(f"🤖大模型应答: {resp}")
        return resp
    except Exception as ex:
        logger.error(f"❌大模型 {config.MODEL} 调用异常：{ex}")


if __name__ == '__main__':
    # 测试
    print(doubao_chat("介绍下你自己"))