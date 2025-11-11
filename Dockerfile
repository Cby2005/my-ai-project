# 第1步：选择基础环境
FROM python:3.10-slim

# 第2步：安装系统依赖 (inference-sdk 内部需要)
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 第3步：配置pip国内加速源
RUN pip config set global.index-url https://repo.huaweicloud.com/repository/pypi/simple

# 第4步：创建工作目录
WORKDIR /app

# 第5步：复制并安装Python依赖 (这会非常快)
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 第6步：复制项目所有文件
COPY . .

# 第7步：声明服务端口
EXPOSE 5000