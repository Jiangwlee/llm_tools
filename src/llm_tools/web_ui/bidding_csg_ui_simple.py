import streamlit as st
import sys
import os
from datetime import datetime, date
import pandas as pd
import time
import threading
from queue import Queue, Empty

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
sys.path.insert(0, project_root)

from src.llm_tools.web_ui.bidding_csg_wrapper import safe_get_price_info, safe_query_price
from src.llm_tools.web_ui.system_check import show_system_status, show_troubleshooting_guide
from src.llm_tools.web_ui.config_manager import get_config_manager, show_model_selector, show_advanced_settings
from src.llm_tools.logger import get_logger

# 获取日志记录器
logger = get_logger()

# 初始化会话状态
if 'page_url_status' not in st.session_state:
    st.session_state.page_url_status = "未开始"
if 'llm_inference_status' not in st.session_state:
    st.session_state.llm_inference_status = "未开始"
if 'status_queue' not in st.session_state:
    st.session_state.status_queue = Queue()
if 'llm_queue' not in st.session_state:
    st.session_state.llm_queue = Queue()


def show_status_panels():
    """显示状态面板"""
    st.markdown("### 📊 实时状态监控")
    
    # 自动刷新容器
    status_container = st.container()
    
    with status_container:
        col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🌐 页面访问状态")
        page_status_container = st.empty()
        
        # 检查是否有新的页面状态更新
        try:
            while True:
                status_update = st.session_state.status_queue.get_nowait()
                st.session_state.page_url_status = status_update
        except Empty:
            pass
        
        # 显示当前页面状态
        if st.session_state.page_url_status == "未开始":
            page_status_container.info("🟡 等待开始...")
        elif st.session_state.page_url_status.startswith("http"):
            # 缩短显示的URL长度
            url_display = st.session_state.page_url_status
            if len(url_display) > 50:
                url_display = url_display[:47] + "..."
            page_status_container.success(f"🟢 访问中:\n`{url_display}`")
        elif "完成" in st.session_state.page_url_status:
            page_status_container.success(f"✅ {st.session_state.page_url_status}")
        elif "错误" in st.session_state.page_url_status or "异常" in st.session_state.page_url_status:
            page_status_container.error(f"❌ {st.session_state.page_url_status}")
        elif "失败" in st.session_state.page_url_status:
            page_status_container.warning(f"⚠️ {st.session_state.page_url_status}")
        else:
            page_status_container.info(f"🔄 {st.session_state.page_url_status}")
    
    with col2:
        st.markdown("#### 🤖 AI推理状态")
        llm_status_container = st.empty()
        
        # 检查是否有新的LLM状态更新
        try:
            while True:
                llm_update = st.session_state.llm_queue.get_nowait()
                st.session_state.llm_inference_status = llm_update
        except Empty:
            pass
        
        # 显示当前LLM状态
        status = st.session_state.llm_inference_status
        if status == "未开始":
            llm_status_container.info("🟡 等待推理...")
        elif any(word in status for word in ["推理中", "分析", "处理中", "初始化", "提取", "模型", "AI", "💭", "📝", "🚀"]):
            llm_status_container.warning(f"🟠 {status}")
        elif any(word in status for word in ["完成", "成功", "✅"]):
            llm_status_container.success(f"✅ {status}")
        elif any(word in status for word in ["错误", "失败", "异常", "❌"]):
            llm_status_container.error(f"❌ {status}")
        elif "中断" in status or "⚠️" in status:
            llm_status_container.warning(f"⚠️ {status}")
        else:
            llm_status_container.info(f"🔄 {status}")
    
    # 状态控制按钮
    col_a, col_b, col_c = st.columns(3)
    
    with col_a:
        if st.button("🔄 刷新状态", help="手动刷新状态显示"):
            st.rerun()
    
    with col_b:
        if st.button("🧹 清空状态", help="清空当前状态显示"):
            st.session_state.page_url_status = "未开始"
            st.session_state.llm_inference_status = "未开始"
            # 清空队列
            while not st.session_state.status_queue.empty():
                try:
                    st.session_state.status_queue.get_nowait()
                except Empty:
                    break
            while not st.session_state.llm_queue.empty():
                try:
                    st.session_state.llm_queue.get_nowait()
                except Empty:
                    break
            st.rerun()
    
    with col_c:
        # 显示调试信息
        if st.checkbox("显示调试信息"):
            st.caption(f"页面状态: `{st.session_state.page_url_status}`")
            st.caption(f"LLM状态: `{st.session_state.llm_inference_status}`")
    
    st.markdown("---")


