import streamlit as st
import sys
import os
from datetime import datetime, date
import pandas as pd
import time

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
sys.path.insert(0, project_root)

from src.llm_tools.web_ui.bidding_csg_wrapper import safe_get_price_info, safe_query_price
from src.llm_tools.web_ui.system_check import show_system_status, show_troubleshooting_guide


def main():
    st.set_page_config(
        page_title="南方电网招投标数据查询系统",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 南方电网招投标数据查询系统")
    st.markdown("---")
    
    # 侧边栏导航
    st.sidebar.title("功能选择")
    page = st.sidebar.selectbox(
        "选择功能",
        ["数据下载", "价格查询", "系统说明"]
    )
    
    if page == "数据下载":
        show_download_page()
    elif page == "价格查询":
        show_query_page()
    else:
        show_help_page()


def show_download_page():
    """显示数据下载页面"""
    st.header("🔍 招投标数据下载")
    st.markdown("从南方电网招投标网站下载招投标公告和成交信息")
    
    col1, col2 = st.columns(2)
    
    with col1:
        keyword = st.text_input(
            "搜索关键字",
            placeholder="请输入要搜索的甲方单位名称，如：汕头供电局",
            help="输入甲方单位名称进行搜索"
        )
        
        bidding_type = st.selectbox(
            "公告类型",
            options=[None, 1, 2],
            format_func=lambda x: "全部类型" if x is None else ("投标报价" if x == 1 else "投标费率"),
            help="选择要下载的公告类型"
        )
    
    with col2:
        max_page = st.number_input(
            "最大爬取页数",
            min_value=1,
            max_value=100,
            value=5,
            help="限制爬取的最大页数，避免过度消耗资源"
        )
        
        end_date = st.date_input(
            "结束日期",
            value=None,
            help="爬取公告的结束日期，留空表示不限制"
        )
    
    # 下载按钮
    if st.button("🚀 开始下载数据", type="primary", use_container_width=True):
        if not keyword:
            st.error("请输入搜索关键字！")
            return
        
        download_data(keyword, bidding_type, max_page, end_date)


def download_data(keyword, bidding_type, max_page, end_date):
    """执行数据下载"""
    # 格式化结束日期
    end_date_str = end_date.strftime("%Y-%m-%d") if end_date else None
    
    # 显示参数信息
    st.info(f"""
    **下载参数：**
    - 搜索关键字: {keyword}
    - 公告类型: {"全部类型" if bidding_type is None else ("投标报价" if bidding_type == 1 else "投标费率")}
    - 最大页数: {max_page}
    - 结束日期: {end_date_str or "不限制"}
    """)
    
    # 显示重要提示
    st.warning("""
    ⚠️ **重要提示**：
    - 数据下载过程需要启动浏览器进行网页爬取
    - 此过程可能需要几分钟到几十分钟不等
    - 请耐心等待，不要关闭浏览器窗口或刷新此页面
    - 建议首次使用时设置较小的页数（如5页）进行测试
    """)
    
    # 创建状态容器
    status_container = st.empty()
    progress_container = st.empty()
    
    try:
        status_container.info("🔄 正在初始化下载任务...")
        
        # 显示进度条
        progress_bar = progress_container.progress(0)
        
        # 调用安全的下载函数
        status_container.info("🌐 正在启动浏览器和连接网站...")
        
        # 模拟进度更新
        progress_steps = [
            (20, "🔍 正在搜索招投标公告..."),
            (40, "📄 正在解析页面内容..."),
            (60, "💾 正在保存数据到数据库..."),
            (80, "🔍 正在分析中标信息..."),
            (90, "⏳ 即将完成...")
        ]
        
        for progress, message in progress_steps:
            progress_bar.progress(progress)
            status_container.info(message)
            time.sleep(1)
        
        # 执行实际的下载任务
        status_container.info("🚀 正在执行数据下载...")
        result = safe_get_price_info(keyword, bidding_type, max_page, end_date_str)
        
        progress_bar.progress(100)
        
        # 清除进度显示
        progress_container.empty()
        
        if result.get("success", False):
            status_container.success("✅ " + result["message"])
            st.balloons()
            
            # 显示下一步操作建议
            st.info("""
            🎉 **下载完成！**
            
            现在您可以：
            1. 切换到"价格查询"页面查看下载的数据
            2. 使用相同的关键字进行价格查询和分析
            3. 导出 CSV 格式的分析结果
            """)
        else:
            status_container.error("❌ " + result.get("message", "未知错误"))
            show_troubleshooting()
            
    except Exception as e:
        progress_container.empty()
        status_container.error(f"❌ 系统错误: {str(e)}")
        
        # 显示详细错误信息
        with st.expander("🐛 详细错误信息"):
            st.code(str(e))
            st.markdown("""
            **如果您看到此错误，请：**
            1. 截图保存错误信息
            2. 尝试减少爬取页数后重试
            3. 检查网络连接是否正常
            4. 联系系统管理员
            """)


def show_troubleshooting():
    """显示故障排除建议"""
    with st.expander("🔧 故障排除建议"):
        st.markdown("""
        **常见问题及解决方案：**
        
        1. **网络连接问题**
           - 检查网络连接是否稳定
           - 尝试使用VPN或更换网络环境
        
        2. **浏览器启动失败**
           - 确保系统有足够的内存空间
           - 尝试重启应用程序
           - 检查是否安装了必要的浏览器驱动
        
        3. **反爬虫检测**
           - 减少爬取页数（建议从5页开始测试）
           - 稍后重试（间隔1-2小时）
        
        4. **数据库连接问题**
           - 检查数据库服务是否正常运行
           - 验证数据库连接配置
        
        5. **Playwright 相关问题**
           - 运行: playwright install chromium
           - 确保在虚拟环境中安装了所有依赖
        """)


def show_query_page():
    """显示价格查询页面"""
    st.header("💰 成交价格查询")
    st.markdown("查询已下载的招投标成交价格信息")
    
    col1, col2 = st.columns(2)
    
    with col1:
        keyword = st.text_input(
            "查询关键字",
            placeholder="请输入要查询的甲方单位名称",
            help="输入甲方单位名称进行查询"
        )
    
    with col2:
        bidding_type = st.selectbox(
            "查询类型",
            options=[1, 2],
            format_func=lambda x: "投标报价" if x == 1 else "投标费率",
            help="选择要查询的价格类型"
        )
    
    # 查询按钮
    if st.button("🔍 查询价格", type="primary", use_container_width=True):
        if not keyword:
            st.error("请输入查询关键字！")
            return
        
        query_data(keyword, bidding_type)


def query_data(keyword, bidding_type):
    """执行数据查询"""
    with st.spinner("正在查询数据..."):
        try:
            # 调用安全的查询函数
            result = safe_query_price(keyword, bidding_type)
            
            if result.get("success", False):
                st.success("✅ " + result["message"])
                
                # 读取生成的 CSV 文件
                csv_file = "bidding_csg.csv"
                if os.path.exists(csv_file):
                    df = pd.read_csv(csv_file, encoding='utf-8')
                    
                    # 显示数据统计
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("总记录数", len(df))
                    with col2:
                        unique_projects = df['项目名称'].nunique() if '项目名称' in df.columns else 0
                        st.metric("项目数量", unique_projects)
                    with col3:
                        unique_companies = df['甲方'].nunique() if '甲方' in df.columns else 0
                        st.metric("甲方数量", unique_companies)
                    
                    # 显示数据表格
                    st.subheader("📋 查询结果")
                    st.dataframe(df, use_container_width=True)
                    
                    # 提供下载链接
                    csv_data = df.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label="📥 下载 CSV 文件",
                        data=csv_data,
                        file_name=f"bidding_csg_{keyword}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                    
                    # 数据可视化（如果有价格数据）
                    if bidding_type == 1 and '中标价格(万元)' in df.columns:
                        show_price_analysis(df)
                        
                else:
                    st.warning("未找到查询结果文件，请先执行数据下载。")
            else:
                st.error("❌ " + result.get("message", "查询失败"))
                
        except Exception as e:
            st.error(f"❌ 查询过程中出现错误: {str(e)}")


def show_price_analysis(df):
    """显示价格分析图表"""
    st.subheader("📈 价格分析")
    
    # 过滤掉无效价格数据
    df_clean = df.dropna(subset=['中标价格(万元)', '最高限价(万元)'])
    df_clean = df_clean[
        (pd.to_numeric(df_clean['中标价格(万元)'], errors='coerce') > 0) &
        (pd.to_numeric(df_clean['最高限价(万元)'], errors='coerce') > 0)
    ]
    
    if len(df_clean) > 0:
        # 转换为数值类型
        df_clean['中标价格(万元)'] = pd.to_numeric(df_clean['中标价格(万元)'], errors='coerce')
        df_clean['最高限价(万元)'] = pd.to_numeric(df_clean['最高限价(万元)'], errors='coerce')
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 价格对比柱状图
            st.subheader("价格对比")
            chart_data = df_clean[['项目名称', '中标价格(万元)', '最高限价(万元)']].head(10)
            st.bar_chart(chart_data.set_index('项目名称'))
        
        with col2:
            # 价格分布统计
            st.subheader("价格统计")
            avg_bid = df_clean['中标价格(万元)'].mean()
            avg_limit = df_clean['最高限价(万元)'].mean()
            savings_rate = ((avg_limit - avg_bid) / avg_limit * 100) if avg_limit > 0 else 0
            
            st.metric("平均中标价格", f"{avg_bid:.2f} 万元")
            st.metric("平均最高限价", f"{avg_limit:.2f} 万元")
            st.metric("平均节约率", f"{savings_rate:.2f}%")
    else:
        st.info("暂无有效的价格数据进行分析")


def show_help_page():
    """显示系统说明页面"""
    st.header("📖 系统说明")
    
    st.markdown("""
    ## 🎯 系统功能
    
    本系统提供南方电网招投标数据的自动化下载和查询功能，主要包括：
    
    ### 1. 数据下载功能
    - 从南方电网招投标网站自动爬取招投标公告
    - 支持按关键字搜索特定甲方单位的招投标信息
    - 支持投标报价和投标费率两种类型的公告
    - 自动提取和分析中标价格信息
    
    ### 2. 价格查询功能
    - 查询已下载的招投标成交价格数据
    - 生成详细的价格对比分析报告
    - 支持数据可视化展示
    - 提供 CSV 格式数据导出
    
    ## 📋 使用步骤
    
    1. **数据下载**：
       - 在"数据下载"页面输入搜索关键字（如：汕头供电局）
       - 选择公告类型（投标报价/投标费率）
       - 设置爬取页数（建议首次使用设置为5页）
       - 点击"开始下载数据"按钮
    
    2. **价格查询**：
       - 在"价格查询"页面输入查询关键字
       - 选择查询类型
       - 点击"查询价格"按钮
       - 查看结果并下载数据
    
    ## ⚠️ 重要提示
    
    - **首次使用**：建议先用较小的页数（5页）进行测试
    - **网络环境**：爬取数据需要良好的网络环境
    - **系统资源**：爬取过程会启动浏览器实例，请确保系统有足够的内存
    - **数据时效性**：下载的数据会保存到数据库中，避免重复爬取
    
    ## 🔧 技术特性
    
    - 使用 Playwright 模拟浏览器访问，规避反爬虫检测
    - 集成大语言模型进行智能信息提取
    - 支持数据库存储，避免重复爬取
    - 多进程架构，避免事件循环冲突
    
    """)
    
    # 使用系统检查模块
    show_system_status()
    
    # 显示故障排除指南
    show_troubleshooting_guide()


if __name__ == "__main__":
    main() 