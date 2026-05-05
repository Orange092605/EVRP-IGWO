import copy
import json
import os
import time
import traceback

from src.config import Config
from src.data_loader import ensure_csv_exists, generate_stations_kmeans, load_data
from src.algorithms import run_igwo
from src.physics import decode_chromosome_to_routes, evaluate_solution


EXPERIMENT_NAME = "Charging_Strategy_Analysis"
TARGET_DATASETS = ["c201", "c202"]
STRATEGIES = ["private_only", "public_only", "mixed"]
RUNS_PER_MODE = 4


def analyze_best_solution_breakdown(chromosome, depot, stations):
    routes = decode_chromosome_to_routes(chromosome)
    _, detailed_paths, breakdown = evaluate_solution(routes, depot, stations)
    return breakdown, detailed_paths


def run_strategy_analysis():
    print(f"Start charging-strategy analysis: {EXPERIMENT_NAME}")
    print(f"Results directory: {os.path.join(Config.RESULT_DIR, EXPERIMENT_NAME)}")

    save_dir = os.path.join(Config.RESULT_DIR, EXPERIMENT_NAME)
    os.makedirs(save_dir, exist_ok=True)

    for dataset_name in TARGET_DATASETS:
        csv_file = f"{dataset_name}.csv"
        ensure_csv_exists(csv_file)
        depot_orig, customers_orig = load_data(csv_file)

        print("=" * 60)
        print(f"Dataset: {dataset_name}")
        print("=" * 60)

        for mode in STRATEGIES:
            print(f"\nMode: {mode}")
            Config.STATION_MODE = mode
            stations = generate_stations_kmeans(customers_orig, depot_orig)

            for run_id in range(RUNS_PER_MODE):
                filename = f"{dataset_name}_IGWO_{mode}_run{run_id}.json"
                file_path = os.path.join(save_dir, filename)
                if os.path.exists(file_path):
                    print(f"  [Skip] {filename} already exists")
                    continue

                print(f"  Running {run_id + 1}/{RUNS_PER_MODE} ... ", end="")
                start_time = time.time()

                try:
                    cust_run = copy.deepcopy(customers_orig)
                    best_cost, detailed_routes, history = run_igwo(depot_orig, cust_run, stations)

                    recovered_chrom = []
                    for route in detailed_routes:
                        for step in route:
                            if step.type == "customer":
                                recovered_chrom.append(step.node)

                    costs, detailed_routes = analyze_best_solution_breakdown(recovered_chrom, depot_orig, stations)
                    elapsed = time.time() - start_time

                    result_data = {
                        "dataset": dataset_name,
                        "algorithm": "IGWO",
                        "mode": mode,
                        "run_id": run_id,
                        "time_seconds": elapsed,
                        "best_cost": best_cost,
                        "history_tail": history[-10:],
                        "costs": costs,
                        "routes_simple": [[step.to_dict() for step in route] for route in detailed_routes],
                    }

                    with open(file_path, "w", encoding="utf-8") as file_obj:
                        json.dump(result_data, file_obj, indent=4, ensure_ascii=False)

                    print(
                        "saved "
                        f"(total={costs['total_cost']:.1f}, drive={costs['driving_cost']:.1f}, "
                        f"charge={costs['charging_cost']:.1f}, queue={costs['queue_wait_time_min']:.1f} min)"
                    )
                except Exception as exc:
                    print(f"failed: {exc}")
                    traceback.print_exc()


if __name__ == "__main__":
    run_strategy_analysis()
