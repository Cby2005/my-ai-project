import os
import requests

# 配置信息（根据实际部署修改）
UPLOAD_FOLDER = "/app/uploads"  # 对应 web_app.py 中的上传目录
STATIC_RESULTS_FOLDER = "/app/static/results"  # 对应 worker.py 中的结果目录
SERVER_URL = "http://localhost:5000"  # 服务器地址（本地部署直接用这个）

def check_video_format(file_path):
    """验证文件格式是否支持"""
    supported_ext = ['.mp4', '.avi', '.mov', '.webm', '.mkv', '.flv']
    _, ext = os.path.splitext(file_path)
    if not ext:
        return False, "文件缺少扩展名"
    if ext.lower() not in supported_ext:
        return False, f"不支持的格式：{ext}，仅支持 {','.join(supported_ext)}"
    return True, f"格式支持：{ext}"

def check_file_exist(task_id_or_filename, is_task_id=True):
    """检查视频文件是否已生成（支持按任务ID或文件名查询）"""
    if is_task_id:
        # 按任务ID查询（假设任务名包含任务ID，可根据实际命名规则修改）
        for root, dirs, files in os.walk(STATIC_RESULTS_FOLDER):
            if task_id_or_filename in root:
                video_files = [f for f in files if f.endswith(('.mp4', '.avi', '.mov', '.webm'))]
                if video_files:
                    return True, f"找到视频文件：{os.path.join(root, video_files[0])}"
        return False, f"未找到任务 {task_id_or_filename} 生成的视频文件"
    else:
        # 按文件名查询
        for root, dirs, files in os.walk(STATIC_RESULTS_FOLDER):
            if task_id_or_filename in files:
                return True, f"文件路径：{os.path.join(root, task_id_or_filename)}"
        return False, f"未找到文件：{task_id_or_filename}"

def test_video_url(video_url):
    """测试视频URL是否可访问"""
    full_url = f"{SERVER_URL}{video_url}" if video_url.startswith('/') else f"{SERVER_URL}/{video_url}"
    try:
        response = requests.get(full_url, stream=True, timeout=10)
        if response.status_code == 200 or response.status_code == 206:
            return True, f"URL 可正常访问：{full_url}"
        else:
            return False, f"URL 访问失败，状态码：{response.status_code}，地址：{full_url}"
    except Exception as e:
        return False, f"URL 访问报错：{str(e)}，地址：{full_url}"

# 示例用法（用户可根据实际情况修改参数）
if __name__ == "__main__":
    # 1. 验证本地文件格式
    local_video_path = "test_video.mp4"  # 本地要上传的视频文件路径
    format_valid, format_msg = check_video_format(local_video_path)
    print(f"格式验证结果：{format_msg}")

    # 2. 检查服务器上的文件（替换为实际任务ID或文件名）
    task_id = "你的任务ID"  # 从上传响应中获取的 task_id
    file_exist, exist_msg = check_file_exist(task_id, is_task_id=True)
    print(f"文件存在性检查：{exist_msg}")

    # 3. 测试视频URL（替换为 get_result 接口返回的 video_url）
    video_url = "/static/results/xxx_result/xxx.mp4"  # 从任务结果中获取的 video_url
    url_valid, url_msg = test_video_url(video_url)
    print(f"URL 测试结果：{url_msg}")