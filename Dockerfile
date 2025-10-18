FROM python:3.10-slim

# 第1步：设置环境变量
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# 第2步：针对 trixie (Debian 13) 配置正确的阿里云镜像源
RUN echo "配置 Trixie (Debian 13) 阿里云镜像源..." && \
    cp /etc/apt/sources.list /etc/apt/sources.list.bak && \
    echo "deb http://mirrors.aliyun.com/debian/ trixie main" > /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian/ trixie-updates main" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian-security trixie-security main" >> /etc/apt/sources.list

# 第3步：安装系统依赖
RUN echo "更新包列表并安装依赖..." && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# 添加健康检查文件（如果不存在）
RUN if [ ! -f healthcheck.py ]; then echo 'from flask import Flask; app = Flask(__name__); @app.route("/health"); def health(): return "OK"' > healthcheck.py; fi

ENV ULTRALYTICS_HOME=/app/models
EXPOSE 5000

# 使用更详细的启动命令
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "--access-logfile", "-", "web_app:app"]