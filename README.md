# LLM Tools - 大语言模型工具集

本项目是一个综合性的大语言模型工具集，提供了多种AI服务集成、爬虫功能、配置管理和现代化的Web界面。

## ✨ 主要功能

- 🤖 **多AI服务集成**：支持豆包、GPT等多种大语言模型
- 🕷️ **智能爬虫系统**：招投标信息抓取和数据处理
- 🎛️ **配置管理**：灵活的系统配置和参数管理
- 📊 **实时日志**：现代化的实时日志查看和监控
- 🌐 **Web界面**：基于Streamlit的友好用户界面

## 📚 文档

详细的项目文档请查看：**[docs目录](docs/README.md)**

- [Streamlit实时日志显示解决方案](docs/streamlit_realtime_log_solution.md) - 核心技术方案
- [项目开发文档](docs/) - 完整的开发和集成文档

## 🚀 快速开始

### 项目构建
```bash
docker build -t llm_tools:latest .
```

### 项目运行
```bash
docker run --name llm_tools -p 12345:8000 -e TZ=Asia/Shanghai -d llm_tools:latest
```

### 本地开发
```bash
# 安装依赖
pip install -r requirements.txt

# 运行Web界面
streamlit run run_bidding_ui.py
```

## 🏗️ 项目结构

```
llm_tools/
├── docs/                    # 📚 项目文档
├── src/                     # 💻 源代码
│   └── biddingcsg/         # 核心包
├── tests/                   # 🧪 测试文件
├── logs/                    # 📋 日志文件
├── notebooks/               # 📓 Jupyter笔记本
└── requirements.txt         # 📦 依赖包列表
```

## 🔗 相关链接

- **项目文档**: [docs/](docs/)
- **源码目录**: [src/](src/)
- **测试文件**: [tests/](tests/)

---

**开发团队**: LLM Tools Team  
**最后更新**: 2024年12月5日