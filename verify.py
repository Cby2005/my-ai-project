# verify_file.py
import os


def verify_file():
    # 从日志中获取的文件名
    video_filename = "0107f4e7-6b69-48b1-ad55-6c778f223817.avi"
    result_run_name = "0107f4e7-6b69-48b1-ad55-6c778f223817_result"

    base_dir = os.path.dirname(os.path.abspath(__file__))
    possible_paths = [
        os.path.join(base_dir, 'static', 'results', result_run_name, video_filename),
        os.path.join(base_dir, 'static', 'results', result_run_name.replace('_result', ''), video_filename),
        os.path.join(base_dir, 'static', 'results', video_filename),
    ]

    print("检查可能的文件路径:")
    for path in possible_paths:
        exists = os.path.exists(path)
        print(f"{path} - 存在: {exists}")
        if exists:
            print(f"  文件大小: {os.path.getsize(path)} 字节")


if __name__ == '__main__':
    verify_file()