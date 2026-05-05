# EVRP-IGWO

This repository provides the experimental code and modified Solomon benchmark instances used in the manuscript:

**Route Optimization for Electric Vehicle Cold Chain Delivery under a Mixed Public–Private Charging Mode**

## Overview

This study addresses the electric refrigerated vehicle routing problem under a mixed public–private charging mode. The model considers vehicle load capacity, battery capacity, customer time windows, refrigeration energy consumption, cargo damage cost, charging station heterogeneity, SOC-dependent nonlinear charging, charging station queuing, and link-based time-dependent travel time.

An Improved Grey Wolf Optimizer (IGWO) is developed to solve the proposed optimization model. The algorithm improves the standard GWO through high-quality individual selection, a destroy–repair operator, and an adaptive position update strategy.

## Dataset

The experiments are based on modified Solomon benchmark instances, including:

- C201–C208
- RC201–RC208

The original Solomon customer and depot data are retained, while additional public and private charging station nodes are added to adapt the benchmark instances to the electric vehicle cold-chain delivery scenario.

## Main Features

- Electric vehicle cold-chain routing
- Mixed public–private charging stations
- SOC-dependent nonlinear charging model
- Charging station queuing mechanism
- Link-based time-dependent travel time
- Refrigeration energy consumption
- Cargo damage cost
- Customer time-window constraints
- Improved Grey Wolf Optimizer

## Repository Structure

```text
EVRP-IGWO/
├── data/                  # Modified Solomon benchmark instances
├── src/                   # Source code
├── ALNS.py                # ALNS-related experimental script
├── benchmark_algorithms.py
├── generate_modeling_docs.py
├── lingmindu.py
├── plot_benchmark.py
├── plot_charging_count.py
├── plot_sensitivity.py
├── plot_strategy.py
├── route_visualizer.py
├── run_sensitivity.py
└── run_strategy_analysis.py