def update_page_status(message):
    """更新页面访问状态"""
    try:
        st.session_state.status_queue.put(message)
        st.session_state.page_url_status = message  # 直接更新状态
        logger.info(f"页面状态更新: {message}")
    except Exception as e:
        logger.error(f"更新页面状态失败: {e}")


def update_llm_status(message):
    """更新LLM推理状态"""
    try:
        st.session_state.llm_queue.put(message)
        st.session_state.llm_inference_status = message  # 直接更新状态
        logger.info(f"LLM状态更新: {message}")
    except Exception as e:
        logger.error(f"更新LLM状态失败: {e}")


def main():
    st.set_page_config(
        page_title="南方电网招投标数据查询系统",
        page_icon="📊",
        layout="wide"
    )
    
    # 获取配置管理器
    config_manager = get_config_manager()
    
    st.title("📊 南方电网招投标数据查询系统")
    st.markdown("---")
    
    # 侧边栏导航
    st.sidebar.title("功能选择")
    page = st.sidebar.selectbox(
        "选择功能",
        ["数据下载", "价格查询", "系统说明"]
    )
    
    # 显示模型选择器
    show_model_selector(config_manager)
    
    # 显示高级设置
    show_advanced_settings(config_manager)
    
    if page == "数据下载":
        show_download_page(config_manager)
    elif page == "价格查询":
        show_query_page(config_manager)
    else:
        show_help_page(config_manager)


def show_download_page(config_manager):
    """显示数据下载页面"""
    st.header("🔍 招投标数据下载")
    st.markdown("从南方电网招投标网站下载招投标公告和成交信息")
    
    # 显示当前使用的模型
    current_model = config_manager.get_current_model_info()
    if current_model["available"]:
        st.info(f"🤖 当前使用模型: {current_model['display_name']}")
    else:
        st.warning(f"⚠️ 当前模型未配置API密钥: {current_model['display_name']}")
    
    # 显示状态面板
    show_status_panels()
    
    col1, col2 = st.columns(2)
    
    with col1:
        keyword = st.text_input(
            "搜索关键字",
            placeholder="请输入要搜索的甲方单位名称，如：汕头供电局",
            help="输入甲方单位名称进行搜索"
        )
        
        # 从配置中获取默认公告类型
        default_bidding_type = config_manager.get("download_settings.default_bidding_type")
        bidding_type = st.selectbox(
            "公告类型",
            options=[None, 1, 2],
            format_func=lambda x: "全部类型" if x is None else ("投标报价" if x == 1 else "投标费率"),
            index=0 if default_bidding_type is None else (1 if default_bidding_type == 1 else 2),
            help="选择要下载的公告类型"
        )
    
    with col2:
        # 从配置中获取默认最大页数
        default_max_pages = config_manager.get("download_settings.default_max_pages", 5)
        max_page = st.number_input(
            "最大爬取页数",
            min_value=1,
            max_value=100,
            value=default_max_pages,
            help="限制爬取的最大页数，避免过度消耗资源"
        )
        
        end_date = st.date_input(
            "结束日期",
            value=None,
            help="爬取公告的结束日期，留空表示不限制"
        )
    
    # 下载按钮
    col_btn1, col_btn2 = st.columns([3, 1])
    
    with col_btn1:
        if st.button("🚀 开始下载数据", type="primary", use_container_width=True):
            if not keyword:
                st.error("请输入搜索关键字！")
                return
            
            download_data(keyword, bidding_type, max_page, end_date)
    
    with col_btn2:
        if st.button("🧪 测试AI", use_container_width=True):
            # 测试实时LLM streaming
            test_llm_streaming()


