import os, json
from datetime import date
from llm_tools.tools.taoguba import Taoguba
from llm_tools.config import TGB_DIR

class TgbCrawler:
    def __init__(self):
        self.hot_articles = []

    def crawl(self):
        tgb = Taoguba()
        self.hot_articles = tgb.get_hot_articles()

    def save(self):
        with open(os.path.join(TGB_DIR, f"hot_articles.json"), 'w', encoding='utf-8') as outfile:
            json.dump(self.hot_articles, outfile, indent=2, ensure_ascii=False)
        return len(self.hot_articles)
    
if __name__ == '__main__':
    date_str = date.today().isoformat()
    crawler = TgbCrawler()
    crawler.crawl()
    crawler.save()
