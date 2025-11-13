import pandas as pd
import matplotlib.pyplot as plt
import os

# -------------------------------------------------------------------
# 配置区域
# -------------------------------------------------------------------
# !!! 重要 !!!
# 这些路径必须与 `机器学习_train.py` 中的 'training_name' 参数一致

# 对比实验的 CSV 路径
COMPARISON_CSVS = {
    "YOLOv8-Nano": "runs/detect/机器学习_YOLOv8n_对比/results.csv",
    "YOLOv8-Small": "runs/detect/机器学习_YOLOv8s_对比/results.csv",
    "RT-DETR-Large": "runs/detect/机器学习_RTDETR-L_对比/results.csv"
}

# 迁移学习实验的 CSV 路径
TRANSFER_CSVS = {
    "使用预训练 (迁移)": "runs/detect/机器学习_迁移验证_使用预训练/results.csv",
    "从头训练": "runs/detect/机器学习_迁移验证_从头训练/results.csv"
}
# -------------------------------------------------------------------

plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号


def plot_comparison_curves(csv_paths_dict: dict, save_path: str):
    """
    绘制算法对比曲线 (满足要求 2 和 3)
    [cite: 24, 25, 26, 29, 30]
    """
    print(f"正在生成对比图表: {save_path}")

    # 1. 创建多子图 (2x2) [cite: 24]
    fig, axs = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('机器学习大作业 - 算法对比分析', fontsize=20)

    # 定义颜色和线型 [cite: 26]
    styles = {
        "YOLOv8-Nano": {"color": "blue", "linestyle": "-"},
        "YOLOv8-Small": {"color": "green", "linestyle": "--"},
        "RT-DETR-Large": {"color": "red", "linestyle": ":"}
    }

    # 2. 遍历每个模型的 CSV
    for model_name, csv_path in csv_paths_dict.items():
        if not os.path.exists(csv_path):
            print(f"警告: 找不到 {csv_path}，跳过 {model_name}")
            continue

        df = pd.read_csv(csv_path)
        # 清理列名 (YOLOv8 会在列名中加入空格)
        df.columns = df.columns.str.strip()

        style = styles.get(model_name, {"color": "black", "linestyle": "-."})

        # 3. 绘制各个子图
        # 图 1: 训练损失 [cite: 30]
        axs[0, 0].plot(df['epoch'], df['train/loss'], label=model_name, **style)

        # 图 2: 验证损失 [cite: 30]
        axs[0, 1].plot(df['epoch'], df['val/loss'], label=model_name, **style)

        # 图 3: 验证 mAP(50-95) (主要指标) [cite: 29]
        axs[1, 0].plot(df['epoch'], df['metrics/mAP50-95(B)'], label=model_name, **style)

        # 图 4: 验证 mAP(50) (次要指标) [cite: 29]
        axs[1, 1].plot(df['epoch'], df['metrics/mAP50(B)'], label=model_name, **style)

    # 4. 设置图表属性 [cite: 25]
    axs[0, 0].set_title('训练损失 (Train Loss)')
    axs[0, 0].set_xlabel('Epoch')
    axs[0, 0].set_ylabel('Loss')
    axs[0, 0].legend()
    axs[0, 0].grid(True)

    axs[0, 1].set_title('验证损失 (Validation Loss)')
    axs[0, 1].set_xlabel('Epoch')
    axs[0, 1].set_ylabel('Loss')
    axs[0, 1].legend()
    axs[0, 1].grid(True)

    axs[1, 0].set_title('验证集 mAP (50-95)')
    axs[1, 0].set_xlabel('Epoch')
    axs[1, 0].set_ylabel('mAP (0-1)')
    axs[1, 0].legend()
    axs[1, 0].grid(True)

    axs[1, 1].set_title('验证集 mAP (50)')
    axs[1, 1].set_xlabel('Epoch')
    axs[1, 1].set_ylabel('mAP (0-1)')
    axs[1, 1].legend()
    axs[1, 1].grid(True)

    # 5. 保存图表
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig(save_path)
    print(f"图表已保存到: {save_path}")


def plot_transfer_curves(csv_paths_dict: dict, save_path: str):
    """
    绘制迁移学习对比曲线 (满足要求 6)

    """
    print(f"正在生成迁移学习图表: {save_path}")

    plt.figure(figsize=(10, 6))

    styles = {
        "使用预训练 (迁移)": {"color": "blue", "linestyle": "-"},
        "从头训练": {"color": "orange", "linestyle": "--"}
    }

    for model_name, csv_path in csv_paths_dict.items():
        if not os.path.exists(csv_path):
            print(f"警告: 找不到 {csv_path}，跳过 {model_name}")
            continue

        df = pd.read_csv(csv_path)
        df.columns = df.columns.str.strip()
        style = styles.get(model_name)

        plt.plot(df['epoch'], df['metrics/mAP50-95(B)'], label=model_name, **style)

    plt.title('迁移能力验证 (mAP 50-95 对比)')
    plt.xlabel('Epoch')
    plt.ylabel('mAP (0-1)')
    plt.legend()
    plt.grid(True)

    plt.savefig(save_path)
    print(f"图表已保存到: {save_path}")


if __name__ == "__main__":
    # 1. 生成算法对比图
    plot_comparison_curves(
        csv_paths_dict=COMPARISON_CSVS,
        save_path="机器学习_算法对比曲线.png"
    )

    # 2. 生成迁移学习对比图
    plot_transfer_curves(
        csv_paths_dict=TRANSFER_CSVS,
        save_path="机器学习_迁移学习对比曲线.png"
    )

    print("\n--- 可视化脚本执行完毕 ---")
    print("请检查生成的 .png 文件。")
    print("\n提示：混淆矩阵 [cite: 31] 和 典型样例 [cite: 33]")
    print("YOLOv8 已自动在每个 'runs/detect/...' 文件夹中生成：")
    print(" - 'confusion_matrix.png' (混淆矩阵)")
    print(" - 'val_batch0_pred.jpg' (典型样例)")
    print("请在您的PPT中直接使用这些自动生成的图片。")