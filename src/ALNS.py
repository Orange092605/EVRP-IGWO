# -*- coding: utf-8 -*-
"""
ALNS for C204 mixed public-private charging mode

核心原则：
1. ALNS 只负责生成客户访问顺序；
2. 最终成本评价统一调用原 GA / IGWO 的 split_chrom_to_routes(chromosome, depot, stations)；
3. 不再使用单独写的简化成本函数，避免成本被放大；
4. 自动读取 C204 数据并加入论文中的 12 个充电桩；
5. 自动运行 4 次，输出简洁 JSON 和详细 JSON。
"""

import csv
import json
import math
import random
import sys
import time
import inspect
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


# ============================================================
# 1. 路径设置：兼容 ALNS.py 放在 car/ 或 car/src/
# ============================================================

THIS_FILE = Path(__file__).resolve()

if THIS_FILE.parent.name.lower() == "src":
    PROJECT_DIR = THIS_FILE.parent.parent
else:
    PROJECT_DIR = THIS_FILE.parent

DATA_PATH = PROJECT_DIR / "data" / "c204.csv"
OUTPUT_DIR = PROJECT_DIR / "results" / "Comparison_Test_Batch_01"

DATASET_NAME = "c204"
MODE = "mixed"
ALGORITHM_NAME = "ALNS"
RUN_TIMES = 4

if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

try:
    from src.config import Config
    from src.physics import split_chrom_to_routes
except Exception:
    from config import Config
    from physics import split_chrom_to_routes


# ============================================================
# 2. 按论文 Table 5 写入参数
# ============================================================

def apply_paper_parameters_to_config():
    """
    将论文 Table 5 中的车辆与成本参数写入 Config。
    由于你原项目 Config 字段名不一定完全一致，这里设置多个常见别名。
    """

    alias_groups = [
        (("BATTERY_CAPACITY BEFORE", "BATTERY_CAP", "Q", "MAX_BATTERY", "battery_capacity"), 60.0),
        (("VEHICLE_CAPACITY", "MAX_LOAD", "CAPACITY", "vehicle_capacity"), 200.0),
        (("DISTANCE_COST", "TRAVEL_COST", "COST_PER_KM", "distance_cost"), 0.8),

        (("BASE_ELECTRICITY_PRICE", "ELECTRICITY_PRICE", "BASE_PRICE", "base_electricity_price"), 0.6),
        (("SERVICE_FEE", "PUBLIC_SERVICE_FEE", "service_fee"), 0.3),
        (("ELECTRICITY_PRICE_FLUCT", "PRICE_FLUCT", "PUBLIC_PRICE_FLUCT", "electricity_price_fluct"), 0.4),

        (("PRIVATE_CHARGING_PRICE", "PRIVATE_PRICE", "private_charging_price"), 0.6),
        (("PUBLIC_CHARGING_PRICE", "PUBLIC_PRICE", "public_charging_price"), 1.14),

        (("REFRIGERATION_POWER", "FRIDGE_POWER", "refrigeration_power"), 2.0),
        (("REFRIGERATION_COST", "FRIDGE_COST_RATE", "REFRIGERATION_COST_PER_HOUR", "refrigeration_cost"), 0.4),
        (("CONVERSION_EFFICIENCY", "ETA", "conversion_efficiency"), 0.9),

        (("EARLY_PENALTY", "EARLY_PENALTY_RATE", "early_penalty"), 2.0),
        (("LATE_PENALTY", "LATE_PENALTY_RATE", "late_penalty"), 4.0),

        (("CARGO_LOSS_COST", "CARGO_LOSS_UNIT_COST", "cargo_loss_cost"), 8.0),
        (("UNLOADING_LOSS_COEFF", "UNLOAD_LOSS_COEFF", "unloading_loss_coeff"), 0.02),
        (("NON_UNLOADING_LOSS_COEFF", "NONUNLOAD_LOSS_COEFF", "non_unloading_loss_coeff"), 0.002),

        (("BASE_ENERGY_CONSUMPTION", "BASE_ENERGY", "EMPTY_ENERGY_RATE", "base_energy_consumption"), 0.4),
        (("WEIGHT_SENSITIVITY", "LOAD_SENSITIVITY", "weight_sensitivity"), 0.05),
        (("SPEED_SENSITIVITY", "speed_sensitivity"), 0.1),

        (("MAX_SPEED", "MAXIMUM_SPEED", "max_speed"), 80.0),
        (("CHARGING_POWER", "CHARGE_POWER", "charging_power"), 60.0),
        (("MAX_DRIVING_RANGE", "MAX_RANGE", "maximum_driving_range"), 120.0),
    ]

    for names, value in alias_groups:
        for name in names:
            try:
                setattr(Config, name, value)
            except Exception:
                pass


