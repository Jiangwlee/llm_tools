import os
import logging
from pathlib import Path
import importlib
from llm_tools_v1.core.logging import setup_logging, get_logger
from llm_tools_v1.core import config as config_mod

def test_setup_logging(tmp_path, monkeypatch):
    # 设置环境变量，确保 config 读取到临时目录
    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    # 清除 lru_cache，确保新环境变量生效
    config_mod.get_settings.cache_clear()
    # 重新加载日志模块，确保使用新配置
    importlib.reload(config_mod)
    setup_logging()
    logger = get_logger("test_logger")
    logger.info("test info message")
    logger.error("test error message")
    # 检查日志文件是否生成
    log_file = tmp_path / "app.log"
    assert log_file.exists()
    # 检查日志内容
    with open(log_file, encoding="utf-8") as f:
        content = f.read()
        assert "test info message" in content
        assert "test error message" in content

def test_get_logger():
    logger1 = get_logger("module1")
    logger2 = get_logger("module2")
    assert isinstance(logger1, logging.Logger)
    assert isinstance(logger2, logging.Logger)
    assert logger1.name == "module1"
    assert logger2.name == "module2" 