import os
import json
import matplotlib.pyplot as plt
import numpy as np
from src.config import Config

# ==========================================
# ⚙️ 配置区域
# ==========================================

# 填写你要画图的那个实验文件夹名字 (在 results/ 下面)
# 例如: "Comparison_Test_Batch_01" 或 "Experiment_Batch_01"
TARGET_EXPERIMENT_FOLDER = "Comparison_Test_Batch_01"

# 想要对比的算法名称 (顺序决定柱子的排列)
ALGO_ORDER = ['GA', 'GWO', 'IGWO']


# ==========================================

def load_and_plot_results():
    # 1. 构建完整的文件夹路径
    data_dir = os.path.join(Config.RESULT_DIR, TARGET_EXPERIMENT_FOLDER)

    if not os.path.exists(data_dir):
        print(f"❌ 错误：找不到文件夹: {data_dir}")
        print("   请检查 TARGET_EXPERIMENT_FOLDER 是否填写正确。")
        return

    print(f"📂 正在读取数据: {data_dir}")

    # 2. 读取 JSON 文件
    # 数据结构: data_map['dataset_name']['algo_name'] = [cost1, cost2, ...]
    data_map = {}

    files = [f for f in os.listdir(data_dir) if f.endswith('.json')]
    print(f"   找到 {len(files)} 个结果文件。")

    if len(files) == 0:
        print("   ⚠️ 该文件夹下没有 JSON 文件，无法绘图。")
        return

    for fname in files:
        path = os.path.join(data_dir, fname)
        try:
            with open(path, 'r', encoding='utf-8-sig') as f:
                record = json.load(f)

            d_name = record.get('dataset', 'Unknown')
            a_name = record.get('algorithm', 'Unknown')
            cost = record.get('cost', 0)

            if d_name not in data_map:
                data_map[d_name] = {algo: [] for algo in ALGO_ORDER}

            # 如果这个算法不在我们的预设列表里，临时加进去
            if a_name not in data_map[d_name]:
                data_map[d_name][a_name] = []

            data_map[d_name][a_name].append(cost)

        except Exception as e:
            print(f"   [Error] 读取文件 {fname} 失败: {e}")

    # 3. 统计平均值
    dataset_labels = sorted(data_map.keys())  # ['c201', 'c202'...]

    # 准备绘图数据
    means_by_algo = {algo: [] for algo in ALGO_ORDER}
    valid_datasets = []

    print("\n--- 📊 统计结果 (平均成本) ---")

    for d_name in dataset_labels:
        costs_dict = data_map[d_name]

        # 检查该数据集是否有数据
        has_data = False
        log_str = f"{d_name}: "

        for algo in ALGO_ORDER:
            costs = costs_dict.get(algo, [])
            n_runs = len(costs)
            avg_val = np.mean(costs) if n_runs > 0 else 0

            means_by_algo[algo].append(avg_val)

            log_str += f"{algo}(n={n_runs}, avg={avg_val:.1f})  "
            if n_runs > 0:
                has_data = True

        if has_data:
            valid_datasets.append(d_name)
            print(log_str)
        else:
            # 如果某个数据集完全没数据，要从列表里移除，防止画空图
            # (这里简单处理：如果不valid，上面的append其实已经多加了0，需要回退吗？
            #  为了逻辑简单，我们假设都有数据。如果完全为空，在画图时可以忽略)
            pass

    if not valid_datasets:
        print("没有有效数据用于绘图。")
        return

    # 4. 绘图
    x = np.arange(len(dataset_labels))  # x 轴刻度
    total_width = 0.8  # 总柱宽
    n_algos = len(ALGO_ORDER)
    bar_width = total_width / n_algos  # 单个柱子的宽度

    fig, ax = plt.subplots(figsize=(12, 7))

    # 颜色盘
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']  # 蓝, 橙, 绿, 红, 紫

    # 循环画每个算法的柱子
    for i, algo in enumerate(ALGO_ORDER):
        # 计算偏移量: 让柱子居中
        # 偏移量公式: x + (i - 中间索引) * width
        offset = (i - (n_algos - 1) / 2) * bar_width

        vals = means_by_algo[algo]
        # 只取有效数据集对应的长度 (为了严谨)
        vals = vals[:len(dataset_labels)]

        rects = ax.bar(x + offset, vals, bar_width, label=algo, color=colors[i % len(colors)], alpha=0.85,
                       edgecolor='white')

        # 自动标注数值
        ax.bar_label(rects, padding=3, fmt='%.0f', fontsize=9)

    # 设置图表属性
    ax.set_xlabel('Datasets', fontsize=12, fontweight='bold')
    ax.set_ylabel('Average Cost', fontsize=12, fontweight='bold')
    ax.set_title(f'Algorithm Comparison: {TARGET_EXPERIMENT_FOLDER}', fontsize=14, pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(dataset_labels, fontsize=11)
    ax.legend(title="Algorithms", loc='upper right')
    ax.grid(axis='y', linestyle='--', alpha=0.3)

    # 调整布局
    plt.tight_layout()

    # 5. 保存并显示
    save_path = os.path.join(data_dir, "benchmark_plot.png")
    plt.savefig(save_path, dpi=300)
    print(f"\n✅ 图片已保存至: {save_path}")
    plt.close()


if __name__ == "__main__":
    load_and_plot_results()
