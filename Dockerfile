 FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先复制依赖文件（这层变化少，可以缓存）
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 最后复制所有代码（这层变化频繁，放在最后）
# 添加一个构建参数来确保每次构建都获取最新代码
ARG CACHE_BUST=1
COPY . .

EXPOSE 5000

CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "web_app:app"]