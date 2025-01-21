import os
import logging
from logging.handlers import RotatingFileHandler

##########################################
# 日志配置
##########################################

# 日志格式
FORMATTER = logging.Formatter('[%(levelname)-8s] - %(asctime)s - %(name)s - %(module)-14s| %(message)s')

# 文件日志格式
FILE_HANDLER = None
if os.name == 'posix':
    os.makedirs('/var/log/llm_tools/', exist_ok=True)
    LOGFILE = '/var/log/llm_tools/llm_tools.log'
    FILE_HANDLER = RotatingFileHandler(LOGFILE, maxBytes=1024*1024, backupCount=3)
    FILE_HANDLER.setFormatter(FORMATTER)

# 命令行日志
CONSOLE_HANDLER = logging.StreamHandler()
CONSOLE_HANDLER.setFormatter(FORMATTER)
CONSOLE_HANDLER.setLevel(logging.DEBUG)

##########################################
# 数据库配置
##########################################
DB_HOST=os.getenv("DB_HOST", "localhost")
DB_USER=os.getenv("DB_USER", "jfsok")
DB_PASSWORD=os.getenv("DB_PASSWORD", "iTbpamPcUYeqkY9k63rQ")
DB_DATABASE=os.getenv("DB_DATABASE", "llm_tools")
DB_CONFIG = {
    "user": DB_USER,
    "password": DB_PASSWORD,
    "host": DB_HOST,
    "database": DB_DATABASE
}

##########################################
# 大模型配置
##########################################
LLM_API_KEY=os.environ.get("DEEPSEEK_API_KEY")
LLM_BASE_URL="https://api.deepseek.com"

##########################################
# 淘股吧配置
##########################################
TGB_USERNAME = os.environ.get('TGB_USERNAME')
TGB_PASSWORD = os.environ.get('TGB_PASSWORD')
TGB_BASEURL = 'https://www.tgb.cn/'