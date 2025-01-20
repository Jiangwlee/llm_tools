# 项目概述

本项目实现了一些大模型小插件.

# 项目构建

docker build -t llm_tools:latest .

# 项目运行

docker run --rm --name test -p 12345:8000 llm_tools:latest