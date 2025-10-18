FROM python:3.10-slim

# 第1步：设置环境变量
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1

# 第2步：针对 trixie (Debian 13) 配置正确的阿里云镜像源
RUN echo "配置 Trixie (Debian 13) 阿里云镜像源..." && \
    # 备份原始源文件
    cp /etc/apt/sources.list /etc/apt/sources.list.bak && \
    # 清空并写入正确的 trixie 源
    echo "deb http://mirrors.aliyun.com/debian/ trixie main" > /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian/ trixie-updates main" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian-security trixie-security main" >> /etc/apt/sources.list

# 第3步：安装系统依赖（增加超时和重试参数）
RUN echo "更新包列表并安装依赖..." && \
    apt-get update -o Acquire::http::Timeout=30 -o Acquire::Retries=3 && \
    apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# 跳过预下载模型以加速构建（运行时自动下载）
RUN echo "跳过预下载模型，将在运行时自动下载"

ENV ULTRALYTICS_HOME=/app/models
EXPOSE 5000

CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "web_app:app"]