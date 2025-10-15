# 导入所需的库
import socket
import cv2
import numpy as np
from ultralytics import YOLO

# --- 配置区 ---
HOST = '0.0.0.0'  # 监听所有网络接口，允许外部连接
PORT = 5000  # 监听 5000 端口
BUFFER_SIZE = 4096  # 每次从网络连接中读取数据的缓冲区大小

# --- 初始化 AI 模型 ---
print("正在加载 YOLOv8 模型...")
try:
    model = YOLO('yolov8n.pt')
    print("模型加载完成。服务器已准备就绪！")
except Exception as e:
    print(f"模型加载失败: {e}")
    # 在实际应用中，这里应该退出程序
    exit()

# --- 创建并启动服务器 ---
# 1. 创建一个 TCP/IP socket 对象
#    AF_INET 表示使用 IPv4 地址
#    SOCK_STREAM 表示使用 TCP 协议
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# 2. 将 socket 绑定到指定的地址和端口
server_socket.bind((HOST, PORT))

# 3. 开始监听传入的连接请求
#    参数 5 表示操作系统可以挂起的最大连接数量
server_socket.listen(5)
print(f"服务器正在 {HOST}:{PORT} 上监听...")

# 启动一个无限循环，以持续接受客户端连接
while True:
    print("\n...等待新的客户端连接...")
    # 4. 接受一个新连接。程序会在此处阻塞，直到有客户端连接进来
    #    accept() 会返回一个新的 socket 对象 (client_socket) 和客户端的地址 (client_address)
    client_socket, client_address = server_socket.accept()
    print(f"已接受来自 {client_address} 的连接")

    try:
        # 5. 从客户端接收图片数据
        #    创建一个空的字节串来存储接收到的数据
        image_data = b""
        #    循环接收数据，直到客户端关闭连接
        while True:
            # 从 socket 读取数据，最多读取 BUFFER_SIZE 字节
            chunk = client_socket.recv(BUFFER_SIZE)
            # 如果 recv 返回一个空字节串，说明客户端已经关闭了连接
            if not chunk:
                break
            # 将接收到的数据块拼接到 image_data
            image_data += chunk

        if not image_data:
            print("警告：未从客户端收到任何数据。")
            continue

        print(f"已接收到 {len(image_data)} 字节的图片数据")

        # 6. 将接收到的原始字节数据解码为 OpenCV 图像格式
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # 检查图片是否解码成功
        if img is None:
            print("错误：无法解码接收到的图片数据。")
            continue

        # 7. 【核心AI逻辑 - 完全复用！】
        #    使用加载好的 YOLO 模型对图像进行预测
        print("正在进行 AI 图像分析...")
        results = model(img)
        #    从结果中获取绘制了检测框和标签的图像
        annotated_img = results[0].plot()
        print("图像分析完成。")

        # 8. 将处理后的图像（numpy数组）编码回 JPEG 格式的字节流
        success, img_encoded = cv2.imencode('.jpg', annotated_img)
        result_bytes = img_encoded.tobytes()

        # 9. 将处理结果的字节流发送回客户端
        client_socket.sendall(result_bytes)
        print(f"已将 {len(result_bytes)} 字节的处理结果发送回客户端")

    except Exception as e:
        print(f"在处理来自 {client_address} 的请求时发生错误: {e}")
    finally:
        # 10. 无论成功还是失败，都要关闭与这个客户端的连接，以准备服务下一个客户端
        client_socket.close()
        print(f"与 {client_address} 的连接已关闭。")

