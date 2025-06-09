# BiddingInfoExtractor 使用手册

## 目录
- [简介](#简介)
- [环境要求](#环境要求)
- [命令行参数说明](#命令行参数说明)
- [使用方法](#使用方法)
- [运行示例](#运行示例)
- [常见问题与建议](#常见问题与建议)
- [附录：参数配置表](#附录参数配置表)

---

## 简介

`bidding_info_extractor.py` 是一个自动化爬取、解析并入库招标/中标公告信息的脚本，支持断点续跑、失败记录和并发处理。适用于批量采集和结构化存储电力行业等领域的招标数据。

---

## 环境要求

- Python 3.9 及以上
- 已安装项目依赖（推荐使用 uv 管理虚拟环境）
- 正确配置数据库和相关依赖

---

## 命令行参数说明

| 参数名         | 类型    | 默认值       | 说明                         |
| -------------- | ------- | ------------ | ---------------------------- |
| --keyword      | str     | 广州供电局   | 检索关键词                   |
| --max_page     | int     | 3            | 最大爬取页数                 |
| --test_url     | str     | None         | 测试模式，指定单个公告URL    |
| --concurrency  | int     | 5            | 并发处理数                   |
| --type         | str     | all          | 公告类型（all/bidding/award）|

---

## 使用方法

1. **激活虚拟环境**  
   ```bash
   uv venv .venv
   .venv/Scripts/activate  # Windows
   source .venv/bin/activate  # Linux/Mac
   ```

2. **安装依赖**  
   ```bash
   uv pip install -r requirements.txt
   ```

3. **运行脚本**  
   ```bash
   python scripts/bidding_info_extractor.py --keyword "广州供电局" --max_page 5 --type bidding
   ```

4. **参数交互（VSCode/Cursor）**  
   - 推荐在 `.vscode/launch.json` 配置 `"args"` 字段，结合 `"inputs"` 实现运行时参数输入。

---

## 运行示例

### 批量爬取并入库

```bash
python scripts/bidding_info_extractor.py --keyword "广州供电局" --max_page 10 --type all
```

### 仅处理中标公告

```bash
python scripts/bidding_info_extractor.py --keyword "南方电网" --type award
```

### 测试单个公告页面

```bash
python scripts/bidding_info_extractor.py --test_url "https://www.bidding.csg.cn/zbgg/1200396075.jhtml"
```

---

## 常见问题与建议

- **断点续跑**：已处理和失败的 URL 会自动记录在 `data/cache/processed_urls.json` 和 `data/cache/failed_urls.json`，重复运行不会重复处理。
- **日志输出**：日志默认输出到控制台和日志文件（`logs/app.log`），可在主入口通过 `setup_logging(logging_level="INFO")` 配置日志级别。
- **依赖管理**：强烈建议使用 uv 管理依赖，保持虚拟环境和依赖一致性。
- **数据库配置**：请确保数据库连接配置正确，且有写入权限。

---

## 附录：参数配置表

| 参数         | 说明                         | 示例值                        |
| ------------ | ---------------------------- | ----------------------------- |
| --keyword    | 检索关键词                   | "广州供电局"                  |
| --max_page   | 最大爬取页数                 | 5                             |
| --test_url   | 测试模式，指定单个公告URL    | "https://..."                 |
| --concurrency| 并发处理数                   | 10                            |
| --type       | 公告类型（all/bidding/award）| "bidding"                     |

---

## 代码片段示例

```python
# 主入口推荐写法
if __name__ == "__main__":
    from llm_tools_v1.core.logging import setup_logging
    setup_logging(logging_level="INFO")
    import asyncio
    asyncio.run(main())
```

---

## 参考

- [项目 README.md](../README.md)
- [依赖管理与环境配置文档](../docs/DEPLOY.md)
- [FastAPI/Pydantic 官方文档](https://fastapi.tiangolo.com/zh/)

---

如有更多使用问题，请查阅项目文档或联系开发团队。 