# 第1步：选择基础环境
# 我们选择一个官方的、轻量级的Python 3.9环境作为起点。
FROM python:3.9-slim

# 第2步：在镜像内部创建工作目录
# 之后的所有操作都会在这个 /app 目录里进行。
WORKDIR /app

# 第3步：复制依赖文件并安装
# 先只复制 requirements.txt，是为了利用Docker的缓存机制。
# 只要这个文件不变，下次构建镜像时就不用重复安装依赖，速度会快很多。
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 第4步：复制项目所有文件
# 将你本地文件夹里除了 .dockerignore 之外的所有文件，都复制到镜像的 /app 目录里。
COPY . .

# 第5步：预下载模型
# 这是一个非常重要的优化。在制作镜像时就把模型下载好。
# 这样，每次启动容器时，服务都能瞬间就绪，无需等待下载。
RUN python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

# 第6步：声明服务端口
# 告诉Docker，我们这个包裹里的服务，计划使用5000端口。
EXPOSE 5000

# 第7步：定义启动命令
# 当容器启动时，执行这条命令。我们使用Gunicorn，一个更稳定、性能更好的服务器来运行Flask应用。
# -w 2: 启动2个工作进程，可以同时处理2个请求。
# -b 0.0.0.0:5000: 绑定到所有网络接口的5000端口，让容器外部可以访问。
# app:app: 第一个app是你的Python文件名(app.py)，第二个app是你在文件中创建的Flask实例(app = Flask(__name__))。
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "app:app"]
