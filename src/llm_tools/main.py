from typing import Union

from fastapi import FastAPI
from tools.taoguba import get_tgb_hot_articles

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/tgb/hot-articles")
def read_root():
    return get_tgb_hot_articles()


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}