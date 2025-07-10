import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from llm_tools_v1.core.config import LlmToolsDirs
from llm_tools_v1.core.config import get_settings

def setup_logging(logging_level: str = "INFO"):
    """
    初始化日志配置，支持文件轮转和控制台输出，参数从 config 读取。
    """
    log_dir = LlmToolsDirs.get_log_dir()
    log_level = logging_level.upper() if logging_level else get_settings().log_level.upper()
    log_file = Path(log_dir) / "app.log"
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    # 文件处理器（按天轮转，保留7天）
    file_handler = TimedRotatingFileHandler(
        filename=log_file,
        when="midnight",
        backupCount=7,
        encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(fmt, datefmt))

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(fmt, datefmt))

    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    logger.handlers.clear()
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # 降低第三方依赖日志级别，避免刷屏
    for noisy_logger in ["LiteLLM", "httpx", "openai", "urllib3"]:
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)


def get_logger(name: str = None) -> logging.Logger:
    """
    获取指定名称的日志器。如果日志系统未初始化，则自动调用 setup_logging（兜底保障）。
    推荐在主入口显式调用 setup_logging()，此自动初始化仅做基础配置。
    :param name: 日志器名称
    :return: logger
    """
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        # 兜底初始化，防止日志丢失
        setup_logging()
    return logging.getLogger(name) 