"""
BiddingCSG 包装器 - 解决 Streamlit 环境下的 Playwright 兼容性问题
"""

import os
import sys
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
import multiprocessing as mp

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
sys.path.insert(0, project_root)

from src.llm_tools.tools.bidding_csg import BiddingCSG, BiddingCsgAnalyzer
from src.llm_tools.logger import get_logger

logger = get_logger()


def run_crawler_process(keyword, bidding_type, max_page, end_date, result_queue):
    """在独立进程中运行爬虫，完全避免事件循环冲突"""
    try:
        # 在新进程中创建 BiddingCSG 实例
        csg = BiddingCSG(verbose=False)  # 在进程中不显示浏览器
        csg.search(keyword, max_page=max_page, end_date=end_date)
        csg.save_to_db()
        csg.filter(keyword, bidding_type)
        
        if bidding_type == 1:
            csg.analyze(keyword)
        
        # 关闭浏览器
        if hasattr(csg, 'browser') and csg.browser:
            csg.browser.close()
        if hasattr(csg, 'playwright') and csg.playwright:
            csg.playwright.stop()
            
        result_queue.put({"success": True, "message": "数据下载完成！"})
        
    except Exception as e:
        logger.error(f"爬虫进程执行错误: {str(e)}")
        result_queue.put({"success": False, "message": f"下载过程中出现错误: {str(e)}"})


class StreamlitBiddingCSG:
    """适用于 Streamlit 环境的 BiddingCSG 包装器"""
    
    def __init__(self):
        self.logger = get_logger()
    
    def download_data(self, keyword, bidding_type=None, max_page=10, end_date=None):
        """
        在 Streamlit 环境中安全地下载数据
        
        Args:
            keyword: 搜索关键字
            bidding_type: 公告类型 (1=投标报价, 2=投标费率, None=全部)
            max_page: 最大爬取页数
            end_date: 结束日期 (YYYY-MM-DD 格式)
        
        Returns:
            dict: 包含 success 和 message 的结果字典
        """
        try:
            # 设置多进程启动方法（Windows 环境需要）
            if mp.get_start_method(allow_none=True) != 'spawn':
                mp.set_start_method('spawn', force=True)
            
            # 创建结果队列
            result_queue = mp.Queue()
            
            # 创建并启动爬虫进程
            process = mp.Process(
                target=run_crawler_process,
                args=(keyword, bidding_type, max_page, end_date, result_queue)
            )
            
            process.start()
            
            # 等待进程完成（最多30分钟）
            process.join(timeout=1800)
            
            if process.is_alive():
                # 如果进程超时，强制终止
                process.terminate()
                process.join()
                return {"success": False, "message": "下载超时，请减少爬取页数后重试"}
            
            # 获取结果
            if not result_queue.empty():
                result = result_queue.get()
                return result
            else:
                return {"success": False, "message": "下载过程异常结束"}
                
        except Exception as e:
            self.logger.error(f"StreamlitBiddingCSG.download_data 错误: {str(e)}")
            return {"success": False, "message": f"系统错误: {str(e)}"}
    
    def query_price(self, keyword, bidding_type):
        """
        查询价格数据
        
        Args:
            keyword: 查询关键字
            bidding_type: 查询类型 (1=投标报价, 2=投标费率)
        
        Returns:
            dict: 包含 success, message 和可选的 data 的结果字典
        """
        try:
            analyzer = BiddingCsgAnalyzer()
            csv_data = analyzer.output_as_csv(keyword, bidding_type)
            
            if csv_data and len(csv_data) > 1:  # 至少有标题行和一行数据
                return {
                    "success": True, 
                    "message": f"查询完成！共找到 {len(csv_data) - 1} 条记录",
                    "data": csv_data
                }
            else:
                return {
                    "success": False, 
                    "message": "未找到匹配的数据，请先执行数据下载或检查查询关键字"
                }
                
        except Exception as e:
            self.logger.error(f"StreamlitBiddingCSG.query_price 错误: {str(e)}")
            return {"success": False, "message": f"查询错误: {str(e)}"}


def safe_get_price_info(keyword, bidding_type=None, max_page=10, end_date=None):
    """
    Streamlit 安全的数据下载函数
    
    这个函数是 get_price_info 的 Streamlit 兼容版本
    """
    wrapper = StreamlitBiddingCSG()
    return wrapper.download_data(keyword, bidding_type, max_page, end_date)


def safe_query_price(keyword, bidding_type):
    """
    Streamlit 安全的价格查询函数
    
    这个函数是 query_price 的 Streamlit 兼容版本
    """
    wrapper = StreamlitBiddingCSG()
    return wrapper.query_price(keyword, bidding_type) 