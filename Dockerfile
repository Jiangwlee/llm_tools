FROM python:3.12

# 设置工作目录，后续的操作都会在这个目录下进行
WORKDIR /app

# 将当前目录下的所有文件复制到容器内的 /app 目录
COPY . /app

ENV PYTHONPATH ${PYTHONPATH}:/app/src

RUN echo "deb https://mirrors.aliyun.com/debian/ bookworm main non-free non-free-firmware contrib\ndeb-src https://mirrors.aliyun.com/debian/ bookworm main non-free non-free-firmware contrib\ndeb https://mirrors.aliyun.com/debian-security/ bookworm-security main\ndeb-src https://mirrors.aliyun.com/debian-security/ bookworm-security main\ndeb https://mirrors.aliyun.com/debian/ bookworm-updates main non-free non-free-firmware contrib\ndeb-src https://mirrors.aliyun.com/debian/ bookworm-updates main non-free non-free-firmware contrib\ndeb https://mirrors.aliyun.com/debian/ bookworm-backports main non-free non-free-firmware contrib\ndeb-src https://mirrors.aliyun.com/debian/ bookworm-backports main non-free non-free-firmware contrib" > /etc/apt/sources.list

# 安装项目所需的Python依赖，假设使用pip安装，requirements.txt需提前准备好
RUN apt-get update && \
    apt-get install -y cron supervisor && \
    cp llm_tools_cron /etc/cron.d/llm_tools_cron && \
    cp supervisord.conf /etc/supervisor/conf.d/supervisord.conf && \
    chmod 0644 /etc/cron.d/llm_tools_cron && \
    crontab /etc/cron.d/llm_tools_cron && \
    touch /var/log/cron.log

RUN pip install -r requirements.txt && \
    playwright install && \
    playwright install-deps && \
    cd src

# CMD ["service", "cron", "start", "&&", "uvicorn", "src.llm_tools.main:app", "--host", "0.0.0.0", "--port", "8000"]
CMD ["supervisord", "-c", "/etc/supervisor/supervisord.conf"]