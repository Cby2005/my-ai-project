import os
from flask import Flask, request, render_template, jsonify, url_for
from celery import Celery
from werkzeug.utils import secure_filename  # 导入安全文件名工具

app = Flask(__name__)
app.config.update(
    CELERY_BROKER_URL='redis://redis:6379/0',
    CELERY_RESULT_BACKEND='redis://redis:6379/0'
)

# 共享卷的路径，对应 docker-compose.yml
UPLOAD_FOLDER = '/app/uploads'
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
        # 获取安全的文件名
        filename = secure_filename(file.filename)

        # 检查文件类型
        if file.content_type.startswith('image/'):
            # --- 图片处理逻辑 (基本不变) ---
            image_bytes = file.read()
            task = process_image_task.delay(image_bytes)  #
            return jsonify({
                "task_id": task.id,
                "status_url": url_for('task_status', task_id=task.id)
            }), 202

        elif file.content_type.startswith('video/'):
            # --- 视频处理逻辑 (新) ---
            # 将视频保存到共享卷的临时上传目录
            temp_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(temp_path)

            # 调用新的视频任务，传递的是文件路径，而不是文件内容
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
        # 如果成功，直接在状态查询里就返回结果URL
        response['result_url'] = url_for('get_result', task_id=task.id)
    return jsonify(response)


@app.route('/result/<task_id>')
def get_result(task_id):
    """根据任务ID获取完整的JSON分析报告"""
    task = celery_app.AsyncResult(task_id)
    if task.ready() and task.state == 'SUCCESS':
        # 从Celery结果后端获取完整的“分析报告”字典
        analysis_report = task.get()
        # 将这个字典作为JSON响应直接返回给前端
        return jsonify(analysis_report)
    else:
        return jsonify({"error": "任务尚未完成或已失败"}), 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)