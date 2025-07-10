import asyncio

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from llm_tools_v1.db.async_engine import get_async_engine
from llm_tools_v1.db.models import SQLModel
from llm_tools_v1.core.config import LlmToolsDirs

async def init_db():
    """
    初始化数据库表结构（如 bidding、biddingpackage 等）
    """
    DB_PATH = LlmToolsDirs.get_db_dir()
    if not os.path.exists(DB_PATH):
        os.makedirs(DB_PATH, exist_ok=True)
    if not os.path.exists(DB_PATH + "/llm_tools.db"):
        engine = get_async_engine()
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        print("数据库表结构已初始化。")

if __name__ == "__main__":
    asyncio.run(init_db()) 