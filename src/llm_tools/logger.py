import os
import logging
from llm_tools.config import CONSOLE_HANDLER, FILE_HANDLER

def get_logger(module: str = ""):
    logger = logging.getLogger('llm_tools')
    logger.addHandler(CONSOLE_HANDLER)
    if os.name == 'posix':
        logger.addHandler(FILE_HANDLER)
    logger.setLevel(logging.DEBUG)
    return logger