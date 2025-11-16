# (假设您已安装 Docker)
import os
import uuid
# 1. 在这里添加 send_from_directory
from flask import Flask, request, render_template, jsonify, url_for, send_from_directory, Response, send_file
from celery import Celery
from werkzeug.utils import secure_filename
from flask_cors import CORS  # 添加这行


app = Flask(__name__)
CORS(app)  # 添加这行
#app.config.update(
 #   CELERY_BROKER_URL='redis://redis:6379/0',
  #  CELERY_RESULT_BACKEND='redis://redis:6379/0'
#)
app.config.update(
    CELERY_BROKER_URL='redis://localhost:6379/0',  # 本地Redis
    CELERY_RESULT_BACKEND='redis://localhost:6379/0'
)

# 共享卷的路径，对应 docker-compose.yml
UPLOAD_FOLDER = '/app/uploads'
# (新) 我们需要知道静态文件夹的绝对路径
STATIC_FOLDER = '/app/static'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def make_celery(app):
    celery = Celery(
        app.import_name,
        backend=app.config['CELERY_RESULT_BACKEND'],
        broker=app.config['CELERY_BROKER_URL']
    )
    celery.conf.update(app.config)
    return celery


celery_app = make_celery(app)
# 注册图片处理任务
process_image_task = celery_app.signature('worker.process_image')
# (新) 注册视频处理任务，添加输出格式参数
process_video_task = celery_app.signature('worker.process_video')


