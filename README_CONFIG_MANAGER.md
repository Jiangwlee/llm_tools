# 配置管理器和模型连接测试使用指南

## 功能概述

本文档介绍南方电网招投标数据查询系统中的配置管理器和模型连接测试功能。

## 主要功能

### 🤖 默认模型配置

- **模型选择**: 支持从多个大语言模型提供商中选择默认模型
- **状态显示**: 实时显示各模型提供商的API密钥配置状态
- **持久化**: 配置自动保存到本地文件，下次启动时自动加载

### 🔌 连接测试

- **单模型测试**: 测试当前选择的模型连通性
- **批量测试**: 测试所有配置的模型提供商
- **详细报告**: 显示响应时间、错误信息等详细信息
- **日志记录**: 完整的连接测试日志记录

### ⚙️ 高级设置

- **下载设置**: 配置默认爬取页数、自动保存等
- **查询设置**: 配置图表显示、结果限制等
- **配置管理**: 重置配置、刷新状态等

## 使用方法

### 1. 模型选择

在侧边栏的"🤖 默认模型配置"部分：

1. 从下拉列表中选择所需的模型
2. ✅ 表示API密钥已配置且可用
3. ❌ 表示需要配置API密钥
4. 选择后配置会自动保存

### 2. 连接测试

#### 侧边栏快速测试
- 点击"🔌 连接测试"按钮
- 测试当前选择的模型
- 查看响应时间和模型回复

#### 详细测试（系统说明页面）
- **测试当前模型**: 详细的单模型测试
- **测试所有模型**: 批量测试所有提供商
- 显示完整的测试结果表格

### 3. 配置API密钥

在操作系统中设置环境变量：

```bash
# Linux/macOS
export DEEPSEEK_API_KEY="your_deepseek_api_key"
export DOUBAO_API_KEY="your_doubao_api_key"
export SILICONFLOW_API_KEY="your_siliconflow_api_key"

# Windows
set DEEPSEEK_API_KEY=your_deepseek_api_key
set DOUBAO_API_KEY=your_doubao_api_key
set SILICONFLOW_API_KEY=your_siliconflow_api_key
```

## 支持的模型提供商

### DeepSeek
- **环境变量**: `DEEPSEEK_API_KEY`
- **API地址**: https://api.deepseek.com
- **支持模型**: 
  - deepseek-chat (默认)
  - deepseek-coder

### 豆包 (字节跳动)
- **环境变量**: `DOUBAO_API_KEY`
- **API地址**: https://ark.cn-beijing.volces.com/api/v3
- **支持模型**: 
  - doubao-1.5-pro-32k-250115 (默认)
  - doubao-lite-4k

### 硅基流动
- **环境变量**: `SILICONFLOW_API_KEY`
- **API地址**: https://api.siliconflow.cn/v1
- **支持模型**: 
  - deepseek-ai/DeepSeek-V3 (默认)
  - Qwen/Qwen2.5-72B-Instruct
  - meta-llama/Meta-Llama-3.1-70B-Instruct

## 配置文件

### 位置
配置文件存储在用户主目录下：
```
~/.llm_tools/web_ui_config.json
```

### 结构
```json
{
  "default_model": {
    "provider": "DEEPSEEK",
    "name": "deepseek-chat"
  },
  "ui_settings": {
    "theme": "light",
    "language": "zh-CN",
    "page_size": 20
  },
  "download_settings": {
    "default_max_pages": 5,
    "default_bidding_type": null,
    "auto_save": true
  },
  "query_settings": {
    "show_charts": true,
    "auto_export": false,
    "result_limit": 100
  }
}
```

## 连接测试详情

### 测试流程
1. 检查提供商配置是否存在
2. 验证API密钥是否已设置
3. 发送测试请求到模型API
4. 记录响应时间和结果
5. 生成测试报告

### 测试指标
- **成功率**: 连接成功的提供商比例
- **响应时间**: API调用的响应延迟
- **错误信息**: 详细的失败原因

### 日志记录
所有连接测试过程都会记录详细日志：
- 测试开始/结束时间
- API调用参数
- 响应时间和结果
- 错误信息和异常

## 故障排除

### 常见问题

1. **API密钥未配置**
   ```
   ❌ API密钥未配置
   详情: 请设置环境变量: DEEPSEEK_API_KEY
   ```
   **解决方案**: 设置相应的环境变量

2. **连接超时**
   ```
   ❌ 连接失败
   详情: timeout: Read timeout
   ```
   **解决方案**: 检查网络连接，或稍后重试

3. **API配额不足**
   ```
   ❌ 连接失败
   详情: 429 Too Many Requests
   ```
   **解决方案**: 检查API配额或稍后重试

4. **模型不可用**
   ```
   ❌ API响应异常
   详情: 未收到有效的响应内容
   ```
   **解决方案**: 检查模型名称和API配置

### 调试模式

查看详细日志信息：
1. 在系统说明页面查看实时日志
2. 检查应用程序日志文件
3. 使用连接测试的详细报告

## 最佳实践

### 1. 模型选择策略
- 优先选择已配置API密钥的提供商
- 根据具体需求选择合适的模型
- 定期测试连接状态

### 2. 配置管理
- 定期备份配置文件
- 使用高级设置优化系统性能
- 根据使用情况调整参数

### 3. 故障预防
- 定期运行连接测试
- 监控API配额使用情况
- 保持API密钥的安全性

## 更新日志

- **v1.0.0**: 初始版本，支持基础模型配置和连接测试
- **v1.1.0**: 添加批量测试功能和详细日志记录
- **v1.2.0**: 集成config.py配置，支持动态提供商加载

---

如有问题或建议，请查看系统日志或联系技术支持。 