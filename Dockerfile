# 第一阶段：构建阶段
FROM python:3.12 as builder

# 设置阿里云镜像源
RUN echo "deb https://mirrors.aliyun.com/debian/ bookworm main non-free non-free-firmware contrib\ndeb-src https://mirrors.aliyun.com/debian/ bookworm main non-free non-free-firmware contrib\ndeb https://mirrors.aliyun.com/debian-security/ bookworm-security main\ndeb-src https://mirrors.aliyun.com/debian-security/ bookworm-security main\ndeb https://mirrors.aliyun.com/debian/ bookworm-updates main non-free non-free-firmware contrib\ndeb-src https://mirrors.aliyun.com/debian/ bookworm-updates main non-free non-free-firmware contrib\ndeb https://mirrors.aliyun.com/debian/ bookworm-backports main non-free non-free-firmware contrib\ndeb-src https://mirrors.aliyun.com/debian/ bookworm-backports main non-free non-free-firmware contrib" > /etc/apt/sources.list

# 安装系统依赖
RUN apt-get update && \
    apt-get install -y cron supervisor

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .
ENV PATH=/root/.local/bin:$PATH

# 安装Python依赖
RUN pip install --user -r requirements.txt && \
    playwright install && \
    playwright install-deps

# 第二阶段：运行阶段
FROM python:3.12-slim

# 复制已安装的Python依赖
COPY --from=builder /root/.local /root/.local
COPY --from=builder /etc/apt/sources.list /etc/apt/sources.list

# 安装运行时系统依赖
RUN apt-get update && \
    apt-get install -y cron supervisor && \
    touch /var/log/cron.log

# 设置环境变量
ENV PYTHONPATH ${PYTHONPATH}:/app/src
ENV PATH=/root/.local/bin:$PATH

# 设置工作目录
WORKDIR /app

# 复制应用代码
COPY . .

# 复制cron和supervisor配置
RUN cp llm_tools_cron /etc/cron.d/llm_tools_cron && \
    cp supervisord.conf /etc/supervisor/conf.d/supervisord.conf && \
    chmod 0644 /etc/cron.d/llm_tools_cron && \
    crontab /etc/cron.d/llm_tools_cron

# 启动命令
CMD ["supervisord", "-c", "/etc/supervisor/supervisord.conf"]
