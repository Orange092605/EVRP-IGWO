import os
import json
import matplotlib.pyplot as plt
import numpy as np
from src.config import Config

# ==========================================
# ⚙️ 绘图配置 (修改这里)
# ==========================================

# 1. 你刚才分析的参数名 (例如 'BATTERY_CAPACITY BEFORE')
TARGET_PARAM = "BATTERY_CAPACITY BEFORE"

# 2. 你刚才分析的数据集
TARGET_DATASET = "c201"

# 3. 算法样式配置
ALGO_CONFIG = {
    'GA': {'color': '#1f77b4', 'marker': 'o', 'linestyle': '--'},
    'GWO': {'color': '#ff7f0e', 'marker': 's', 'linestyle': '-.'},
    'IGWO': {'color': '#2ca02c', 'marker': '^', 'linestyle': '-'}
}


# ==========================================

def get_charging_count(routes_simple):
    """
    统计所有路线中充电站出现的总次数
    规则: 节点 ID > 1000 即为充电站
    """
    count = 0
    if not routes_simple:
        return 0

    for route in routes_simple:
        for node_id in route:
            if node_id > 1000:
                count += 1
    return count


def plot_charging_counts():
    # 构建根路径: results/Sensitivity_Analysis BEFORE/{参数}/{数据集}
    base_dir = os.path.join(Config.RESULT_DIR, "Sensitivity_Analysis BEFORE", TARGET_PARAM, TARGET_DATASET)

    if not os.path.exists(base_dir):
        print(f"❌ 错误：找不到路径 {base_dir}")
        print("   请确认 run_sensitivity.py 是否已执行完毕，且参数名/数据集拼写正确。")
        return

    print(f"📂 正在读取数据: {base_dir}")

    # 准备数据容器
    # plot_data = { 'GA': { 60: [count1, count2], 80: [...] }, 'IGWO': ... }
    plot_data = {}

    # 1. 遍历算法文件夹
    # 获取目录下所有子文件夹 (即算法名)
    algo_folders = [algo for algo in ALGO_CONFIG if os.path.isdir(os.path.join(base_dir, algo))]

    for algo in algo_folders:
        if algo not in plot_data:
            plot_data[algo] = {}

        algo_path = os.path.join(base_dir, algo)
        files = [f for f in os.listdir(algo_path) if f.endswith('.json')]

        for fname in files:
            file_path = os.path.join(algo_path, fname)
            try:
                with open(file_path, 'r', encoding='utf-8-sig') as f:
                    data = json.load(f)

                val = data.get('value')
                routes = data.get('routes_simple', [])

                # === 核心统计逻辑 ===
                count = get_charging_count(routes)
                # ===================

                if val not in plot_data[algo]:
                    plot_data[algo][val] = []
                plot_data[algo][val].append(count)

            except Exception as e:
                print(f"   [Error] 读取 {fname} 失败: {e}")

    if not plot_data:
        print("❌ 未读取到有效数据。")
        return

    # 2. 绘图
    plt.figure(figsize=(10, 6))

    # 获取所有出现的参数值用于设置 X 轴
    all_x_values = set()

    print("\n📊 充电次数统计摘要:")

    for algo, val_dict in plot_data.items():
        # 排序参数值 (X轴)
        sorted_params = sorted(val_dict.keys())
        x = np.array(sorted_params)
        all_x_values.update(x)

        means = []
        stds = []

        for val in sorted_params:
            counts = val_dict[val]
            means.append(np.mean(counts))
            stds.append(np.std(counts))

        means = np.array(means)
        stds = np.array(stds)

        # 获取样式配置
        style = ALGO_CONFIG.get(algo, {'color': 'gray', 'marker': 'x', 'linestyle': ':'})

        # 画折线
        plt.plot(x, means, label=algo, **style, linewidth=2, alpha=0.9)

        # 画阴影误差带 (Mean ± Std)
        plt.fill_between(x, means - stds, means + stds, color=style['color'], alpha=0.1)

        # 打印简单报告
        print(f"   🔹 {algo}: X={x}, Avg_Counts={means}")

    # 图表美化
    plt.title(f'Impact of {TARGET_PARAM} on Charging Frequency\nDataset: {TARGET_DATASET}', fontsize=14, pad=15)
    plt.xlabel(f'Parameter Value ({TARGET_PARAM})', fontsize=12)
    plt.ylabel('Average Number of Charging Stops', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.4)
    plt.legend(title="Algorithm", fontsize=10)

    # 强制 X 轴显示所有刻度 (如果点不多的话)
    if len(all_x_values) < 20:
        plt.xticks(sorted(list(all_x_values)))

    # 保存图片到该分析的根目录
    save_path = os.path.join(base_dir, f"charging_count_plot_{TARGET_PARAM}.png")
    plt.savefig(save_path, dpi=300)
    print(f"\n✅ 图片已保存至: {save_path}")
    plt.close()


if __name__ == "__main__":
    plot_charging_counts()