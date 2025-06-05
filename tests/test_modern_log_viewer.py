#!/usr/bin/env python3
"""
测试现代化日志查看器的实时刷新功能

这个脚本测试基于 Streamlit fragments 的新日志系统
"""

import sys
import os
from pathlib import Path
import streamlit as st
import threading
import time
import random

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.biddingcsg.ui.components.log_viewer_v2 import ModernLogViewer, get_global_log_viewer

def main():
    """主测试函数"""
    st.set_page_config(
        page_title="现代化日志查看器测试",
        page_icon="🧪",
        layout="wide"
    )
    
    st.title("🧪 现代化日志查看器测试")
    st.markdown("---")
    
    # 获取全局日志查看器
    log_viewer = get_global_log_viewer()
    
    # 控制面板
    st.subheader("🎮 测试控制面板")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📝 添加信息日志", use_container_width=True):
            log_viewer.add_log_threadsafe("这是一条信息日志", "INFO")
    
    with col2:
        if st.button("✅ 添加成功日志", use_container_width=True):
            log_viewer.add_log_threadsafe("操作成功完成", "SUCCESS")
    
    with col3:
        if st.button("⚠️ 添加警告日志", use_container_width=True):
            log_viewer.add_log_threadsafe("这是一条警告信息", "WARNING")
    
    with col4:
        if st.button("❌ 添加错误日志", use_container_width=True):
            log_viewer.add_log_threadsafe("发生了一个错误", "ERROR")
    
    st.markdown("---")
    
    # 批量测试按钮
    col5, col6, col7 = st.columns(3)
    
    with col5:
        if st.button("🚀 启动模拟爬虫", use_container_width=True):
            start_mock_crawler(log_viewer)
    
    with col6:
        if st.button("🔧 批量添加日志", use_container_width=True):
            add_batch_logs(log_viewer)
    
    with col7:
        if st.button("🧪 压力测试", use_container_width=True):
            stress_test_logs(log_viewer)
    
    st.markdown("---")
    
    # 显示现代化日志查看器
    st.subheader("📝 实时日志显示")
    log_viewer.render_modern(height=500, show_controls=True)
    
    # 显示紧凑版本
    st.markdown("---")
    st.subheader("📋 紧凑版日志显示")
    log_viewer.render_compact(max_display=5)

def start_mock_crawler(log_viewer: ModernLogViewer):
    """启动模拟爬虫进行测试"""
    
    def mock_crawler_worker():
        """模拟爬虫工作线程"""
        try:
            log_viewer.add_log_threadsafe("🚀 启动模拟爬虫任务", "SUCCESS")
            
            # 模拟初始化阶段
            log_viewer.add_log_threadsafe("🔧 初始化浏览器驱动", "INFO")
            time.sleep(1)
            
            log_viewer.add_log_threadsafe("🌐 连接到目标网站", "INFO")
            time.sleep(1)
            
            log_viewer.add_log_threadsafe("✅ 网站连接成功", "SUCCESS")
            
            # 模拟数据爬取
            total_pages = 5
            for page in range(1, total_pages + 1):
                log_viewer.add_log_threadsafe(f"📄 正在爬取第 {page}/{total_pages} 页", "INFO")
                time.sleep(2)
                
                # 随机模拟一些事件
                if random.random() < 0.2:  # 20% 概率警告
                    log_viewer.add_log_threadsafe(f"⚠️ 第 {page} 页加载较慢", "WARNING")
                elif random.random() < 0.1:  # 10% 概率错误
                    log_viewer.add_log_threadsafe(f"❌ 第 {page} 页访问失败，正在重试", "ERROR")
                    time.sleep(1)
                    log_viewer.add_log_threadsafe(f"🔄 第 {page} 页重试成功", "SUCCESS")
                else:
                    items_found = random.randint(5, 15)
                    log_viewer.add_log_threadsafe(f"✅ 第 {page} 页爬取完成，找到 {items_found} 条记录", "SUCCESS")
            
            log_viewer.add_log_threadsafe("🎉 模拟爬虫任务完成！", "SUCCESS")
            
        except Exception as e:
            log_viewer.add_log_threadsafe(f"❌ 模拟爬虫异常: {e}", "ERROR")
    
    # 启动后台线程
    thread = threading.Thread(target=mock_crawler_worker, daemon=True)
    thread.start()
    
    st.success("🚀 模拟爬虫已启动！请观察实时日志更新")

def add_batch_logs(log_viewer: ModernLogViewer):
    """批量添加测试日志"""
    messages = [
        ("📊 系统初始化完成", "INFO"),
        ("🔍 开始数据搜索", "INFO"),
        ("✅ 找到 25 条匹配记录", "SUCCESS"),
        ("📥 开始下载数据", "INFO"),
        ("⚠️ 网络连接不稳定", "WARNING"),
        ("🔄 正在重新连接", "INFO"),
        ("✅ 连接恢复正常", "SUCCESS"),
        ("💾 数据保存完成", "SUCCESS"),
        ("📈 性能统计：平均响应时间 2.3秒", "INFO"),
        ("🎯 任务执行完毕", "SUCCESS")
    ]
    
    for message, level in messages:
        log_viewer.add_log_threadsafe(message, level)
        time.sleep(0.1)  # 短暂延迟
    
    st.success("✅ 批量日志添加完成！")

def stress_test_logs(log_viewer: ModernLogViewer):
    """压力测试日志系统"""
    
    def stress_worker():
        """压力测试工作线程"""
        levels = ["INFO", "SUCCESS", "WARNING", "ERROR", "DEBUG"]
        
        for i in range(50):
            level = random.choice(levels)
            message = f"压力测试消息 #{i+1:03d} - {random.choice(['处理中', '完成', '失败', '重试', '跳过'])}"
            log_viewer.add_log_threadsafe(message, level)
            time.sleep(0.05)  # 快速添加
        
        log_viewer.add_log_threadsafe("🏁 压力测试完成 - 共生成50条日志", "SUCCESS")
    
    # 启动压力测试线程
    thread = threading.Thread(target=stress_worker, daemon=True)
    thread.start()
    
    st.warning("⚡ 压力测试已启动！将快速生成50条测试日志")

if __name__ == "__main__":
    main() 