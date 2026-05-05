import random
import math
import numpy as np
from src.config import Config
from src.physics import split_chrom_to_routes


# ==========================================
# 遗传算法 (Genetic Algorithm)
# ==========================================
def run_ga(depot, customers, stations):
    # 初始化
    population = []
    for _ in range(Config.POP_SIZE):
        ind = customers[:]
        random.shuffle(ind)
        population.append(ind)

    best_fitness = float('inf')
    best_paths = []
    history = []

    print(f"开始 GA 优化... (代数: {Config.GENERATIONS})")

    for gen in range(Config.GENERATIONS):
        # 评估
        scored_pop = []
        for ind in population:
            cost, paths = split_chrom_to_routes(ind, depot, stations)
            scored_pop.append((cost, ind))

            if cost < best_fitness:
                best_fitness = cost
                best_paths = paths

        history.append(best_fitness)
        if gen % 10 == 0:
            print(f"Gen {gen}: Best Cost = {best_fitness:.2f}")

        # 选择 (保留前 20%)
        scored_pop.sort(key=lambda x: x[0])
        elite_size = int(Config.POP_SIZE * 0.2)
        next_gen = [x[1] for x in scored_pop[:elite_size]]

        # 交叉变异补齐
        while len(next_gen) < Config.POP_SIZE:
            parent = random.choice(next_gen[:elite_size])[:]
            # 变异 Swap
            if random.random() < Config.MUTATION_RATE:
                i1, i2 = random.sample(range(len(parent)), 2)
                parent[i1], parent[i2] = parent[i2], parent[i1]
            next_gen.append(parent)

        population = next_gen

    return best_fitness, best_paths, history





