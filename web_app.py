from flask import Flask, request, render_template, jsonify, url_for, send_file
from celery import Celery
import io

# --- Flask & Celery 配置 ---
app = Flask(__name__)
# 使用Redis作为Celery的消息代理和结果后端
# 'redis' 是我们在docker-compose.yml中定义的服务名
app.config.update(
    CELERY_BROKER_URL='redis://redis:6379/0',
    CELERY_RESULT_BACKEND='redis://redis:6379/0'
)

# --- 初始化Celery ---
def make_celery(app):
    celery = Celery(
        app.import_name,
        backend=app.config['CELERY_RESULT_BACKEND'],
        broker=app.config['CELERY_BROKER_URL']
    )
    celery.conf.update(app.config)
    return celery

celery_app = make_celery(app)
# 我们需要从worker文件中导入真正的任务
# 注意: 这里的 'worker.process_image' 指的是 worker.py 文件里的 process_image 任务
process_image = celery_app.signature('worker.process_image')

# --- 路由定义 ---
@app.route('/')
def index():
    """显示主网页"""
    return render_template('index.html')

@app.route('/detect', methods=['POST'])
def detect():
    """接收图片，派发AI分析任务，并立即返回任务ID"""
    if 'file' not in request.files:
        return jsonify({"error": "请求中没有文件部分"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "没有选择任何文件"}), 400

    if file:
        image_bytes = file.read()
        # 【关键改变】调用 .delay() 将任务异步发送给Celery
        task = process_image.delay(image_bytes)
        # 立即返回一个包含任务ID和查询URL的JSON响应
        return jsonify({
            "task_id": task.id,
            "status_url": url_for('task_status', task_id=task.id)
        }), 202 # 202 Accepted: 表示请求已被接受，但处理尚未完成

@app.route('/status/<task_id>')
def task_status(task_id):
    """根据任务ID查询任务状态"""
    task = celery_app.AsyncResult(task_id)
    if task.state == 'PENDING':
        # 任务还在等待或正在处理
        response = {'state': task.state, 'status': '等待中或正在处理...'}
    elif task.state != 'FAILURE':
        # 任务成功完成
        response = {
            'state': task.state,
            'status': '处理完成',
            'result_url': url_for('get_result', task_id=task.id)
        }
    else:
        # 任务失败
        response = {
            'state': task.state,
            'status': str(task.info),  # 获取异常信息
        }
    return jsonify(response)

@app.route('/result/<task_id>')
def get_result(task_id):
    """根据任务ID获取结果图片"""
    task = celery_app.AsyncResult(task_id)
    if task.ready():
        # 从Celery结果后端获取二进制图片数据
        image_data = task.get()
        return send_file(io.BytesIO(image_data), mimetype='image/jpeg')
    else:
        return jsonify({"error": "任务尚未完成"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)