# ============================================================
# 3. 数据结构
# ============================================================

@dataclass
class Node:
    id: int
    x: float
    y: float
    demand: float = 0.0
    ready: float = 0.0
    due: float = 10 ** 9
    service: float = 0.0
    node_type: str = "customer"   # depot / customer / private / public
    price: float = 0.0            # 新增：充电站价格，解决 Node 缺少 price 的问题

    # ---- 常见属性别名，兼容 physics.py 中不同写法 ----

    @property
    def node_id(self):
        return self.id

    @property
    def idx(self):
        return self.id

    @property
    def index(self):
        return self.id

    @property
    def name(self):
        if self.node_type == "depot":
            return "D0"
        return str(self.id)

    @property
    def type(self):
        return self.node_type

    @property
    def ready_time(self):
        return self.ready

    @property
    def due_time(self):
        return self.due

    @property
    def service_time(self):
        return self.service

    @property
    def tw_start(self):
        return self.ready

    @property
    def tw_end(self):
        return self.due

    @property
    def start_time(self):
        return self.ready

    @property
    def end_time(self):
        return self.due

    @property
    def coordinate(self):
        return (self.x, self.y)

    @property
    def coordinates(self):
        return (self.x, self.y)

    @property
    def coord(self):
        return (self.x, self.y)

    @property
    def is_customer(self):
        return self.node_type == "customer"

    @property
    def is_depot(self):
        return self.node_type == "depot"

    @property
    def is_station(self):
        return self.node_type in ("private", "public", "station")

    @property
    def is_charging_station(self):
        return self.node_type in ("private", "public", "station")

    @property
    def is_private(self):
        return self.node_type == "private"

    @property
    def is_public(self):
        return self.node_type == "public"

    @property
    def station_type(self):
        return self.node_type

    @property
    def charging_price(self):
        return self.price

    @property
    def electricity_price(self):
        return self.price

    @property
    def charge_price(self):
        return self.price

    @property
    def unit_price(self):
        return self.price

    def __getitem__(self, key):
        mapping = {
            "id": self.id,
            "node_id": self.id,
            "idx": self.id,
            "index": self.id,
            "name": self.name,

            "x": self.x,
            "y": self.y,

            "demand": self.demand,

            "ready": self.ready,
            "ready_time": self.ready,
            "tw_start": self.ready,
            "start_time": self.ready,

            "due": self.due,
            "due_time": self.due,
            "tw_end": self.due,
            "end_time": self.due,

            "service": self.service,
            "service_time": self.service,

            "type": self.node_type,
            "node_type": self.node_type,
            "station_type": self.node_type,

            "coord": (self.x, self.y),
            "coordinate": (self.x, self.y),
            "coordinates": (self.x, self.y),

            "price": self.price,
            "charging_price": self.price,
            "electricity_price": self.price,
            "charge_price": self.price,
            "unit_price": self.price,
        }

        if key not in mapping:
            raise KeyError(key)

        return mapping[key]


NODE_MAP = {}


# ============================================================
# 4. 读取 c204数据
# ============================================================

def _to_float(value):
    try:
        return float(value)
    except Exception:
        return None


def load_c204_csv(path: Path):
    """
    读取 C204 数据。
    返回：
    depot = 0
    customers = [1, 2, ..., 100]

    节点详细信息保存在 NODE_MAP 中。
    """

    if not path.exists():
        raise FileNotFoundError(f"找不到数据文件：{path}")

    NODE_MAP.clear()

    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)

        for row in reader:
            if not row:
                continue

            raw = " ".join(str(x) for x in row)
            raw = raw.replace(",", " ").replace(";", " ")
            parts = raw.split()

            nums = []

            for p in parts:
                v = _to_float(p)
                if v is not None:
                    nums.append(v)

            if len(nums) < 7:
                continue

            node_id = int(nums[0])

            # 只读取配送中心和客户。充电站后面按论文坐标单独加入。
            if node_id != 0 and not (1 <= node_id <= 100):
                continue

            node = Node(
                id=node_id,
                x=float(nums[1]),
                y=float(nums[2]),
                demand=float(nums[3]),
                ready=float(nums[4]),
                due=float(nums[5]),
                service=float(nums[6]),
                node_type="depot" if node_id == 0 else "customer",
                price=0.0,
            )

            NODE_MAP[node_id] = node

    if 0 not in NODE_MAP:
        raise ValueError("c204.csv 中没有找到编号为 0 的配送中心。")

    customers = sorted([i for i in NODE_MAP.keys() if 1 <= i <= 100])

    if not customers:
        raise ValueError("没有读取到客户节点，请检查 c204.csv 列顺序是否为 id,x,y,demand,ready,due,service。")

    return 0, customers


