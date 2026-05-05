import time
import json
import os
import copy
import traceback
from src.config import Config
from src.data_loader import ensure_csv_exists, load_data, generate_stations_kmeans
from src.algorithms import run_igwo, run_ga, run_gwo

# ==========================================
# ⚙️ 实验配置区域 (修改这里)
# ==========================================

# 1. 实验名称 (结果会保存在 results/这个名字/ 下)
EXPERIMENT_NAME = "Comparison_Test_Batch_01"

# 2. 要运行的算法列表 (注释掉不想跑的)
ALGORITHMS_TO_RUN = {
    'IGWO': run_igwo,  # 你的改进算法
    'GA': run_ga,  # 遗传算法 (作为对比)
    'GWO': run_gwo  # 离散麻雀 (作为对比)
}

# 3. 数据集和运行次数
TARGET_DATASETS = ['c201', 'c202']  # 要测试的数据集
RUNS_PER_ALG = 4  # 每个算法跑多少次 (取平均值用)


# ==========================================

def save_result_json(dataset, algo_name, run_id, cost, time_taken, path_nodes, sub_folder):
    """
    保存单次运行结果到 JSON 文件
    """
    # 1. 构建保存路径: results / 实验名 /
    save_dir = os.path.join(Config.RESULT_DIR, sub_folder)
    os.makedirs(save_dir, exist_ok=True)

    # 2. 转换路径对象为字典
    simple_path = []
    for node in path_nodes:
        simple_path.append(node.to_dict())

    # 3. 准备数据
    result_data = {
        "dataset": dataset,
        "algorithm": algo_name,
        "run_id": run_id,
        "cost": float(cost),
        "time_seconds": float(time_taken),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "route_details": simple_path
    }

    # 4. 写入文件
    filename = f"{dataset}_{algo_name}_run{run_id}.json"
    file_path = os.path.join(save_dir, filename)

    with open(file_path, 'w') as f:
        json.dump(result_data, f, indent=4)

    print(f"    ✅ [Saved] {sub_folder}/{filename} | Cost: {cost:.2f} | Time: {time_taken:.2f}s")


def run_benchmark():
    """主运行逻辑"""
    print(f"🚀 开始算法对比测试: {EXPERIMENT_NAME}")
    print(f"📂 结果将保存至: {os.path.join(Config.RESULT_DIR, EXPERIMENT_NAME)}")

    # 遍历数据集
    for dataset_name in TARGET_DATASETS:
        csv_file = f"{dataset_name}.csv"

        # 准备数据 (确保文件存在 -> 读取 -> 生成桩)
        ensure_csv_exists(csv_file)
        depot, customers = load_data(csv_file)
        stations = generate_stations_kmeans(customers, depot)

        print(f"\n------------------------------------------------")
        print(f"📦 正在处理数据集: {dataset_name}")
        print(f"------------------------------------------------")

        # 遍历算法
        for algo_name, algo_func in ALGORITHMS_TO_RUN.items():
            print(f"\n🔹 正在评估算法: {algo_name}")

            for i in range(RUNS_PER_ALG):
                # 检查是否已跑过 (断点续传)
                filename = f"{dataset_name}_{algo_name}_run{i}.json"
                save_dir = os.path.join(Config.RESULT_DIR, EXPERIMENT_NAME)
                if os.path.exists(os.path.join(save_dir, filename)):
                    print(f"    Start Run {i}/{RUNS_PER_ALG}: [Skip] 文件已存在")
                    continue

                print(f"    Start Run {i}/{RUNS_PER_ALG}...", end="\r")

                # ⚠️ 关键: 必须深拷贝客户列表，防止算法修改原始数据影响下一次运行
                cust_copy = copy.deepcopy(customers)

                start_time = time.time()
                try:
                    # === 核心运行 ===
                    # 注意: 这里假设你的算法返回 (cost, paths, history) 或 (cost, paths)
                    # 我们统一接收返回值，防止解包错误
                    result = algo_func(depot, cust_copy, stations)

                    # 兼容性处理: 有的算法可能返回3个值(带history)，有的可能只返回2个
                    if len(result) == 3:
                        best_cost, best_paths, _ = result
                    else:
                        best_cost, best_paths = result

                    elapsed = time.time() - start_time

                    # 展平路径用于保存
                    flat_path = []
                    for route in best_paths:
                        flat_path.extend(route)

                    # 保存
                    save_result_json(
                        dataset_name, algo_name, i,
                        best_cost, elapsed, flat_path,
                        sub_folder=EXPERIMENT_NAME
                    )

                except Exception as e:
                    print(f"\n    ❌ [Error] Run {i} failed: {e}")
                    traceback.print_exc()  # 打印详细报错信息，方便调试

    print(f"\n🎉 所有测试任务完成！")


if __name__ == "__main__":
    run_benchmark()