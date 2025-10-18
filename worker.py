from celery import Celery
import cv2
import numpy as np
from ultralytics import YOLO
import base64  # 导入base64库，用于将图片数据编码成文本

# --- Celery & AI 模型初始化 ---
# 'redis' 是我们在docker-compose.yml中定义的服务名
celery_app = Celery(
    'tasks',
    broker='redis://redis:6379/0',
    backend='redis://redis:6379/0'
)

print("Worker: 正在加载YOLOv8模型...")
model = YOLO('yolov8n.pt')
print("Worker: 模型加载完成，准备接收任务！")


# --- 定义AI分析任务 ---
@celery_app.task(name='worker.process_image')
def process_image(image_bytes):
    """
    这是一个Celery任务，它接收二进制图片数据，进行AI分析，
    并返回一个包含“分析报告”的JSON对象。
    """
    print(f"Worker: 接收到新任务，数据大小 {len(image_bytes)} 字节")
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
        # results[0].boxes.cls 是一个包含所有检测框类别ID的列表
        for cls_id in results[0].boxes.cls:
            class_name = model.names[int(cls_id)]  # 获取类别ID对应的名称
            class_counts[class_name] = class_counts.get(class_name, 0) + 1

        total_objects = len(results[0].boxes.cls)
        print(f"Worker: 分析完成，共检测到 {total_objects} 个物体。")

        # 2. 将处理后的图片编码为JPEG格式，然后再次编码为Base64字符串
        success, img_encoded = cv2.imencode('.jpg', annotated_img)
        if not success:
            raise ValueError("结果图片编码失败")

        # Base64编码，使其可以被安全地放在JSON里传输
        image_base64 = base64.b64encode(img_encoded).decode('utf-8')

        # 3. 构建最终的“分析报告” (一个字典)
        analysis_report = {
            "image_data": image_base64,
            "analysis_data": {
                "total_objects": total_objects,
                "class_counts": class_counts
            }
        }

        return analysis_report

    except Exception as e:
        print(f"Worker: 任务处理失败: {e}")
        raise

