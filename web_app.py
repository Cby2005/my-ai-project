# (假设您已安装 Docker)
import os
import uuid
# 1. 在这里添加 send_from_directory
from flask import Flask, request, render_template, jsonify, url_for, send_from_directory
from celery import Celery
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config.update(
    CELERY_BROKER_URL='redis://redis:6379/0',
    CELERY_RESULT_BACKEND='redis://redis:6379/0'
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
# (新) 注册视频处理任务
process_video_task = celery_app.signature('worker.process_video')


# --- 路由定义 ---
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/detect', methods=['POST'])
def detect():
    if 'file' not in request.files:
        return jsonify({"error": "请求中没有文件部分"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "没有选择任何文件"}), 400

    if file:

        # --- 这是【UUID 修复】---
        original_filename = file.filename
        _, ext = os.path.splitext(original_filename)

        if not ext:
            return jsonify({"error": "文件缺少 .webm, .mp4 等扩展名"}), 400

        filename = f"{uuid.uuid4()}{ext}"
        # --- 【UUID 修复】结束 ---

        # 检查文件类型
        if file.content_type.startswith('image/'):
            image_bytes = file.read()
            task = process_image_task.delay(image_bytes)
            return jsonify({
                "task_id": task.id,
                "status_url": url_for('task_status', task_id=task.id)
            }), 202

        elif file.content_type.startswith('video/'):
            temp_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(temp_path)
            task = process_video_task.delay(temp_path)
            return jsonify({
                "task_id": task.id,
                "status_url": url_for('task_status', task_id=task.id)
            }), 202
        else:
            return jsonify({"error": "不支持的文件类型，请上传图片或视频"}), 400


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
@app.route('/static/results/<path:path>')
def send_static_result(path):
    """
    这个新路由会捕获所有 /static/results/ 开头的请求
    'path' 变量会包含 URL 中 'results/' 之后的所有内容
    例如: "a4985629..._result/a4985629....webm"
    """
    # 我们从 '/app/static/results' 目录中安全地发送文件
    return send_from_directory(os.path.join(STATIC_FOLDER, 'results'), path)


# --- 【新增路由】结束 ---


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)