def run_dssa_optimizer(depot, customers, stations):
    # --- 参数设置 ---
    pop_size = Config.POP_SIZE  # 种群数量
    max_iter = Config.GENERATIONS # 迭代次数

    # 麻雀比例设置
    p_producer = 0.2    # 20% 是发现者
    p_danger = 0.2      # 20% 是侦察者 (意识到危险)

    # 阈值 (ST): 如果 < ST，说明环境安全，发现者广泛搜索
    ST = 0.8

    print(f"🐦 启动离散麻雀搜索算法 (DSSA)...")
    print(f"   - 发现者比例: {p_producer}")
    print(f"   - 侦察者(危险感知): {p_danger}")

    # --- 辅助算子 (用于模拟麻雀移动) ---

    # 算子1: 随机交换 (模拟广泛搜索)
    def op_swap(route):
        new_r = route[:]
        i, j = random.sample(range(len(new_r)), 2)
        new_r[i], new_r[j] = new_r[j], new_r[i]
        return new_r

    # 算子2: 2-Opt (模拟深度开发/跟随)
    def op_2opt(route):
        new_r = route[:]
        # 随机选一段反转，模拟局部优化
        n = len(new_r)
        if n < 2: return new_r
        i, j = sorted(random.sample(range(n), 2))
        new_r[i:j+1] = new_r[i:j+1][::-1]
        return new_r

    # 算子3: 贪婪交叉 (模拟跟随最优解)
    def op_crossover(my_route, best_route):
        # 简单实现: 保持自己的一部分，剩下的按 best_route 的顺序填入
        # 这种操作能让麻雀迅速向最优解靠拢
        size = len(my_route)
        start, end = sorted(random.sample(range(size), 2))
        child = [None] * size
        # 遗传自己的一段
        child[start:end] = my_route[start:end]

        # 剩下的空位，按 best_route 的顺序填入
        ptr = 0
        for gene in best_route:
            if gene not in child:
                while ptr < size and child[ptr] is not None:
                    ptr += 1
                if ptr < size:
                    child[ptr] = gene
        return child

    # --- 1. 初始化种群 ---
    print("   -> 初始化狼种群...")
    population = []
    fitness_list = []

    for _ in range(pop_size):
        ind = customers[:]
        random.shuffle(ind)
        cost, _ = split_chrom_to_routes(ind, depot, stations)
        population.append(ind)
        fitness_list.append(cost)

    # 记录全局最优
    best_idx = np.argmin(fitness_list)
    global_best_cost = fitness_list[best_idx]
    global_best_path = population[best_idx][:] # 只存序列
    final_best_routes = [] # 存解码后的 routes

    # 预计算一次最优解的 routes
    _, final_best_routes = split_chrom_to_routes(global_best_path, depot, stations)

    history = []

    # --- 2. 主循环 ---
    for t in range(max_iter):

        # 根据适应度排序，区分发现者和加入者
        # sort_indices[0] 是最优麻雀，sort_indices[-1] 是最差麻雀
        sort_indices = np.argsort(fitness_list)
        worst_idx = sort_indices[-1]
        best_current_idx = sort_indices[0]

        current_best_pos = population[best_current_idx]

        # 每一只麻雀更新位置
        for i in range(pop_size):
            current_sparrow = population[i]
            new_sparrow = current_sparrow[:]

            # --- 阶段 A: 发现者 (Producer) 更新 ---
            # 排名靠前的麻雀是发现者
            if i in sort_indices[:int(pop_size * p_producer)]:
                r2 = random.random()
                if r2 < ST:
                    # 环境安全 -> 广泛搜索 (多做几次变异/交换)
                    # 模拟公式: X = X * exp(...)
                    new_sparrow = op_swap(new_sparrow)
                    if random.random() < 0.5: new_sparrow = op_2opt(new_sparrow)
                else:
                    # 发现捕食者 -> 迅速移动 (大步跳跃)
                    # 模拟公式: X = X + Q * L
                    new_sparrow = op_swap(new_sparrow)
                    new_sparrow = op_swap(new_sparrow) # 剧烈变动

            # --- 阶段 B: 加入者 (Scrounger) 更新 ---
            else:
                # 剩下的麻雀
                if i == worst_idx: # 最差的那只
                    # 饿得不行了，跳到最优解附近吃剩饭
                    # 模拟公式: X = X_best + ...
                    new_sparrow = op_crossover(current_sparrow, current_best_pos)
                    # 并做一次局部搜索优化
                    new_sparrow = op_2opt(new_sparrow)
                else:
                    # 普通加入者，跟随最优者
                    # 模拟公式: |X - X_best| ...
                    # 一半概率自己找，一半概率跟大哥
                    if random.random() < 0.5:
                        new_sparrow = op_2opt(current_sparrow)
                    else:
                        new_sparrow = op_crossover(current_sparrow, current_best_pos)

            # --- 阶段 C: 侦察者 (Vigilante) 随机更新 ---
            # 随机选取一部分麻雀作为侦察者 (可能来自发现者，也可能来自加入者)
            if random.random() < p_danger:
                # 意识到危险
                if fitness_list[i] != global_best_cost:
                    # 不是最优麻雀 -> 逃向最优位置
                    new_sparrow = op_crossover(new_sparrow, global_best_path)
                else:
                    # 自己就是最优麻雀 -> 只能随机逃窜到附近 (局部抖动)
                    # 模拟公式: X + K * ...
                    new_sparrow = op_swap(new_sparrow)

            # --- 贪婪选择 ---
            # 只有新位置更好时才移动
            new_cost, new_routes = split_chrom_to_routes(new_sparrow, depot, stations)
            if new_cost < fitness_list[i]:
                population[i] = new_sparrow
                fitness_list[i] = new_cost

                # 更新全局最优
                if new_cost < global_best_cost:
                    global_best_cost = new_cost
                    global_best_path = new_sparrow[:]
                    final_best_routes = new_routes

        history.append(global_best_cost)
        if t % 10 == 0:
            print(f"Iter {t}: Best Cost = {global_best_cost:.2f}")

    return global_best_cost, final_best_routes, history



