import socket
import cv2
import numpy as np
from ultralytics import YOLO

# --- 配置 ---
HOST = '0.0.0.0'  # 监听所有网络接口
PORT = 5001  # 【关键修正】为AI服务明确指定专属的内部端口 5001
BUFFER_SIZE = 4096

# --- 初始化AI模型 ---
print("AI Server: 正在加载YOLOv8模型...")
model = YOLO('yolov8n.pt')
print("AI Server: 模型加载完成。")

# --- 创建并启动服务器 ---
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen(5)
print(f"AI Server: 正在 {HOST}:{PORT} 上监听...")

while True:
    print("\nAI Server: 等待新的内部连接...")
    client_socket, client_address = server_socket.accept()
    print(f"AI Server: 接受来自 {client_address} (Web网关) 的连接")

    try:
        image_data = b""
        while True:
            chunk = client_socket.recv(BUFFER_SIZE)
            if not chunk:
                break
            image_data += chunk

        if not image_data:
            continue

        print(f"AI Server: 接收到 {len(image_data)} 字节数据")
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            print("AI Server Error: 无法解码图片")
            continue

        results = model(img)
        annotated_img = results[0].plot()

        success, img_encoded = cv2.imencode('.jpg', annotated_img)
        result_bytes = img_encoded.tobytes()

        client_socket.sendall(result_bytes)
        print(f"AI Server: 已发送 {len(result_bytes)} 字节结果")

    except Exception as e:
        print(f"AI Server Error: 处理时发生错误: {e}")
    finally:
        client_socket.close()
        print(f"AI Server: 与 {client_address} 的连接已关闭")

