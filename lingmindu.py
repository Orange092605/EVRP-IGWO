import math
import pandas as pd
import matplotlib.pyplot as plt


# =====================================================
# 1. Optimized routes from Table 6
# =====================================================
# Note:
# Route 6 in the manuscript appears as "50→430".
# Here it is interpreted as "50→43→0".
# Node 1006 is included as a charging station with coordinate (61, 83).

routes = [
    [0, 68, 37, 54, 1005, 53, 40, 42, 41, 78, 77, 87, 0],
    [0, 32, 33, 35, 7, 86, 84, 1002, 82, 70, 80, 96, 0],
    [0, 2, 30, 39, 34, 36, 1001, 57, 52, 25, 10, 1007, 48, 1009, 0],
    [0, 20, 22, 27, 61, 49, 56, 59, 1009, 26, 1001, 44, 46, 1002, 13, 9, 90, 0],
    [0, 64, 100, 97, 92, 1002, 38, 18, 23, 1001, 14, 47, 1009, 79, 1006, 81, 0],
    [0, 1, 99, 94, 95, 98, 1003, 55, 58, 60, 45, 51, 50, 43, 0],
    [0, 93, 5, 75, 74, 3, 4, 89, 8, 0],
    [0, 63, 66, 66, 69, 65, 91, 88, 83, 85, 76, 1006, 71, 73, 0],
    [0, 67, 24, 62, 72, 29, 1008, 6, 1004, 31, 19, 16, 15, 11, 0],
    [0, 28, 12, 17, 21, 0]
]


# =====================================================
# 2. Node coordinates
# =====================================================
coords = {
    0: (40, 50),

    1: (52, 75), 2: (45, 70), 3: (62, 69), 4: (60, 66), 5: (42, 65),
    6: (16, 42), 7: (58, 70), 8: (34, 60), 9: (28, 70), 10: (35, 66),
    11: (35, 69), 12: (25, 85), 13: (22, 75), 14: (22, 85), 15: (20, 80),
    16: (20, 85), 17: (18, 75), 18: (15, 75), 19: (15, 80), 20: (30, 50),
    21: (30, 56), 22: (28, 52), 23: (14, 66), 24: (25, 50), 25: (22, 66),
    26: (8, 62), 27: (23, 52), 28: (4, 55), 29: (20, 50), 30: (20, 55),
    31: (10, 35), 32: (10, 40), 33: (8, 40), 34: (8, 45), 35: (5, 35),
    36: (5, 45), 37: (2, 40), 38: (0, 40), 39: (0, 45), 40: (36, 18),
    41: (35, 32), 42: (33, 32), 43: (33, 35), 44: (32, 20), 45: (30, 30),
    46: (34, 25), 47: (30, 35), 48: (36, 40), 49: (48, 20), 50: (26, 32),
    51: (25, 30), 52: (25, 35), 53: (44, 5), 54: (42, 10), 55: (42, 15),
    56: (40, 5), 57: (38, 15), 58: (38, 5), 59: (38, 10), 60: (35, 5),
    61: (50, 30), 62: (50, 35), 63: (50, 40), 64: (48, 30), 65: (44, 25),
    66: (47, 35), 67: (47, 40), 68: (42, 30), 69: (45, 35), 70: (95, 30),
    71: (95, 35), 72: (53, 30), 73: (92, 30), 74: (53, 35), 75: (45, 65),
    76: (90, 35), 77: (72, 45), 78: (78, 40), 79: (87, 30), 80: (85, 25),
    81: (85, 35), 82: (75, 55), 83: (72, 55), 84: (70, 58), 85: (86, 46),
    86: (66, 55), 87: (64, 46), 88: (65, 60), 89: (56, 64), 90: (60, 55),
    91: (60, 60), 92: (67, 85), 93: (42, 58), 94: (65, 82), 95: (62, 80),
    96: (62, 40), 97: (60, 85), 98: (58, 75), 99: (55, 80), 100: (55, 85),

    # Private charging stations
    1000: (49, 34),
    1001: (18, 66),
    1002: (67, 54),
    1003: (6, 42),
    1004: (39, 12),
    1005: (88, 34),

    # Public charging station added according to your update
    1006: (61, 83),

    # Public charging stations
    1007: (40, 65),
    1008: (25, 52),
    1009: (20, 80),
    1010: (58, 70),
    1011: (31, 33)
}