def build_mixed_stations():
    """
    论文实验设置：
    1000-1005 为私人充电桩；
    1006-1011 为公共充电桩。

    price:
    private = 0.6
    public = 0.6 * (1 + 0.4) + 0.3 = 1.14
    """

    private_price = 0.6
    public_price = 0.6 * (1.0 + 0.4) + 0.3

    station_data = [
        (1000, 49, 34, "private", private_price),
        (1001, 18, 66, "private", private_price),
        (1002, 67, 54, "private", private_price),
        (1003, 6, 42, "private", private_price),
        (1004, 39, 12, "private", private_price),
        (1005, 88, 34, "private", private_price),

        (1006, 61, 83, "public", public_price),
        (1007, 40, 65, "public", public_price),
        (1008, 25, 52, "public", public_price),
        (1009, 20, 80, "public", public_price),
        (1010, 58, 70, "public", public_price),
        (1011, 31, 33, "public", public_price),
    ]

    stations = []

    for sid, x, y, stype, price in station_data:
        NODE_MAP[sid] = Node(
            id=sid,
            x=float(x),
            y=float(y),
            demand=0.0,
            ready=0.0,
            due=10 ** 9,
            service=0.0,
            node_type=stype,
            price=float(price),
        )

        stations.append(sid)

    return stations


def apply_data_to_config(depot, customers, stations):
    """
    将节点数据写入 Config，兼容 split_chrom_to_routes 内部从 Config 读取数据的情况。
    """

    depot_obj = NODE_MAP.get(get_node_id(depot))
    customer_objs = [NODE_MAP[get_node_id(i)] for i in customers]
    station_objs = [NODE_MAP[get_node_id(i)] for i in stations]

    private_stations = [s for s in stations if NODE_MAP[s].node_type == "private"]
    public_stations = [s for s in stations if NODE_MAP[s].node_type == "public"]

    data_aliases = {
        "DEPOT": depot,
        "DEPOT_ID": get_node_id(depot),
        "DEPOT_NODE": depot_obj,

        "CUSTOMERS": customers,
        "CUSTOMER_IDS": customers,
        "CUSTOMER_NODES": customer_objs,

        "STATIONS": stations,
        "CHARGING_STATIONS": stations,
        "STATION_IDS": stations,
        "STATION_NODES": station_objs,

        "PRIVATE_STATIONS": private_stations,
        "PUBLIC_STATIONS": public_stations,
        "PRIVATE_STATION_NODES": [NODE_MAP[s] for s in private_stations],
        "PUBLIC_STATION_NODES": [NODE_MAP[s] for s in public_stations],

        "NODES": NODE_MAP,
        "NODE_MAP": NODE_MAP,
        "NODE_DICT": NODE_MAP,
        "ALL_NODES": NODE_MAP,
    }

    for key, value in data_aliases.items():
        try:
            setattr(Config, key, value)
        except Exception:
            pass


# ============================================================
# 5. 节点工具函数
# ============================================================

def get_node_id(node):
    if isinstance(node, int):
        return node

    if isinstance(node, Node):
        return node.id

    if isinstance(node, dict):
        for key in ["id", "node_id", "node", "idx", "index", "name"]:
            if key in node:
                value = node[key]
                if isinstance(value, str) and value.startswith("D"):
                    return 0
                try:
                    return int(value)
                except Exception:
                    return value

    for attr in ["id", "node_id", "node", "idx", "index", "name"]:
        if hasattr(node, attr):
            value = getattr(node, attr)
            if isinstance(value, str) and value.startswith("D"):
                return 0
            try:
                return int(value)
            except Exception:
                return value

    return node


