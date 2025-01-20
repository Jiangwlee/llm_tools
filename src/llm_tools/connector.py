import mysql.connector
from mysql.connector.pooling import PooledMySQLConnection 
from llm_tools.config import DB_CONFIG

from llm_tools.logger import get_logger

log = get_logger()

# 连接到 MySQL 数据库
connection_pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="llm_tool_db_pool",
    pool_size=10,
    pool_reset_session=True,
    **DB_CONFIG
)



# 获取连接
def getConnection() -> PooledMySQLConnection:
    return connection_pool.get_connection()
