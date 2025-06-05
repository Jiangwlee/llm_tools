# LLM 重构使用指南

## 📖 概述

本项目对 `LLMHelper` 类进行了重构，实现了统一的模型调用接口，不再绑定特定的模型提供商（如 `deepseek_chat` 或 `coze_chat`），而是支持用户配置的任意模型进行推理。

## 🎯 重构目标

- ✅ **解耦模型绑定**：移除对特定模型的硬编码依赖
- ✅ **统一调用接口**：提供一致的模型调用体验
- ✅ **配置驱动**：支持通过配置文件或 Web UI 选择模型
- ✅ **降级机制**：提供备选方案确保系统稳定性
- ✅ **易于扩展**：方便添加新的模型提供商

## 🏗️ 架构设计

### 核心组件

#### 1. UnifiedLLMClient
统一的 LLM 调用客户端，支持多种模型提供商：

```python
# 使用默认配置
client = UnifiedLLMClient()

# 指定提供商
client = UnifiedLLMClient(provider="DEEPSEEK")

# 完全自定义
client = UnifiedLLMClient(
    provider="DOUBAO",
    model="doubao-1.5-pro-32k-250115",
    api_key="your_api_key",
    base_url="https://ark.cn-beijing.volces.com/api/v3"
)
```

#### 2. LLMHelper (重构后)
提供三个主要的LLM功能接口：

```python
# 基本信息提取
result = LLMHelper.llm_basic_info_extract("招标公告文本")

# 内容总结
summary = LLMHelper.llm_summary("需要总结的内容")

# 价格信息提取
price_info = LLMHelper.llm_price_extract("包含价格的文本")
```

## 🚀 使用方法

### 1. 基本使用

重构后的 `LLMHelper` 会自动使用配置的模型：

```python
from src.llm_tools.tools.bidding_csg import LLMHelper

# 直接使用，会自动初始化为用户配置的模型
result = LLMHelper.llm_basic_info_extract("南方电网招标公告文本")
print(result)
```

### 2. 切换模型提供商

```python
# 切换到豆包模型
LLMHelper.switch_provider("DOUBAO")

# 切换到硅基流动
LLMHelper.switch_provider("SILICONFLOW")

# 切换到 DeepSeek
LLMHelper.switch_provider("DEEPSEEK")
```

### 3. 从 Web UI 配置初始化

```python
# 从 Web UI 用户配置中初始化模型
LLMHelper.initialize_from_config_manager()

# 现在使用的就是用户在 Web UI 中选择的模型
result = LLMHelper.llm_summary("要总结的内容")
```

### 4. 自定义模型配置

```python
# 设置完全自定义的模型配置
LLMHelper.set_llm_client(
    provider="DOUBAO",
    api_key="your_custom_api_key",
    base_url="your_custom_endpoint"
)
```

## 🔧 配置说明

### config.py 配置

模型配置在 `src/llm_tools/config.py` 的 `PROVIDERS` 字典中：

```python
PROVIDERS = {
    "DEEPSEEK": {
        "BASE_URL": "https://api.deepseek.com",
        "MODEL": "deepseek-chat",
        "API_KEY": os.getenv("DEEPSEEK_API_KEY", None),
        "API_KEY_ENV": "DEEPSEEK_API_KEY"
    },
    "DOUBAO": {
        "BASE_URL": "https://ark.cn-beijing.volces.com/api/v3",
        "MODEL": "doubao-1.5-pro-32k-250115",
        "API_KEY": os.getenv("DOUBAO_API_KEY", None),
        "API_KEY_ENV": "DOUBAO_API_KEY"
    },
    "SILICONFLOW": {
        "BASE_URL": "https://api.siliconflow.cn/v1",
        "MODEL": "deepseek-ai/DeepSeek-V3",
        "API_KEY": os.getenv("SILICONFLOW_API_KEY", None),
        "API_KEY_ENV": "SILICONFLOW_API_KEY"
    }
}
```

### 环境变量

设置相应的 API 密钥环境变量：

```bash
# DeepSeek
export DEEPSEEK_API_KEY="your_deepseek_api_key"

# 豆包
export DOUBAO_API_KEY="your_doubao_api_key"

# 硅基流动
export SILICONFLOW_API_KEY="your_siliconflow_api_key"
```

## 🔀 模型选择逻辑

### 自动选择优先级

1. **Web UI 配置**：如果从 Web UI 调用，使用用户选择的模型
2. **环境变量优先级**：DEEPSEEK > DOUBAO > SILICONFLOW
3. **配置文件首选**：使用 config.py 中第一个配置的提供商
4. **兜底默认值**：DEEPSEEK

### 降级机制

