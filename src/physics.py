import math
from src.config import Config


def get_current_real_hour(sim_min):
    return Config.START_HOUR + (sim_min / 60.0)


def get_speed(sim_min):
    hour = get_current_real_hour(sim_min) % 24
    for start, end in Config.PEAK_HOURS:
        if start <= hour < end:
            return Config.SPEED_PEAK
    return Config.SPEED_NORMAL


def calc_energy(dist_km, load_kg, speed_kmh):
    if speed_kmh <= 0.001: return 0
    e_drive = dist_km * (Config.F_E + Config.ALPHA_WEIGHT * load_kg + Config.BETA_SPEED * speed_kmh)
    if speed_kmh < 5.0:
        e_fridge = 0.0
    else:
        time_h = dist_km / speed_kmh
        e_fridge = (Config.POWER_FRIDGE * time_h) / Config.EFFICIENCY
    return e_drive + e_fridge


def calc_cargo_loss(dist_km, current_load, unload_load):
    loss_transit = Config.LOSS_BETA_TRANSIT * dist_km * current_load
    loss_unload = Config.LOSS_BETA_UNLOAD * unload_load
    return (loss_transit + loss_unload) * Config.COST_CARGO_LOSS


def evaluate_route(route_nodes, depot, stations):
    """
    [最终优化版]
    1. 允许极低速行驶 (JIT Speed) 以消除早到惩罚
    2. 配合 calc_energy 的低速豁免，消除制冷成本导致的死路(inf)
    """
    total_cost = 0.0
    cost_breakdown = {
        "driving_cost": 0.0, "charging_cost": 0.0,
        "penalty_cost": 0.0, "penalty_early": 0.0, "penalty_late": 0.0,
        "cargo_loss": 0.0, "fridge_cost": 0.0, "total_cost": 0.0
    }

    curr_node = depot
    curr_time = 0.0
    curr_batt = Config.BATTERY_CAPACITY
    curr_load = sum(c.demand for c in route_nodes)

    if curr_load > Config.CAPACITY:
        return float('inf'), [], cost_breakdown

    detailed_path = [depot]
    full_sequence = route_nodes + [depot]

    for target_node in full_sequence:
        dist = math.sqrt((curr_node.x - target_node.x) ** 2 + (curr_node.y - target_node.y) ** 2)

        # 1. 物理限速
        limit_speed = get_speed(curr_time)

        # 2. 计算 JIT 速度 (不再设下限！)
        time_window_gap_min = target_node.ready_time - curr_time
        jit_speed = limit_speed

        if time_window_gap_min > 0:
            time_window_gap_hour = time_window_gap_min / 60.0
            if time_window_gap_hour > 0:
                # 直接算，哪怕算出 0.1 km/h 也没关系
                calculated_slow_speed = dist / time_window_gap_hour
                jit_speed = min(limit_speed, calculated_slow_speed)

        # 兜底防止速度为0
        real_speed = jit_speed

        travel_time_h = dist / real_speed
        travel_time_min = travel_time_h * 60.0

        # 这里调用的 calc_energy 会触发“低速豁免”，不会产生巨额制冷费
        energy_req = calc_energy(dist, curr_load, real_speed)

        # --- 前瞻雷达 (保命电量) ---
        min_escape_energy = float('inf')
        load_after = curr_load - target_node.demand if target_node.type == 'customer' else curr_load

        for s_next in stations:
            d_escape = math.sqrt((target_node.x - s_next.x) ** 2 + (target_node.y - s_next.y) ** 2)
            # [重要] 逃生计算依然强制使用正常速度 (limit_speed)
            e_escape = calc_energy(d_escape, load_after, limit_speed)
            if e_escape < min_escape_energy:
                min_escape_energy = e_escape

        safe_escape_energy = min_escape_energy * 1.1

        best_decision = None
        min_step_cost = float('inf')
        decision_data = {}
        best_components = {}

        # --- 决策 A：直达 ---
        if curr_batt >= (energy_req + safe_escape_energy):
            arr_time = curr_time + travel_time_min
            wait_t = max(0, target_node.ready_time - arr_time)
            start_t = arr_time + wait_t

            c_early = wait_t * Config.COST_EARLY
            late_t = max(0, start_t - target_node.due_time)
            c_late = late_t * Config.COST_LATE
            c_penalty = c_early + c_late

            c_dist = dist * Config.COST_DIST

            # 统计制冷成本 (如果在路上因为低速被豁免了，这里就只剩 wait_t 的制冷费)
            # 这里的逻辑稍微复杂一点：evaluate_route 里的 fridge_cost 只是用来计费的
            # 真正的电量扣除是在 curr_batt -= energy_req 里完成的

            # 为了保持一致，我们手动计算显示的制冷费
            if real_speed < 5.0:
                # 路上不计费，只算等待时间的制冷
                c_fridge = (wait_t / 60.0) * Config.COST_FRIDGE_HOUR
            else:
                # 正常计费
                c_fridge = ((travel_time_min + wait_t) / 60.0) * Config.COST_FRIDGE_HOUR

            unload_amt = target_node.demand if target_node.type == 'customer' else 0
            c_cargo = calc_cargo_loss(dist, curr_load, unload_amt)

            step_cost = c_dist + c_penalty + c_fridge + c_cargo

            if step_cost < min_step_cost:
                min_step_cost = step_cost
                best_decision = 'direct'
                decision_data = {'energy': energy_req, 'start_t': start_t}
                best_components = {
                    "dist": c_dist, "charge": 0.0,
                    "penalty": c_penalty, "early": c_early, "late": c_late,
                    "cargo": c_cargo, "fridge": c_fridge
                }

        # --- 决策 B：充电 ---
        if curr_batt < (energy_req + safe_escape_energy) or curr_batt < Config.BATTERY_CAPACITY * 0.6:
            if curr_node.id != depot.id or curr_batt < Config.BATTERY_CAPACITY * 0.9:
                for station in stations:
                    if station.id == curr_node.id: continue
                    d1 = math.sqrt((curr_node.x - station.x) ** 2 + (curr_node.y - station.y) ** 2)

                    # 去充电站必须正常开，不能慢悠悠
                    e1 = calc_energy(d1, curr_load, limit_speed)
                    if curr_batt < e1: continue

                    d2 = math.sqrt((station.x - target_node.x) ** 2 + (station.y - target_node.y) ** 2)
                    # 充完电去客户，可以用 JIT 速度，但也可能太慢触发豁免，这里为了简化，假设正常速度
                    e2 = calc_energy(d2, curr_load, limit_speed)

                    if 'private' in station.type or station.type == 'depot':
                        target_level = Config.BATTERY_CAPACITY
                    else:
                        target_level = min(Config.BATTERY_CAPACITY, e2 + safe_escape_energy)

                    charge_need = max(0, target_level - (curr_batt - e1))
                    charge_time_min = (charge_need / Config.CHARGING_POWER) * 60.0
                    c_charge_fee = charge_need * station.price

                    t1_min = (d1 / limit_speed) * 60;
                    t2_min = (d2 / limit_speed) * 60
                    arr_target = curr_time + t1_min + charge_time_min + t2_min

                    wait_t = max(0, target_node.ready_time - arr_target)
                    start_t = arr_target + wait_t
                    late_t = max(0, start_t - target_node.due_time)

                    c_dist = (d1 + d2) * Config.COST_DIST
                    c_early = wait_t * Config.COST_EARLY
                    c_late = late_t * Config.COST_LATE
                    c_penalty = c_early + c_late

                    c_fridge = ((t1_min + charge_time_min + t2_min + wait_t) / 60.0) * Config.COST_FRIDGE_HOUR
                    unload_amt = target_node.demand if target_node.type == 'customer' else 0
                    c_cargo = calc_cargo_loss(d1 + d2, curr_load, unload_amt)

                    step_cost = c_dist + c_penalty + c_fridge + c_cargo + c_charge_fee

                    if step_cost < min_step_cost:
                        min_step_cost = step_cost
                        best_decision = station
                        decision_data = {'new_batt': target_level - e2, 'start_t': start_t}
                        best_components = {
                            "dist": c_dist, "charge": c_charge_fee,
                            "penalty": c_penalty, "early": c_early, "late": c_late,
                            "cargo": c_cargo, "fridge": c_fridge
                        }

        # --- 执行 ---
        if best_decision is None:
            return float('inf'), [], cost_breakdown

        cost_breakdown["driving_cost"] += best_components["dist"]
        cost_breakdown["charging_cost"] += best_components["charge"]
        cost_breakdown["penalty_cost"] += best_components["penalty"]
        cost_breakdown["penalty_early"] += best_components["early"]
        cost_breakdown["penalty_late"] += best_components["late"]
        cost_breakdown["cargo_loss"] += best_components["cargo"]
        cost_breakdown["fridge_cost"] += best_components["fridge"]
        total_cost += min_step_cost

        if best_decision == 'direct':
            curr_batt -= decision_data['energy']
            curr_time = decision_data['start_t'] + target_node.service_time
            detailed_path.append(target_node)
            curr_node = target_node
        else:
            station = best_decision
            curr_batt = decision_data['new_batt']
            curr_time = decision_data['start_t'] + target_node.service_time
            detailed_path.append(station)
            detailed_path.append(target_node)
            curr_node = target_node

        if target_node.type == 'customer':
            curr_load -= target_node.demand

    cost_breakdown["total_cost"] = total_cost
    return total_cost, detailed_path, cost_breakdown


