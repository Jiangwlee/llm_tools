import pytest
from llm_tools.connector import getConnection

def test_db_connection():
    try:
        conn = getConnection()
        assert conn.is_connected()
        
        # 创建游标对象
        cursor = conn.cursor()

        # 执行 SQL 查询
        cursor.execute("SELECT * FROM llm_tools.bidding_csg")

        # 获取结果
        result = cursor.fetchall()
        print(len(result))
    except Exception as e:
        pytest.fail(f"连接数据库失败：{e}")