# =====================================================
# 3. Customer demands
# =====================================================
demand = {
    1: 10, 2: 30, 3: 10, 4: 10, 5: 10,
    6: 20, 7: 20, 8: 20, 9: 10, 10: 10,
    11: 10, 12: 20, 13: 30, 14: 10, 15: 40,
    16: 40, 17: 20, 18: 20, 19: 10, 20: 10,
    21: 20, 22: 20, 23: 10, 24: 10, 25: 40,
    26: 10, 27: 10, 28: 20, 29: 10, 30: 10,
    31: 20, 32: 30, 33: 40, 34: 20, 35: 10,
    36: 10, 37: 20, 38: 30, 39: 20, 40: 10,
    41: 10, 42: 20, 43: 10, 44: 10, 45: 10,
    46: 30, 47: 10, 48: 10, 49: 10, 50: 10,
    51: 10, 52: 10, 53: 20, 54: 40, 55: 10,
    56: 30, 57: 40, 58: 30, 59: 10, 60: 20,
    61: 10, 62: 20, 63: 50, 64: 10, 65: 10,
    66: 10, 67: 10, 68: 10, 69: 10, 70: 30,
    71: 20, 72: 10, 73: 10, 74: 50, 75: 20,
    76: 10, 77: 10, 78: 20, 79: 10, 80: 10,
    81: 30, 82: 20, 83: 10, 84: 20, 85: 30,
    86: 10, 87: 20, 88: 30, 89: 10, 90: 10,
    91: 10, 92: 20, 93: 40, 94: 10, 95: 30,
    96: 10, 97: 30, 98: 20, 99: 10, 100: 20
}


# =====================================================
# 4. Charging station sets
# =====================================================
# If node 1006 is private in your manuscript, move it from public_charging_nodes to private_charging_nodes.
private_charging_nodes = {1000, 1001, 1002, 1003, 1004, 1005}
public_charging_nodes = {1006, 1007, 1008, 1009, 1010, 1011}
charging_nodes = private_charging_nodes | public_charging_nodes


# =====================================================
# 5. Model parameters
# =====================================================
params = {
    # Vehicle parameters
    "battery_capacity": 60.0,              # kWh
    "vehicle_max_load": 200.0,             # kg
    "vehicle_max_speed": 80.0,             # km/h
    "average_speed": 50.0,                 # km/h

    # Energy consumption parameters
    "base_energy_rate": 0.4,               # e0, kWh/km
    "alpha_load": 0.0005,                  # alpha, kWh/(km·kg)
    "beta_speed": 0.10,                    # beta, kWh/km
    "lambda_gradient": 0.08,               # lambda, kWh/km
    "mu_stop_go": 0.15,                    # mu, kWh/km
    "delta_temp_driving": 0.005,           # delta, kWh/(km·°C)

    # Refrigeration parameters
    "base_refrigeration_power": 2.0,       # P_k^0, kW
    "eta_temp_ref": 0.02,                  # eta_T
    "reference_temp": 25.0,                # T0, °C
    "unload_time_per_customer": 90 / 60,   # h

    # Charging parameters
    "charging_power": 60.0,                # kW
    "safety_margin": 2.0,                  # kWh

    # Cost parameters
    "fixed_cost_per_vehicle": 120.0,       # CNY/vehicle
    "distance_cost": 0.8,                  # CNY/km

    # Charging prices
    "private_electricity_price": 0.6,      # CNY/kWh
    "public_base_price": 0.6,              # CNY/kWh
    "public_service_fee": 0.3,             # CNY/kWh

    # Refrigeration electricity price
    "refrigeration_electricity_price": 0.6 # CNY/kWh
}


