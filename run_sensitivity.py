import copy
import json
import os
import time
import traceback

import numpy as np

from src.algorithms import run_ga, run_gwo, run_igwo
from src.config import Config
from src.data_loader import ensure_csv_exists, generate_stations_kmeans, load_data
from src.physics import decode_chromosome_to_routes, evaluate_solution


# ======================================================
# 结果保存路径
# 如果你希望结果保存在 results1/results 下面，就用这个路径
# ======================================================
RESULT_ROOT = r"C:\Users\admin\Desktop\普刊\代码\car\results1\results"

# 覆盖 Config.RESULT_DIR，避免保存到错误的 results 文件夹
Config.RESULT_DIR = RESULT_ROOT


def analyze_best_solution_breakdown(chromosome, depot, stations):
    """
    根据恢复出的客户访问序列，重新解码并计算详细成本。
    """
    routes = decode_chromosome_to_routes(chromosome)
    _, detailed_paths, breakdown = evaluate_solution(routes, depot, stations)
    return breakdown, detailed_paths


def run_sensitivity_analysis_multi_algo(
    param_name,
    start_val,
    end_val,
    step_val,
    dataset_name,
    run_times=3
):
    """
    多算法灵敏度分析：
    对指定参数 param_name 进行取值变化，
    分别运行 GA、GWO、IGWO，并保存每次运行结果为 JSON。
    """

    # 去掉参数名前后隐藏空格，防止 BATTERY_CAPACITY 后面误带空格
    param_name = param_name.strip()
    dataset_name = dataset_name.strip()

    # 检查 Config 中是否存在该参数
    if not hasattr(Config, param_name):
        print(f"Unknown Config parameter: {param_name}")
        print("请检查 src/config.py 中是否定义了该参数。")
        return

    # 创建结果根目录
    os.makedirs(Config.RESULT_DIR, exist_ok=True)

    original_val = getattr(Config, param_name)

    print("=" * 70)
    print(f"Start sensitivity analysis for: {param_name}")
    print(f"Range: {start_val} -> {end_val}, step = {step_val}")
    print(f"Dataset: {dataset_name}")
    print(f"Result root: {Config.RESULT_DIR}")
    print("=" * 70)

    algorithms = {
        "GA": run_ga,
        "GWO": run_gwo,
        "IGWO": run_igwo,
    }

    # 读取数据
    csv_file = f"{dataset_name}.csv"
    ensure_csv_exists(csv_file)
    depot_orig, customers_orig = load_data(csv_file)

    # 参数取值序列
    param_values = np.arange(
        start_val,
        end_val + step_val / 1000.0,
        step_val
    )

    try:
        for raw_value in param_values:
            if isinstance(original_val, int):
                current_val = int(round(raw_value))
            else:
                current_val = round(float(raw_value), 4)

            # 修改 Config 中对应参数
            setattr(Config, param_name, current_val)

            print("\n" + "-" * 70)
            print(f"Testing {param_name} = {current_val}")
            print("-" * 70)

            # 每个参数值下重新生成充电站
            stations = generate_stations_kmeans(customers_orig, depot_orig)

            for algo_name, algo_func in algorithms.items():

                # 注意：这里的 Sensitivity_Analysis 后面不能有空格
                save_folder = os.path.join(
                    Config.RESULT_DIR,
                    "Sensitivity_Analysis",
                    param_name,
                    dataset_name,
                    algo_name,
                )

                os.makedirs(save_folder, exist_ok=True)

                print(f"\n  Algorithm: {algo_name}")
                print(f"  Save folder: {save_folder}")

                for run_id in range(run_times):
                    filename = f"{current_val}_{run_id}.json"
                    file_path = os.path.join(save_folder, filename)

                    if os.path.exists(file_path):
                        print(f"    [Skip] {filename} already exists")
                        continue

                    print(f"    Run {run_id + 1}/{run_times} ... ", end="")
                    start_time = time.time()

                    try:
                        # 深拷贝客户数据，避免算法内部修改原始数据
                        cust_run = copy.deepcopy(customers_orig)

                        result = algo_func(depot_orig, cust_run, stations)

                        if len(result) == 3:
                            _, detailed_routes, history = result
                        else:
                            _, detailed_routes = result
                            history = []

                        elapsed = time.time() - start_time

                        # 从详细路径中恢复客户访问序列
                        recovered_chrom = []
                        for route in detailed_routes:
                            for step in route:
                                if step.type == "customer":
                                    recovered_chrom.append(step.node)

                        # 重新计算成本分解
                        costs, detailed_routes = analyze_best_solution_breakdown(
                            recovered_chrom,
                            depot_orig,
                            stations
                        )

                        result_data = {
                            "algorithm": algo_name,
                            "parameter": param_name,
                            "value": current_val,
                            "dataset": dataset_name,
                            "run_id": run_id,
                            "time_seconds": elapsed,
                            "history_tail": history[-10:] if history else [],
                            "costs": costs,
                            "routes_simple": [
                                [step.id for step in route]
                                for route in detailed_routes
                            ],
                            "route_details": [
                                [step.to_dict() for step in route]
                                for route in detailed_routes
                            ],
                        }

                        with open(file_path, "w", encoding="utf-8") as file_obj:
                            json.dump(
                                result_data,
                                file_obj,
                                indent=4,
                                ensure_ascii=False
                            )

                        total_cost = costs.get("total_cost", 0)
                        queue_time = costs.get("queue_wait_time_min", 0)
                        congestion_time = costs.get("congestion_delay_time_min", 0)

                        print(
                            "saved "
                            f"(cost={total_cost:.1f}, "
                            f"queue={queue_time:.1f} min, "
                            f"congestion={congestion_time:.1f} min)"
                        )

                    except Exception as exc:
                        print(f"failed: {exc}")
                        traceback.print_exc()

    finally:
        # 恢复原始参数值，避免影响后续实验
        setattr(Config, param_name, original_val)
        print("\n" + "=" * 70)
        print(f"Restored Config.{param_name} = {original_val}")
        print("=" * 70)


if __name__ == "__main__":
    run_sensitivity_analysis_multi_algo(
        param_name="BATTERY_CAPACITY",
        start_val=60.0,
        end_val=200.0,
        step_val=20.0,
        dataset_name="c201",
        run_times=3,
    )
