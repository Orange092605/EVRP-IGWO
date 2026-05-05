import os
import re
import random
import numpy as np
from sklearn.cluster import KMeans
from src.config import Config
from src.models import Node


def ensure_csv_exists(filename):
    file_path = os.path.join(Config.DATA_DIR, filename)
    if not os.path.exists(file_path):
        print(f"[Info] File {filename} not found in {Config.DATA_DIR}. Generating mock data...")
        with open(file_path, "w") as f:
            f.write("CUST NO. XCOORD. YCOORD. DEMAND READY TIME DUE DATE SERVICE TIME\n")
            f.write("0 50 50 0 0 1200 0\n")
            for i in range(1, 51):
                if i <= 20:
                    cx, cy = 20, 20
                elif i <= 40:
                    cx, cy = 80, 80
                else:
                    cx, cy = 20, 80
                x = int(cx + random.uniform(-15, 15))
                y = int(cy + random.uniform(-15, 15))
                demand = random.randint(5, 15)
                ready = random.randint(0, 120)
                due = ready + random.randint(120, 300)
                service = 30
                f.write(f"{i} {x} {y} {demand} {ready} {due} {service}\n")


def load_data(filename):
    file_path = os.path.join(Config.DATA_DIR, filename)
    customers = []
    depot = None

    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return None, []

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        parts = re.split(r'[ ,;]+', line.strip())
        parts = [p for p in parts if p]
        if not parts or not parts[0].isdigit(): continue

        nid = int(parts[0])
        x, y, dem, ready, due, serv = map(float, parts[1:7])

        if nid == 0:
            depot = Node(nid, x, y, dem, ready, due, serv, 'depot', Config.PRICE_BASIC)
        else:
            customers.append(Node(nid, x, y, dem, ready, due, serv, 'customer'))

    return depot, customers


def generate_stations_kmeans(customers, depot):
    all_stations = [depot]
    coords = np.array([[c.x, c.y] for c in customers])
    total_new = Config.NUM_PRIVATE_STATIONS + Config.NUM_PUBLIC_STATIONS

    if len(customers) < total_new:
        return all_stations

    kmeans = KMeans(n_clusters=total_new, random_state=42, n_init=10).fit(coords)
    centers = kmeans.cluster_centers_

    for i, center in enumerate(centers):
        s_id = 1000 + i
        if i < Config.NUM_PRIVATE_STATIONS:
            s_type = 'station_private'
            price = Config.PRICE_BASIC
        else:
            s_type = 'station_public'
            price = Config.PRICE_PUBLIC

        if Config.STATION_MODE == 'mixed' or \
                (Config.STATION_MODE == 'private_only' and 'private' in s_type) or \
                (Config.STATION_MODE == 'public_only' and 'public' in s_type):
            station = Node(s_id, center[0], center[1], 0, 0, 1440, 0, s_type, price)
            all_stations.append(station)

    return all_stations