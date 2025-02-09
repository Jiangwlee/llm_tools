import os, json
from datetime import datetime
from typing import Union
from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Any
from llm_tools.tools.taoguba import get_tgb_hot_articles
from llm_tools.crawlers.bidding_notification import BiddingCrawler
from llm_tools.config import BIDDING_DIR, TGB_DIR

app = FastAPI()

class LLMToolResponse(BaseModel):
    code: int
    data: Any
    msg: str

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/tgb/hot-articles")
def read_root():
    try:
        filename = os.path.join(TGB_DIR, f"hot_articles.json")
        if not os.path.exists(filename):
            return LLMToolResponse(code=404, data=None, msg=f"找不到淘股吧热帖.")
        else:
            with open(filename, 'r', encoding="utf-8") as infile:
                json_obj = json.load(infile)
                return LLMToolResponse(code=200, data=json_obj, msg=f"成功.")
    except ValueError:
        return LLMToolResponse(code=200, data="", msg=f"Error.")


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}

@app.get("/bidding/notice/{date_str}")
def get_notice(date_str: str):
    try:
        bidding_filename = os.path.join(BIDDING_DIR, f"bidding_notice_{date_str}.json")
        if not os.path.exists(bidding_filename):
            return LLMToolResponse(code=404, data=None, msg=f"找不到 {date_str} 日的招标公告.")
        else:
            with open(bidding_filename, 'r', encoding="utf-8") as infile:
                json_obj = json.load(infile)
                return LLMToolResponse(code=200, data=json_obj, msg=f"成功.")
    except ValueError:
        return {"error": "输入的日期格式不正确，请使用 YYYYMMDD 格式。"}