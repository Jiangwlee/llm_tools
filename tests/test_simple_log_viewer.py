#!/usr/bin/env python3
"""
简化的日志查看器测试
用于验证实时日志刷新功能
"""

import streamlit as st
import time
import threading
from datetime import datetime
from pathlib import Path
import queue
import logging

# 配置页面
st.set_page_config(
    page_title="简化日志测试",
    page_icon="📊",
    layout="wide"
)

st.title("🔍 简化日志查看器测试")

# 初始化
if 'log_messages' not in st.session_state:
    st.session_state.log_messages = []
if 'log_queue' not in st.session_state:
    st.session_state.log_queue = queue.Queue()
if 'counter' not in st.session_state:
    st.session_state.counter = 0
if 'crawler_thread_count' not in st.session_state:
    st.session_state.crawler_thread_count = 0
if 'mock_crawler_start_time' not in st.session_state:
    st.session_state.mock_crawler_start_time = None
if 'mock_crawler_message_count' not in st.session_state:
    st.session_state.mock_crawler_message_count = 0
if 'fast_crawler_start_time' not in st.session_state:
    st.session_state.fast_crawler_start_time = None
if 'fast_crawler_message_count' not in st.session_state:
    st.session_state.fast_crawler_message_count = 0
if 'force_update_counter' not in st.session_state:
    st.session_state.force_update_counter = 0
if 'last_rerun_time' not in st.session_state:
    st.session_state.last_rerun_time = datetime.now()

# 模拟爬虫写入日志的函数
def simulate_crawler(thread_id):
    """模拟爬虫持续写入日志"""
    try:
        # 立即发送启动日志
        start_msg = f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 线程{thread_id}启动 - 开始模拟爬虫"
        st.session_state.log_queue.put(start_msg)
        
        messages = [
            "🚀 启动爬虫引擎",
            "🔧 初始化配置", 
            "⚙️ 设置ProactorEventLoop成功",
            "🌐 连接到目标网站",
            "📄 解析页面结构",
            "📊 提取数据字段",
            "💾 保存到数据库",
            "✅ 处理完成一页",
            "🔄 继续下一页",
            "📈 统计信息更新"
        ]
        
        i = 0
        while st.session_state.get('crawler_running', False):
            msg = messages[i % len(messages)]
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] 线程{thread_id}: {msg} (第{i+1}条)"
            st.session_state.log_queue.put(log_entry)
            i += 1
            
            # 每隔一定时间发送心跳
            if i % 3 == 0:
                heartbeat = f"[{timestamp}] 💓 线程{thread_id}心跳检测 - 已处理{i}条"
                st.session_state.log_queue.put(heartbeat)
            
            time.sleep(2)  # 每2秒一条
        
        # 发送停止日志
        stop_msg = f"[{datetime.now().strftime('%H:%M:%S')}] ⏹️ 线程{thread_id}正常停止"
        st.session_state.log_queue.put(stop_msg)
        
    except Exception as e:
        error_msg = f"[{datetime.now().strftime('%H:%M:%S')}] ❌ 线程{thread_id}错误: {e}"
        st.session_state.log_queue.put(error_msg)

# 处理队列中的日志
def process_log_queue():
    """处理日志队列"""
    count = 0
    while not st.session_state.log_queue.empty():
        try:
            message = st.session_state.log_queue.get_nowait()
            st.session_state.log_messages.append(message)
            count += 1
        except queue.Empty:
            break
    return count

# 处理调试队列
def process_debug_queue():
    """处理调试队列"""
    debug_messages = []
    while not global_debug_queue.empty():
        try:
            message = global_debug_queue.get_nowait()
            debug_messages.append(message)
        except queue.Empty:
            break
    return debug_messages

