# 第一阶段：构建阶段
FROM python:3.12-bookworm AS builder

# 设置阿里云镜像源
RUN echo "deb https://mirrors.aliyun.com/debian/ bookworm main non-free non-free-firmware contrib\ndeb-src https://mirrors.aliyun.com/debian/ bookworm main non-free non-free-firmware contrib\ndeb https://mirrors.aliyun.com/debian-security/ bookworm-security main\ndeb-src https://mirrors.aliyun.com/debian-security/ bookworm-security main\ndeb https://mirrors.aliyun.com/debian/ bookworm-updates main non-free non-free-firmware contrib\ndeb-src https://mirrors.aliyun.com/debian/ bookworm-updates main non-free non-free-firmware contrib\ndeb https://mirrors.aliyun.com/debian/ bookworm-backports main non-free non-free-firmware contrib\ndeb-src https://mirrors.aliyun.com/debian/ bookworm-backports main non-free non-free-firmware contrib" > /etc/apt/sources.list

# 安装系统依赖
RUN apt-get update && \
    apt-get install -y cron supervisor

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 配置pip使用阿里云镜像源
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip config set global.trusted-host mirrors.aliyun.com

# 安装Python依赖
RUN pip install -r requirements.txt

# playwright 相关安装（仅在构建阶段）
ENV PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright
RUN pip install playwright && \
    playwright install chromium && \
    playwright install-deps && \
    touch /var/log/cron.log

# 第二阶段：运行时阶段
FROM python:3.12-slim-bookworm

# 安装运行时依赖
RUN apt-get update && \
    apt-get install -y cron supervisor && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 从构建阶段复制Python依赖和Playwright浏览器
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /root/.cache/ms-playwright /root/.cache/ms-playwright

# 设置环境变量
ENV PYTHONPATH ${PYTHONPATH}:/app/src

# 复制应用代码
COPY . .

# 复制cron和supervisor配置
RUN cp llm_tools_cron /etc/cron.d/llm_tools_cron && \
    mkdir -p /var/log/supervisor && \
    touch /var/log/supervisor/supervisord.log && \
    cp supervisord.conf /etc/supervisor/conf.d/supervisord.conf && \
    chmod 0644 /etc/cron.d/llm_tools_cron && \
    crontab /etc/cron.d/llm_tools_cron

# 启动命令
CMD ["supervisord", "-c", "/etc/supervisor/supervisord.conf"]
