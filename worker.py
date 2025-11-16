from celery import Celery
import cv2
import numpy as np
from ultralytics import YOLO
import base64  # 导入base64库
import os  # 导入os库

# --- Celery & AI 模型初始化 ---
# 'redis' 是我们在docker-compose.yml中定义的服务名
# 尝试导入 lap，如果失败则使用替代方案
try:
    import lap

    LAP_AVAILABLE = True
    print("lap 模块可用")
except ImportError:
    LAP_AVAILABLE = False
    print("警告: lap 模块不可用，将使用替代方案")
    # 尝试导入 scipy 作为替代
    try:
        from scipy.optimize import linear_sum_assignment

        SCIPY_AVAILABLE = True
        print("scipy 模块可用，将用作 lap 的替代")
    except ImportError:
        SCIPY_AVAILABLE = False
        print("警告: scipy 模块也不可用")
celery_app = Celery(
    'tasks',
     broker='redis://redis:6379/0',
     backend='redis://redis:6379/0'
   # broker='redis://localhost:6379/0',
    #backend='redis://localhost:6379/0'
)

print("Worker: 正在加载自定义模型...")
model = YOLO('yolov8n.pt')
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

        # 3. 构建最终的"分析报告"
        # 在 process_video 函数中，修改返回的 video_url
        analysis_report = {
            "is_video": False,
            "image_data": image_base64,  # Base64编码的处理后图片
            "analysis_data": {
                "total_objects": total_objects,  # 检测到的物体总数
                "class_counts": class_counts  # 每个类别的数量统计
            }
        }
        return analysis_report

    except Exception as e:
        print(f"Worker: 图片任务处理失败: {e}")
        raise


# --- (新) 定义AI分析任务 (视频) ---
@celery_app.task(name='worker.process_video')
def process_video(video_path, output_format='webm'):
    print(f"Worker: 接收到新视频任务，路径 {video_path}，输出格式: {output_format}")
    try:
        RESULT_DIR = "static/results"
        os.makedirs(RESULT_DIR, exist_ok=True)

        base_filename = os.path.basename(video_path)
        base_name = os.path.splitext(base_filename)[0]
        result_run_name = f"{base_name}_result"

        result_dir_path = os.path.join(RESULT_DIR, result_run_name)
        os.makedirs(result_dir_path, exist_ok=True)

        print(f"Worker: 开始处理视频: {base_filename}")

        # 使用普通检测，不保存视频（我们将手动处理视频编码）
        results = model.predict(video_path, save=False, project=RESULT_DIR, name=result_run_name, exist_ok=True)

        print(f"Worker: YOLO处理完成，开始手动处理视频编码...")

        # 读取原始视频
        cap = cv2.VideoCapture(video_path)

        # 获取视频参数
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # 设置输出文件名和编码器
        if output_format == 'webm':
            output_filename = f"{base_name}.webm"
            # 使用 VP8 编码器用于 WebM
            fourcc = cv2.VideoWriter_fourcc(*'VP80')
            mimetype = 'video/webm'
        else:
            # 默认回退到 MP4
            output_filename = f"{base_name}.mp4"
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            mimetype = 'video/mp4'

        output_path = os.path.join(result_dir_path, output_filename)

        # 创建视频写入器
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        frame_count = 0
        processed_frames = 0

        print(f"Worker: 开始处理视频帧，格式: {output_format}")

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # 对当前帧进行目标检测
            frame_results = model(frame)

            # 绘制检测结果
            annotated_frame = frame_results[0].plot()

            # 写入处理后的帧
            out.write(annotated_frame)

            frame_count += 1
            processed_frames += 1

            # 每处理100帧打印一次进度
            if frame_count % 100 == 0:
                print(f"Worker: 已处理 {frame_count} 帧")

        cap.release()
        out.release()

        print(f"Worker: 视频处理完成，共处理 {processed_frames} 帧")
        print(f"Worker: 输出文件: {output_path}")

        # 构建URL路径
        result_url_path = f"/static/results/{result_run_name}/{output_filename}"
        print(f"Worker: 最终视频URL路径: {result_url_path}")

        # 清理临时文件
        os.remove(video_path)

        # 构建分析报告
        analysis_report = {
            "is_video": True,
            "video_url": result_url_path,
            "analysis_data": {
                "total_objects": "N/A (视频处理)",
                "class_counts": {},
                "processed_frames": processed_frames,
                "output_format": output_format
            }
        }
        return analysis_report

    except Exception as e:
        print(f"Worker: 视频任务处理失败: {e}")
        if os.path.exists(video_path):
            os.remove(video_path)
        raise