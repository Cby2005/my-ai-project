# 第1步：选择基础环境
FROM python:3.10-slim

# 第2步：安装系统依赖
RUN apt-get update && apt-get install -y libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# 第3步：【新增的终极优化】配置pip国内加速源
# 在安装任何库之前，先将pip的下载源永久指向清华大学镜像站
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 第4步：创建工作目录
WORKDIR /app

# 第5步：复制并安装Python依赖 (现在会飞快)
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 第6步：复制项目所有文件
COPY . .

# 第7步：预下载模型 (这一步速度取决于GitHub，但通常也会变快)
RUN python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

# 第8步：声明服务端口
EXPOSE 5000

# 第9步：定义启动命令
CMD ["python", "app.py"]