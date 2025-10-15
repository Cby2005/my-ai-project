from flask import Flask, request, send_file, jsonify
from ultralytics import YOLO
import cv2
import numpy as np
import io

# ----------------- 初始化 -----------------
# 初始化Flask Web应用
app = Flask(__name__)

# 加载预训练的YOLOv8n模型 (n代表nano, 是最小最快的版本)
# 模型文件 'yolov8n.pt' 会在第一次运行时自动下载，请确保网络连接正常
print("正在加载YOLOv8模型，首次运行需要下载模型文件，请稍候...")
try:
    model = YOLO('yolov8n.pt')
    print("模型加载完成。服务器准备就绪！")
except Exception as e:
    print(f"模型加载失败: {e}")
    print("请检查你的网络连接是否正常，以及ultralytics库是否已正确安装。")
    # 如果模型加载失败，后续请求将无法处理，但服务器仍会启动以报告错误。
    model = None


# -----------------------------------------


# ----------------- API端点定义 -----------------
# 定义一个API端点(endpoint)，URL路径为 /detect
# 这个端点只接受POST请求
@app.route('/detect', methods=['POST'])
def detect_objects():
    """
    接收上传的图片文件，进行物体检测，并返回带有标注的结果图片。
    """
    # 检查模型是否已成功加载
    if model is None:
        return jsonify({"error": "模型未成功加载，无法处理请求"}), 500

    # 1. 检查请求中是否包含名为 'file' 的文件部分
    if 'file' not in request.files:
        # 如果没有文件，返回一个JSON格式的错误信息和400状态码 (错误的请求)
        return jsonify({"error": "请求中没有文件部分"}), 400

    file = request.files['file']

    # 2. 检查用户是否选择了文件（文件名是否为空）
    if file.filename == '':
        return jsonify({"error": "没有选择文件"}), 400

    # 3. 如果文件存在且有效，则进行处理
    if file:
        try:
            # a. 读取上传的图片文件数据流
            image_bytes = file.read()

            # b. 将原始字节数据转换为OpenCV可以处理的图像格式
            #    首先转为numpy一维数组
            nparr = np.frombuffer(image_bytes, np.uint8)
            #    然后从数组解码为三维图像矩阵 (height, width, channels)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            # c. 【核心步骤】使用加载好的YOLO模型对图像进行预测
            results = model(img)

            # d. 从模型结果中获取绘制了检测框和标签的图像
            #    results[0] 代表对第一张（也是唯一一张）图片的处理结果
            #    .plot() 方法是一个便捷函数，可以自动完成绘制工作
            annotated_img = results[0].plot()

            # e. 将处理后的图像（numpy数组格式）编码回JPEG格式的字节流
            #    cv2.imencode会返回一个元组 (True/False, 编码后的数据)
            success, img_encoded = cv2.imencode('.jpg', annotated_img)

            if not success:
                return jsonify({"error": "图像编码失败"}), 500

            # f. 使用send_file函数将图片字节流作为文件直接返回给客户端
            return send_file(
                io.BytesIO(img_encoded.tobytes()),
                mimetype='image/jpeg',  # 告诉客户端这是一个JPEG图片
                as_attachment=True,  # 建议客户端作为附件下载
                download_name='result.jpg'  # 客户端下载时默认的文件名
            )
        except Exception as e:
            # 如果处理过程中发生任何错误，返回一个服务器内部错误信息
            return jsonify({"error": "处理图片时发生未知错误", "details": str(e)}), 500


# -----------------------------------------------


# ----------------- 启动服务器 -----------------
# 确保当这个脚本被直接执行时 (而不是被其他脚本导入时)，才运行Flask应用
if __name__ == '__main__':
    # app.run() 会启动一个本地的Web服务器
    # host='0.0.0.0' 表示服务器会监听你电脑上所有的网络接口（比如Wi-Fi, 以太网）
    # 这意味着不仅你自己能访问(通过127.0.0.1)，同一局域网下的其他设备也能访问(通过你的局域网IP)
    # port=5000 指定服务运行在5000端口
    # debug=True 表示开启调试模式，这在你开发时非常有用：
    #            1. 代码修改后服务器会自动重启。
    #            2. 发生错误时会在浏览器和终端里显示详细的错误追踪信息。
    #            注意：在最终的生产部署时，应关闭debug模式。
    print("服务器即将在 http://127.0.0.1:5000 上启动...")
    print("你也可以在局域网内通过 http://<你的局域网IP>:5000 访问")
    app.run(host='0.0.0.0', port=5000, debug=True)
# ---------------------------------------------