# =====================================================
# 6. Scenario settings
# =====================================================
scenarios = [
    {
        "Scenario": "Baseline",
        "road_gradient_deg": 0.0,
        "stop_go_coefficient": 0.0,
        "ambient_temp": 25.0
    },
    {
        "Scenario": "Mild condition",
        "road_gradient_deg": 2.0,
        "stop_go_coefficient": 0.1,
        "ambient_temp": 30.0
    },
    {
        "Scenario": "Moderate condition",
        "road_gradient_deg": 4.0,
        "stop_go_coefficient": 0.2,
        "ambient_temp": 35.0
    },
    {
        "Scenario": "Severe condition",
        "road_gradient_deg": 6.0,
        "stop_go_coefficient": 0.3,
        "ambient_temp": 40.0
    }
]


# =====================================================
# 7. Calculation functions
# =====================================================
def euclidean_distance(i, j, coords):
    """Calculate Euclidean distance between two nodes."""
    if i not in coords or j not in coords:
        raise KeyError(f"Missing coordinate for node {i} or node {j}.")
    xi, yi = coords[i]
    xj, yj = coords[j]
    return math.sqrt((xi - xj) ** 2 + (yi - yj) ** 2)


def calculate_route_initial_load(route, demand):
    """Calculate initial load of a route. Repeated customers are counted only once."""
    customer_nodes = set(node for node in route if node in demand)
    return sum(demand[node] for node in customer_nodes)


def driving_energy_per_arc(distance, load, scenario, params):
    """
    Extended driving energy consumption function:
    E_ijk^drv = d_ij [e0 + alpha*q_ik + beta*(v_ij/vmax)^2
                      + lambda*sin(theta_ij) + mu*S_ij + delta*|T-T0|]
    """
    e0 = params["base_energy_rate"]
    alpha = params["alpha_load"]
    beta = params["beta_speed"]
    lamb = params["lambda_gradient"]
    mu = params["mu_stop_go"]
    delta = params["delta_temp_driving"]

    v = params["average_speed"]
    vmax = params["vehicle_max_speed"]

    theta = math.radians(scenario["road_gradient_deg"])
    S = scenario["stop_go_coefficient"]
    T = scenario["ambient_temp"]
    T0 = params["reference_temp"]

    unit_energy = (
        e0
        + alpha * load
        + beta * (v / vmax) ** 2
        + lamb * max(0.0, math.sin(theta))
        + mu * S
        + delta * abs(T - T0)
    )

    return distance * unit_energy


def refrigeration_power(scenario, params):
    """
    Temperature-dependent refrigeration power:
    P_k^ref(T) = P_k^0 [1 + eta_T * max(0, T - T0)]
    """
    P0 = params["base_refrigeration_power"]
    eta = params["eta_temp_ref"]
    T = scenario["ambient_temp"]
    T0 = params["reference_temp"]

    return P0 * (1 + eta * max(0.0, T - T0))


def get_charging_price(node, params):
    """Return charging price according to charging station type."""
    if node in private_charging_nodes:
        return params["private_electricity_price"]
    if node in public_charging_nodes:
        return params["public_base_price"] + params["public_service_fee"]
    return 0.0


def estimate_energy_to_next_charge_or_depot(route, start_idx, current_load, scenario, params):
    """
    Estimate required driving energy from the current charging station
    to the next charging station or depot along the fixed route.
    This is used for approximate partial charging.
    """
    temp_load = current_load
    required_energy = 0.0
    temp_served = set()

    for idx in range(start_idx, len(route) - 1):
        i = route[idx]
        j = route[idx + 1]

        if i in demand and i not in temp_served:
            temp_load -= demand[i]
            temp_served.add(i)

        dist = euclidean_distance(i, j, coords)
        required_energy += driving_energy_per_arc(dist, temp_load, scenario, params)

        if j in charging_nodes or j == 0:
            break

    return required_energy


