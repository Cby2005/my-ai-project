 FROM python:3.10-slim

# 保守版本：跳过复杂的源配置，直接使用官方源（阿里云服务器访问官方源通常很快）
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1

# 直接使用官方源（阿里云服务器访问国外源通常没问题）
RUN echo "使用官方Debian源..." && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 配置pip源（可选，如果pip安装慢可以开启）
# RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# 可选：预下载模型（如果网络稳定）
RUN mkdir -p /app/models && \
    python -c " \
    try: \
        from ultralytics import YOLO; \
        YOLO('yolov8n.pt'); \
        print('模型预下载成功'); \
    except Exception as e: \
        print(f'模型预下载跳过: {e}'); \
    "

ENV ULTRALYTICS_HOME=/app/models
EXPOSE 5000

CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "web_app:app"]