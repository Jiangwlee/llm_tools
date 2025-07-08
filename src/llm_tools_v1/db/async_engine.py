"""
异步数据库 Engine 工厂
支持多数据库驱动，自动读取配置，单例缓存
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from functools import lru_cache
from llm_tools_v1.core.config import get_settings

@lru_cache()
def get_async_engine():
    """
    获取全局唯一异步数据库 Engine 实例
    """
    settings = get_settings()
    # print(f"settings.db_async_url: {settings.db_async_url}")
    return create_async_engine(
        str(settings.db_async_url),
        echo=settings.db_echo,
        future=True
    ) 