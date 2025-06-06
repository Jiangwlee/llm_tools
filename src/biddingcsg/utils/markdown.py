def remove_markdown_mark(text: str) -> str:
    """移除markdown开始和结束标记

    例子：
    输入：```json\n{"name": "张三"}\n```
    输出：{"name": "张三"}
    """
    # 移除markdown代码块标记
    if text.startswith("```") and text.endswith("```"):
        # 移除开头的```和可能的语言标识符
        text = text[text.find("\n") + 1:]
        # 移除结尾的```
        text = text[:-3]
        # 移除可能的开头和结尾空白
        text = text.strip()
    return text