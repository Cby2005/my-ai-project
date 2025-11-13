# 您的原始 'worker.py' 修改而来
import torch
import os
import json
import time
from redis import Redis
from ultralytics import YOLO
from PIL import Image
import io

# -------------------------------------------------------------------
# !!! [核心修改 1]: 加载所有模型 !!!
# -------------------------------------------------------------------
print("--- 机器学习 Worker 启动 ---")

# !!! 警告: 这会占用大量内存/显存 !!!
# 确保您的服务器有足够的资源
print("正在加载所有对比模型，请稍候...")
models = {}
try:
    # (确保这些 .pt 文件与 `机器学习_train.py` 的输出路径一致)
    models = {
        'yolov8n': YOLO('runs/detect/机器学习_YOLOv8n_对比/weights/best.pt'),
        'yolov8s': YOLO('runs/detect/机器学习_YOLOv8s_对比/weights/best.pt'),
        'rtdetr_l': YOLO('runs/detect/机器学习_RTDETR-L_对比/weights/best.pt')
    }
    # (可选) 将模型移到 GPU
    if torch.cuda.is_available():
        print("正在将模型移动到 GPU...")
        for key in models:
            models[key].to('cuda')
    print("--- 所有模型加载完毕 ---")
except Exception as e:
    print(f"[!! 致命错误 !!] 加载模型失败: {e}")
    print("请确保您已成功运行 '机器学习_train.py' 并且权重文件路径正确。")
    # 在实际应用中，这里应该退出

# 确保 'static' 文件夹存在
STATIC_FOLDER = 'static'
if not os.path.exists(STATIC_FOLDER):
    os.makedirs(STATIC_FOLDER)

# --- 连接 Redis ---
try:
    redis_conn = Redis(host=os.getenv('REDIS_HOST', 'localhost'), port=6379, db=0)
    redis_conn.ping()
    print("Worker 成功连接到 Redis")
except Exception as e:
    print(f"Worker 无法连接到 Redis: {e}")


# --- 核心处理函数 ---
def process_image(job_data_str: str):
    """
    从队列中取出一个作业并处理
    """
    try:
        job_data = json.loads(job_data_str)
        job_id = job_data['job_id']
        result_key = f"job:{job_id}"

        print(f"\n[处理作业: {job_id}]")

        # 1. 解码图片
        image_data_list = json.loads(job_data['image_data_b64'])
        image_bytes = bytes(image_data_list)
        image = Image.open(io.BytesIO(image_bytes))

        # 2. !!! [核心修改 2]: 根据选择获取模型 !!!
        model_choice = job_data.get('model_choice', 'yolov8n')
        model = models.get(model_choice)

        if model is None:
            print(f"错误: 无法找到模型 '{model_choice}'")
            raise Exception(f"未知的模型: {model_choice}")

        print(f"使用模型: {model_choice}")

        # 3. 执行推理
        start_time = time.time()
        results = model(image)  # 在图片上运行检测
        end_time = time.time()

        print(f"推理耗时: {end_time - start_time:.2f} 秒")

        # 4. 保存结果图片
        # (YOLOv8 的 results[0].save() 会自动绘制边界框)
        result_filename = f"{job_id}_result.jpg"
        result_image_path = os.path.join(STATIC_FOLDER, result_filename)
        results[0].save(filename=result_image_path)

        print(f"结果已保存到: {result_image_path}")

        # 5. 构建要存回 Redis 的结果
        result_data_to_store = {
            'status': 'completed',
            'job_id': job_id,
            'model_used': model_choice,
            'inference_time_seconds': end_time - start_time,
            'image_url': f"/{result_image_path}"  # 前端可以访问的 URL
        }

        # 6. 将结果存入 Redis (并设置过期时间, e.g., 1小时)
        redis_conn.set(result_key, json.dumps(result_data_to_store), ex=3600)

    except Exception as e:
        print(f"[!! 作业失败 !!] Job {job_id}: {e}")
        # (可选) 向 Redis 报告失败
        job_id = job_data.get('job_id', 'unknown')
        result_key = f"job:{job_id}"
        error_data = {
            'status': 'failed',
            'job_id': job_id,
            'error': str(e)
        }
        redis_conn.set(result_key, json.dumps(error_data), ex=3600)


# --- Worker 主循环 ---
def main():
    print("Worker 正在等待 'image_queue' 中的作业...")
    while True:
        try:
            # 阻塞式地从 'image_queue' 队列左侧弹出一个作业
            # 'blpop' 返回一个元组 (队列名, 作业数据)
            queue_name, job_data_str = redis_conn.blpop('image_queue')

            if job_data_str:
                process_image(job_data_str.decode('utf-8'))

        except redis.exceptions.ConnectionError as e:
            print(f"Redis 连接断开: {e}。正在尝试重连...")
            time.sleep(5)
            # (重新连接逻辑)
        except Exception as e:
            print(f"处理循环中发生未知错误: {e}")
            time.sleep(1)


if __name__ == '__main__':
    main()