from celery import Celery
import cv2
import numpy as np
from ultralytics import YOLO

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
    这是一个Celery任务，它接收二进制图片数据，
    进行AI分析，并返回处理后的二进制图片数据。
    """
    print(f"Worker: 接收到新任务，数据大小 {len(image_bytes)} 字节")
    try:
        # 核心AI逻辑 - 完全复用！
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            raise ValueError("无法解码图片")

        results = model(img)
        annotated_img = results[0].plot()

        success, img_encoded = cv2.imencode('.jpg', annotated_img)
        if not success:
            raise ValueError("结果图片编码失败")

        result_bytes = img_encoded.tobytes()
        print(f"Worker: 任务处理完成，返回 {len(result_bytes)} 字节结果")
        return result_bytes
    except Exception as e:
        print(f"Worker: 任务处理失败: {e}")
        # 重新抛出异常，Celery会将其标记为FAILURE
        raise