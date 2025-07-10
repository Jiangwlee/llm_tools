# 第一阶段：构建阶段
FROM python:3.12-bookworm AS builder

# 设置阿里云镜像源
RUN echo "deb https://mirrors.aliyun.com/debian/ bookworm main non-free non-free-firmware contrib\ndeb-src https://mirrors.aliyun.com/debian/ bookworm main non-free non-free-firmware contrib\ndeb https://mirrors.aliyun.com/debian-security/ bookworm-security main\ndeb-src https://mirrors.aliyun.com/debian-security/ bookworm-security main\ndeb https://mirrors.aliyun.com/debian/ bookworm-updates main non-free non-free-firmware contrib\ndeb-src https://mirrors.aliyun.com/debian/ bookworm-updates main non-free non-free-firmware contrib\ndeb https://mirrors.aliyun.com/debian/ bookworm-backports main non-free non-free-firmware contrib\ndeb-src https://mirrors.aliyun.com/debian/ bookworm-backports main non-free non-free-firmware contrib" > /etc/apt/sources.list

# 安装系统依赖
RUN apt-get update && \
    apt-get install -y cron supervisor

# 设置工作目录
WORKDIR /app

# 配置pip使用阿里云镜像源
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip config set global.trusted-host mirrors.aliyun.com

# 先安装 playwright（独立层，避免频繁重建）
ENV PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright
RUN pip install playwright && \
    playwright install chromium && \
    playwright install-deps

# 复制依赖文件并安装Python依赖
COPY requirements.txt .
RUN pip install -r requirements.txt

# 第二阶段：运行时阶段
FROM python:3.12-slim-bookworm

RUN echo "deb https://mirrors.aliyun.com/debian/ bookworm main non-free non-free-firmware contrib\ndeb-src https://mirrors.aliyun.com/debian/ bookworm main non-free non-free-firmware contrib\ndeb https://mirrors.aliyun.com/debian-security/ bookworm-security main\ndeb-src https://mirrors.aliyun.com/debian-security/ bookworm-security main\ndeb https://mirrors.aliyun.com/debian/ bookworm-updates main non-free non-free-firmware contrib\ndeb-src https://mirrors.aliyun.com/debian/ bookworm-updates main non-free non-free-firmware contrib\ndeb https://mirrors.aliyun.com/debian/ bookworm-backports main non-free non-free-firmware contrib\ndeb-src https://mirrors.aliyun.com/debian/ bookworm-backports main non-free non-free-firmware contrib" > /etc/apt/sources.list

# 配置pip使用阿里云镜像源
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip config set global.trusted-host mirrors.aliyun.com

# 安装运行时依赖，包括 playwright 所需的系统依赖
RUN apt-get update && \
    apt-get install -y \
    cron \
    supervisor \
    # playwright 系统依赖
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxcb1 \
    libxkbcommon0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    libgtk-3-0 \
    libgdk-pixbuf2.0-0 \
    libxss1 \
    libxshmfence1 \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 从构建阶段复制Python依赖和Playwright浏览器
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /root/.cache/ms-playwright /root/.cache/ms-playwright

# 设置环境变量
ENV PYTHONPATH /app/src:/app/scripts

# 复制应用代码
COPY . .

# 复制cron和supervisor配置
RUN cp llm_tools_cron /etc/cron.d/llm_tools_cron && \
    mkdir -p /var/log/supervisor && \
    touch /var/log/supervisor/supervisord.log && \
    cp supervisord.conf /etc/supervisor/conf.d/supervisord.conf && \
    chmod 0644 /etc/cron.d/llm_tools_cron && \
    crontab /etc/cron.d/llm_tools_cron

# 初始化数据库表结构（确保表已创建）
RUN chmod +x /app/scripts/entrypoint.sh
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
# 启动命令
CMD ["supervisord", "-c", "/etc/supervisor/supervisord.conf"]
