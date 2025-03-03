# 第一阶段：构建阶段
FROM python:3.12

# 设置阿里云镜像源
RUN echo "deb https://mirrors.aliyun.com/debian/ bookworm main non-free non-free-firmware contrib\ndeb-src https://mirrors.aliyun.com/debian/ bookworm main non-free non-free-firmware contrib\ndeb https://mirrors.aliyun.com/debian-security/ bookworm-security main\ndeb-src https://mirrors.aliyun.com/debian-security/ bookworm-security main\ndeb https://mirrors.aliyun.com/debian/ bookworm-updates main non-free non-free-firmware contrib\ndeb-src https://mirrors.aliyun.com/debian/ bookworm-updates main non-free non-free-firmware contrib\ndeb https://mirrors.aliyun.com/debian/ bookworm-backports main non-free non-free-firmware contrib\ndeb-src https://mirrors.aliyun.com/debian/ bookworm-backports main non-free non-free-firmware contrib" > /etc/apt/sources.list

# 安装系统依赖
RUN apt-get update && \
    apt-get install -y cron supervisor

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install -r requirements.txt && \
    playwright install && \
    playwright install-deps && \
    touch /var/log/cron.log

# 设置环境变量
ENV PYTHONPATH ${PYTHONPATH}:/app/src

# 复制应用代码
COPY . .

# 复制cron和supervisor配置
RUN cp llm_tools_cron /etc/cron.d/llm_tools_cron && \
    mkdir /var/log/supervisor && \
    touch /var/log/supervisor/supervisord.log && \
    cp supervisord.conf /etc/supervisor/conf.d/supervisord.conf && \
    chmod 0644 /etc/cron.d/llm_tools_cron && \
    crontab /etc/cron.d/llm_tools_cron

# 启动命令
CMD ["supervisord", "-c", "/etc/supervisor/supervisord.conf"]
