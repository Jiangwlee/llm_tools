import os, json
from datetime import date
from llm_tools.tools.taoguba import Taoguba
from llm_tools.config import TGB_DIR
from llm_tools.tools.deepseek import deepseek_chat
from llm_tools.logger import get_logger

SYS_PROMPT = """
你是一个经验丰富的交易员，擅长技术分析、市场情绪分析和短线交易。请仔细阅读以下文章内容，分析：
1. 市场整体情绪
2. 市场的主线板块
3. 市场的核心个股：分析个股上涨的原因
4. 对后市的预期

必要时可以调用搜索工具来查询股票上涨的原因

分析结束后，按照如下格式输出：
### 标题：<subject>
#### 作者：<userName>
#### 地址：<url>
#### 总结：
- 市场情绪：<市场整体情绪总结>
- 主线板块：<市场的主线板块>
- 核心个股：<市场的领涨核心和上涨原因>
- 后市预期：<对后市的展望>
"""

USER_PROMPT = """
# {subject}

## 作者: {userName}

## 发帖日期: {date}

## 链接地址: {url}

{content}
"""

logger = get_logger()

class TgbCrawler:
    def __init__(self):
        self.hot_articles = []
        self.cache = os.path.join(TGB_DIR, f"hot_articles.json")

    def crawl(self):
        tgb = Taoguba()
        self.hot_articles  = tgb.get_hot_articles()
        cached_articles = self.get_cached_articles()
        # cached_subjects = [x['subject'] for x in cached_articles]
        cache_map = {obj['subject']: obj for obj in cached_articles}

        logger.info(f"爬取到 {len(self.hot_articles)} 条帖子")
        for article in self.hot_articles:
            subject = article['subject']
            if subject in cache_map.keys():
                logger.info(f"帖子\"{subject}\"已存在，跳过")
                article['summary'] = cache_map[subject]['summary']
                continue
            logger.info(f"调用大模型分析【{article['userName']}】的帖子\"{article['subject']}\"")
            summary = self.summarize(self.format_article(article))
            article['summary'] = summary

    def get_cached_articles(self):
        if not os.path.exists(self.cache):
            with open(self.cache, 'w', encoding='utf-8') as cache:
                cache.write("[]")
        with open(self.cache, 'r', encoding='utf-8') as infile:
            return json.load(infile)

    def summarize(self, article):
        # summary = deepseek_chat(article, SYS_PROMPT)
        summary = deepseek_chat(article, SYS_PROMPT, api_key='sk-dtutquenqznknnrhrykiqzaxwwxruifmfwwnbrxkajwmkbmf', base_url='https://api.siliconflow.cn/v1', model='deepseek-ai/DeepSeek-V3')
        # print(summary)
        return summary

    def format_article(self, article_obj):
        return USER_PROMPT.format(subject=article_obj["subject"], userName=article_obj["userName"], date=article_obj["date"], url=article_obj["url"], content=article_obj["content"])

    def save(self):
        with open(self.cache, 'w', encoding='utf-8') as outfile:
            json.dump(self.hot_articles, outfile, indent=2, ensure_ascii=False)
        return len(self.hot_articles)
    
if __name__ == '__main__':
    crawler = TgbCrawler()
    crawler.crawl()
    crawler.save()