def test_llm_streaming():
    """测试LLM实时streaming功能"""
    st.markdown("### 🧪 AI实时推理测试")
    
    # 创建状态显示容器
    test_status_area = st.empty()
    test_progress_area = st.empty()
    test_result_area = st.empty()
    
    try:
        from src.llm_tools.tools.bidding_csg import LLMHelper
        
        # 状态回调函数
        def test_status_callback(message):
            update_llm_status(message)
            with test_status_area.container():
                st.info(f"🤖 AI状态: {message}")
        
        # 设置全局回调
        LLMHelper.set_global_status_callback(test_status_callback)
        
        update_page_status("🧪 开始AI测试...")
        update_llm_status("🚀 准备AI测试...")
        
        with test_progress_area.container():
            progress = st.progress(0)
            progress.progress(20)
        
        # 测试基本信息提取
        test_text = "南方电网广东汕头供电局2024年变电站设备检修项目招标公告，预算1000万元，工期6个月，投标截止时间2024年12月31日。"
        
        with test_status_area.container():
            st.info("🔍 测试基本信息提取...")
        
        result1 = LLMHelper.llm_basic_info_extract(test_text)
        
        with test_progress_area.container():
            progress.progress(60)
        
        # 测试内容总结
        with test_status_area.container():
            st.info("📝 测试内容总结...")
        
        result2 = LLMHelper.llm_summary("这是一个电力设备检修项目的招标，包含变压器检修、开关设备检修等内容。项目预算充足，技术要求较高。")
        
        with test_progress_area.container():
            progress.progress(100)
        
        # 显示结果
        with test_result_area.container():
            st.success("🎉 AI测试完成！")
            
            if result1:
                st.markdown("**基本信息提取结果：**")
                st.text_area("结果1", result1, height=100)
            
            if result2:
                st.markdown("**内容总结结果：**")
                st.text_area("结果2", result2, height=100)
        
        # 更新最终状态
        update_page_status("✅ AI测试完成")
        update_llm_status("✅ 所有测试通过")
        
    except Exception as e:
        with test_result_area.container():
            st.error(f"❌ AI测试失败: {str(e)}")
        
        update_page_status("❌ AI测试失败")
        update_llm_status("❌ 测试异常")
        
    finally:
        # 清除回调
        try:
            LLMHelper.clear_global_status_callback()
        except:
            pass
        
        # 3秒后清除测试界面
        import time
        time.sleep(3)
        test_status_area.empty()
        test_progress_area.empty()


