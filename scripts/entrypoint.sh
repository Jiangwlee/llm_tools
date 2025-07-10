#!/bin/bash
set -e

DB_PATH="/root/.llm_tools/data/db/llm_tools.db"

echo "🔍 检查数据库是否存在和初始化..."

if [ ! -f "$DB_PATH" ]; then
    echo "📦 创建数据库: $DB_PATH"
    /usr/local/bin/python /app/scripts/init_db.py
fi

echo "✅ 数据库初始化完成，启动主服务..."
exec "$@"  # 继续执行 CMD 指令（如 uvicorn 等）
