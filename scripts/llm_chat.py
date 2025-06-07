import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

import argparse
import os
from src.llm_tools_v1.core.llm import LLMClient
from src.llm_tools_v1.core.config import get_settings, set_current_llm
from src.llm_tools_v1.core.logging import setup_logging

def main():
    parser = argparse.ArgumentParser(description="大模型命令行对话工具")
    parser.add_argument("--model", type=str, default="doubao", help="指定大模型名称（如 doubao、deepseek）")
    args = parser.parse_args()

    # 强制设置日志级别为 DEBUG
    os.environ["LOG_LEVEL"] = "ERROR"
    set_current_llm(args.model)
    setup_logging()

    client = LLMClient(model_name=args.model)
    print(f"当前大模型: {client.model_name}")
    print("请输入对话内容，输入 exit 退出：")
    while True:
        user_input = input("你: ").strip()
        if user_input.lower() in ("exit", "quit", "q"):
            print("已退出。"); break
        messages = [{"role": "user", "content": user_input}]
        try:
            response = client.chat(messages)
            # 兼容不同模型的返回格式
            content = response["choices"][0]["message"]["content"]
            print(f"模型: {content}")
        except Exception as e:
            print(f"调用失败: {e}")

if __name__ == "__main__":
    main() 