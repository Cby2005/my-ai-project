import torch
from ultralytics import YOLO

# -------------------------------------------------------------------
# 配置区域
# -------------------------------------------------------------------
DATASET_YAML_PATH = 'coco128.yaml'  # !!! 替换为您的 .yaml 路径
NUM_EPOCHS = 50  # 确保 Epochs 数量一致


# -------------------------------------------------------------------

def train_model_for_transfer(model_init: str, training_name: str):
    """
    训练模型并指定名称
    """
    print(f"\n--- [开始迁移实验]: {training_name} ({model_init}) ---")
    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    try:
        model = YOLO(model_init)

        model.train(
            data=DATASET_YAML_PATH,
            epochs=NUM_EPOCHS,
            imgsz=640,
            device=device,
            name=training_name,
            project='runs/detect'
        )

        print(f"--- [实验完成]: {training_name} ---")
        print(f"结果已保存到: runs/detect/{training_name}")

    except Exception as e:
        print(f"[!! 错误 !!] 实验 {training_name} 失败: {e}")


if __name__ == "__main__":
    # --- 运行两个迁移学习对比实验 ---
    #  (满足"模型迁移能力验证")

    # 实验 A: 迁移学习 (使用预训练权重)
    # 我们加载 '.pt' 文件，它包含了在 COCO 上预训练的权重
    train_model_for_transfer(
        model_init='yolov8n.pt',
        training_name='机器学习_迁移验证_使用预训练'
    )

    # 实验 B: 从头训练 (不使用预训练权重)
    # 我们加载 '.yaml' 文件，它只定义了模型结构，没有权重
    train_model_for_transfer(
        model_init='yolov8n.yaml',
        training_name='机器学习_迁移验证_从头训练'
    )

    print("\n--- 迁移学习对比实验已完成 ---")