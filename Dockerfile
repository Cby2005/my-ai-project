# 第1步：选择基础环境 - 使用国内镜像源
FROM docker.mirrors.ustc.edu.cn/library/python:3.9-slim

# 第2步：在镜像内部创建工作目录
WORKDIR /app

# 第3步：设置 pip 使用国内源并安装依赖
COPY requirements.txt .
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple \
    && pip config set install.trusted-host pypi.tuna.tsinghua.edu.cn \
    && pip install --no-cache-dir -r requirements.txt

# 第4步：复制项目所有文件
COPY . .

# 第5步：预下载模型
RUN python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

# 第6步：声明服务端口
EXPOSE 5000

# 第7步：设置启动命令
CMD ["python", "app.py"]