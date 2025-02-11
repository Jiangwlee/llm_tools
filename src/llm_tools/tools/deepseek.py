from openai import OpenAI
from llm_tools.config import LLM_API_KEY, LLM_BASE_URL, LLM_DOUBAO_DEEPSEEK_BASE_URL, LLM_DOUBAO_DEEPSEEK_MODEL

def deepseek_chat(user_prompt: str, system_prompt="You are a helpful assistant."):
        """调用 Deepseek 大模型完成任务.
        """
        # print(LLM_API_KEY)
        # print(LLM_BASE_URL)
        client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_DOUBAO_DEEPSEEK_BASE_URL)

        # print('user prompt:', user_prompt)

        response = client.chat.completions.create(
            #model="deepseek-chat",
            model=LLM_DOUBAO_DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            stream=False
        )

        resp = response.choices[0].message.content

        return resp

if __name__ == '__main__':
    # 测试
    print(deepseek_chat("介绍下你自己"))