# 第1步：选择基础环境
FROM python:3.10-slim

# 第2步：安装所有已知的系统依赖
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 第3步：配置pip国内加速源
RUN pip config set global.index-url [https://pypi.tuna.tsinghua.edu.cn/simple](https://pypi.tuna.tsinghua.edu.cn/simple)

# 第4步：创建工作目录
WORKDIR /app

# 第5步：复制并安装Python依赖
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 第6步：复制项目所有文件
COPY . .

# 第7步：预下载模型
RUN python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

# 第8步：声明服务端口
EXPOSE 5000

# 第9步：定义启动命令
CMD ["python", "app.py"]

