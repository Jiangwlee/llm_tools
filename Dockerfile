FROM python:3.12-slim

# 设置工作目录，后续的操作都会在这个目录下进行
WORKDIR /app

# 将当前目录下的所有文件复制到容器内的 /app 目录
COPY . /app

ENV PYTHONPATH ${PYTHONPATH}:/app/src

# 安装项目所需的Python依赖，假设使用pip安装，requirements.txt需提前准备好
RUN pip install -r requirements.txt && cd src

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]