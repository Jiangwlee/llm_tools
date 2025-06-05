#!/usr/bin/env python3
"""
南方电网招投标数据查询系统启动脚本

使用方法:
    python run_bidding_ui.py

或者直接运行:
    streamlit run src/llm_tools/web_ui/bidding_csg_ui.py
"""

import os
import sys
import subprocess

def main():
    """启动 Streamlit Web UI"""
    
    # 获取当前脚本所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Web UI 文件路径 (使用简化版)
    ui_file = os.path.join(current_dir, "src", "llm_tools", "web_ui", "bidding_csg_ui_simple.py")
    
    # 检查文件是否存在
    if not os.path.exists(ui_file):
        print(f"❌ 错误：找不到 Web UI 文件: {ui_file}")
        return 1
    
    # 检查 streamlit 是否安装
    try:
        import streamlit
        print("✅ Streamlit 已安装")
    except ImportError:
        print("❌ 错误：Streamlit 未安装")
        print("请运行: pip install streamlit")
        return 1
    
    print("🚀 启动南方电网招投标数据查询系统...")
    print(f"📁 UI 文件路径: {ui_file}")
    print("🌐 访问地址: http://localhost:8501")
    print("⏹️  按 Ctrl+C 停止服务")
    print("=" * 50)
    
    try:
        # 运行 Streamlit
        cmd = [sys.executable, "-m", "streamlit", "run", ui_file, "--server.port", "8501"]
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n👋 系统已停止")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"❌ 启动失败: {e}")
        return 1
    except Exception as e:
        print(f"❌ 未知错误: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 