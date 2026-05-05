import os

class Config:
    # --- 路径配置 (自动获取当前项目路径) ---
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    RESULT_DIR = os.path.join(BASE_DIR, 'results')

    # --- 基础物理参数 ---
    BATTERY_CAPACITY = 60.0
    CAPACITY = 200.0
    MAX_RANGE = 120.0

    # --- 成本参数 ---
    COST_DIST = 0.8
    PRICE_BASIC = 0.6
    PRICE_SERVICE = 0.3
    PRICE_FLOAT_RATE = 0.4
    PRICE_PUBLIC = PRICE_BASIC * (1 + PRICE_FLOAT_RATE) + PRICE_SERVICE

    # --- 设备与能耗参数 ---
    POWER_FRIDGE = 2.0
    COST_FRIDGE_HOUR = 0.4
    EFFICIENCY = 0.9
    F_E = 0.4
    ALPHA_WEIGHT = 0.00005
    BETA_SPEED = 0.001
    CHARGING_POWER = 60.0

    # --- 惩罚与货损参数 ---
    COST_EARLY = 0.5
    COST_LATE = 3.5
    COST_CARGO_LOSS = 8.0
    LOSS_BETA_UNLOAD = 0.02
    LOSS_BETA_TRANSIT = 0.00002

    # --- 速度与时间约束 ---
    START_HOUR = 7.0
    SPEED_PEAK = 30.0
    SPEED_NORMAL = 80.0
    PEAK_HOURS = [(7, 9), (17, 19)]

    # --- 算法与场景设置 ---
    VEHICLE_COUNT = 10
    NUM_PRIVATE_STATIONS = 6
    NUM_PUBLIC_STATIONS = 6
    STATION_MODE = 'mixed'

    POP_SIZE = 100
    GENERATIONS = 1500
    MUTATION_RATE = 0.3

# 确保结果目录存在
os.makedirs(Config.RESULT_DIR, exist_ok=True)
os.makedirs(Config.DATA_DIR, exist_ok=True)