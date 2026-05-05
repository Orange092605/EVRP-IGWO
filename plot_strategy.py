import os
import json
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from src.config import Config

# ==========================================
# ⚙️ 配置区域
# ==========================================

# 填写刚才运行 run_strategy_analysis.py 时设置的 EXPERIMENT_NAME
TARGET_EXPERIMENT_FOLDER = "Charging_Strategy_Analysis"
TARGET_ALGORITHM = "IGWO"


# ==========================================

def plot_strategy_comparison():
    data_dir = os.path.join(Config.RESULT_DIR, TARGET_EXPERIMENT_FOLDER)

    if not os.path.exists(data_dir):
        print(f"❌ 错误：找不到文件夹 {data_dir}")
        print("   请先运行 run_strategy_analysis.py 生成数据。")
        return

    records = []

    # 1. 读取所有 JSON 文件
    files = [f for f in os.listdir(data_dir) if f.endswith('.json')]
    print(f"📂 正在读取数据: {data_dir}")
    print(f"   找到 {len(files)} 个文件...")

    for fname in files:
        path = os.path.join(data_dir, fname)
        try:
            with open(path, 'r') as f:
                data = json.load(f)

            if data.get('algorithm') != TARGET_ALGORITHM:
                continue

            # 提取关键信息
            # 注意: 这里假设你的 JSON 里有 'costs' 字段 (run_strategy_analysis.py 生成的)
            if 'costs' not in data:
                continue

            costs = data['costs']
            records.append({
                'Dataset': data.get('dataset', 'Unknown'),
                'Mode': data.get('mode', 'Unknown'),
                'Total_Cost': costs.get('total_cost', 0),
                'Driving_Cost': costs.get('driving_cost', 0),
                'Charging_Cost': costs.get('charging_cost', 0),
                'Penalty_Cost': costs.get('penalty_cost', 0)
            })
        except Exception as e:
            print(f"   [Error] 读取 {fname} 失败: {e}")

    if not records:
        print("❌ 没有有效数据 (Records 为空)。")
        return

    # 2. 使用 Pandas 聚合计算平均值
    df = pd.DataFrame(records)

    # 按 Dataset 和 Mode 分组求平均
    df_avg = df.groupby(['Dataset', 'Mode']).mean().reset_index()

    # 确保 Mode 的显示顺序
    mode_order = ['private_only', 'public_only', 'mixed']
    # 过滤掉不在 mode_order 里的异常数据
    df_avg = df_avg[df_avg['Mode'].isin(mode_order)]

    # 设置 Categorical 类型以便排序
    df_avg['Mode'] = pd.Categorical(df_avg['Mode'], categories=mode_order, ordered=True)
    df_avg = df_avg.sort_values(['Dataset', 'Mode'])

    # 3. 准备绘图
    datasets = df_avg['Dataset'].unique()
    x = np.arange(len(datasets))
    width = 0.25

    fig, ax = plt.subplots(figsize=(12, 7))

    colors = ['#1f77b4', '#d62728', '#2ca02c']  # 蓝(Private), 红(Public), 绿(Mixed)
    labels = ['Private Only', 'Public Only', 'Mixed']

    # 循环画三种模式
    for i, mode in enumerate(mode_order):
        subset = df_avg[df_avg['Mode'] == mode]

        # 对齐数据: 确保每个 Dataset 都有对应的值 (没有则补0)
        # 创建一个包含所有 dataset 的基准表
        full_idx = pd.DataFrame({'Dataset': datasets})
        subset = pd.merge(full_idx, subset, on='Dataset', how='left')

        vals = subset['Total_Cost'].fillna(0).values

        rects = ax.bar(x + (i - 1) * width, vals, width, label=labels[i], color=colors[i], alpha=0.85,
                       edgecolor='white')

        # 标注数值
        ax.bar_label(rects, fmt='%.0f', padding=3, fontsize=9)

    # 4. 图表美化
    ax.set_xlabel('Datasets', fontsize=12, fontweight='bold')
    ax.set_ylabel('Average Total Cost', fontsize=12, fontweight='bold')
    ax.set_title(f'Charging Strategy Analysis: {TARGET_EXPERIMENT_FOLDER} ({TARGET_ALGORITHM})', fontsize=14, pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(datasets, fontsize=11)
    ax.legend(title="Strategy Mode", loc='upper right')
    ax.grid(axis='y', linestyle='--', alpha=0.3)

    plt.tight_layout()

    # 保存图片
    save_path = os.path.join(data_dir, "strategy_comparison_plot.png")
    plt.savefig(save_path, dpi=300)
    print(f"\n✅ 图片已保存至: {save_path}")
    plt.show()

    # 5. 打印文本分析报告
    print("\n" + "=" * 60)
    print("🏆 策略优劣详细分析 (平均成本)")
    print("=" * 60)

    for ds in datasets:
        subset = df_avg[df_avg['Dataset'] == ds]
        if subset.empty: continue

        # 获取各模式成本
        costs = {}
        for mode in mode_order:
            val = subset[subset['Mode'] == mode]['Total_Cost'].values
            if len(val) > 0:
                costs[mode] = val[0]
            else:
                costs[mode] = float('inf')  # 缺失数据视为无穷大

        # 找最小值
        best_mode = min(costs, key=costs.get)
        min_cost = costs[best_mode]

        print(f"\n📌 数据集 {ds}:")
        print(f"   - Private Only : {costs['private_only']:.1f}")
        print(f"   - Public Only  : {costs['public_only']:.1f}")
        print(f"   - Mixed Mode   : {costs['mixed']:.1f}")

        if best_mode == 'mixed':
            # 计算比第二名省多少
            sorted_costs = sorted(costs.values())
            second_best = sorted_costs[1]
            if second_best < float('inf'):
                saving = (second_best - min_cost) / second_best * 100
                print(f"   ✅ 结论: Mixed 最优! (节省了 {saving:.1f}%)")
            else:
                print(f"   ✅ 结论: Mixed 最优!")
        else:
            diff = (min_cost - costs['mixed']) / costs['mixed'] * 100
            print(f"   ⚠️ 结论: {best_mode} 最优。Mixed 比它贵了 {abs(diff):.1f}%")


if __name__ == "__main__":
    plot_strategy_comparison()