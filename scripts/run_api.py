import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

import argparse
import uvicorn

def main():
    parser = argparse.ArgumentParser(description="启动 llm_tools_v1 FastAPI 服务")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="监听地址")
    parser.add_argument("--port", type=int, default=8000, help="监听端口")
    parser.add_argument("--reload", action="store_true", help="自动重载（开发模式）")
    args = parser.parse_args()

    uvicorn.run(
        "llm_tools_v1.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        factory=False
    )

if __name__ == "__main__":
    main() 