def get_xy(node):
    node_id = get_node_id(node)

    if node_id in NODE_MAP:
        n = NODE_MAP[node_id]
        return float(n.x), float(n.y)

    if isinstance(node, dict):
        return float(node.get("x", 0.0)), float(node.get("y", 0.0))

    return float(getattr(node, "x", 0.0)), float(getattr(node, "y", 0.0))


def node_distance(a, b):
    ax, ay = get_xy(a)
    bx, by = get_xy(b)
    return math.hypot(ax - bx, ay - by)


def simplify_routes(routes):
    if routes is None:
        return []

    simple = []

    for route in routes:
        if isinstance(route, (list, tuple)):
            simple.append([get_node_id(n) for n in route])
        else:
            simple.append([get_node_id(route)])

    return simple


def is_routes_like(obj):
    return isinstance(obj, (list, tuple)) and len(obj) > 0 and isinstance(obj[0], (list, tuple))


def normalize_costs(costs_or_cost):
    if isinstance(costs_or_cost, (int, float)):
        return {"total_cost": float(costs_or_cost)}

    if isinstance(costs_or_cost, dict):
        if "total_cost" in costs_or_cost:
            total = costs_or_cost["total_cost"]
        elif "cost" in costs_or_cost:
            total = costs_or_cost["cost"]
        elif "total" in costs_or_cost:
            total = costs_or_cost["total"]
        else:
            total = 0.0
            for value in costs_or_cost.values():
                if isinstance(value, (int, float)):
                    total += float(value)

        output = dict(costs_or_cost)
        output["total_cost"] = float(total)
        return output

    raise ValueError(f"无法识别成本返回值：{type(costs_or_cost)}")


def parse_split_result(result):
    """
    兼容 split_chrom_to_routes 常见返回形式。
    """

    if isinstance(result, dict):
        routes = result.get("routes", result.get("routes_simple", []))

        costs_raw = result.get("costs", None)
        if costs_raw is None:
            costs_raw = result.get("cost", result.get("total_cost", result.get("total", None)))

        costs = normalize_costs(costs_raw)
        return costs["total_cost"], routes, costs

    if isinstance(result, tuple):
        routes = None
        costs_raw = None
        numeric_cost = None

        for item in result:
            if isinstance(item, dict):
                costs_raw = item
            elif isinstance(item, (int, float)):
                numeric_cost = float(item)
            elif is_routes_like(item):
                routes = item

        if costs_raw is not None:
            costs = normalize_costs(costs_raw)

            if numeric_cost is not None:
                costs["total_cost"] = numeric_cost

            return costs["total_cost"], routes, costs

        if numeric_cost is not None:
            costs = {"total_cost": numeric_cost}
            return numeric_cost, routes, costs

    raise ValueError(f"split_chrom_to_routes 的返回格式无法解析：{type(result)}")


# ============================================================
# 6. 唯一成本评价入口：调用原始 split_chrom_to_routes
# ============================================================

def evaluate_by_original_cost(chrom, depot, customers, stations, mode=MODE):
    """
    ALNS 只生成客户访问顺序；
    成本统一调用原 GA / IGWO 中的 split_chrom_to_routes。

    你的函数签名已经确认：
    split_chrom_to_routes(chromosome, depot, stations)

    因此这里不传 customers，也不传 mode。
    """

    chrom_objs = []

    for cid in chrom:
        node_id = get_node_id(cid)

        if node_id not in NODE_MAP:
            raise KeyError(f"客户节点 {node_id} 不在 NODE_MAP 中，请检查c204 .csv 是否读取完整。")

        chrom_objs.append(NODE_MAP[node_id])

    depot_id = get_node_id(depot)

    if depot_id not in NODE_MAP:
        raise KeyError(f"配送中心节点 {depot_id} 不在 NODE_MAP 中。")

    depot_obj = NODE_MAP[depot_id]

    station_objs = []

    for sid in stations:
        station_id = get_node_id(sid)

        if station_id not in NODE_MAP:
            raise KeyError(f"充电站节点 {station_id} 不在 NODE_MAP 中。")

        station_objs.append(NODE_MAP[station_id])

    try:
        result = split_chrom_to_routes(chrom_objs, depot_obj, station_objs)
        total_cost, routes, costs = parse_split_result(result)
        return float(total_cost), routes, costs

    except Exception as e:
        raise RuntimeError(
            "split_chrom_to_routes(chromosome, depot, stations) 调用失败。\n"
            "当前已传入：\n"
            f"  chromosome 类型：{type(chrom_objs)}，元素类型：{type(chrom_objs[0]) if chrom_objs else None}\n"
            f"  depot 类型：{type(depot_obj)}\n"
            f"  stations 类型：{type(station_objs)}，元素类型：{type(station_objs[0]) if station_objs else None}\n"
            f"原始错误：{type(e).__name__}: {e}"
        )


