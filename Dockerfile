# 第1步：选择基础环境
# 我们统一使用 Python 3.10 的极简镜像作为起点
FROM python:3.10-slim

# 第2步：【新增的关键步骤】安装系统依赖
# 在安装任何Python库之前，先用apt-get安装OpenCV需要的底层系统库
# apt-get update: 更新软件列表
# apt-get install -y libgl1-mesa-glx: 安装包含 libGL.so.1 的软件包
# rm -rf /var/lib/apt/lists/*: 清理缓存，保持镜像体积小
RUN apt-get update && apt-get install -y libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# 第3步：在镜像内部创建工作目录
WORKDIR /app

# 第4步：复制并安装Python依赖
# 我们使用之前精简过的、兼容性最好的requirements.txt
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 第5步：复制项目所有文件
COPY . .

# 第6步：预下载模型 (这一步现在可以成功了，因为OpenCV已经可以正常工作)
RUN python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

# 第7步：声明服务端口
EXPOSE 5000

# 第8步：定义启动命令
# 使用Gunicorn作为生产级Web服务器来运行你的app
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "app:app"]

