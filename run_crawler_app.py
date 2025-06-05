#!/usr/bin/env python3
"""
招标公告爬虫应用启动脚本
"""

import sys
import subprocess
from pathlib import Path

def main():
    """启动Streamlit应用"""
    
    # 获取项目根目录
    project_root = Path(__file__).parent
    app_path = project_root / "src" / "biddingcsg" / "ui" / "app.py"
    
    # 检查文件是否存在
    if not app_path.exists():
        print(f"❌ 找不到应用文件: {app_path}")
        return 1
    
    # 启动Streamlit应用
    cmd = [
        sys.executable, "-m", "streamlit", "run", 
        str(app_path),
        "--server.port", "8501",
        "--server.headless", "true",
        "--server.address", "localhost"
    ]
    
    print("🚀 启动招标公告爬虫应用...")
    print(f"📁 应用路径: {app_path}")
    print(f"🌐 访问地址: http://localhost:8501")
    print("-" * 50)
    
    try:
        # 运行命令
        subprocess.run(cmd, cwd=str(project_root))
    except KeyboardInterrupt:
        print("\n⏹️ 应用已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 