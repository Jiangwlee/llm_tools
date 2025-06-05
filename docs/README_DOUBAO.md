# 豆包大模型集成使用指南

## 概述

本文档介绍如何在 llm_tools 项目中使用豆包（字节跳动）大模型。豆包是字节跳动推出的大语言模型，具有强大的中文理解和生成能力。

## 功能特性

- ✅ **基础对话**: 支持标准的问答对话
- ✅ **流式对话**: 支持实时流式响应
- ✅ **批量处理**: 支持批量处理多个问题
- ✅ **参数调节**: 支持温度、超时等参数自定义
- ✅ **错误处理**: 完善的异常处理和日志记录
- ✅ **配置集成**: 与项目配置系统无缝集成

## 快速开始

### 1. 获取 API 密钥

1. 访问 [火山引擎-模型推理](https://www.volcengine.com/product/ark)
2. 注册账号并完成实名认证
3. 创建推理接入点并获取 API Key

### 2. 配置环境变量

```bash
# Linux/macOS
export DOUBAO_API_KEY="your_doubao_api_key_here"

# Windows
set DOUBAO_API_KEY=your_doubao_api_key_here
```

### 3. 安装依赖

```bash
# 如果使用 uv
uv add openai

# 如果使用 pip
pip install openai
```

### 4. 测试安装

```bash
python test_doubao.py
```

## 使用方法

### 基础对话

```python
from src.llm_tools.tools.bytedance import doubao_chat

# 简单对话
response = doubao_chat("你好，请介绍下你自己")
print(response)

# 带系统提示的对话
response = doubao_chat(
    user_prompt="请用专业的语言解释机器学习",
    system_prompt="你是一个机器学习专家"
)
print(response)
```

### 流式对话

```python
from src.llm_tools.tools.bytedance import doubao_chat_stream

print("豆包回复: ", end="")
for chunk in doubao_chat_stream("请讲一个关于编程的笑话"):
    print(chunk, end="", flush=True)
print()
```

### 批量处理

```python
from src.llm_tools.tools.bytedance import doubao_batch_chat

questions = [
    "什么是Python？",
    "什么是机器学习？",
    "什么是深度学习？"
]

responses = doubao_batch_chat(questions)
for q, a in zip(questions, responses):
    print(f"问: {q}")
    print(f"答: {a}\n")
```

### 自定义参数

```python
from src.llm_tools.tools.bytedance import doubao_chat

# 高创造性回答
creative_response = doubao_chat(
    user_prompt="写一首关于编程的诗",
    temperature=0.9,  # 高温度，更有创意
    timeout=60        # 60秒超时
)

# 精确回答
precise_response = doubao_chat(
    user_prompt="1+1等于多少？",
    temperature=0.1,  # 低温度，更精确
    timeout=10        # 10秒超时
)
```

## API 参考

### doubao_chat()

标准对话接口

```python
def doubao_chat(
    user_prompt: str,           # 用户输入
    system_prompt: str = "你是人工智能助手",  # 系统提示
    api_key: str = None,        # API密钥
    base_url: str = None,       # API地址
    model: str = None,          # 模型名称
    temperature: float = 0.3,   # 温度参数 (0.0-1.0)
    timeout: int = 30           # 超时时间(秒)
) -> str:
```

### doubao_chat_stream()

流式对话接口

```python
def doubao_chat_stream(
    user_prompt: str,           # 用户输入
    system_prompt: str = "你是人工智能助手",  # 系统提示
    api_key: str = None,        # API密钥
    base_url: str = None,       # API地址
    model: str = None,          # 模型名称
    temperature: float = 0.3,   # 温度参数
    timeout: int = 30           # 超时时间(秒)
) -> Iterator[str]:             # 返回文本片段迭代器
```

### doubao_batch_chat()

批量处理接口

```python
def doubao_batch_chat(
    prompts: list,              # 问题列表
    system_prompt: str = "你是人工智能助手",  # 系统提示
    temperature: float = 0.3    # 温度参数
) -> list:                      # 返回回答列表
```

### check_doubao_availability()

检查可用性

```python
def check_doubao_availability() -> bool:
    """检查豆包大模型是否可用"""
```

## 配置说明

### 默认配置

```python
DOUBAO_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
DOUBAO_MODEL = "doubao-1.5-pro-32k-250115"
DOUBAO_API_KEY = os.environ.get("DOUBAO_API_KEY")
```

### 配置文件集成

豆包配置已集成到 `src/llm_tools/config.py` 中：

```python
DOUBAO: {
    "BASE_URL": "https://ark.cn-beijing.volces.com/api/v3",
    "MODEL": "doubao-1.5-pro-32k-250115",
    "API_KEY": os.getenv("DOUBAO_API_KEY", None),
    "API_KEY_ENV": "DOUBAO_API_KEY"
}
```

## 参数说明

### temperature (温度参数)

控制生成文本的随机性：

- `0.0-0.3`: 确定性强，适合事实性问答
- `0.3-0.7`: 平衡创造性和准确性，适合一般对话
- `0.7-1.0`: 创造性强，适合创意写作

### timeout (超时时间)

API 请求的超时时间（秒）：

- 简单问答: 10-30秒
- 复杂生成: 30-60秒
- 长文本生成: 60-120秒

## 错误处理

### 常见错误

1. **API密钥未配置**
   ```
   ❌豆包 API_KEY 未设置
   ```
   解决: 设置环境变量 `DOUBAO_API_KEY`

2. **网络连接错误**
   ```
   ❌豆包大模型调用异常: Connection error
   ```
   解决: 检查网络连接和防火墙设置

3. **API配额不足**
   ```
   ❌豆包大模型调用异常: Quota exceeded
   ```
   解决: 检查火山引擎账户余额和配额

4. **模型不可用**
   ```
   ❌豆包大模型返回空的响应
   ```
   解决: 检查模型名称和接入点配置

### 调试模式

```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)

from src.llm_tools.tools.bytedance import doubao_chat
response = doubao_chat("测试")
```

## 最佳实践

### 1. 提示词设计

```python
# ❌ 模糊的提示
response = doubao_chat("写代码")

# ✅ 清晰的提示
response = doubao_chat(
    "请用Python写一个计算斐波那契数列的函数，包含注释",
    system_prompt="你是一个资深的Python开发者"
)
```

### 2. 错误处理

```python
from src.llm_tools.tools.bytedance import doubao_chat

def safe_chat(prompt):
    try:
        response = doubao_chat(prompt, timeout=30)
        if response:
            return response
        else:
            return "模型暂时无法回复，请稍后重试"
    except Exception as e:
        return f"请求失败: {str(e)}"

result = safe_chat("你好")
```

### 3. 资源管理

```python
# 批量处理时控制并发
import time

def batch_with_delay(prompts, delay=1):
    responses = []
    for prompt in prompts:
        response = doubao_chat(prompt)
        responses.append(response)
        time.sleep(delay)  # 避免频率限制
    return responses
```

## 集成示例

### 在 bidding_csg 中使用

```python
# 在 src/llm_tools/tools/bidding_csg.py 中添加
from llm_tools.tools.bytedance import doubao_chat

class LLMHelper:
    @staticmethod
    def doubao_summary(user_prompt):
        """使用豆包模型总结内容"""
        try:
            return doubao_chat(
                user_prompt, 
                SYS_BIDDING_SUMMARY_PROMPT, 
                temperature=0.1
            )
        except Exception as ex:
            logger.warning(f"豆包模型调用出错: {ex}")
            return None
```

### 在 Web UI 中使用

```python
import streamlit as st
from src.llm_tools.tools.bytedance import doubao_chat, doubao_chat_stream

st.title("豆包AI助手")

if prompt := st.chat_input("请输入您的问题"):
    with st.chat_message("user"):
        st.write(prompt)
    
    with st.chat_message("assistant"):
        # 流式显示
        response_placeholder = st.empty()
        full_response = ""
        
        for chunk in doubao_chat_stream(prompt):
            full_response += chunk
            response_placeholder.write(full_response)
```

## 故障排除

### 测试连接

```bash
# 运行测试脚本
python test_doubao.py

# 预期输出
🔍 豆包大模型功能测试
==================================================
🧪 执行测试: API密钥配置
  ✅ DOUBAO_API_KEY 已配置: ak-*****abc
...
🎉 所有测试通过！豆包大模型集成成功
```

### 检查配置

```python
from src.llm_tools.tools.bytedance import DOUBAO_API_KEY, DOUBAO_BASE_URL, DOUBAO_MODEL

print(f"API Key: {'已配置' if DOUBAO_API_KEY else '未配置'}")
print(f"Base URL: {DOUBAO_BASE_URL}")
print(f"Model: {DOUBAO_MODEL}")
```

## 更新日志

- **v1.0.0** (2025-01-05): 初始版本，支持基础对话、流式对话、批量处理
- 支持的模型: `doubao-1.5-pro-32k-250115`
- 支持的功能: 对话、流式、批量、参数自定义

## 许可证

本模块遵循项目主许可证。豆包大模型的使用需遵循火山引擎的服务条款。

---

如有问题或建议，请提交 Issue 或联系开发团队。 