# 自动刷新片段
@st.fragment(run_every=1)
def auto_refresh_logs():
    """自动刷新日志显示"""
    st.session_state.counter += 1
    
    # 显示刷新状态
    current_time = datetime.now().strftime("%H:%M:%S")
    st.markdown(f"🔄 **自动刷新中** - {current_time} (第{st.session_state.counter}次)")
    
    # 处理新日志
    new_count = process_log_queue()
    if new_count > 0:
        st.success(f"✅ 新增 {new_count} 条日志")
        
        # 智能重新渲染（避免过于频繁）
        now = datetime.now()
        if (now - st.session_state.last_rerun_time).total_seconds() > 0.5:  # 至少间隔0.5秒
            st.session_state.last_rerun_time = now
            st.session_state.force_update_counter += 1
            st.rerun()
    
    # 处理调试信息
    debug_messages = process_debug_queue()
    if debug_messages:
        st.info(f"🔧 调试信息: {len(debug_messages)} 条")
        for debug_msg in debug_messages[-3:]:  # 只显示最新3条
            st.text(debug_msg)
    
    # 模拟基于时间的爬虫（不使用线程）- 改进版
    if st.session_state.mock_crawler_start_time:
        elapsed = datetime.now() - st.session_state.mock_crawler_start_time
        # 每2秒发送一条消息（缩短间隔）
        expected_messages = int(elapsed.total_seconds() // 2)
        
        messages = [
            "🕐 基于时间的模拟爬虫启动",
            "🔧 初始化配置完成", 
            "⚙️ 设置ProactorEventLoop成功",
            "🌐 连接到目标网站成功",
            "📄 开始解析页面结构",
            "📊 提取数据字段中...",
            "💾 保存数据到数据库",
            "✅ 第一页处理完成",
            "🔄 继续处理下一页",
            "📈 更新统计信息"
        ]
        
        # 每次只发送一条新消息
        if expected_messages > st.session_state.mock_crawler_message_count and st.session_state.mock_crawler_message_count < len(messages):
            msg_index = st.session_state.mock_crawler_message_count
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_msg = f"[{timestamp}] {messages[msg_index]} (第{msg_index+1}条)"
            st.session_state.log_queue.put(log_msg)
            st.session_state.mock_crawler_message_count += 1
            
            # 强制触发UI更新
            st.session_state.log_last_update = datetime.now()
            
            # 显示实时状态
            st.success(f"🔥 实时发送: {messages[msg_index]}")
            
        # 如果消息发完了，停止模拟
        elif st.session_state.mock_crawler_message_count >= len(messages):
            stop_msg = f"[{datetime.now().strftime('%H:%M:%S')}] ⏹️ 基于时间的模拟爬虫完成"
            st.session_state.log_queue.put(stop_msg)
            st.session_state.mock_crawler_start_time = None
            st.balloons()  # 庆祝完成
        
        # 显示进度信息
        progress = st.session_state.mock_crawler_message_count / len(messages)
        st.progress(progress, f"进度: {st.session_state.mock_crawler_message_count}/{len(messages)}")
    
    # 快速实时爬虫（每秒一条）
    if st.session_state.fast_crawler_start_time:
        elapsed = datetime.now() - st.session_state.fast_crawler_start_time
        # 每1秒发送一条消息
        expected_messages = int(elapsed.total_seconds())
        
        if expected_messages > st.session_state.fast_crawler_message_count and st.session_state.fast_crawler_message_count < 10:
            timestamp = datetime.now().strftime("%H:%M:%S")
            count = st.session_state.fast_crawler_message_count + 1
            log_msg = f"[{timestamp}] ⚡ 快速实时测试 - 第{count}秒"
            st.session_state.log_queue.put(log_msg)
            st.session_state.fast_crawler_message_count += 1
            
            # 显示实时状态
            st.info(f"⚡ 快速模式: 第{count}秒")
            
        # 10秒后停止
        elif st.session_state.fast_crawler_message_count >= 10:
            stop_msg = f"[{datetime.now().strftime('%H:%M:%S')}] ⏹️ 快速实时测试完成"
            st.session_state.log_queue.put(stop_msg)
            st.session_state.fast_crawler_start_time = None

# 控制面板
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🚀 开始模拟爬虫"):
        if not st.session_state.get('crawler_running', False):
            st.session_state.crawler_running = True
            st.session_state.crawler_thread_count += 1
            thread_id = st.session_state.crawler_thread_count
            
            # 立即添加一条启动确认日志
            start_confirm = f"[{datetime.now().strftime('%H:%M:%S')}] 🎯 用户点击启动按钮 - 准备启动线程{thread_id}"
            st.session_state.log_queue.put(start_confirm)
            
            # 在后台线程启动模拟爬虫
            crawler_thread = threading.Thread(target=simulate_crawler, args=(thread_id,), daemon=True)
            crawler_thread.start()
            
            st.success(f"✅ 已启动模拟爬虫线程 #{thread_id}")
            
            # 确认线程启动
            confirm_msg = f"[{datetime.now().strftime('%H:%M:%S')}] 🔧 线程{thread_id}创建完成，等待执行..."
            st.session_state.log_queue.put(confirm_msg)
        else:
            st.warning("⚠️ 爬虫已在运行中")

with col2:
    if st.button("⏹️ 停止爬虫"):
        st.session_state.crawler_running = False
        st.info("已停止爬虫")

with col3:
    if st.button("🗑️ 清空日志"):
        st.session_state.log_messages = []
        # 清空队列
        while not st.session_state.log_queue.empty():
            try:
                st.session_state.log_queue.get_nowait()
            except:
                break
        st.success("已清空日志和队列")

# 添加第二行控制按钮
col4, col5, col6 = st.columns(3)

with col4:
    if st.button("📤 直接添加测试日志"):
        test_msg = f"[{datetime.now().strftime('%H:%M:%S')}] 🧪 这是一条直接测试日志"
        st.session_state.log_queue.put(test_msg)
        st.info("已添加测试日志到队列")

# 全局队列用于调试
import queue as queue_module
global_debug_queue = queue_module.Queue()

# 简化测试线程
def simple_test_thread():
    """简化的测试线程"""
    try:
        # 使用全局队列测试
        start_debug = f"[{datetime.now().strftime('%H:%M:%S')}] 🔧 线程内部开始执行"
        global_debug_queue.put(start_debug)
        
        # 尝试访问session_state
        try:
            queue_ref = st.session_state.log_queue
            debug_msg = f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 成功获取session_state.log_queue"
            global_debug_queue.put(debug_msg)
        except Exception as e:
            error_msg = f"[{datetime.now().strftime('%H:%M:%S')}] ❌ 无法访问session_state: {e}"
            global_debug_queue.put(error_msg)
            return
        
        # 不使用sleep，立即发送5条消息
        for i in range(5):
            msg = f"[{datetime.now().strftime('%H:%M:%S')}] 🧪 简化测试线程 - 第{i+1}条"
            try:
                st.session_state.log_queue.put(msg)
                debug = f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 成功发送第{i+1}条"
                global_debug_queue.put(debug)
            except Exception as e:
                error = f"[{datetime.now().strftime('%H:%M:%S')}] ❌ 发送第{i+1}条失败: {e}"
                global_debug_queue.put(error)
        
        # 发送完成消息
        complete_msg = f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 简化测试线程完成"
        st.session_state.log_queue.put(complete_msg)
        global_debug_queue.put(f"[{datetime.now().strftime('%H:%M:%S')}] 🔧 线程执行完毕")
        
    except Exception as e:
        error = f"[{datetime.now().strftime('%H:%M:%S')}] ❌ 简化测试线程错误: {e}"
        global_debug_queue.put(error)

# 实时测试线程（带sleep）
def realtime_test_thread():
    """实时测试线程（带延迟）"""
    try:
        for i in range(3):
            msg = f"[{datetime.now().strftime('%H:%M:%S')}] ⏰ 实时测试 - 第{i+1}条"
            st.session_state.log_queue.put(msg)
            if i < 2:  # 最后一条不需要sleep
                time.sleep(2)
        
        final_msg = f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 实时测试完成"
        st.session_state.log_queue.put(final_msg)
        
    except Exception as e:
        error = f"[{datetime.now().strftime('%H:%M:%S')}] ❌ 实时测试错误: {e}"
        st.session_state.log_queue.put(error)

# 添加第三行按钮
col7, col8, col9 = st.columns(3)

with col7:
    if st.button("🧪 启动简化测试线程"):
        test_thread = threading.Thread(target=simple_test_thread, daemon=True)
        test_thread.start()
        start_msg = f"[{datetime.now().strftime('%H:%M:%S')}] 🎯 启动简化测试线程"
        st.session_state.log_queue.put(start_msg)
        st.success("已启动简化测试线程")

with col8:
    if st.button("⏰ 启动实时测试线程"):
        realtime_thread = threading.Thread(target=realtime_test_thread, daemon=True)
        realtime_thread.start()
        start_msg = f"[{datetime.now().strftime('%H:%M:%S')}] 🎯 启动实时测试线程"
        st.session_state.log_queue.put(start_msg)
        st.success("已启动实时测试线程")

with col9:
    if st.button("💥 批量添加测试"):
        for i in range(3):
            batch_msg = f"[{datetime.now().strftime('%H:%M:%S')}] 📦 批量测试 - 第{i+1}条"
            st.session_state.log_queue.put(batch_msg)
        st.success("已批量添加3条测试日志")

# 使用全局队列的测试线程
def global_queue_test_thread():
    """完全使用全局队列的测试线程"""
    try:
        # 记录开始
        start_msg = f"[{datetime.now().strftime('%H:%M:%S')}] 🌟 全局队列线程开始"
        global_debug_queue.put(start_msg)
        
        # 发送几条测试消息
        for i in range(3):
            msg = f"[{datetime.now().strftime('%H:%M:%S')}] 🌟 全局测试 - 第{i+1}条"
            global_debug_queue.put(msg)
        
        # 记录结束
        end_msg = f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 全局队列线程完成"
        global_debug_queue.put(end_msg)
        
    except Exception as e:
        error_msg = f"[{datetime.now().strftime('%H:%M:%S')}] ❌ 全局队列线程错误: {e}"
        global_debug_queue.put(error_msg)

# 添加第四行控制按钮
st.markdown("---")
col10, col11, col12 = st.columns(3)

with col10:
    if st.button("🌟 全局队列线程测试"):
        test_thread = threading.Thread(target=global_queue_test_thread, daemon=True)
        test_thread.start()
        st.success("已启动全局队列测试线程")

with col11:
    if st.button("📋 显示所有调试信息"):
        debug_messages = process_debug_queue()
        if debug_messages:
            st.success(f"找到 {len(debug_messages)} 条调试信息:")
            for msg in debug_messages:
                st.text(msg)
        else:
            st.warning("没有调试信息")

with col12:
    if st.button("🧹 清空调试队列"):
        while not global_debug_queue.empty():
            try:
                global_debug_queue.get_nowait()
            except:
                break
        st.success("已清空调试队列")

# 添加第五行控制按钮
st.markdown("### 🕐 基于时间的模拟测试（无线程）")
col13, col14, col15 = st.columns(3)

# 添加第六行控制按钮（快速测试）
st.markdown("### ⚡ 快速实时测试（每秒一条）")
col16, col17, col18 = st.columns(3)

with col13:
    if st.button("🕐 启动时间模拟爬虫"):
        if not st.session_state.mock_crawler_start_time:
            st.session_state.mock_crawler_start_time = datetime.now()
            st.session_state.mock_crawler_message_count = 0
            start_msg = f"[{datetime.now().strftime('%H:%M:%S')}] 🎯 启动基于时间的模拟爬虫"
            st.session_state.log_queue.put(start_msg)
            st.success("✅ 已启动基于时间的模拟爬虫")
        else:
            st.warning("⚠️ 时间模拟爬虫已在运行")

with col14:
    if st.button("⏹️ 停止时间模拟爬虫"):
        if st.session_state.mock_crawler_start_time:
            stop_msg = f"[{datetime.now().strftime('%H:%M:%S')}] ⏹️ 用户停止时间模拟爬虫"
            st.session_state.log_queue.put(stop_msg)
            st.session_state.mock_crawler_start_time = None
            st.success("已停止时间模拟爬虫")
        else:
            st.info("时间模拟爬虫未运行")

with col15:
    if st.session_state.mock_crawler_start_time:
        elapsed = datetime.now() - st.session_state.mock_crawler_start_time
        st.metric("运行时间", f"{elapsed.total_seconds():.0f}秒")
        st.metric("已发送消息", st.session_state.mock_crawler_message_count)

with col16:
    if st.button("⚡ 启动快速实时测试"):
        if not st.session_state.fast_crawler_start_time:
            st.session_state.fast_crawler_start_time = datetime.now()
            st.session_state.fast_crawler_message_count = 0
            start_msg = f"[{datetime.now().strftime('%H:%M:%S')}] 🎯 启动快速实时测试（每秒一条）"
            st.session_state.log_queue.put(start_msg)
            st.success("✅ 已启动快速实时测试")
        else:
            st.warning("⚠️ 快速测试已在运行")

with col17:
    if st.button("⏹️ 停止快速测试"):
        if st.session_state.fast_crawler_start_time:
            stop_msg = f"[{datetime.now().strftime('%H:%M:%S')}] ⏹️ 用户停止快速测试"
            st.session_state.log_queue.put(stop_msg)
            st.session_state.fast_crawler_start_time = None
            st.success("已停止快速测试")
        else:
            st.info("快速测试未运行")

with col18:
    if st.session_state.fast_crawler_start_time:
        elapsed = datetime.now() - st.session_state.fast_crawler_start_time
        st.metric("运行时间", f"{elapsed.total_seconds():.0f}秒")
        st.metric("已发送消息", st.session_state.fast_crawler_message_count)
        st.metric("预期消息", min(int(elapsed.total_seconds()), 10))

with col5:
    if st.button("📊 显示队列状态"):
        queue_size = st.session_state.log_queue.qsize()
        log_count = len(st.session_state.log_messages)
        crawler_status = st.session_state.get('crawler_running', False)
        st.json({
            "队列大小": queue_size,
            "已显示日志": log_count,
            "爬虫状态": crawler_status
        })

with col6:
    if st.button("🔄 手动处理队列"):
        processed = process_log_queue()
        debug_processed = process_debug_queue()
        st.success(f"手动处理了 {processed} 条日志")
        if debug_processed:
            st.info(f"获取到 {len(debug_processed)} 条调试信息")
            for debug in debug_processed:
                st.text(debug)

# 显示统计信息
col_stat1, col_stat2 = st.columns(2)
with col_stat1:
    st.metric("日志总数", len(st.session_state.log_messages))
with col_stat2:
    st.metric("队列大小", st.session_state.log_queue.qsize())

# 启动自动刷新
st.markdown("---")
auto_refresh_logs()

# 显示日志
st.markdown("### 📋 实时日志")

if st.session_state.log_messages:
    # 显示最新的20条日志
    recent_logs = st.session_state.log_messages[-20:]
    
    log_container = st.container()
    with log_container:
        for i, message in enumerate(reversed(recent_logs)):
            # 使用不同颜色显示不同类型的日志
            if "✅" in message:
                st.success(message)
            elif "🚀" in message or "🔧" in message:
                st.info(message)
            elif "⚙️" in message:
                st.warning(message)
            else:
                st.text(message)
else:
    st.info("暂无日志，点击'开始模拟爬虫'来生成测试日志")

# 调试信息
with st.expander("🔧 调试信息"):
    st.json({
        "刷新次数": st.session_state.counter,
        "爬虫状态": st.session_state.get('crawler_running', False),
        "日志总数": len(st.session_state.log_messages),
        "队列大小": st.session_state.log_queue.qsize(),
        "最后一条日志": st.session_state.log_messages[-1] if st.session_state.log_messages else "无"
    }) 