from celery import Celery
import os
import base64
from inference_sdk import InferenceHTTPClient
import httpx  # (新) 导入 httpx 库

# --- Celery 初始化 ---
celery_app = Celery(
    'tasks',
    broker='redis://redis:6379/0',
    backend='redis://redis:6379/0'
)

# --- (新) Roboflow API 客户端初始化 (带超时设置) ---
print("Worker: 正在初始化 Roboflow API 客户端...")
API_KEY = os.environ.get("ROBOFLOW_API_KEY")
if not API_KEY:
    print("Worker 错误: 未找到 ROBOFLOW_API_KEY 环境变量！")
    API_KEY = "YOUR_API_KEY_GOES_HERE"  # 确保 .env 文件配置正确

# (新) 创建一个自定义超时的 httpx 客户端
# 将超时时间设置为 30 分钟 (1800.0 秒)
# 这对于处理大型视频文件是必要的
timeout_config = httpx.Timeout(1800.0, connect=5.0)
custom_httpx_client = httpx.Client(timeout=timeout_config)

client = InferenceHTTPClient(
    api_url="https://serverless.roboflow.com",
    api_key=API_KEY,
    # (新) 将我们自定义的 httpx 客户端注入
    client=custom_httpx_client
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
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        # (新) 调用 Roboflow 工作流
        result = client.run_workflow(
            workspace_name=WORKSPACE_NAME,
            workflow_id=WORKFLOW_ID,
            images={"image": image_base64}
        )

        print("Worker: 收到 Roboflow API 响应。")

        # --- 解析 API 响应 ---
        if 'workflow_outputs' not in result or 'annotated_image' not in result['workflow_outputs']:
            raise ValueError(f"Roboflow API 响应格式不正确: {result}")

        annotated_image_data = result['workflow_outputs']['annotated_image']['value']
        count_data = result['workflow_outputs'].get('count_objects', {})
        total_objects = count_data.get('total', 0)
        class_counts = count_data.get('class_counts', {})

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
        print(f"Worker: 正在提交视频作业到 Roboflow API...")
        job_id = client.run_video_inference_job(
            workspace_name=WORKSPACE_NAME,
            workflow_id=WORKFLOW_ID,
            video_path=video_path
        )

        print(f"Worker: Roboflow 作业 {job_id} 已提交，正在等待完成 (最长 30 分钟)...")
        # (新) 这个等待调用现在会使用我们设置的 30 分钟超时
        client.wait_for_video_inference_job(job_id)

        print(f"Worker: Roboflow 作业 {job_id} 已完成，正在下载结果...")
        client.download_video_inference_job_result(job_id, output_path=result_save_path)

        print(f"Worker: 视频处理完成，保存在 {result_save_path}")
        os.remove(video_path)

        analysis_report = {
            "is_video": True,
            "video_url": f"/static/results/{result_filename}",
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