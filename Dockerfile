# 第1步：选择基础环境
FROM python:3.10-slim

# 第2步：【终极网络修复】用阿里云镜像源强制覆盖系统软件源
# 这个命令会直接重写apt的配置文件，确保100%使用国内源
RUN echo "deb http://mirrors.aliyun.com/debian/ trixie main contrib non-free" > /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian/ trixie-updates main contrib non-free" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian-security trixie-security main contrib non-free" >> /etc/apt/sources.list

# 第3步：安装所有已知的系统依赖 (现在会飞快)
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 第4步：配置pip国内加速源
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 第5步：创建工作目录
WORKDIR /app

# 第6步：复制并安装Python依赖
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 第7步：复制项目所有文件
COPY . .

# 第8步：预下载模型
RUN python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

# 第9步：声明服务端口
EXPOSE 5000

# 第10步：定义启动命令
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "web_app:app"]