def download_data(keyword, bidding_type, max_page, end_date):
    """执行数据下载"""
    # 重置状态
    update_page_status("初始化中...")
    update_llm_status("等待推理...")
    
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
        update_page_status("启动浏览器中...")
        
        # 显示进度条
        progress_bar = progress_container.progress(0)
        
        # 调用安全的下载函数
        status_container.info("🌐 正在启动浏览器和连接网站...")
        update_page_status("https://www.bidding.csg.cn/ - 连接中...")
        
        # 模拟进度更新并更新状态
        progress_steps = [
            (20, "🔍 正在搜索招投标公告...", f"https://www.bidding.csg.cn/dbsearch.jspx?q={keyword}", "搜索页面解析中..."),
            (40, "📄 正在解析页面内容...", f"第1页 - 解析中", "提取基本信息推理中..."),
            (60, "💾 正在保存数据到数据库...", f"第{min(2, max_page)}页 - 解析中", "内容总结推理中..."),
            (80, "🔍 正在分析中标信息...", f"第{min(3, max_page)}页 - 解析中", "价格信息提取推理中..."),
            (90, "⏳ 即将完成...", "数据处理完成", "推理任务完成")
        ]
        
        for progress, message, page_status, llm_status in progress_steps:
            progress_bar.progress(progress)
            status_container.info(message)
            update_page_status(page_status)
            update_llm_status(llm_status)
            time.sleep(1)
        
        # 执行实际的下载任务
        status_container.info("🚀 正在执行数据下载...")
        update_page_status("🚀 准备启动...")
        update_llm_status("⏳ 等待开始...")
        
        # 先进行AI功能测试，确保AI能正常工作
        st.info("🧪 首先测试AI功能连通性...")
        
        try:
            from src.llm_tools.tools.bidding_csg import LLMHelper
            
            # 设置临时状态回调
            def temp_callback(message):
                update_llm_status(message)
                status_container.info(f"🤖 {message}")
            
            LLMHelper.set_global_status_callback(temp_callback)
            
            # 简单测试
            test_result = LLMHelper.llm_summary("测试AI连通性")
            
            if test_result:
                st.success("✅ AI功能测试通过，开始数据下载...")
                update_llm_status("✅ AI连通性正常")
            else:
                st.warning("⚠️ AI功能可能存在问题，但继续执行下载...")
                update_llm_status("⚠️ AI连通性异常")
                
            LLMHelper.clear_global_status_callback()
            
        except Exception as ai_error:
            st.warning(f"⚠️ AI测试失败: {ai_error}，继续执行下载...")
            update_llm_status(f"❌ AI测试失败: {str(ai_error)}")
        
        # 创建实时状态回调
        def process_status_callback(status_type, message):
            """处理进程间状态更新"""
            if status_type == "page":
                update_page_status(message)
                status_container.info(f"🌐 {message}")
            elif status_type == "llm":
                update_llm_status(message)
                status_container.info(f"🤖 {message}")
        
        # 更新状态为准备下载
        update_page_status("🌐 启动浏览器...")
        update_llm_status("🚀 初始化AI模型...")
        
        try:
            result = safe_get_price_info(
                keyword, 
                bidding_type, 
                max_page, 
                end_date_str, 
                status_callback=process_status_callback
            )
        except Exception as e:
            update_page_status(f"❌ 下载异常: {str(e)}")
            update_llm_status("❌ 处理中断")
            result = {"success": False, "message": f"下载过程中出现错误: {str(e)}"}
        
        progress_bar.progress(100)
        
        # 清除进度显示
        progress_container.empty()
        
        if result.get("success", False):
            status_container.success("✅ " + result["message"])
            update_page_status("下载完成")
            update_llm_status("推理完成")
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
            update_page_status("下载失败")
            update_llm_status("推理中断")
            show_troubleshooting()
            
    except Exception as e:
        progress_container.empty()
        status_container.error(f"❌ 系统错误: {str(e)}")
        update_page_status(f"错误: {str(e)}")
        update_llm_status("推理失败")
        
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


def show_query_page(config_manager):
    """显示价格查询页面"""
    st.header("💰 成交价格查询")
    st.markdown("查询已下载的招投标成交价格信息")
    
    # 显示当前使用的模型
    current_model = config_manager.get_current_model_info()
    if current_model["available"]:
        st.info(f"🤖 当前使用模型: {current_model['display_name']}")
    else:
        st.warning(f"⚠️ 当前模型未配置API密钥: {current_model['display_name']}")
    
    # 显示状态面板
    show_status_panels()
    
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
        
        query_data(keyword, bidding_type, config_manager)


