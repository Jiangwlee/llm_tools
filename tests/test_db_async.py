import os
import pytest
import asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from src.llm_tools_v1.core.config import get_settings, Settings
from src.llm_tools_v1.db.async_engine import get_async_engine
from src.llm_tools_v1.db.async_session import get_async_session

@pytest.fixture(autouse=True)
def clear_settings_cache():
    """
    每个测试前后清理配置缓存，保证环境变量生效
    """
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()

def test_settings_default_and_env(monkeypatch):
    """
    测试 Settings 默认值和环境变量覆盖
    """
    # 默认值
    settings = get_settings()
    assert settings.db_type == "sqlite"
    assert settings.db_async_url.startswith("sqlite+aiosqlite://")
    assert settings.db_echo is False

    # 环境变量覆盖
    monkeypatch.setenv("DB_TYPE", "mysql")
    monkeypatch.setenv("DB_ASYNC_URL", "mysql+asyncmy://user:pass@localhost/testdb")
    monkeypatch.setenv("DB_ECHO", "True")
    get_settings.cache_clear()
    settings2 = get_settings()
    assert settings2.db_type == "mysql"
    assert settings2.db_async_url.startswith("mysql+asyncmy://")
    assert settings2.db_echo is True

def test_async_engine_singleton():
    """
    测试异步 Engine 工厂单例
    """
    engine1 = get_async_engine()
    engine2 = get_async_engine()
    assert isinstance(engine1, AsyncEngine)
    assert engine1 is engine2  # 单例缓存

@pytest.mark.asyncio
async def test_get_async_session():
    """
    测试异步 Session 获取与上下文管理
    """
    async with get_async_session() as session:
        assert isinstance(session, AsyncSession)
    # 关闭后再次 enter 应无异常
    async with get_async_session() as session2:
        assert isinstance(session2, AsyncSession) 