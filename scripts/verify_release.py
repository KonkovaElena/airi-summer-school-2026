#!/usr/bin/env python3
"""Release gate: validate analysis JSON and check frozen headline metrics."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "artifacts/non_oracle_defer_results_2026_05_full_analysis.json"

# Tolerances for float comparison (percentage points, as fractions)
EXPECTED = {
    "model_only": {"mean_accuracy": 0.7187, "mean_review_rate": 0.0},
    "naive_threshold": {"mean_accuracy": 0.8105, "mean_review_rate": 0.3492},
    "calibrated_defer": {"mean_accuracy": 0.8129, "mean_review_rate": 0.3396},
    "always_review": {"mean_accuracy": 0.8752, "mean_review_rate": 1.0},
}
CAL_VS_NAIVE_DIFF = 0.0024
TOL = 0.0005


def main() -> int:
    if not ANALYSIS.exists():
        print("ERROR: missing", ANALYSIS)
        return 2

    from validate_analysis import validate

    if validate(str(ANALYSIS), strict_provenance=True) != 0:
        return 3

    data = json.loads(ANALYSIS.read_text(encoding="utf-8"))
    if data.get("protocol_version") not in ("1.1", 1.1):
        print("ERROR: unexpected protocol_version", data.get("protocol_version"))
        return 4

    metrics = data["metrics"]
    for policy, exp in EXPECTED.items():
        if policy not in metrics:
            print("ERROR: missing policy", policy)
            return 5
        for key, target in exp.items():
            got = metrics[policy][key]
            if abs(got - target) > TOL:
                print(f"ERROR: {policy}.{key}={got:.6f} expected ~{target:.4f}")
                return 6

    comp = next(
        (c for c in data["comparisons"] if c["a"] == "calibrated_defer" and c["b"] == "naive_threshold"),
        None,
    )
    if not comp or abs(comp["mean_diff"] - CAL_VS_NAIVE_DIFF) > TOL:
        print("ERROR: calibrated vs naive mean_diff", comp)
        return 7

    print("VERIFY_RELEASE_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
