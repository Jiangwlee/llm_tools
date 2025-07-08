"""
异步数据库 Session 管理与 FastAPI 依赖
"""
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from llm_tools_v1.db.async_engine import get_async_engine

@asynccontextmanager
async def get_async_session():
    """
    异步 Session 上下文管理器，自动关闭
    """
    async with AsyncSession(get_async_engine()) as session:
        yield session

# FastAPI 依赖
async def get_async_db():
    async with AsyncSession(get_async_engine()) as session:
        try:
            yield session
        finally:
            await session.close() 