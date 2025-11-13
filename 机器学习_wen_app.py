# 您的原始 'web_app.py' 修改而来
import os
import json
import uuid
from flask import Flask, request, render_template, jsonify, send_from_directory
from redis import Redis

# --- 配置 ---
app = Flask(__name__, static_folder='static')
# 确保 'static' 文件夹存在，用于存放结果图片
if not os.path.exists('static'):
    os.makedirs('static')

# 连接 Redis
# (请确保 Redis 服务正在运行, 与您 docker-compose.yml 中配置的一致)
try:
    redis_conn = Redis(host=os.getenv('REDIS_HOST', 'localhost'), port=6379, db=0)
    redis_conn.ping()
    print("成功连接到 Redis")
except Exception as e:
    print(f"无法连接到 Redis: {e}")
    # 在实际应用中，这里可能应该退出

UPLOAD_FOLDER = 'uploads'  # 临时存放上传文件的文件夹
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# --- 路由 ---

@app.route('/')
def index():
    """
    渲染主页面
    """
    # [修改] 渲染新的 HTML 文件
    return render_template('机器学习_index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """
    处理文件上传，并将任务推送到 Redis 队列
    """
    if 'image' not in request.files:
        return jsonify({'error': '没有文件部分'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400

    if file:
        # 生成一个唯一的 job_id
        job_id = str(uuid.uuid4())

        # 保存原始图片 (可选, 但有助于调试)
        # filename = f"{job_id}_{file.filename}"
        # raw_image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        # file.save(raw_image_path)

        # 重置文件读取指针
        file.seek(0)
        image_bytes = file.read()

        # !!! [核心修改] !!!
        # 从表单获取用户选择的模型
        model_choice = request.form.get('model_select', 'yolov8n')  # 默认为 yolov8n

        # 准备要推送到 Redis 的作业数据
        job_data = {
            'job_id': job_id,
            'image_data_b64': json.dumps(list(image_bytes)),  # 简单的序列化
            'original_filename': file.filename,
            'model_choice': model_choice  # <--- 将模型选择传递给 worker
        }

        try:
            # 推送作业到 'image_queue'
            redis_conn.rpush('image_queue', json.dumps(job_data))

            # 立即返回 job_id，前端将用它来轮询结果
            return jsonify({'job_id': job_id})

        except Exception as e:
            return jsonify({'error': f'无法推送到 Redis: {e}'}), 500

    return jsonify({'error': '未知错误'}), 500


@app.route('/result/<job_id>')
def get_result(job_id):
    """
    前端轮询此端点以检查作业状态
    """
    try:
        # 从 Redis 中按 job_id 检查结果
        result_key = f"job:{job_id}"
        result_data = redis_conn.get(result_key)

        if result_data:
            # 找到结果，任务已完成
            result = json.loads(result_data.decode('utf-8'))
            return jsonify(result)
        else:
            # 没找到结果，任务仍在队列中或正在处理
            return jsonify({'status': 'pending'})

    except Exception as e:
        return jsonify({'status': 'failed', 'error': f'检查结果时出错: {e}'}), 500


@app.route('/static/<path:filename>')
def static_files(filename):
    """
    提供静态文件 (例如结果图片)
    """
    return send_from_directory(app.config['STATIC_FOLDER'], filename)


# --- 启动 ---
if __name__ == '__main__':
    # 注意：在生产环境中，应使用 Gunicorn 或 uWSGI
    app.run(debug=True, host='0.0.0.0', port=5000)