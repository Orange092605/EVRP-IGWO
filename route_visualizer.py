import json
import matplotlib.pyplot as plt
import os

# ==========================================
# 👇 在这里修改你要画的文件路径
# ==========================================
# 你可以使用相对路径 (例如 'results/...')
# 也可以使用绝对路径 (例如 'D:/Projects/EV_Routing/results/...')
# 建议在引号前加 r，防止路径中的斜杠被转义

TARGET_FILE = r"results/Comparison_Test_Batch_01/c201_IGWO_run0.json"


# ==========================================

def plot_route_from_file(json_path):
    """读取指定 JSON 文件并绘图"""

    # 1. 检查文件是否存在
    if not os.path.exists(json_path):
        print(f"❌ 错误: 找不到文件")
        print(f"   路径: {json_path}")
        print("   -> 请检查路径拼写，或确保文件已放入该目录。")
        return

    print(f"📂 正在读取: {os.path.basename(json_path)} ...")

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print("❌ 错误: 文件格式不对，不是有效的 JSON 文件。")
        return

    # 2. 解析数据
    flat_nodes = data.get('route_details', [])
    cost = data.get('cost', 0)
    dataset = data.get('dataset', 'Unknown')
    algo = data.get('algorithm', 'Unknown')
    run_id = data.get('run_id', '?')

    if not flat_nodes:
        print("⚠️ 警告: 该文件中没有路线数据 (route_details 为空)")
        return

    # 3. 重建路线结构 (从扁平列表还原为分车次的列表)
    routes = []
    current_route = []

    for node in flat_nodes:
        current_route.append(node)
        # 逻辑：遇到 Depot 且当前路线长度 > 1，说明这辆车跑完了
        if node['type'] == 'depot' and len(current_route) > 1:
            routes.append(current_route)
            current_route = []

            # 4. 开始绘图
    plt.figure(figsize=(12, 8))
    colors = plt.cm.tab20.colors  # 颜色板

    # A. 画背景点 (Depot, Customer, Station)
    legend_added = set()

    for node in flat_nodes:
        n_type = node['type']
        x, y = node['x'], node['y']

        if n_type == 'depot' and 'Depot' not in legend_added:
            plt.scatter(x, y, c='black', marker='s', s=120, zorder=10, label='Depot')
            legend_added.add('Depot')

        elif n_type == 'customer':
            plt.scatter(x, y, c='lightgray', s=30, zorder=1)  # 客户点太多，不加图例

        elif 'station' in n_type:
            is_private = 'private' in n_type
            lbl = 'Private Stn' if is_private else 'Public Stn'
            col = 'blue' if is_private else 'red'
            mk = '^' if is_private else 'v'

            if lbl not in legend_added:
                plt.scatter(x, y, c=col, marker=mk, s=80, zorder=9, label=lbl)
                legend_added.add(lbl)
            else:
                plt.scatter(x, y, c=col, marker=mk, s=80, zorder=9)

    # 手动补充 Customer 图例
    plt.scatter([], [], c='lightgray', s=30, label='Customer')

    # B. 画路线 (Line)
    for i, route in enumerate(routes):
        xs = [n['x'] for n in route]
        ys = [n['y'] for n in route]
        c = colors[i % len(colors)]

        plt.plot(xs, ys, color=c, linewidth=2, alpha=0.8, label=f'Vehicle {i + 1}')

    # 5. 图表修饰
    plt.title(f"Route Visualization\nFile: {os.path.basename(json_path)}\nDataset: {dataset} | Cost: {cost:.2f}")
    plt.xlabel("X Coordinate")
    plt.ylabel("Y Coordinate")
    plt.grid(True, linestyle='--', alpha=0.4)

    # 图例放外面，避免遮挡
    plt.legend(bbox_to_anchor=(1.02, 1), loc='upper left', borderaxespad=0.)

    plt.tight_layout()
    plt.show()
    print("✅ 绘图完成")


if __name__ == "__main__":
    # 运行绘图
    plot_route_from_file(TARGET_FILE)