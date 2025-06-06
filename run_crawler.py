#!/usr/bin/env python3
"""
招标公告爬虫应用启动脚本

使用方法:
    python run_crawler.py

功能:
    - 启动Streamlit Web应用
    - 提供爬虫配置界面
    - 实时显示爬取进度和日志
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

def main():
    """主函数"""
    
    # 抑制 Streamlit 的所有警告日志
    logging.getLogger("streamlit").setLevel(logging.ERROR)
    logging.getLogger("streamlit.runtime").setLevel(logging.ERROR)
    logging.getLogger("streamlit.runtime.state").setLevel(logging.ERROR)
    logging.getLogger("streamlit.runtime.fragment").setLevel(logging.ERROR)
    logging.getLogger("streamlit.runtime.scriptrunner").setLevel(logging.ERROR)
    logging.getLogger("streamlit.runtime.scriptrunner.script_runner").setLevel(logging.ERROR)
    
    # 抑制线程上下文警告
    import warnings
    warnings.filterwarnings("ignore", message=".*missing ScriptRunContext.*")
    
    # 获取项目根目录
    project_root = Path(__file__).parent
    
    # 检查依赖
    try:
        import streamlit
        import playwright
        import bs4
    except ImportError as e:
        print(f"❌ 缺少必要的依赖包: {e}")
        print("\n📦 请安装以下依赖:")
        print("pip install streamlit playwright beautifulsoup4")
        print("playwright install chromium")
        sys.exit(1)
    
    # 设置环境变量
    os.environ['PYTHONPATH'] = str(project_root)
    
    # Streamlit应用路径
    app_path = project_root / "src" / "biddingcsg" / "ui" / "app.py"
    
    if not app_path.exists():
        print(f"❌ 应用文件不存在: {app_path}")
        sys.exit(1)
    
    # 启动参数
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        str(app_path),
        "--server.port", "8501",
        "--server.address", "localhost",
        "--server.headless", "false",
        "--browser.gatherUsageStats", "false",
        "--theme.base", "light"
    ]
    
    print("🚀 启动招标公告爬虫应用...")
    print(f"📂 项目目录: {project_root}")
    print(f"🌐 访问地址: http://localhost:8501")
    print("🔄 正在启动服务器...")
    print("-" * 50)
    
    try:
        # 启动Streamlit应用
        subprocess.run(cmd, cwd=project_root, check=True)
    except KeyboardInterrupt:
        print("\n\n👋 应用已停止")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 启动失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 未知错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 