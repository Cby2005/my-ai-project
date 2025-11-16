import os
import uuid
from flask import Flask, request, render_template, jsonify, url_for, send_from_directory
from celery import Celery
from werkzeug.utils import secure_filename
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# 使用本地 Redis 配置
app.config.update(
    CELERY_BROKER_URL='redis://localhost:6379/0',
    CELERY_RESULT_BACKEND='redis://localhost:6379/0'
)

# 上传目录配置
UPLOAD_FOLDER = '/app/uploads'
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
# 注册任务
process_image_task = celery_app.signature('worker.process_image')
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
                    content_type = 'video/mp4'
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
                    task = process_video_task.delay(temp_path)
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


@app.route('/static/results/<path:path>')
def send_static_result(path):
    """提供 /static/results 下的文件"""
    return send_from_directory(os.path.join(STATIC_FOLDER, 'results'), path)


if __name__ == '__main__':
    print(f"Celery Broker URL: {app.config['CELERY_BROKER_URL']}")
    print(f"Celery Backend URL: {app.config['CELERY_RESULT_BACKEND']}")
    app.run(host='0.0.0.0', port=5000, debug=True)