def evaluate_route(route, coords, demand, charging_nodes, scenario, params):
    """Evaluate one route under a given scenario."""
    if len(route) <= 2:
        return None

    battery_capacity = params["battery_capacity"]
    battery = battery_capacity
    safety_margin = params["safety_margin"]

    total_distance = 0.0
    driving_energy = 0.0
    charging_energy = 0.0
    charging_cost = 0.0
    charging_frequency = 0
    charging_time = 0.0
    travel_time = 0.0
    infeasible = False

    current_load = calculate_route_initial_load(route, demand)
    served_customers = set()

    for idx in range(len(route) - 1):
        i = route[idx]
        j = route[idx + 1]

        # Load decreases after serving customer i.
        if i in demand and i not in served_customers:
            current_load -= demand[i]
            served_customers.add(i)

        distance = euclidean_distance(i, j, coords)
        total_distance += distance

        arc_energy = driving_energy_per_arc(distance, current_load, scenario, params)
        driving_energy += arc_energy
        travel_time += distance / params["average_speed"]

        battery -= arc_energy

        if battery < -1e-6:
            infeasible = True

        # Approximate partial charging at charging stations.
        if j in charging_nodes:
            required_energy = estimate_energy_to_next_charge_or_depot(
                route=route,
                start_idx=idx + 1,
                current_load=current_load,
                scenario=scenario,
                params=params
            )

            target_battery = min(battery_capacity, required_energy + safety_margin)
            charge_amount = max(0.0, target_battery - max(0.0, battery))

            if charge_amount > 1e-6:
                unit_price = get_charging_price(j, params)
                charging_energy += charge_amount
                charging_cost += charge_amount * unit_price
                charging_frequency += 1
                charging_time += charge_amount / params["charging_power"]
                battery = min(battery_capacity, max(0.0, battery) + charge_amount)

    customer_count = len(set(node for node in route if node in demand))
    unload_time = customer_count * params["unload_time_per_customer"]

    P_ref = refrigeration_power(scenario, params)
    refrigeration_energy = P_ref * (travel_time + unload_time + charging_time)
    refrigeration_cost = refrigeration_energy * params["refrigeration_electricity_price"]

    fixed_cost = params["fixed_cost_per_vehicle"]
    travel_cost = total_distance * params["distance_cost"]

    # This is not the complete objective value in the manuscript.
    # It excludes cargo-loss cost and time-window penalty cost.
    comparative_operating_cost = fixed_cost + travel_cost + charging_cost + refrigeration_cost

    return {
        "distance": total_distance,
        "driving_energy": driving_energy,
        "refrigeration_energy": refrigeration_energy,
        "charging_energy": charging_energy,
        "charging_frequency": charging_frequency,
        "travel_time": travel_time,
        "unload_time": unload_time,
        "charging_time": charging_time,
        "fixed_cost": fixed_cost,
        "travel_cost": travel_cost,
        "charging_cost": charging_cost,
        "refrigeration_cost": refrigeration_cost,
        "comparative_operating_cost": comparative_operating_cost,
        "infeasible": infeasible
    }


