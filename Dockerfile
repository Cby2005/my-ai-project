 # 第1步：选择基础环境
    FROM python:3.10-slim

    # 第2步：【关键网络修复】更换系统软件源为国内镜像
    # 在执行任何apt-get操作之前，先将下载地址指向速度更快的阿里云镜像
    RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources

    # 第3步：安装所有已知的系统依赖 (现在可以成功了)
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
