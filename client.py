# 导入 socket 库，用于网络通信
import socket

# --- 配置区 ---
# !! 重要 !!
# 1. 在你的电脑上本地测试服务器时, 请将 SERVER_HOST 设置为 '127.0.0.1'
# 2. 当你将服务器部署到云端后, 请将 SERVER_HOST 替换成你【服务器的公网IP地址】
SERVER_HOST = '39.103.63.159'
SERVER_PORT = 5000
IMAGE_PATH = 'test_image.jpg'  # 要发送进行分析的图片文件名
RESULT_PATH = 'result_from_server.jpg'  # 从服务器接收到的结果，要保存的文件名
BUFFER_SIZE = 4096  # 每次从网络连接中读取数据的缓冲区大小

# --- 创建客户端并连接 ---
# 1. 创建一个 TCP/IP socket 对象
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    # 2. 连接到服务器
    print(f"正在连接到服务器 {SERVER_HOST}:{SERVER_PORT}...")
    client_socket.connect((SERVER_HOST, SERVER_PORT))
    print("连接成功！")

    # 3. 读取本地图片文件并发送到服务器
    #    'rb' 表示以二进制读取模式打开文件
    with open(IMAGE_PATH, 'rb') as f:
        image_data = f.read()
    #    sendall 会持续发送数据，直到所有数据都已发送完毕
    client_socket.sendall(image_data)
    #    发送完毕后，关闭写入流，这会向服务器发送一个信号，表示数据已发送完成
    client_socket.shutdown(socket.SHUT_WR)
    print(f"已将 '{IMAGE_PATH}' ({len(image_data)} 字节) 的图片数据发送到服务器")

    # 4. 接收服务器返回的处理结果
    print("正在等待服务器返回处理结果...")
    result_data = b""
    #    循环接收数据，直到服务器关闭连接
    while True:
        chunk = client_socket.recv(BUFFER_SIZE)
        if not chunk:
            break
        result_data += chunk

    # 5. 如果收到了数据，就将其保存为文件
    if result_data:
        with open(RESULT_PATH, 'wb') as f:
            f.write(result_data)
        print(f"成功！已将从服务器收到的结果保存为 '{RESULT_PATH}'")
    else:
        print("警告：未收到服务器的返回结果。")

except FileNotFoundError:
    print(f"错误：找不到要发送的图片文件 '{IMAGE_PATH}'。请确保该文件与脚本在同一个文件夹下。")
except ConnectionRefusedError:
    print(f"错误：连接被服务器拒绝。请确认服务器脚本 app.py 是否正在运行，并且IP地址和端口正确。")
except Exception as e:
    print(f"发生了一个未知错误: {e}")
finally:
    # 6. 无论成功与否，都要关闭与服务器的连接
    client_socket.close()
    print("与服务器的连接已关闭。")

