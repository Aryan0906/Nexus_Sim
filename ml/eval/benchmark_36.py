"""Phase 36 - Complete 48-Algorithm Evaluation & Benchmark Suite.

Generates the 48-algorithm inventory matrix (12 each across CV, Soft
Computing, NLP, and RL) from the canonical catalog in
sidecars/algo_explorer_service.py, outputting ml/results/36_algo_matrix.json.

Note: the file name is kept for backward compatibility with the dashboard
fetch path; the catalog contains 48 algorithms.
"""

from __future__ import annotations

import json
import os
import sys
import time

ML_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ML_DIR not in sys.path:
    sys.path.insert(0, ML_DIR)

from sidecars.algo_explorer_service import ALGORITHM_CATALOG


def generate_benchmark_matrix() -> dict:
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    summary = {
        "generated_at": timestamp,
        "total_algorithms": len(ALGORITHM_CATALOG),
        "subjects": {
            "Computer Vision": [a for a in ALGORITHM_CATALOG if a["category"] == "CV"],
            "Soft Computing": [a for a in ALGORITHM_CATALOG if a["category"] == "SC"],
            "Natural Language Processing": [a for a in ALGORITHM_CATALOG if a["category"] == "NLP"],
            "Reinforcement Learning": [a for a in ALGORITHM_CATALOG if a["category"] == "RL"],
        },
        # Honest status: per-algorithm latency/accuracy/metric fields in the
        # catalog are design targets unless explicitly labelled "(measured)".
        # Verified measurements come from the engine benchmark binaries.
        "performance_summary": {
            "fastest_subsystem": "C++ ONNX policy inference, 0.04-0.13 ms p95 (engine bench_inference, measured range)",
            "most_accurate_cv": "Not independently measured; CV detectors are classical/surrogate (no real YOLO/U-Net/Mask R-CNN weights in repo)",
            "best_calibration_optimizer": "Not measured; MAPE figures in the catalog are design targets",
            "highest_rl_throughput": "Not measured; reward-gain figures in the catalog are training-log claims",
        },
        "metrics_provenance": (
            "Per-algorithm latency_ms/accuracy/metric values are catalog "
            "design targets unless suffixed '(measured)'. Verified numbers: "
            "engine bench_inference (ONNX policy), bench_quadtree/spatial "
            "(index speedup), and the engine --profile phase breakdown."
        ),
    }

    out_file = os.path.join(ML_DIR, "results", "36_algo_matrix.json")
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w") as f:
        json.dump(summary, f, indent=2)

    # Copy to dashboard public
    dash_file = os.path.join(ML_DIR, "..", "dashboard", "public", "data", "36_algo_matrix.json")
    os.makedirs(os.path.dirname(dash_file), exist_ok=True)
    with open(dash_file, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"48-Algorithm Master Matrix written to {out_file} and synced to dashboard/public.")
    return summary


if __name__ == "__main__":
    generate_benchmark_matrix()
