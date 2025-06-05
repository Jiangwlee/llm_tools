import streamlit as st
import sys
import os
from datetime import datetime, date
import pandas as pd
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
import time

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
sys.path.insert(0, project_root)

from src.llm_tools.web_ui.bidding_csg_wrapper import safe_get_price_info, safe_query_price, StreamlitBiddingCSG


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


def run_crawler_safely(keyword, bidding_type, max_page, end_date_str):
    """安全地运行爬虫，使用多进程避免事件循环冲突"""
    try:
        # 使用安全的包装器函数
        result = safe_get_price_info(keyword, bidding_type, max_page, end_date_str)
        return result
    except Exception as e:
        return {"success": False, "message": f"下载过程中出现错误: {str(e)}"}


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
            max_value=1000,
            value=10,
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
        - 如果遇到问题，可以尝试减少爬取页数或稍后重试
        """)
        
        # 创建状态容器
        status_container = st.empty()
        progress_container = st.empty()
        
        try:
            # 初始化状态
            status_container.info("🔄 正在初始化下载任务...")
            
            # 使用线程池执行器运行爬虫任务
            with ThreadPoolExecutor(max_workers=1) as executor:
                status_container.info("🌐 正在启动浏览器和连接网站...")
                
                # 提交任务到线程池
                future = executor.submit(run_crawler_safely, keyword, bidding_type, max_page, end_date_str)
                
                # 显示进度指示器
                progress_bar = progress_container.progress(0)
                progress_text = st.empty()
                
                # 模拟进度更新（因为无法获取实际进度）
                for i in range(100):
                    if future.done():
                        break
                    progress_bar.progress(i + 1)
                    if i < 10:
                        progress_text.text("🔍 正在搜索招投标公告...")
                    elif i < 30:
                        progress_text.text("📄 正在解析页面内容...")
                    elif i < 60:
                        progress_text.text("💾 正在保存数据到数据库...")
                    elif i < 90:
                        progress_text.text("🔍 正在分析中标信息...")
                    else:
                        progress_text.text("⏳ 即将完成...")
                    time.sleep(0.5)
                
                # 等待任务完成
                result = future.result(timeout=1800)  # 30分钟超时
                
                # 清除进度显示
                progress_container.empty()
                progress_text.empty()
                
                if result["success"]:
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
                    status_container.error("❌ " + result["message"])
                    
                    # 显示故障排除建议
                    with st.expander("🔧 故障排除建议"):
                        st.markdown("""
                        **常见问题及解决方案：**
                        
                        1. **网络连接问题**
                           - 检查网络连接是否稳定
                           - 尝试使用VPN或更换网络环境
                        
                        2. **浏览器启动失败**
                           - 确保系统有足够的内存空间
                           - 尝试重启应用程序
                        
                        3. **反爬虫检测**
                           - 减少爬取页数
                           - 稍后重试（间隔1-2小时）
                        
                        4. **数据库连接问题**
                           - 检查数据库服务是否正常运行
                           - 验证数据库连接配置
                        """)
                        
        except Exception as e:
            progress_container.empty()
            status_container.error(f"❌ 系统错误: {str(e)}")
            
            # 显示详细错误信息
            with st.expander("🐛 详细错误信息"):
                st.code(str(e))
                st.markdown("""
                **如果您看到此错误，请：**
                1. 截图保存错误信息
                2. 联系系统管理员
                3. 或尝试重启应用程序后再试
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
        
        with st.spinner("正在查询数据..."):
            try:
                # 调用查询函数
                result = safe_query_price(keyword, bidding_type)
                
                # 读取生成的 CSV 文件
                csv_file = "bidding_csg.csv"
                if os.path.exists(csv_file):
                    df = pd.read_csv(csv_file, encoding='utf-8')
                    
                    st.success(f"✅ 查询完成！共找到 {len(df)} 条记录")
                    
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
       - 设置爬取页数和结束日期
       - 点击"开始下载数据"按钮
    
    2. **价格查询**：
       - 在"价格查询"页面输入查询关键字
       - 选择查询类型
       - 点击"查询价格"按钮
       - 查看结果并下载数据
    
    ## ⚠️ 注意事项
    
    - 首次使用请先执行数据下载，再进行价格查询
    - 爬取数据需要一定时间，请耐心等待
    - 建议合理设置爬取页数，避免过度消耗系统资源
    - 系统已内置反爬虫检测规避机制
    
    ## 🔧 技术特性
    
    - 使用 Playwright 模拟浏览器访问，规避反爬虫检测
    - 集成大语言模型进行智能信息提取
    - 支持数据库存储，避免重复爬取
    - 提供直观的 Web 界面操作
    
    ## 📞 技术支持
    
    如有问题或建议，请联系系统管理员。
    """)
    
    # 系统状态检查
    st.subheader("🔍 系统状态")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 检查数据库连接
        try:
            from src.llm_tools.connector import getConnection
            conn = getConnection()
            if conn and conn.is_connected():
                st.success("✅ 数据库连接正常")
                conn.close()
            else:
                st.error("❌ 数据库连接异常")
        except Exception as e:
            st.error(f"❌ 数据库连接错误: {str(e)}")
    
    with col2:
        # 检查必要的依赖包
        required_packages = ['playwright', 'beautifulsoup4', 'openai', 'pandas']
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing_packages.append(package)
        
        if not missing_packages:
            st.success("✅ 依赖包完整")
        else:
            st.error(f"❌ 缺少依赖包: {', '.join(missing_packages)}")


if __name__ == "__main__":
    main() 