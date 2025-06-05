"""
招标公告爬虫应用主入口
"""

import streamlit as st
import sys
from pathlib import Path

# 配置页面 - 必须是第一个Streamlit命令
st.set_page_config(
    page_title="招标公告爬虫",
    page_icon="🕷️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 使用绝对导入
from src.biddingcsg.ui.pages.crawler_config import CrawlerConfigPage

def main():
    """应用主函数"""
    
    # 添加自定义CSS
    st.markdown("""
    <style>
    .main > div {
        padding-top: 2rem;
    }
    
    .stForm {
        border: 1px solid #e1e5e9;
        border-radius: 0.5rem;
        padding: 1rem;
        background-color: #f8f9fa;
    }
    
    .stTextArea textarea {
        font-family: 'Courier New', monospace;
        font-size: 0.8rem;
        line-height: 1.4;
    }
    
    .crawler-status {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    
    .status-running {
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
    }
    
    .status-completed {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    
    .status-error {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 侧边栏（如果需要的话）
    with st.sidebar:
        st.markdown("### 🔧 工具选项")
        
        # 应用信息
        st.markdown("---")
        st.markdown("### ℹ️ 应用信息")
        st.info("""
        **招标公告爬虫 v1.0**
        
        🎯 **功能特点:**
        - 南方电网招标网站数据爬取
        - 智能去重避免重复下载
        - 实时日志显示爬取进度
        - 本地文件存储管理
        - 支持多种公告类型
        
        📁 **文件结构:**
        - `raw_html/` - 原始HTML文件
        - `metadata/` - 元数据JSON文件
        - `logs/` - 爬取日志文件
        """)
        
        # 帮助信息
        st.markdown("---")
        st.markdown("### 💡 使用说明")
        
        with st.expander("📖 快速开始"):
            st.markdown("""
            1. **配置搜索参数**
               - 输入关键词（如公司名称）
               - 设置最大爬取页数
               - 选择公告类型
            
            2. **设置输出目录**
               - 默认保存到 `output/bidding_data`
               - 可自定义输出路径
            
            3. **启动爬取**
               - 点击"开始爬取"按钮
               - 实时查看爬取日志
               - 等待任务完成
            
            4. **查看结果**
               - HTML文件按日期分目录保存
               - 元数据保存为JSON格式
               - 支持导出日志文件
            """)
        
        with st.expander("⚙️ 高级设置说明"):
            st.markdown("""
            - **请求间隔**: 防止被反爬虫检测，建议2-5秒
            - **启用去重**: 跳过已爬取的URL，提高效率
            - **无头模式**: 浏览器后台运行，推荐开启
            - **页面超时**: 网页加载最大等待时间
            """)
        
        with st.expander("⚠️ 注意事项"):
            st.markdown("""
            - 请遵守网站robots.txt规则
            - 不要设置过小的请求间隔
            - 大量爬取时建议在低峰期进行
            - 及时清理旧的HTML文件释放空间
            """)
    
    # 主页面内容
    try:
        # 创建并渲染爬虫配置页面
        page = CrawlerConfigPage()
        page.render()
        
    except Exception as e:
        st.error(f"应用启动失败: {e}")
        st.exception(e)
        
        # 提供错误恢复选项
        st.markdown("### 🔧 错误恢复")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 重新加载页面"):
                st.rerun()
        
        with col2:
            if st.button("🗑️ 清除缓存"):
                # 清除session state
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()

if __name__ == "__main__":
    main() 