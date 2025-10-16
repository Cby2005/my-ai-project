from flask import Flask, request, render_template, send_file, Response, jsonify
import socket
import io

# --- 配置 ---
app = Flask(__name__)
# Docker Compose会自动将这个服务名解析为AI服务器的IP地址
# 在docker-compose.yml中，我们定义了AI服务器的服务名为 'ai_server'
AI_SERVER_HOST = 'ai_server'
AI_SERVER_PORT = 5001  # 我们为AI服务指定的内部端口
BUFFER_SIZE = 4096


# --- 网页页面路由 ---
@app.route('/')
def index():
    """向用户显示主网页 (index.html)。"""
    return render_template('index.html')


# --- “翻译”API路由，增加了更健壮的错误处理 ---
@app.route('/detect', methods=['POST'])
def detect():
    """
    处理来自网页的图片上传请求，
    通过socket连接到后端的AI分析服务，
    并将结果返回给前端。
    """
    # 1. 检查文件是否存在
    if 'file' not in request.files:
        return jsonify({"error": "请求中没有文件部分"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "没有选择任何文件"}), 400

    if file:
        image_bytes = file.read()

        # 2. 【关键升级】使用一个大的try...except块包裹所有与后端服务的通信
        #    这样无论后端发生任何网络错误，这个网关服务本身都不会崩溃。
        try:
            # 创建一个新的socket，每次请求都新建一个连接，更稳定
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                # 设置一个超时时间，防止后端服务无响应时无限等待
                s.settimeout(30)  # 30秒超时

                print(f"Web Gateway: 正在连接到 AI 服务器 {AI_SERVER_HOST}:{AI_SERVER_PORT}...")
                s.connect((AI_SERVER_HOST, AI_SERVER_PORT))
                print("Web Gateway: 连接成功。")

                # 发送图片数据
                s.sendall(image_bytes)
                s.shutdown(socket.SHUT_WR)  # 告知AI服务器数据已发完
                print(f"Web Gateway: 已发送 {len(image_bytes)} 字节数据。")

                # 接收AI服务器返回的结果
                print("Web Gateway: 正在等待AI服务器返回结果...")
                result_data = b""
                while True:
                    chunk = s.recv(BUFFER_SIZE)
                    if not chunk:
                        break
                    result_data += chunk

                if not result_data:
                    print("Web Gateway Error: AI服务器返回了空数据。")
                    # 返回一个JSON错误，而不是崩溃
                    return jsonify({"error": "AI服务器返回了空数据"}), 500

                print(f"Web Gateway: 已接收 {len(result_data)} 字节结果。")

                # 将结果图片作为响应发回给浏览器
                return send_file(
                    io.BytesIO(result_data),
                    mimetype='image/jpeg'
                )

        # 3. 捕获所有可能的异常，并返回一个清晰的JSON错误给前端
        except socket.timeout:
            print("Web Gateway Error: 连接AI服务器超时。")
            return jsonify({"error": "连接AI服务器超时，它可能正忙或已离线。"}), 504  # Gateway Timeout
        except ConnectionRefusedError:
            print("Web Gateway Error: AI服务器拒绝连接。")
            return jsonify({"error": "AI服务器拒绝连接，请检查它是否正在运行。"}), 503  # Service Unavailable
        except Exception as e:
            # 捕获所有其他未知错误
            print(f"Web Gateway Error: 与AI服务器通信时发生未知错误: {e}")
            return jsonify({"error": f"与AI服务器通信时发生未知错误: {e}"}), 500  # Internal Server Error


if __name__ == '__main__':
    # 这里的端口是给浏览器访问的
    app.run(host='0.0.0.0', port=5000)

