# 第1步：选择基础环境
FROM python:3.10-slim

# 第2步：安装所有已知的系统依赖
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 第3步：配置pip国内加速源
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 第4步：创建工作目录
WORKDIR /app

# 第5步：复制并安装Python依赖
# 注意：这份 requirements.txt 里应该包含 flask 和 gunicorn
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 第6步：复制项目所有文件
COPY . .

# 第7步：预下载模型
RUN python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

# 第8步：声明服务端口
EXPOSE 5000

# 第9步：【关键区别】定义启动命令
# 使用Gunicorn来运行我们的Flask网页应用 (web_app.py)
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "web_app:app"]
```

### **接下来如何使用？**

现在你的项目里有两个`Dockerfile`了。当你需要在云服务器上打包时，可以根据需要选择：

* **打包Socket版 (用于提交作业)**:
    ```bash
    docker build -t my-socket-app:1.0 -f Dockerfile.socket .
    ```

* **打包网页版 (用于功能扩展和答辩演示)**:
    ```bash
    docker build -t my-web-app:1.0 -f Dockerfile .


