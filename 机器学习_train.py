import torch
from ultralytics import YOLO

# -------------------------------------------------------------------
# 配置区域
# -------------------------------------------------------------------
# !!! 重要 !!!
# 请将 'coco128.yaml' 替换为您自己的数据集配置 .yaml 文件的路径
# (您可以先用 'coco128.yaml' 测试，它会自动下载)
DATASET_YAML_PATH = 'coco128.yaml'

# 训练的 Epochs 数量 (建议 50-100 用于真实作业)
NUM_EPOCHS = 50


# -------------------------------------------------------------------

def train_model(model_name: str, training_name: str):
    """
    一个通用的训练函数
    :param model_name: 模型名称 (例如 'yolov8n.pt' 或 'rtdetr-l.pt')
    :param training_name: 本次训练的保存名称 (将保存在 'runs/detect/...')
    """
    print(f"\n--- [开始训练]: {training_name} ({model_name}) ---")

    # 检查是否有可用的 GPU
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"使用设备: {device}")

    try:
        # 1. 加载模型
        #    - 使用 '.pt' 会加载预训练权重 (迁移学习)
        #    - 使用 '.yaml' 会从头开始训练 (见下一个脚本)
        model = YOLO(model_name)

        # 2. 训练模型
        #    - 'data': 指向您的 .yaml 配置文件
        #    - 'epochs': 训练轮数
        #    - 'imgsz': 图像大小
        #    - 'name': 结果保存的文件夹名 (非常重要!)
        results = model.train(
            data=DATASET_YAML_PATH,
            epochs=NUM_EPOCHS,
            imgsz=640,
            device=device,
            name=training_name,
            project='runs/detect'  # 确保所有结果都在一个主文件夹下
        )

        print(f"--- [训练完成]: {training_name} ---")
        print(f"结果已保存到: runs/detect/{training_name}")
        print(f"训练历史 (CSV): runs/detect/{training_name}/results.csv")
        print(f"最佳模型权重: runs/detect/{training_name}/weights/best.pt")

    except Exception as e:
        print(f"[!! 错误 !!] 训练 {training_name} 失败: {e}")


if __name__ == "__main__":
    # --- 运行三个对比实验 ---
    #  (满足"至少采用三种不同算法或模型")

    # 实验一: YOLOv8-Nano
    train_model(model_name='yolov8n.pt', training_name='机器学习_YOLOv8n_对比')

    # 实验二: YOLOv8-Small
    train_model(model_name='yolov8s.pt', training_name='机器学习_YOLOv8s_对比')

    # 实验三: RT-DETR-Large (基于Transformer的SOTA检测器)
    # 这是一个与YOLO架构完全不同的模型，非常适合作为对比
    train_model(model_name='rtdetr-l.pt', training_name='机器学习_RTDETR-L_对比')

    print("\n--- 所有对比训练已完成 ---")