```python
# 基本信息提取的降级逻辑
def llm_basic_info_extract(user_prompt):
    try:
        # 1. 尝试使用配置的统一模型
        llm_client = LLMHelper.get_llm_client()
        if llm_client.is_available():
            result = llm_client.chat(...)
            if result:
                return result
        
        # 2. 降级到本地 ollama 模型
        return extract_bidding_info(str(user_prompt))
        
    except Exception as ex:
        logger.error(f"所有模型调用失败: {ex}")
        return None
```

## 🧪 测试

运行测试脚本验证功能：

```bash
python test_llm_refactor.py
```

测试内容包括：
- ✅ 统一 LLM 客户端基本功能
- ✅ LLMHelper 三个主要接口
- ✅ 模型提供商切换
- ✅ Web UI 配置集成
- ✅ 错误处理和降级方案

## 📊 使用示例

### 在 Web UI 中使用

```python
# 在 Web UI 页面中
def process_bidding_data():
    # 自动使用用户在 UI 中选择的模型
    LLMHelper.ensure_initialized()
    
    # 提取信息
    info = LLMHelper.llm_basic_info_extract(bidding_text)
    
    # 生成总结
    summary = LLMHelper.llm_summary(bidding_text)
    
    # 提取价格
    price_info = LLMHelper.llm_price_extract(bidding_text)
    
    return info, summary, price_info
```

### 在命令行工具中使用

```python
# 在命令行脚本中
def analyze_bidding_file(filename):
    # 可以手动指定模型
    LLMHelper.switch_provider("DOUBAO")
    
    with open(filename, 'r') as f:
        content = f.read()
    
    # 分析内容
    analysis = LLMHelper.llm_summary(content)
    return analysis
```

## 🔄 迁移指南

### 从旧版本迁移

**旧代码**：
```python
# 硬编码使用特定模型
result = deepseek_chat(prompt, system_prompt, temperature=0.1)
# 或
result = coze_chat(prompt, system_prompt)
```

**新代码**：
```python
# 使用统一接口，自动选择配置的模型
result = LLMHelper.llm_summary(prompt)
# 或
result = LLMHelper.llm_price_extract(prompt)
```

### 兼容性

- ✅ **向后兼容**：原有的函数签名保持不变
- ✅ **功能增强**：增加了模型选择和配置功能
- ✅ **稳定性提升**：增加了错误处理和降级机制

## 🛠️ 扩展新模型

### 添加新的模型提供商

1. **在 config.py 中添加配置**：
```python
PROVIDERS["NEW_PROVIDER"] = {
    "BASE_URL": "https://api.newprovider.com",
    "MODEL": "new-model-name",
    "API_KEY": os.getenv("NEW_PROVIDER_API_KEY", None),
    "API_KEY_ENV": "NEW_PROVIDER_API_KEY"
}
```

2. **设置环境变量**：
```bash
export NEW_PROVIDER_API_KEY="your_api_key"
```

3. **使用新模型**：
```python
LLMHelper.switch_provider("NEW_PROVIDER")
```

### 自定义模型行为

如果新模型需要特殊处理，可以在 `UnifiedLLMClient` 中添加特定逻辑：

```python
def chat(self, user_prompt, system_prompt="你是人工智能助手", **kwargs):
    if self.provider == "NEW_PROVIDER":
        # 新提供商的特殊处理逻辑
        pass
    
    # 通用处理逻辑
    return self.client.chat.completions.create(...)
```

## 📝 注意事项

1. **API 密钥**：确保设置了相应模型的 API 密钥环境变量
2. **网络连接**：模型调用需要稳定的网络连接
3. **错误处理**：建议在业务代码中添加适当的错误处理
4. **性能考虑**：不同模型的响应时间可能差异较大
5. **成本控制**：注意不同模型的计费方式和成本

## 🆘 故障排除

### 常见问题

1. **模型不可用**：
   - 检查 API 密钥是否正确设置
   - 验证网络连接
   - 查看日志中的详细错误信息

2. **降级失败**：
   - 确保 ollama 服务正在运行（用于基本信息提取的降级）
   - 检查本地模型是否正确安装

3. **配置未生效**：
   - 确保调用了 `LLMHelper.ensure_initialized()`
   - 检查 config.py 中的配置是否正确

### 调试技巧

```python
# 启用详细日志
import logging
logging.getLogger("llm_tools").setLevel(logging.DEBUG)

# 检查当前模型状态
client = LLMHelper.get_llm_client()
print(f"当前提供商: {client.provider}")
print(f"当前模型: {client.model}")
print(f"可用性: {client.is_available()}")
```

## 🔮 未来规划

- 🔄 **流式响应**：支持流式模型调用
- 📊 **使用统计**：添加模型使用统计和监控
- 🔧 **模型池管理**：支持模型负载均衡和故障转移
- 🎛️ **高级配置**：支持更细粒度的模型参数配置 