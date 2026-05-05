import os
import json
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from src.config import Config


# ==========================================
# 绘图配置
# ==========================================

TARGET_PARAM = "BATTERY_CAPACITY"
TARGET_DATASET = "c201"

ALGO_CONFIG = {
    "GA": {"color": "#1f77b4", "marker": "o", "linestyle": "--"},
    "GWO": {"color": "#ff7f0e", "marker": "s", "linestyle": "-."},
    "IGWO": {"color": "#2ca02c", "marker": "^", "linestyle": "-"},
}


def find_base_dir():
    """
    自动查找灵敏度分析结果路径。
    兼容 Sensitivity_Analysis 和 Sensitivity_Analysis 后面误带空格的情况。
    """
    target_param = TARGET_PARAM.strip()

    candidate_dirs = [
        os.path.join(Config.RESULT_DIR, "Sensitivity_Analysis", target_param, TARGET_DATASET),
        os.path.join(Config.RESULT_DIR, "Sensitivity_Analysis ", target_param, TARGET_DATASET),
        os.path.join(Config.RESULT_DIR, "Sensitivity_Analysis", target_param + " ", TARGET_DATASET),
        os.path.join(Config.RESULT_DIR, "Sensitivity_Analysis ", target_param + " ", TARGET_DATASET),
    ]

    print("当前 Config.RESULT_DIR =", Config.RESULT_DIR)
    print("正在尝试查找以下路径：")
    for path in candidate_dirs:
        print("  ", path)

    for path in candidate_dirs:
        if os.path.exists(path):
            return path

    return None


def plot_sensitivity():
    base_dir = find_base_dir()

    if base_dir is None:
        print("\n错误：没有找到灵敏度分析结果路径。")
        print("请检查 run_sensitivity.py 是否已经正常运行完毕。")
        print("重点检查文件夹是否为：Sensitivity_Analysis / BATTERY_CAPACITY / c201")
        return

    print(f"\n正在读取数据: {base_dir}")

    plot_data = {}

    for algo in ALGO_CONFIG.keys():
        algo_path = os.path.join(base_dir, algo)

        if not os.path.isdir(algo_path):
            print(f"[跳过] 未找到算法文件夹: {algo_path}")
            continue

        plot_data[algo] = {}

        files = [f for f in os.listdir(algo_path) if f.endswith(".json")]

        if not files:
            print(f"[提示] {algo} 文件夹中没有 json 文件")
            continue

        for fname in files:
            file_path = os.path.join(algo_path, fname)

            try:
                with open(file_path, "r", encoding="utf-8-sig") as f:
                    data = json.load(f)

                val = data.get("value", None)
                costs = data.get("costs", {})
                cost = costs.get("total_cost", None)

                if val is None or cost is None:
                    print(f"[跳过] {fname} 中缺少 value 或 total_cost")
                    continue

                val = float(val)

                if val not in plot_data[algo]:
                    plot_data[algo][val] = []

                plot_data[algo][val].append(float(cost))

            except Exception as e:
                print(f"[Error] 读取 {fname} 失败: {e}")

    plot_data = {algo: values for algo, values in plot_data.items() if values}

    if not plot_data:
        print("\n错误：未读取到有效数据。")
        return

    summary_rows = []

    plt.figure(figsize=(10, 6))

    print("\n统计摘要:")

    for algo, val_dict in plot_data.items():
        sorted_params = sorted(val_dict.keys())
        x = np.array(sorted_params)

        means = []
        stds = []

        for val in sorted_params:
            costs = val_dict[val]
            mean_cost = np.mean(costs)
            std_cost = np.std(costs)

            means.append(mean_cost)
            stds.append(std_cost)

            summary_rows.append({
                "algorithm": algo,
                "parameter": TARGET_PARAM,
                "value": val,
                "mean_total_cost": mean_cost,
                "std_total_cost": std_cost,
                "run_times": len(costs),
            })

        means = np.array(means)
        stds = np.array(stds)

        style = ALGO_CONFIG.get(
            algo,
            {"color": "gray", "marker": "x", "linestyle": ":"}
        )

        plt.plot(
            x,
            means,
            label=algo,
            color=style["color"],
            marker=style["marker"],
            linestyle=style["linestyle"],
            linewidth=2,
            markersize=6,
        )

        plt.fill_between(
            x,
            means - stds,
            means + stds,
            color=style["color"],
            alpha=0.15,
        )

        print(f"{algo}:")
        print(f"  X = {x}")
        print(f"  Mean Cost = {means.round(2)}")
        print(f"  Std = {stds.round(2)}")

    plt.title(
        f"Sensitivity Analysis of {TARGET_PARAM} on {TARGET_DATASET}",
        fontsize=14,
        pad=15,
    )
    plt.xlabel(f"Battery Capacity", fontsize=12)
    plt.ylabel("Total Cost", fontsize=12)
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.legend(title="Algorithm", fontsize=10)
    plt.tight_layout()

    save_fig_path = os.path.join(base_dir, f"sensitivity_plot_{TARGET_PARAM}.png")
    save_csv_path = os.path.join(base_dir, f"sensitivity_summary_{TARGET_PARAM}.csv")

    plt.savefig(save_fig_path, dpi=300, bbox_inches="tight")
    plt.close()

    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(save_csv_path, index=False, encoding="utf-8-sig")

    print(f"\n图片已保存至: {save_fig_path}")
    print(f"统计结果已保存至: {save_csv_path}")


if __name__ == "__main__":
    plot_sensitivity()