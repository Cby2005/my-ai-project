from flask import Flask, request, render_template, send_file, Response
import socket
import io

# --- 配置 ---
app = Flask(__name__)
AI_SERVER_HOST = 'ai_server'  # Docker Compose会自动将这个名字解析为AI服务器的IP
AI_SERVER_PORT = 5001  # 我们为AI服务指定一个新的端口
BUFFER_SIZE = 4096


# --- 网页页面路由 ---
@app.route('/')
def index():
    return render_template('index.html')


# --- “翻译”API路由 ---
@app.route('/detect', methods=['POST'])
def detect():
    if 'file' not in request.files:
        return "No file part", 400
    file = request.files['file']
    if file.filename == '':
        return "No selected file", 400

    if file:
        image_bytes = file.read()

        # Flask应用在这里扮演了Socket客户端的角色！
        try:
            # 1. 创建socket并连接到幕后的AI服务器
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((AI_SERVER_HOST, AI_SERVER_PORT))

                # 2. 发送图片数据
                s.sendall(image_bytes)
                s.shutdown(socket.SHUT_WR)  # 告知AI服务器数据已发完

                # 3. 接收AI服务器返回的结果
                result_data = b""
                while True:
                    chunk = s.recv(BUFFER_SIZE)
                    if not chunk:
                        break
                    result_data += chunk

                if not result_data:
                    return "AI server returned no data", 500

                # 4. 将结果图片作为响应发回给浏览器
                return send_file(
                    io.BytesIO(result_data),
                    mimetype='image/jpeg'
                )
        except Exception as e:
            print(f"Error communicating with AI server: {e}")
            return f"Error communicating with AI server: {e}", 500


if __name__ == '__main__':
    # 注意：这里的端口是给浏览器访问的
    app.run(host='0.0.0.0', port=5000)
