# 第1步：选择基础环境
# 第1步：选择基础环境
# 我们统一使用 Python 3.10 的极简镜像作为起点
FROM python:3.10-slim

# 第2步：【关键修正】安装OpenCV需要的、在新版系统中最通用的系统库
# 我们将 libgl1-mesa-glx 换成了更基础、更通用的 libgl1
RUN apt-get update && apt-get install -y libgl1 \
    && rm -rf /var/lib/apt/lists/*

# 第3步：【终极优化】配置pip国内加速源
# 在安装任何库之前，先将pip的下载源永久指向清华大学镜像站
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 第4步：创建工作目录
WORKDIR /app

# 第5步：复制并安装Python依赖
# 我们使用之前精简过的、兼容性最好的requirements.txt
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 第6步：复制项目所有文件
COPY . .

# 第7步：预下载模型 (在这一步会执行，因为OpenCV已经可以正常工作)
RUN python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

# 第8步：声明服务端口
EXPOSE 5000

# 第9步：定义启动命令 (符合我们Socket服务器的要求)
CMD ["python", "app.py"]