def split_chrom_to_routes(chromosome, depot, stations):
    """
    解码器: 将染色体拆分为车辆路径
    [修改] 适配 evaluate_route 返回 3 个值的情况
    """
    total_cost = 0
    all_paths = []

    current_route = []
    current_load = 0

    for cust in chromosome:
        if current_load + cust.demand <= Config.CAPACITY:
            current_route.append(cust)
            current_load += cust.demand
        else:
            # 结算当前车
            # [修改点 1] 这里原本是 c, p = ... 现在改成 c, p, _ = ...
            # 我们用 _ 忽略掉 breakdown，因为在优化过程中只需要总分 c
            c, p, _ = evaluate_route(current_route, depot, stations)
            total_cost += c
            all_paths.append(p)
            # 新车
            current_route = [cust]
            current_load = cust.demand

    if current_route:
        # [修改点 2] 同样处理最后一辆车
        c, p, _ = evaluate_route(current_route, depot, stations)
        total_cost += c
        all_paths.append(p)

    # 车辆数量惩罚 (如果超过车队限制)
    # 这个惩罚必须加在 total_cost 里，否则算法会倾向于派很多车
    if len(all_paths) > Config.VEHICLE_COUNT:
        total_cost += (len(all_paths) - Config.VEHICLE_COUNT) * 10000

    return total_cost, all_paths


def decode_chromosome_to_routes():
    return None


def evaluate_solution():
    return None