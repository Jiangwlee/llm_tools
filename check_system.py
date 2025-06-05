#!/usr/bin/env python3
"""
南方电网招投标数据查询系统 - 系统环境检查工具

使用方法:
    python check_system.py

功能:
    - 检查所有必要的 Python 包
    - 验证 Playwright 浏览器驱动安装
    - 测试数据库连接
    - 提供自动修复建议
"""

import os
import sys
import subprocess

# 添加项目根目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def print_header():
    """打印标题"""
    print("=" * 60)
    print("🔍 南方电网招投标数据查询系统 - 环境检查工具")
    print("=" * 60)
    print()

def check_python_version():
    """检查 Python 版本"""
    print("🐍 检查 Python 版本:")
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        print(f"  ✅ Python {version.major}.{version.minor}.{version.micro} - 版本符合要求")
        return True
    else:
        print(f"  ❌ Python {version.major}.{version.minor}.{version.micro} - 版本过低，建议使用 Python 3.8+")
        return False

def check_packages():
    """检查必要的 Python 包"""
    print("\n📦 检查 Python 包:")
    
    # 包名映射：{pip包名: (导入名, 描述)}
    required_packages = {
        'streamlit': ('streamlit', 'Web UI 框架'),
        'pandas': ('pandas', '数据分析库'),
        'playwright': ('playwright', 'Playwright 浏览器自动化'),
        'beautifulsoup4': ('bs4', 'HTML 解析库'),
        'openai': ('openai', 'OpenAI API 客户端'),
        'mysql-connector-python': ('mysql.connector', 'MySQL 数据库连接器')
    }
    
    missing_packages = []
    
    for package, (import_name, description) in required_packages.items():
        try:
            __import__(import_name)
            print(f"  ✅ {package} - {description}")
        except ImportError:
            print(f"  ❌ {package} - {description} (未安装)")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n💡 安装缺失的包:")
        print(f"    pip install {' '.join(missing_packages)}")
    
    return len(missing_packages) == 0

def check_playwright_browsers():
    """检查 Playwright 浏览器驱动"""
    print("\n🌐 检查 Playwright 浏览器驱动:")
    
    try:
        from playwright.sync_api import sync_playwright
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                browser.close()
            print("  ✅ Chromium 浏览器驱动正常")
            return True
        except Exception as e:
            if "Executable doesn't exist" in str(e):
                print("  ❌ Chromium 浏览器驱动未安装")
                print("  💡 解决方案: playwright install chromium")
                
                # 询问是否自动安装
                try:
                    response = input("\n🤔 是否自动安装 Chromium 浏览器驱动? (y/n): ").lower().strip()
                    if response in ['y', 'yes', '是']:
                        print("  🔄 正在安装 Chromium 浏览器驱动...")
                        result = subprocess.run(
                            [sys.executable, "-m", "playwright", "install", "chromium"],
                            capture_output=True,
                            text=True
                        )
                        
                        if result.returncode == 0:
                            print("  ✅ Chromium 浏览器驱动安装成功")
                            return True
                        else:
                            print(f"  ❌ 安装失败: {result.stderr}")
                            return False
                    else:
                        print("  ⏭️ 跳过自动安装")
                        return False
                except KeyboardInterrupt:
                    print("\n  ⏹️ 用户取消安装")
                    return False
            else:
                print(f"  ❌ 浏览器启动错误: {str(e)}")
                return False
    except ImportError:
        print("  ❌ Playwright 未安装")
        return False

def check_database():
    """检查数据库连接"""
    print("\n🗄️ 检查数据库连接:")
    
    try:
        from src.llm_tools.connector import getConnection
        conn = getConnection()
        if conn and conn.is_connected():
            conn.close()
            print("  ✅ 数据库连接正常")
            return True
        else:
            print("  ❌ 数据库连接失败")
            return False
    except Exception as e:
        print(f"  ❌ 数据库连接错误: {str(e)}")
        print("  💡 请检查:")
        print("    - MySQL 服务是否运行")
        print("    - 连接参数配置是否正确")
        print("    - 数据库和表是否已创建")
        return False

def show_summary(results):
    """显示检查结果总结"""
    print("\n" + "=" * 60)
    print("📋 检查结果总结:")
    print("=" * 60)
    
    total_checks = len(results)
    passed_checks = sum(results.values())
    
    for check, result in results.items():
        status = "✅" if result else "❌"
        print(f"  {status} {check}")
    
    print(f"\n📊 总体状态: {passed_checks}/{total_checks} 项检查通过")
    
    if passed_checks == total_checks:
        print("🎉 恭喜！系统环境配置完整，可以正常使用 Web UI")
        print("\n🚀 启动 Web UI:")
        print("    python run_bidding_ui.py")
    else:
        print("⚠️ 系统环境存在问题，请根据上述建议进行修复")
        print("\n📚 更多帮助:")
        print("    - 查看 README_WebUI.md 文档")
        print("    - 在 Web UI 的'系统说明'页面查看详细故障排除指南")

def main():
    """主函数"""
    print_header()
    
    # 执行各项检查
    results = {
        "Python 版本": check_python_version(),
        "Python 包": check_packages(),
        "Playwright 浏览器驱动": check_playwright_browsers(),
        "数据库连接": check_database()
    }
    
    # 显示总结
    show_summary(results)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 检查已取消")
    except Exception as e:
        print(f"\n❌ 检查过程中出现错误: {str(e)}")
        print("请手动检查系统环境或联系技术支持") 