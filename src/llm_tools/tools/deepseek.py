from openai import OpenAI
from llm_tools.config import LLM_API_KEY, LLM_BASE_URL

def deepseek_chat(user_prompt: str, system_prompt="You are a helpful assistant."):
        """调用 Deepseek 大模型完成任务.
        """
        client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)

        print('user prompt:', user_prompt)

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            stream=False
        )

        resp = response.choices[0].message.content
        return resp