def evaluate_scenario(routes, coords, demand, charging_nodes, scenario, params):
    """Evaluate all routes under one scenario."""
    total_distance = 0.0
    total_driving_energy = 0.0
    total_refrigeration_energy = 0.0
    total_charging_energy = 0.0
    total_charging_frequency = 0

    total_fixed_cost = 0.0
    total_travel_cost = 0.0
    total_charging_cost = 0.0
    total_refrigeration_cost = 0.0
    total_comparative_operating_cost = 0.0

    infeasible_routes = 0
    used_vehicles = 0

    for route in routes:
        result = evaluate_route(route, coords, demand, charging_nodes, scenario, params)
        if result is None:
            continue

        used_vehicles += 1
        total_distance += result["distance"]
        total_driving_energy += result["driving_energy"]
        total_refrigeration_energy += result["refrigeration_energy"]
        total_charging_energy += result["charging_energy"]
        total_charging_frequency += result["charging_frequency"]

        total_fixed_cost += result["fixed_cost"]
        total_travel_cost += result["travel_cost"]
        total_charging_cost += result["charging_cost"]
        total_refrigeration_cost += result["refrigeration_cost"]
        total_comparative_operating_cost += result["comparative_operating_cost"]

        if result["infeasible"]:
            infeasible_routes += 1

    return {
        "Scenario": scenario["Scenario"],
        "Road gradient": scenario["road_gradient_deg"],
        "Stop-and-go coefficient": scenario["stop_go_coefficient"],
        "Ambient temperature": scenario["ambient_temp"],
        "Total distance": total_distance,
        "Driving energy consumption": total_driving_energy,
        "Refrigeration energy consumption": total_refrigeration_energy,
        "Charging energy": total_charging_energy,
        "Charging frequency": total_charging_frequency,
        "Number of vehicles": used_vehicles,
        "Infeasible routes": infeasible_routes,
        "Fixed cost": total_fixed_cost,
        "Travel cost": total_travel_cost,
        "Charging cost": total_charging_cost,
        "Refrigeration cost": total_refrigeration_cost,
        "Comparative operating cost": total_comparative_operating_cost
    }


# =====================================================
# 8. Run sensitivity analysis
# =====================================================
print("Number of routes:", len(routes))
print("Number of coordinates:", len(coords))
print("Number of demand nodes:", len(demand))
print("Number of charging nodes:", len(charging_nodes))

results = []

for scenario in scenarios:
    scenario_result = evaluate_scenario(
        routes=routes,
        coords=coords,
        demand=demand,
        charging_nodes=charging_nodes,
        scenario=scenario,
        params=params
    )
    results.append(scenario_result)

df_results = pd.DataFrame(results)

df_results_rounded = df_results.copy()
numeric_cols = df_results_rounded.select_dtypes(include=["float", "int"]).columns
df_results_rounded[numeric_cols] = df_results_rounded[numeric_cols].round(4)

print("\nSensitivity analysis results:")
print(df_results_rounded.to_string(index=False))


# =====================================================
# 9. Save results
# =====================================================
csv_name = "sensitivity_analysis_road_temp_traffic_corrected.csv"
df_results_rounded.to_csv(csv_name, index=False, encoding="utf-8-sig")
print(f"\nCSV file saved as: {csv_name}")

excel_name = "sensitivity_analysis_road_temp_traffic_corrected.xlsx"
try:
    df_results_rounded.to_excel(excel_name, index=False)
    print(f"Excel file saved as: {excel_name}")
except Exception as e:
    print("\nExcel file was not saved.")
    print("Reason:", e)
    print("You can install openpyxl by running:")
    print('pip install openpyxl -i https://pypi.tuna.tsinghua.edu.cn/simple')


# =====================================================
# 10. Draw figures
# =====================================================
def plot_metric(df, metric, ylabel):
    plt.figure(figsize=(8, 5))
    plt.plot(df["Scenario"], df[metric], marker="o")
    plt.xlabel("Scenario")
    plt.ylabel(ylabel)
    plt.title(ylabel + " under Different Scenarios")
    plt.xticks(rotation=20)
    plt.tight_layout()
    plt.show()


plot_metric(df_results_rounded, "Comparative operating cost", "Comparative operating cost")
plot_metric(df_results_rounded, "Driving energy consumption", "Driving energy consumption")
plot_metric(df_results_rounded, "Refrigeration energy consumption", "Refrigeration energy consumption")
plot_metric(df_results_rounded, "Charging frequency", "Charging frequency")