# ============================================================
# 7. ALNS destroy operators
# ============================================================

def random_removal(order, q, rng):
    q = min(q, len(order))

    remove_idx = set(rng.sample(range(len(order)), q))

    removed = [order[i] for i in sorted(remove_idx)]
    remaining = [n for i, n in enumerate(order) if i not in remove_idx]

    return remaining, removed


def block_removal(order, q, rng):
    q = min(q, len(order))

    if q <= 0:
        return order[:], []

    start = rng.randint(0, len(order) - q)
    remove_idx = set(range(start, start + q))

    removed = [order[i] for i in sorted(remove_idx)]
    remaining = [n for i, n in enumerate(order) if i not in remove_idx]

    return remaining, removed


def related_removal(order, q, rng):
    q = min(q, len(order))

    if q <= 0:
        return order[:], []

    seed = rng.choice(order)
    scored = []

    for i, node in enumerate(order):
        scored.append((node_distance(seed, node), i))

    scored.sort(key=lambda x: x[0])

    remove_idx = set(i for _, i in scored[:q])

    removed = [order[i] for i in sorted(remove_idx)]
    remaining = [n for i, n in enumerate(order) if i not in remove_idx]

    return remaining, removed


def worst_removal(order, q, rng, depot):
    q = min(q, len(order))

    if q <= 0:
        return order[:], []

    scored = []

    for i, node in enumerate(order):
        prev_node = depot if i == 0 else order[i - 1]
        next_node = depot if i == len(order) - 1 else order[i + 1]

        saving = (
            node_distance(prev_node, node)
            + node_distance(node, next_node)
            - node_distance(prev_node, next_node)
        )

        scored.append((saving, i))

    scored.sort(key=lambda x: x[0], reverse=True)

    remove_idx = set(i for _, i in scored[:q])

    removed = [order[i] for i in sorted(remove_idx)]
    remaining = [n for i, n in enumerate(order) if i not in remove_idx]

    return remaining, removed


# ============================================================
# 8. ALNS repair operators
# ============================================================

def greedy_insertion(partial, removed, depot, customers, stations, rng):
    order = partial[:]
    pool = removed[:]
    rng.shuffle(pool)

    for node in pool:
        best_pos = 0
        best_cost = float("inf")

        for pos in range(len(order) + 1):
            candidate = order[:pos] + [node] + order[pos:]

            try:
                cost, _, _ = evaluate_by_original_cost(candidate, depot, customers, stations)
            except Exception:
                cost = float("inf")

            if cost < best_cost:
                best_cost = cost
                best_pos = pos

        order.insert(best_pos, node)

    return order


def regret_2_insertion(partial, removed, depot, customers, stations, rng):
    order = partial[:]
    pool = removed[:]

    while pool:
        best_node = None
        best_pos = 0
        best_regret = -float("inf")
        best_first_cost = float("inf")

        for node in pool:
            results = []

            for pos in range(len(order) + 1):
                candidate = order[:pos] + [node] + order[pos:]

                try:
                    cost, _, _ = evaluate_by_original_cost(candidate, depot, customers, stations)
                except Exception:
                    cost = float("inf")

                results.append((cost, pos))

            results.sort(key=lambda x: x[0])

            first_cost, first_pos = results[0]
            second_cost = results[1][0] if len(results) > 1 else first_cost
            regret = second_cost - first_cost

            if regret > best_regret or (
                abs(regret - best_regret) < 1e-9 and first_cost < best_first_cost
            ):
                best_regret = regret
                best_first_cost = first_cost
                best_node = node
                best_pos = first_pos

        if best_node is None:
            best_node = pool[0]
            best_pos = rng.randint(0, len(order))

        order.insert(best_pos, best_node)
        pool.remove(best_node)

    return order


# ============================================================
# 9. ALNS 主参数
# ============================================================

ALNS_ITERATIONS = 250
ALNS_INIT_TRIALS = 20
MIN_REMOVE_RATIO = 0.05
MAX_REMOVE_RATIO = 0.16
COOLING_RATE = 0.995
UPDATE_SEGMENT = 30

