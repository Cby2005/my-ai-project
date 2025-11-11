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
# 注意：这里我们加载您在 Roboflow 上训练的新模型
# 请确保您已经下载了 best.pt 并将其与此文件放在同一目录
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
@celery_app.task(name='worker.process_video')
def process_video(video_path):
    print(f"Worker: 接收到新视频任务，路径 {video_path}")
    try:
        # 定义结果保存路径 (对应 docker-compose.yml 中的共享卷)
        RESULT_DIR = "/app/static/results"
        os.makedirs(RESULT_DIR, exist_ok=True)

        # 创建一个安全的结果文件名
        base_filename = os.path.basename(video_path)
        result_filename = f"{os.path.splitext(base_filename)[0]}_result.mp4"

        # --- 核心AI逻辑 (处理视频) ---
        # 使用 model.track() 进行目标跟踪，效果更好
        # YOLOv8 会自动处理视频的读写
        # 'project' 定义保存的根目录
        # 'name' 定义保存的文件名
        print(f"Worker: 开始处理视频: {base_filename}")
        model.track(video_path, save=True, project=RESULT_DIR, name=result_filename, exist_ok=True)

        result_save_path = os.path.join(RESULT_DIR, result_filename)
        print(f"Worker: 视频处理完成，保存在 {result_save_path}")

        # 清理已处理的上传文件 (从 /app/uploads 删除)
        os.remove(video_path)

        # 3. 构建最终的“分析报告”
        # (注意：从 model.track() 统计物体比较复杂，这里暂时简化)
        analysis_report = {
            "is_video": True,  # (新) 告诉前端这是视频
            "video_url": f"/static/results/{result_filename}",  # (新) 返回视频的URL
            "analysis_data": {
                "total_objects": "N/A (视频处理)",  # 您可以后续实现此统计
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