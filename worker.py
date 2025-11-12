from celery import Celery
import cv2
import numpy as np
from ultralytics import YOLO
import base64  # 导入base64库
import os  # 导入os库

# --- Celery & AI 模型初始化 ---
# 'redis' 是我们在docker-compose.yml中定义的服务名
celery_app = Celery(
    'tasks',
    broker='redis://redis:6379/0',
    backend='redis://redis:6379/0'
)

print("Worker: 正在加载自定义模型...")
model = YOLO('best.pt')
print("Worker: 模型加载完成，准备接收任务！")


# --- 定义AI分析任务 (图片) ---
@celery_app.task(name='worker.process_image')
def process_image(image_bytes):
    print(f"Worker: 接收到新图片任务，数据大小 {len(image_bytes)} 字节")
    try:
        # --- 核心AI逻辑 ---
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            raise ValueError("无法解码图片")

        results = model(img)
        annotated_img = results[0].plot()

        # --- 【关键业务逻辑】 ---
        # 1. 统计每个类别的数量
        class_counts = {}
        for cls_id in results[0].boxes.cls:
            class_name = model.names[int(cls_id)]
            class_counts[class_name] = class_counts.get(class_name, 0) + 1

        total_objects = len(results[0].boxes.cls)
        print(f"Worker: 图片分析完成，共检测到 {total_objects} 个物体。")

        # 2. 将处理后的图片编码为JPEG格式，然后再次编码为Base64字符串
        success, img_encoded = cv2.imencode('.jpg', annotated_img)
        if not success:
            raise ValueError("结果图片编码失败")

        image_base64 = base64.b64encode(img_encoded).decode('utf-8')

        # 3. 构建最终的“分析报告”
        analysis_report = {
            "is_video": False,  # (新) 添加一个标志，告诉前端这是图片
            "image_data": image_base64,
            "analysis_data": {
                "total_objects": total_objects,
                "class_counts": class_counts
            }
        }
        return analysis_report

    except Exception as e:
        print(f"Worker: 图片任务处理失败: {e}")
        raise


# --- (新) 定义AI分析任务 (视频) ---
# --- (新) 定义AI分析任务 (视频) ---
@celery_app.task(name='worker.process_video')
def process_video(video_path):
    print(f"Worker: 接收到新视频任务，路径 {video_path}")
    try:
        # 定义结果保存路径 (对应 docker-compose.yml 中的共享卷)
        RESULT_DIR = "/app/static/results"
        os.makedirs(RESULT_DIR, exist_ok=True)

        # 原始文件名 (例如: "test_video.mp4")
        base_filename = os.path.basename(video_path)

        # (修改) 'name' 应该是 "run" 的名称，不应包含 .mp4
        # (例如: "test_video_result")
        result_run_name = f"{os.path.splitext(base_filename)[0]}_result"

        print(f"Worker: 开始处理视频: {base_filename}")

        # (修改) 'name' 参数现在使用不带 .mp4 的 'result_run_name'
        model.track(video_path, save=True, project=RESULT_DIR, name=result_run_name, exist_ok=True)

        # YOLO 会将视频保存在: <project>/<name>/<base_filename>
        # (例如: /app/static/results/test_video_result/test_video.mp4)

        # (修改) 我们的URL必须指向YOLO实际保存文件的位置
        result_url_path = f"/static/results/{result_run_name}/{base_filename}"

        # 打印新的保存路径
        print(f"Worker: 视频处理完成，保存在 {os.path.join(RESULT_DIR, result_run_name, base_filename)}")

        # 清理已处理的上传文件 (从 /app/uploads 删除)
        os.remove(video_path)

        # 3. 构建最终的“分析报告”
        analysis_report = {
            "is_video": True,
            "video_url": result_url_path,  # (修改) 返回正确的URL
            "analysis_data": {
                "total_objects": "N/A (视频处理)",
                "class_counts": {}
            }
        }
        return analysis_report

    except Exception as e:
        print(f"Worker: 视频任务处理失败: {e}")
        # 如果处理失败，也删除临时文件
        if os.path.exists(video_path):
            os.remove(video_path)
        raise