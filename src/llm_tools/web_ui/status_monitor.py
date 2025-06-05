"""
状态监控模块 - 用于Web UI中实时显示系统状态
"""

import threading
import time
from typing import Callable, Optional
from src.llm_tools.logger import get_logger

logger = get_logger()

class StatusMonitor:
    """状态监控器"""
    
    def __init__(self):
        self.page_callback: Optional[Callable] = None
        self.llm_callback: Optional[Callable] = None
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
    
    def set_callbacks(self, page_callback: Callable, llm_callback: Callable):
        """
        设置状态更新回调函数
        
        Args:
            page_callback: 页面状态更新回调
            llm_callback: LLM状态更新回调
        """
        self.page_callback = page_callback
        self.llm_callback = llm_callback
    
    def start_monitoring(self):
        """开始监控"""
        if not self._monitoring:
            self._monitoring = True
            self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._monitor_thread.start()
            logger.info("状态监控器已启动")
    
    def stop_monitoring(self):
        """停止监控"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1)
        logger.info("状态监控器已停止")
    
    def _monitor_loop(self):
        """监控循环"""
        while self._monitoring:
            try:
                # 这里可以添加实际的状态检查逻辑
                # 例如检查文件变化、日志更新等
                time.sleep(1)
            except Exception as e:
                logger.error(f"状态监控错误: {e}")
    
    def update_page_status(self, status: str):
        """更新页面状态"""
        if self.page_callback:
            try:
                self.page_callback(status)
                logger.debug(f"页面状态更新: {status}")
            except Exception as e:
                logger.error(f"页面状态更新失败: {e}")
    
    def update_llm_status(self, status: str):
        """更新LLM状态"""
        if self.llm_callback:
            try:
                self.llm_callback(status)
                logger.debug(f"LLM状态更新: {status}")
            except Exception as e:
                logger.error(f"LLM状态更新失败: {e}")

# 全局状态监控器实例
status_monitor = StatusMonitor()

def get_status_monitor() -> StatusMonitor:
    """获取全局状态监控器实例"""
    return status_monitor 