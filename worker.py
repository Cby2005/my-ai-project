from celery import Celery
import os
import base64
from inference_sdk import InferenceHTTPClient  # (新) 导入 Roboflow 客户端

# --- Celery 初始化 ---
celery_app = Celery(
    'tasks',
    broker='redis://redis:6379/0',
    backend='redis://redis:6379/0'
)

# --- (新) Roboflow API 客户端初始化 ---
print("Worker: 正在初始化 Roboflow API 客户端...")
# (新) 从 .env 文件读取环境变量
API_KEY = os.environ.get("ROBOFLOW_API_KEY")
if not API_KEY:
    print("Worker 错误: 未找到 ROBOFLOW_API_KEY 环境变量！")
    # 在实际生产中，这里应该抛出异常
    API_KEY = "YOUR_API_KEY_GOES_HERE"  # 备用（请确保 .env 文件配置正确）

client = InferenceHTTPClient(
    api_url="https://serverless.roboflow.com",
    api_key=API_KEY
)

# (新) 从您的 Roboflow 工作流中获取
WORKSPACE_NAME = "ai-m7pkz"
WORKFLOW_ID = "detect-count-and-visualize-2"
print("Worker: 客户端初始化完成，准备接收任务！")


# --- (新) 图像分析任务 (调用 API) ---
@celery_app.task(name='worker.process_image')
def process_image(image_bytes):
    print(f"Worker: 接收到新图片任务，数据大小 {len(image_bytes)} 字节")
    print("Worker: 正在发送到 Roboflow API...")
    try:
        # 将原始字节转换为 Base64 字符串
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        # (新) 调用 Roboflow 工作流
        result = client.run_workflow(
            workspace_name=WORKSPACE_NAME,
            workflow_id=WORKFLOW_ID,
            images={"image": image_base64}  # API 支持 base64
        )

        print("Worker: 收到 Roboflow API 响应。")

        # --- 解析 API 响应 ---
        # 您的工作流 包含 'annotated_image' 和 'count_objects'
        if 'workflow_outputs' not in result or 'annotated_image' not in result['workflow_outputs']:
            raise ValueError(f"Roboflow API 响应格式不正确: {result}")

        # 1. 提取带标注的图片 (已经是 base64)
        annotated_image_data = result['workflow_outputs']['annotated_image']['value']

        # 2. 提取统计数据
        count_data = result['workflow_outputs'].get('count_objects', {})
        total_objects = count_data.get('total', 0)
        class_counts = count_data.get('class_counts', {})  # Roboflow 自动统计

        # 3. 构建与前端 index.html 匹配的“分析报告”
        analysis_report = {
            "is_video": False,
            "image_data": annotated_image_data,
            "analysis_data": {
                "total_objects": total_objects,
                "class_counts": class_counts
            }
        }
        return analysis_report

    except Exception as e:
        print(f"Worker: 图片任务处理失败: {e}")
        raise


# --- (新) 视频分析任务 (调用 API) ---
@celery_app.task(name='worker.process_video')
def process_video(video_path):
    print(f"Worker: 接收到新视频任务，路径 {video_path}")

    RESULT_DIR = "/app/static/results"
    os.makedirs(RESULT_DIR, exist_ok=True)
    base_filename = os.path.basename(video_path)
    result_filename = f"{os.path.splitext(base_filename)[0]}_result.mp4"
    result_save_path = os.path.join(RESULT_DIR, result_filename)

    try:
        # --- (新) 核心AI逻辑：调用 Roboflow 视频处理作业 ---
        print(f"Worker: 正在提交视频作业到 Roboflow API...")
        job_id = client.run_video_inference_job(
            workspace_name=WORKSPACE_NAME,
            workflow_id=WORKFLOW_ID,
            video_path=video_path
        )

        print(f"Worker: Roboflow 作业 {job_id} 已提交，正在等待完成...")
        # (新) 等待 Roboflow 在云端处理完视频
        client.wait_for_video_inference_job(job_id)

        print(f"Worker: Roboflow 作业 {job_id} 已完成，正在下载结果...")
        # (新) 下载处理好的视频
        client.download_video_inference_job_result(job_id, output_path=result_save_path)

        print(f"Worker: 视频处理完成，保存在 {result_save_path}")
        os.remove(video_path)  # 清理上传的临时文件

        # 3. 构建分析报告
        analysis_report = {
            "is_video": True,
            "video_url": f"/static/results/{result_filename}",  # 返回给前端的URL
            "analysis_data": {
                "total_objects": "N/A (视频)",
                "class_counts": {}
            }
        }
        return analysis_report

    except Exception as e:
        print(f"Worker: 视频任务处理失败: {e}")
        if os.path.exists(video_path):
            os.remove(video_path)
        raise