"""
系统检查模块 - 检查 Web UI 运行所需的依赖和环境
"""

import os
import sys
import subprocess
from pathlib import Path
import streamlit as st

def check_playwright_browsers():
    """检查 Playwright 浏览器是否已安装"""
    try:
        from playwright.sync_api import sync_playwright
        
        # 尝试启动浏览器来检查是否正确安装
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
                browser.close()
                return {"status": "success", "message": "Chromium 浏览器驱动正常"}
            except Exception as e:
                if "Executable doesn't exist" in str(e):
                    return {
                        "status": "error", 
                        "message": "Chromium 浏览器驱动未安装",
                        "solution": "运行: playwright install chromium"
                    }
                else:
                    return {"status": "error", "message": f"浏览器启动错误: {str(e)}"}
    except ImportError:
        return {"status": "error", "message": "Playwright 未安装"}


def check_database_connection():
    """检查数据库连接"""
    try:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
        sys.path.insert(0, project_root)
        
        from src.llm_tools.connector import getConnection
        conn = getConnection()
        if conn and conn.is_connected():
            conn.close()
            return {"status": "success", "message": "数据库连接正常"}
        else:
            return {"status": "error", "message": "数据库连接失败"}
    except Exception as e:
        return {"status": "error", "message": f"数据库连接错误: {str(e)}"}


def check_required_packages():
    """检查必要的 Python 包"""
    # 包名映射：{pip包名: (导入名, 描述)}
    required_packages = {
        'playwright': ('playwright', 'Playwright 浏览器自动化'),
        'beautifulsoup4': ('bs4', 'HTML 解析库'),
        'openai': ('openai', 'OpenAI API 客户端'),
        'pandas': ('pandas', '数据分析库'),
        'streamlit': ('streamlit', 'Web UI 框架'),
        'mysql-connector-python': ('mysql.connector', 'MySQL 数据库连接器')
    }
    
    results = {}
    for package, (import_name, description) in required_packages.items():
        try:
            __import__(import_name)
            results[package] = {"status": "success", "message": f"{description} - 已安装"}
        except ImportError:
            results[package] = {"status": "error", "message": f"{description} - 未安装"}
    
    return results


def run_playwright_install():
    """运行 Playwright 浏览器安装命令"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )
        
        if result.returncode == 0:
            return {"status": "success", "message": "Chromium 浏览器驱动安装成功"}
        else:
            return {"status": "error", "message": f"安装失败: {result.stderr}"}
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "安装超时，请手动执行: playwright install chromium"}
    except Exception as e:
        return {"status": "error", "message": f"安装过程出错: {str(e)}"}


def show_system_status():
    """在 Streamlit 中显示系统状态"""
    st.subheader("🔍 系统状态检查")
    
    # 检查 Python 包
    st.write("**📦 Python 包状态**")
    packages = check_required_packages()
    
    col1, col2 = st.columns(2)
    
    with col1:
        for package, result in list(packages.items())[:3]:
            if result["status"] == "success":
                st.success(f"✅ {package}")
            else:
                st.error(f"❌ {package}")
    
    with col2:
        for package, result in list(packages.items())[3:]:
            if result["status"] == "success":
                st.success(f"✅ {package}")
            else:
                st.error(f"❌ {package}")
    
    # 检查数据库连接
    st.write("**🗄️ 数据库连接**")
    db_result = check_database_connection()
    if db_result["status"] == "success":
        st.success(f"✅ {db_result['message']}")
    else:
        st.error(f"❌ {db_result['message']}")
    
    # 检查 Playwright 浏览器
    st.write("**🌐 Playwright 浏览器驱动**")
    browser_result = check_playwright_browsers()
    
    if browser_result["status"] == "success":
        st.success(f"✅ {browser_result['message']}")
    else:
        st.error(f"❌ {browser_result['message']}")
        
        if "solution" in browser_result:
            st.warning(f"💡 解决方案: {browser_result['solution']}")
            
            # 提供一键安装按钮
            if st.button("🔧 自动安装 Chromium 浏览器驱动", type="secondary"):
                with st.spinner("正在安装 Chromium 浏览器驱动..."):
                    install_result = run_playwright_install()
                    
                    if install_result["status"] == "success":
                        st.success(install_result["message"])
                        st.experimental_rerun()  # 重新运行页面以更新状态
                    else:
                        st.error(install_result["message"])


def show_troubleshooting_guide():
    """显示故障排除指南"""
    st.subheader("🛠️ 故障排除指南")
    
    with st.expander("🌐 Playwright 相关问题"):
        st.markdown("""
        **问题**: BrowserType.launch: Executable doesn't exist
        
        **原因**: Playwright 浏览器驱动未安装
        
        **解决方案**:
        1. 运行: `playwright install chromium`
        2. 或点击上方的"自动安装"按钮
        3. 确保网络连接正常（需要下载约87MB文件）
        
        **手动安装步骤**:
        ```bash
        # 在项目目录下运行
        playwright install chromium
        
        # 或安装所有浏览器
        playwright install
        ```
        """)
    
    with st.expander("🗄️ 数据库连接问题"):
        st.markdown("""
        **常见问题**:
        - MySQL 服务未启动
        - 连接参数配置错误
        - 数据库表未创建
        
        **解决方案**:
        1. 检查 MySQL 服务状态
        2. 验证 `src/llm_tools/connector.py` 中的连接参数
        3. 确保数据库 `llm_tools` 存在
        4. 确保表 `bidding_csg` 已创建
        """)
    
    with st.expander("📦 Python 包安装问题"):
        st.markdown("""
        **批量安装命令**:
        ```bash
        pip install -r requirements_webui.txt
        ```
        
        **单独安装**:
        ```bash
        pip install streamlit pandas playwright
        pip install beautifulsoup4 openai mysql-connector-python
        ```
        
        **虚拟环境问题**:
        - 确保在正确的虚拟环境中安装依赖
        - 检查 Python 版本兼容性（推荐 Python 3.8+）
        """)


if __name__ == "__main__":
    # 命令行运行时进行系统检查
    print("🔍 正在检查系统状态...\n")
    
    # 检查包状态
    print("📦 检查 Python 包:")
    packages = check_required_packages()
    for package, result in packages.items():
        status = "✅" if result["status"] == "success" else "❌"
        print(f"  {status} {package}: {result['message']}")
    
    # 检查数据库
    print("\n🗄️ 检查数据库连接:")
    db_result = check_database_connection()
    status = "✅" if db_result["status"] == "success" else "❌"
    print(f"  {status} {db_result['message']}")
    
    # 检查浏览器
    print("\n🌐 检查 Playwright 浏览器:")
    browser_result = check_playwright_browsers()
    status = "✅" if browser_result["status"] == "success" else "❌"
    print(f"  {status} {browser_result['message']}")
    
    if browser_result["status"] == "error" and "solution" in browser_result:
        print(f"  💡 解决方案: {browser_result['solution']}")
    
    print("\n✨ 系统检查完成!") 