def query_data(keyword, bidding_type, config_manager):
    """执行数据查询"""
    # 重置状态
    update_page_status("查询初始化...")
    update_llm_status("准备数据分析...")
    
    with st.spinner("正在查询数据..."):
        try:
            # 设置全局LLM状态回调
            from src.llm_tools.tools.bidding_csg import LLMHelper
            
            def llm_status_callback(status_message):
                update_llm_status(status_message)
            
            LLMHelper.set_global_status_callback(llm_status_callback)
            
            # 调用安全的查询函数
            update_page_status("正在查询数据库...")
            update_llm_status("分析查询参数...")
            
            try:
                result = safe_query_price(keyword, bidding_type)
            finally:
                # 清除全局回调
                LLMHelper.clear_global_status_callback()
            
            if result.get("success", False):
                st.success("✅ " + result["message"])
                update_page_status("数据查询成功")
                update_llm_status("数据分析完成")
                
                # 读取生成的 CSV 文件
                csv_file = "bidding_csg.csv"
                if os.path.exists(csv_file):
                    update_page_status("读取CSV文件...")
                    df = pd.read_csv(csv_file, encoding='utf-8')
                    
                    # 应用结果限制配置
                    result_limit = config_manager.get("query_settings.result_limit", 100)
                    if len(df) > result_limit:
                        st.warning(f"⚠️ 查询结果超过设置的限制({result_limit}条)，仅显示前{result_limit}条记录")
                        df_display = df.head(result_limit)
                    else:
                        df_display = df
                    
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
                    st.dataframe(df_display, use_container_width=True)
                    
                    # 提供下载链接
                    csv_data = df.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label="📥 下载 CSV 文件",
                        data=csv_data,
                        file_name=f"bidding_csg_{keyword}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                    
                    # 数据可视化（如果启用了图表显示）
                    if (config_manager.get("query_settings.show_charts", True) and 
                        bidding_type == 1 and '中标价格(万元)' in df.columns):
                        update_llm_status("生成数据图表...")
                        show_price_analysis(df_display)
                        update_llm_status("图表生成完成")
                        
                else:
                    st.warning("未找到查询结果文件，请先执行数据下载。")
                    update_page_status("未找到CSV文件")
                    update_llm_status("无数据可分析")
            else:
                st.error("❌ " + result.get("message", "查询失败"))
                update_page_status("查询失败")
                update_llm_status("分析失败")
                
        except Exception as e:
            st.error(f"❌ 查询过程中出现错误: {str(e)}")
            update_page_status(f"查询异常: {str(e)}")
            update_llm_status("分析异常")


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


def test_current_model_connection(config_manager):
    """测试当前模型连接"""
    logger.info("开始测试当前模型连接")
    
    with st.spinner("正在测试当前模型连接..."):
        try:
            current_model = config_manager.get_current_model_info()
            logger.info(f"测试模型: {current_model['provider']} - {current_model['model']}")
            
            test_result = config_manager.test_model_connection()
            
            if test_result["success"]:
                st.success(f"✅ {test_result['message']}")
                
                # 显示详细信息
                with st.expander("📊 连接详情"):
                    st.write(f"**提供商**: {test_result['provider_name']}")
                    st.write(f"**响应时间**: {test_result.get('response_time', 'N/A')}ms")
                    st.write(f"**模型回复**: {test_result.get('response_content', 'N/A')}")
                
                logger.info(f"模型连接测试成功: {test_result['provider_name']}, 响应时间: {test_result.get('response_time', 'N/A')}ms")
                
            else:
                st.error(f"❌ {test_result['message']}")
                st.warning(f"**详情**: {test_result['details']}")
                logger.error(f"模型连接测试失败: {test_result['provider']} - {test_result['message']} - {test_result['details']}")
                
                # 显示解决建议
                if "API密钥未配置" in test_result['message']:
                    st.info(f"💡 **解决方案**: 请设置环境变量 `{test_result['details'].split(': ')[1]}`")
                elif "连接失败" in test_result['message']:
                    st.info("💡 **解决方案**: 请检查网络连接和API服务状态")
                    
        except Exception as e:
            st.error(f"❌ 连接测试异常: {str(e)}")
            logger.error(f"连接测试异常: {str(e)}")