def run_stable_idssa(depot, customers, stations):
    # --- 参数 ---
    pop_size = Config.POP_SIZE
    max_iter = Config.GENERATIONS

    p_producer = 0.2    # 20% 发现者
    p_danger = 0.2      # 20% 警戒者
    ST = 0.7            # 安全阈值

    # [修改点1] 退火参数调整：降温更快
    T = 100.0           # 初始温度降低
    alpha = 0.90        # 降温系数加快

    print(f"🦅 启动稳健型 IDSSA (限制了破坏力)...")

    # --- 算子 (保持不变) ---
    def op_swap(route):
        new_r = route[:]
        if len(new_r) < 2: return new_r
        i, j = random.sample(range(len(new_r)), 2)
        new_r[i], new_r[j] = new_r[j], new_r[i]
        return new_r

    def op_2opt(route):
        new_r = route[:]
        n = len(new_r)
        if n < 3: return new_r
        i, j = sorted(random.sample(range(n), 2))
        new_r[i:j+1] = new_r[i:j+1][::-1]
        return new_r

    def op_insert(route):
        new_r = route[:]
        if len(new_r) < 2: return new_r
        val = new_r.pop(random.randint(0, len(new_r)-1))
        new_r.insert(random.randint(0, len(new_r)), val)
        return new_r

    def op_crossover(my_route, best_route):
        size = len(my_route)
        start, end = sorted(random.sample(range(size), 2))
        child = [None] * size
        child[start:end] = my_route[start:end]
        ptr = 0
        for gene in best_route:
            if gene not in child:
                while ptr < size and child[ptr] is not None: ptr += 1
                if ptr < size: child[ptr] = gene
        return child

    # [修改点2] 温和的 Levy 飞行
    def gentle_levy_walk(route):
        new_route = route[:]
        # 只做 1 到 2 次微调，不再做 3-6 次大跳
        steps = 1 if random.random() < 0.8 else 2
        for _ in range(steps):
            # 优先用 2-opt (VRP里最稳的算子)
            if random.random() < 0.6:
                new_route = op_2opt(new_route)
            else:
                new_route = op_swap(new_route)
        return new_route

    # --- 初始化 ---
    population = []
    fitness_list = []

    # 贪婪生成
    temp_pop = []
    for _ in range(pop_size * 2):
        ind = customers[:]
        random.shuffle(ind)
        c, _ = split_chrom_to_routes(ind, depot, stations)
        temp_pop.append((c, ind))
    temp_pop.sort(key=lambda x: x[0])

    for i in range(pop_size):
        fitness_list.append(temp_pop[i][0])
        population.append(temp_pop[i][1])

    global_best_cost = fitness_list[0]
    global_best_path = population[0][:]
    final_routes = []
    history = []

    # --- 主循环 ---
    for t in range(max_iter):

        sort_indices = np.argsort(fitness_list)
        best_current_idx = sort_indices[0]
        worst_idx = sort_indices[-1]
        current_best_pos = population[best_current_idx][:]

        # [修改点3] 精英保留：这一代最好的那只麻雀，直接复制到下一代，不许动
        # 这保证了最优解只会变好，绝不会变差
        new_population = [None] * pop_size
        new_fitness = [None] * pop_size

        # 强制保留第一名
        new_population[0] = population[best_current_idx][:]
        new_fitness[0] = fitness_list[best_current_idx]

        # 从索引 1 开始更新其他人
        for i in range(1, pop_size):
            # 获取真实的麻雀索引（因为 sort_indices 是排序后的）
            # 这里为了简单，我们直接遍历原 population，除了已经被保留的 best

            idx = sort_indices[i] # 当前处理的麻雀在原列表的索引
            current_sparrow = population[idx]
            new_sparrow = current_sparrow[:]

            # --- 角色更新 ---
            # 发现者
            if i < int(pop_size * p_producer):
                if random.random() < ST:
                    new_sparrow = gentle_levy_walk(current_sparrow)
                else:
                    new_sparrow = op_insert(current_sparrow)
            # 加入者
            else:
                if i == pop_size - 1: # 最差的
                    new_sparrow = op_crossover(current_sparrow, current_best_pos)
                    new_sparrow = op_2opt(new_sparrow)
                else:
                    new_sparrow = op_crossover(current_sparrow, current_best_pos)

            # 警戒者 (随机覆盖)
            if random.random() < p_danger:
                 new_sparrow = op_swap(new_sparrow)

            # --- 接受准则 ---
            cost, routes = split_chrom_to_routes(new_sparrow, depot, stations)
            delta = cost - fitness_list[idx]

            accepted = False
            if delta < 0:
                accepted = True
            else:
                # 模拟退火概率接受
                if random.random() < math.exp(-delta / T):
                    accepted = True

            if accepted:
                new_population[i] = new_sparrow
                new_fitness[i] = cost
                # 更新全局最优
                if cost < global_best_cost:
                    global_best_cost = cost
                    global_best_path = new_sparrow[:]
                    final_routes = routes
            else:
                # 不接受，保留上一代
                new_population[i] = current_sparrow
                new_fitness[i] = fitness_list[idx]

        # 更新种群
        population = new_population
        fitness_list = new_fitness

        # 降温
        T = max(0.1, T * alpha)

        history.append(global_best_cost)
        if t % 10 == 0:
            print(f"Iter {t}: Best Cost = {global_best_cost:.2f}")

    return global_best_cost, final_routes, history


def run_gwo():
    return None


def run_igwo():
    return None