RHO = 0.25
SIGMA_BEST = 25.0
SIGMA_BETTER = 20.0
SIGMA_ACCEPT = 12.0


# ============================================================
# 10. ALNS 主过程
# ============================================================

def roulette_select(weights, rng):
    total = sum(weights)

    if total <= 0:
        return rng.randrange(len(weights))

    r = rng.random() * total
    acc = 0.0

    for i, w in enumerate(weights):
        acc += w

        if acc >= r:
            return i

    return len(weights) - 1


def generate_initial_solution(customers, depot, stations, rng):
    candidates = []

    base = sorted(
        customers,
        key=lambda cid: (
            NODE_MAP[get_node_id(cid)].ready,
            NODE_MAP[get_node_id(cid)].x,
            NODE_MAP[get_node_id(cid)].y,
        )
    )

    candidates.append(base)

    for _ in range(ALNS_INIT_TRIALS):
        temp = base[:]

        for _ in range(max(5, len(temp) // 10)):
            i = rng.randrange(len(temp))
            j = rng.randrange(len(temp))
            temp[i], temp[j] = temp[j], temp[i]

        candidates.append(temp)

    for _ in range(max(5, ALNS_INIT_TRIALS // 2)):
        temp = customers[:]
        rng.shuffle(temp)
        candidates.append(temp)

    best_order = None
    best_cost = float("inf")
    best_routes = None
    best_costs = None
    errors = []

    for candidate in candidates:
        try:
            cost, routes, costs = evaluate_by_original_cost(candidate, depot, customers, stations)
        except Exception as e:
            errors.append(str(e))
            continue

        if cost < best_cost:
            best_order = candidate[:]
            best_cost = cost
            best_routes = routes
            best_costs = costs

    if best_order is None:
        try:
            signature = str(inspect.signature(split_chrom_to_routes))
        except Exception:
            signature = "无法读取函数签名"

        error_preview = "\n\n".join(errors[-3:])

        raise RuntimeError(
            "初始解均无法被 split_chrom_to_routes 评价。\n"
            f"split_chrom_to_routes 函数签名：{signature}\n"
            "最近错误如下：\n"
            f"{error_preview}\n\n"
            "如果仍失败，请检查 physics.py 中 split_chrom_to_routes 是否还需要其他节点属性。"
        )

    return best_order, best_cost, best_routes, best_costs


def run_alns_once(depot, customers, stations, run_id, seed):
    rng = random.Random(seed)
    start_time = time.perf_counter()

    current_order, current_cost, current_routes, current_costs = generate_initial_solution(
        customers, depot, stations, rng
    )

    best_order = current_order[:]
    best_cost = current_cost
    best_routes = current_routes
    best_costs = current_costs

    destroy_names = ["random", "related", "worst", "block"]
    repair_names = ["greedy", "regret2"]

    destroy_weights = [1.0] * len(destroy_names)
    repair_weights = [1.0] * len(repair_names)

    destroy_scores = [0.0] * len(destroy_names)
    repair_scores = [0.0] * len(repair_names)

    destroy_uses = [0] * len(destroy_names)
    repair_uses = [0] * len(repair_names)

    temperature = max(1.0, 0.01 * current_cost / max(math.log(2), 1e-9))

    print("=" * 70)
    print(f"开始 ALNS：dataset={DATASET_NAME}, mode={MODE}, run_id={run_id}")
    print(f"初始成本：{current_cost:.4f}")
    print("=" * 70)

    for it in range(1, ALNS_ITERATIONS + 1):
        q = max(1, int(len(customers) * rng.uniform(MIN_REMOVE_RATIO, MAX_REMOVE_RATIO)))

        d_idx = roulette_select(destroy_weights, rng)
        r_idx = roulette_select(repair_weights, rng)

        d_name = destroy_names[d_idx]
        r_name = repair_names[r_idx]

        if d_name == "random":
            partial, removed = random_removal(current_order, q, rng)
        elif d_name == "related":
            partial, removed = related_removal(current_order, q, rng)
        elif d_name == "worst":
            partial, removed = worst_removal(current_order, q, rng, depot)
        else:
            partial, removed = block_removal(current_order, q, rng)

        if r_name == "greedy":
            candidate_order = greedy_insertion(partial, removed, depot, customers, stations, rng)
        else:
            candidate_order = regret_2_insertion(partial, removed, depot, customers, stations, rng)

        try:
            candidate_cost, candidate_routes, candidate_costs = evaluate_by_original_cost(
                candidate_order, depot, customers, stations
            )
        except Exception:
            candidate_cost = float("inf")
            candidate_routes = None
            candidate_costs = None

        accepted = False
        score = 0.0

        if candidate_cost < current_cost:
            accepted = True
            score = SIGMA_BETTER
        else:
            delta = candidate_cost - current_cost
            prob = math.exp(-delta / max(temperature, 1e-9)) if math.isfinite(delta) else 0.0

            if rng.random() <= prob:
                accepted = True
                score = SIGMA_ACCEPT

        if accepted:
            current_order = candidate_order[:]
            current_cost = candidate_cost
            current_routes = candidate_routes
            current_costs = candidate_costs

        if candidate_cost < best_cost:
            best_order = candidate_order[:]
            best_cost = candidate_cost
            best_routes = candidate_routes
            best_costs = candidate_costs
            score = SIGMA_BEST

            print(f"Iter {it:4d} | best_cost={best_cost:.4f}")

        destroy_scores[d_idx] += score
        repair_scores[r_idx] += score

        destroy_uses[d_idx] += 1
        repair_uses[r_idx] += 1

        temperature *= COOLING_RATE

        if it % UPDATE_SEGMENT == 0:
            for i in range(len(destroy_weights)):
                if destroy_uses[i] > 0:
                    avg = destroy_scores[i] / destroy_uses[i]
                    destroy_weights[i] = (1 - RHO) * destroy_weights[i] + RHO * avg

            for i in range(len(repair_weights)):
                if repair_uses[i] > 0:
                    avg = repair_scores[i] / repair_uses[i]
                    repair_weights[i] = (1 - RHO) * repair_weights[i] + RHO * avg

            destroy_scores = [0.0] * len(destroy_names)
            repair_scores = [0.0] * len(repair_names)

            destroy_uses = [0] * len(destroy_names)
            repair_uses = [0] * len(repair_names)

    duration = time.perf_counter() - start_time

    result = {
        "dataset": DATASET_NAME,
        "algorithm": ALGORITHM_NAME,
        "run_id": run_id,
        "cost": float(best_cost),
        "time_seconds": float(duration),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    detail = {
        **result,
        "mode": MODE,
        "costs": best_costs,
        "routes_simple": simplify_routes(best_routes),
    }

    print("-" * 70)
    print(f"ALNS 完成：run_id={run_id}")
    print(f"最终成本 cost：{best_cost:.4f}")
    print(f"运行时间：{duration:.2f}s")
    print("-" * 70)

    return result, detail


def save_json(result, detail):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    run_id = result["run_id"]

    simple_path = OUTPUT_DIR / f"{DATASET_NAME}_{ALGORITHM_NAME}_{MODE}_run{run_id}.json"
    detail_path = OUTPUT_DIR / f"{DATASET_NAME}_{ALGORITHM_NAME}_{MODE}_run{run_id}_detail.json"

    with open(simple_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    with open(detail_path, "w", encoding="utf-8") as f:
        json.dump(detail, f, ensure_ascii=False, indent=2)

    print(f"简洁 JSON 已保存：{simple_path}")
    print(f"详细 JSON 已保存：{detail_path}")


def main():
    apply_paper_parameters_to_config()

    print(f"正在读取数据：{DATA_PATH}")

    depot, customers = load_c204_csv(DATA_PATH)
    stations = build_mixed_stations()

    apply_data_to_config(depot, customers, stations)

    print(f"客户数量：{len(customers)}")
    print(f"充电桩数量：{len(stations)}")
    print(f"输出目录：{OUTPUT_DIR}")
    print("成本评价函数：split_chrom_to_routes")
    print(f"split_chrom_to_routes 函数签名：{inspect.signature(split_chrom_to_routes)}")

    all_results = []

    for run_id in range(RUN_TIMES):
        result, detail = run_alns_once(
            depot=depot,
            customers=customers,
            stations=stations,
            run_id=run_id,
            seed=2026 + run_id,
        )

        save_json(result, detail)
        all_results.append(result)

    print("\n四次 ALNS 运行结果汇总：")

    for r in all_results:
        print(
            f"run_id={r['run_id']} | "
            f"cost={r['cost']:.4f} | "
            f"time={r['time_seconds']:.2f}s | "
            f"timestamp={r['timestamp']}"
        )


if __name__ == "__main__":
    main()