def test_all_models_connection(config_manager):
    """测试所有模型连接"""
    logger.info("开始测试所有模型连接")
    
    available_models = config_manager.get_available_models()
    providers = list(available_models.keys())
    
    st.info(f"开始测试 {len(providers)} 个模型提供商的连接状态...")
    
    # 创建结果表格
    results = []
    
    for i, provider in enumerate(providers):
        provider_name = available_models[provider]["name"]
        
        # 显示进度
        progress = (i + 1) / len(providers)
        st.progress(progress, text=f"正在测试 {provider_name}...")
        
        logger.info(f"测试提供商: {provider}")
        
        try:
            test_result = config_manager.test_model_connection(provider)
            
            results.append({
                "提供商": provider_name,
                "状态": "✅ 成功" if test_result["success"] else "❌ 失败",
                "响应时间": f"{test_result.get('response_time', 'N/A')}ms" if test_result["success"] else "N/A",
                "详情": test_result.get("details", test_result["message"])
            })
            
            if test_result["success"]:
                logger.info(f"提供商 {provider} 连接成功，响应时间: {test_result.get('response_time', 'N/A')}ms")
            else:
                logger.warning(f"提供商 {provider} 连接失败: {test_result['message']}")
                
        except Exception as e:
            results.append({
                "提供商": provider_name,
                "状态": "❌ 异常",
                "响应时间": "N/A",
                "详情": str(e)
            })
            logger.error(f"提供商 {provider} 测试异常: {str(e)}")
    
    # 显示结果
    st.subheader("📊 连接测试结果")
    
    # 统计信息
    success_count = len([r for r in results if "✅ 成功" in r["状态"]])
    total_count = len(results)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("总数", total_count)
    with col2:
        st.metric("成功", success_count)
    with col3:
        st.metric("成功率", f"{success_count/total_count*100:.1f}%")
    
    # 结果表格
    import pandas as pd
    df = pd.DataFrame(results)
    st.dataframe(df, use_container_width=True)
    
    logger.info(f"所有模型连接测试完成，成功率: {success_count}/{total_count}")


def show_help_page(config_manager):
    """显示系统说明页面"""
    st.header("📖 系统说明")
    
    # 显示当前配置信息
    with st.expander("🔧 当前系统配置"):
        current_model = config_manager.get_current_model_info()
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**模型配置**")
            st.write(f"- 提供商: {current_model['provider']}")
            st.write(f"- 模型: {current_model['model']}")
            st.write(f"- 状态: {'✅ 可用' if current_model['available'] else '❌ 需要配置API密钥'}")
        
        with col2:
            st.write("**下载配置**")
            st.write(f"- 默认最大页数: {config_manager.get('download_settings.default_max_pages', 5)}")
            st.write(f"- 自动保存: {'✅ 启用' if config_manager.get('download_settings.auto_save', True) else '❌ 禁用'}")
            
        st.write("**查询配置**")
        col3, col4 = st.columns(2)
        with col3:
            st.write(f"- 显示图表: {'✅ 启用' if config_manager.get('query_settings.show_charts', True) else '❌ 禁用'}")
        with col4:
            st.write(f"- 结果限制: {config_manager.get('query_settings.result_limit', 100)} 条")
        
        st.write(f"**配置文件位置**: `{config_manager.config_file}`")
        
        # 添加连接测试按钮
        st.markdown("---")
        st.subheader("🔌 模型连接测试")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("测试当前模型", help="测试当前选择的模型连通性", key="test_current"):
                test_current_model_connection(config_manager)
        
        with col2:
            if st.button("测试所有模型", help="测试所有配置的模型连通性", key="test_all"):
                test_all_models_connection(config_manager)
    
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