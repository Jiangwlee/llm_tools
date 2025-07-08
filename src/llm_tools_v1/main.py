from fastapi import FastAPI
from contextlib import asynccontextmanager
from sqlmodel import SQLModel
from llm_tools_v1.api.v1.helloworld import router as helloworld_router
from llm_tools_v1.api.v1.biddingcsg import router as biddingcsg_router
from llm_tools_v1.db.async_engine import get_async_engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时创建表
    engine = get_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    # 关闭时清理资源
    await engine.dispose()

app = FastAPI(lifespan=lifespan)
app.include_router(helloworld_router, prefix="/api/v1")
app.include_router(biddingcsg_router, prefix="/api/v1") 