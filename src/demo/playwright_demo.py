from playwright.sync_api import sync_playwright

# 启动 Playwright
with sync_playwright() as p:
    # 启动 Chromium 浏览器
    browser = p.chromium.launch(headless=True)  # 设置 headless=True 可隐藏浏览器窗口
    # 打开新页面
    page = browser.new_page()
    # 导航到 百度
    page.goto("https://www.baidu.com")
    # 输入搜索内容
    page.fill("input[name='wd']", "Playwright Python 示例")
    # 提交搜索
    page.press("input[id='su']", "Enter")
    # 等待页面加载
    page.wait_for_load_state("networkidle")
    # 获取并打印页面标题
    print("页面标题:", page.title())
    page.screenshot(path="baidu.png")
    print("Screenshot saved as baidu.png")
    browser.close()
