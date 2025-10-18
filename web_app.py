from flask import Flask, request, render_template, jsonify, url_for
from celery import Celery

# --- Flask & Celery 配置 (无变化) ---
app = Flask(__name__)
app.config.update(
    CELERY_BROKER_URL='redis://redis:6379/0',
    CELERY_RESULT_BACKEND='redis://redis:6379/0'
)

def make_celery(app):
    celery = Celery(
        app.import_name,
        backend=app.config['CELERY_RESULT_BACKEND'],
        broker=app.config['CELERY_BROKER_URL']
    )
    celery.conf.update(app.config)
    return celery

celery_app = make_celery(app)
process_image = celery_app.signature('worker.process_image')

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
        image_bytes = file.read()
        task = process_image.delay(image_bytes)
        return jsonify({
            "task_id": task.id,
            "status_url": url_for('task_status', task_id=task.id)
        }), 202

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