# --- 路由定义 ---
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/detect', methods=['POST'])
def detect():
    try:
        print("收到检测请求...")

        if 'file' not in request.files:
            print("错误：请求中没有文件部分")
            return jsonify({"error": "请求中没有文件部分"}), 400

        file = request.files['file']
        print(f"文件名: {file.filename}")

        if file.filename == '':
            print("错误：没有选择任何文件")
            return jsonify({"error": "没有选择任何文件"}), 400

        if file:
            original_filename = file.filename
            _, ext = os.path.splitext(original_filename)
            print(f"文件扩展名: {ext}")

            if not ext:
                return jsonify({"error": "文件缺少扩展名"}), 400

            filename = f"{uuid.uuid4()}{ext}"
            print(f"生成的文件名: {filename}")

            # 修复：处理 content_type 为 None 的情况
            content_type = file.content_type
            print(f"原始文件类型: {content_type}")

            # 如果 content_type 为 None，根据文件扩展名推断
            if content_type is None:
                image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
                video_extensions = ['.mp4', '.avi', '.mov', '.webm', '.mkv', '.flv']

                if ext.lower() in image_extensions:
                    content_type = 'image/jpeg'
                elif ext.lower() in video_extensions:
                    content_type = 'video/webm'  # 改为webm
                else:
                    content_type = 'application/octet-stream'

                print(f"推断的文件类型: {content_type}")

            # 检查文件类型
            if content_type.startswith('image/'):
                print("处理图片文件...")
                image_bytes = file.read()
                print(f"图片大小: {len(image_bytes)} 字节")

                try:
                    task = process_image_task.delay(image_bytes)
                    print(f"任务已提交，ID: {task.id}")
                    return jsonify({
                        "task_id": task.id,
                        "status_url": url_for('task_status', task_id=task.id)
                    }), 202
                except Exception as e:
                    print(f"提交任务时出错: {str(e)}")
                    return jsonify({"error": f"提交任务失败: {str(e)}"}), 500

            elif content_type.startswith('video/'):
                print("处理视频文件...")
                temp_path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(temp_path)
                print(f"视频已保存到: {temp_path}")

                try:
                    # 修改：传递输出格式参数为webm
                    task = process_video_task.delay(temp_path, 'webm')
                    print(f"视频任务已提交，ID: {task.id}")
                    return jsonify({
                        "task_id": task.id,
                        "status_url": url_for('task_status', task_id=task.id)
                    }), 202
                except Exception as e:
                    print(f"提交视频任务时出错: {str(e)}")
                    return jsonify({"error": f"提交视频任务失败: {str(e)}"}), 500
            else:
                print(f"不支持的文件类型: {content_type}")
                return jsonify({"error": "不支持的文件类型，请上传图片或视频"}), 400

    except Exception as e:
        print(f"detect路由发生未捕获的异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"服务器内部错误: {str(e)}"}), 500


@app.route('/status/<task_id>')
def task_status(task_id):
    task = celery_app.AsyncResult(task_id)
    response = {'state': task.state, 'status': str(task.info)}
    if task.state == 'SUCCESS':
        response['result_url'] = url_for('get_result', task_id=task.id)
    return jsonify(response)


@app.route('/result/<task_id>')
def get_result(task_id):
    """根据任务ID获取完整的JSON分析报告"""
    task = celery_app.AsyncResult(task_id)
    if task.ready() and task.state == 'SUCCESS':
        analysis_report = task.get()
        return jsonify(analysis_report)
    else:
        return jsonify({"error": "任务尚未完成或已失败"}), 404


# --- 2. 【新增的路由】，用于提供 /static/results 下的文件 ---
@app.route('/static/results/<path:filename>')
def send_static_result(filename):
    """
    提供 /static/results 下的文件，支持范围请求
    """
    try:
        # 获取项目根目录
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # 构建静态文件目录的绝对路径
        static_results_dir = os.path.join(base_dir, 'static', 'results')

        print(f"请求静态文件: {filename}")
        print(f"静态文件目录: {static_results_dir}")

        # 构建完整文件路径
        full_path = os.path.join(static_results_dir, filename)
        print(f"完整文件路径: {full_path}")

        # 检查文件是否存在
        if not os.path.exists(full_path):
            print(f"文件不存在: {full_path}")

            # 列出静态目录内容以便调试
            if os.path.exists(static_results_dir):
                print(f"静态目录内容: {os.listdir(static_results_dir)}")

            return jsonify({"error": f"文件未找到: {filename}"}), 404

        print(f"文件存在，准备发送: {full_path}")

        # 获取文件大小
        file_size = os.path.getsize(full_path)

        # 处理范围请求
        range_header = request.headers.get('Range', None)

        if not range_header:
            # 没有范围请求，返回整个文件
            response = send_file(full_path)
        else:
            # 解析范围请求
            byte1, byte2 = 0, None
            range_header = range_header.replace('bytes=', '').split('-')

            if range_header[0]:
                byte1 = int(range_header[0])
            if range_header[1]:
                byte2 = int(range_header[1])

            length = file_size - byte1
            if byte2 is not None:
                length = byte2 - byte1 + 1

            # 读取部分文件内容
            with open(full_path, 'rb') as f:
                f.seek(byte1)
                data = f.read(length)

            # 构建部分内容响应
            response = Response(data,
                                206,  # Partial Content
                                mimetype='video/webm',  # 改为webm
                                direct_passthrough=True)

            response.headers.add('Content-Range',
                                 f'bytes {byte1}-{byte1 + length - 1}/{file_size}')
            response.headers.add('Content-Length', str(length))

        # 设置正确的MIME类型
        if filename.lower().endswith('.avi'):
            response.headers['Content-Type'] = 'video/x-msvideo'
        elif filename.lower().endswith('.mp4'):
            response.headers['Content-Type'] = 'video/mp4'
        elif filename.lower().endswith('.webm'):
            response.headers['Content-Type'] = 'video/webm'  # webm类型
        else:
            response.headers['Content-Type'] = 'video/webm'  # 默认改为webm

        # 添加范围请求支持头
        response.headers['Accept-Ranges'] = 'bytes'
        response.headers['Cache-Control'] = 'no-cache'

        # 添加CORS头
        response.headers.add('Access-Control-Allow-Origin', '*')

        return response

    except Exception as e:
        print(f"提供静态文件时出错: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

from flask import  render_template_string


@app.route('/video/<path:filename>')
def serve_video_optimized(filename):
    """
    专门为视频文件优化的服务路由，支持范围请求
    """
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        video_path = os.path.join(base_dir, 'static', 'results', filename)

        if not os.path.exists(video_path):
            return "Video not found", 404

        file_size = os.path.getsize(video_path)
        range_header = request.headers.get('Range', None)

        # 设置正确的MIME类型
        if filename.lower().endswith('.mp4'):
            mimetype = 'video/mp4'
        elif filename.lower().endswith('.avi'):
            mimetype = 'video/x-msvideo'
        elif filename.lower().endswith('.webm'):
            mimetype = 'video/webm'  # webm类型
        else:
            mimetype = 'video/webm'  # 默认改为webm

        if not range_header:
            # 完整文件请求
            response = send_file(video_path, mimetype=mimetype)
            response.headers['Content-Length'] = str(file_size)
        else:
            # 范围请求
            byte1, byte2 = 0, None
            range_header = range_header.replace('bytes=', '').split('-')

            if range_header[0]:
                byte1 = int(range_header[0])
            if range_header[1]:
                byte2 = int(range_header[1])

            length = file_size - byte1
            if byte2 is not None:
                length = byte2 - byte1 + 1

            with open(video_path, 'rb') as f:
                f.seek(byte1)
                data = f.read(length)

            response = Response(data, 206, mimetype=mimetype)
            response.headers.add('Content-Range', f'bytes {byte1}-{byte1 + length - 1}/{file_size}')
            response.headers.add('Content-Length', str(length))

        # 设置必要的头部
        response.headers['Accept-Ranges'] = 'bytes'
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['Access-Control-Allow-Origin'] = '*'

        return response

    except Exception as e:
        print(f"视频服务错误: {e}")
        return str(e), 500


# 更新测试页面使用新的视频路由
@app.route('/optimized_video_test')
def optimized_video_test():
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>优化视频测试</title>
</head>
<body style="margin: 20px;">
    <h1>优化视频播放测试</h1>

    <div>
        <h3>测试1: 使用原始路由</h3>
        <video controls width="800" height="450">
            <source src="/static/results/8f505dc3-13f6-495a-881b-2e699d5735ff_result/8f505dc3-13f6-495a-881b-2e699d5735ff.webm" type="video/webm">
        </video>
    </div>

    <div>
        <h3>测试2: 使用优化路由</h3>
        <video controls width="800" height="450">
            <source src="/video/8f505dc3-13f6-495a-881b-2e699d5735ff_result/8f505dc3-13f6-495a-881b-2e699d5735ff.webm" type="video/webm">
        </video>
    </div>

    <script>
        // 添加错误监听
        document.querySelectorAll('video').forEach(video => {
            video.addEventListener('error', function(e) {
                console.log('视频错误:', this.error, 'src:', this.src);
            });
            video.addEventListener('loadeddata', function() {
                console.log('视频数据加载:', this.src);
            });
        });
    </script>
</body>
</html>
    ''')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)