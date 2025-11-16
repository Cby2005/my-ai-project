# check_directories.py
import os


def check_directories():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"项目根目录: {base_dir}")

    # 检查静态目录
    static_dir = os.path.join(base_dir, 'static')
    results_dir = os.path.join(static_dir, 'results')

    print(f"静态目录: {static_dir} - 存在: {os.path.exists(static_dir)}")
    print(f"结果目录: {results_dir} - 存在: {os.path.exists(results_dir)}")

    if os.path.exists(results_dir):
        print(f"结果目录内容:")
        for item in os.listdir(results_dir):
            item_path = os.path.join(results_dir, item)
            print(f"  {item} - 目录: {os.path.isdir(item_path)}")

            if os.path.isdir(item_path):
                for file in os.listdir(item_path):
                    print(f"    {file}")


if __name__ == '__main__':
    check_directories()