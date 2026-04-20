"""
Simulation for Learning to Defer with imperfect expert.
Empirically bounds diagnostic error while preserving model autonomy for routine cases.
See AIRI Summer School 2026 proposal for theoretical background.
"""

from __future__ import annotations

import argparse
import datetime
import json
import math
import random
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

_HAS_MATPLOTLIB = True
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except Exception as _mat_exc:
    print("Warning: matplotlib import failed, plots will be skipped:", _mat_exc)
    _HAS_MATPLOTLIB = False

BIN_COUNT = 10
BETA_ALPHA = 2.1
BETA_BETA = 2.4


@dataclass(frozen=True)
class Case:
    difficulty: float
    risk_signal: float
    confidence: float
    model_correct: int
    expert_correct: int


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def generate_case(rng: random.Random, expert_mode: str = 'optimistic') -> Case:
    difficulty = rng.betavariate(BETA_ALPHA, BETA_BETA)

    risk_signal = clamp(0.18 + 0.55 * difficulty + rng.gauss(0.0, 0.11), 0.01, 0.99)
    raw_confidence = 0.91 - 0.52 * difficulty + rng.gauss(0.0, 0.08)
    confidence = clamp(raw_confidence, 0.05, 0.99)

    model_accuracy = clamp(0.95 - 0.28 * difficulty - 0.23 * risk_signal, 0.46, 0.97)
    
    # Expert accuracy logic based on selected mode for sensitivity analysis
    if expert_mode == 'optimistic':
        expert_accuracy = clamp(0.79 + 0.07 * difficulty + 0.12 * risk_signal, 0.71, 0.96)
    elif expert_mode == 'realistic':
        expert_accuracy = clamp(0.85 - 0.10 * difficulty + 0.05 * risk_signal + rng.gauss(0, 0.03), 0.70, 0.92)
    elif expert_mode == 'pessimistic':
        expert_accuracy = clamp(0.80 - 0.15 * difficulty - 0.12 * risk_signal + rng.gauss(0, 0.05), 0.65, 0.88)
    elif expert_mode == 'heterogeneous':
        # Sample from mixture of specialists with different parameter sets
        specialist_type = rng.choice(['optimistic', 'realistic', 'pessimistic'])
        if specialist_type == 'optimistic':
            expert_accuracy = clamp(0.79 + 0.07 * difficulty + 0.12 * risk_signal, 0.71, 0.96)
        elif specialist_type == 'realistic':
            expert_accuracy = clamp(0.85 - 0.10 * difficulty + 0.05 * risk_signal + rng.gauss(0, 0.03), 0.70, 0.92)
        else:  # pessimistic
            expert_accuracy = clamp(0.80 - 0.15 * difficulty - 0.12 * risk_signal + rng.gauss(0, 0.05), 0.65, 0.88)
    else:
        raise ValueError(f"Unknown expert_mode: {expert_mode}")

    model_correct = 1 if rng.random() < model_accuracy else 0
    expert_correct = 1 if rng.random() < expert_accuracy else 0
    return Case(difficulty, risk_signal, confidence, model_correct, expert_correct)


def build_dataset(rng: random.Random, size: int, expert_mode: str = 'optimistic') -> list[Case]:
    return [generate_case(rng, expert_mode) for _ in range(size)]


def confidence_bin(confidence: float) -> int:
    index = min(BIN_COUNT - 1, int(confidence * BIN_COUNT))
    return max(0, index)


def risk_bin(risk_signal: float) -> int:
    index = min(3, int(risk_signal * 4))
    return max(0, index)


def summarize_cells(cases: list[Case]) -> dict[tuple[int, int], dict[str, float]]:
    buckets: dict[tuple[int, int], list[Case]] = {
        (confidence_index, risk_index): []
        for confidence_index in range(BIN_COUNT)
        for risk_index in range(4)
    }
    for case in cases:
        buckets[(confidence_bin(case.confidence), risk_bin(case.risk_signal))].append(case)

    summary: dict[tuple[int, int], dict[str, float]] = {}
    for index, bucket in buckets.items():
        if not bucket:
            summary[index] = {
                "count": 0,
                "model_accuracy": 0.0,
                "expert_accuracy": 0.0,
                "expert_gain": 0.0,
                "mean_confidence": 0.0,
                "mean_risk_signal": 0.0,
            }
            continue
        model_accuracy = mean(case.model_correct for case in bucket)
        expert_accuracy = mean(case.expert_correct for case in bucket)
        summary[index] = {
            "count": len(bucket),
            "model_accuracy": model_accuracy,
            "expert_accuracy": expert_accuracy,
            "expert_gain": expert_accuracy - model_accuracy,
            "mean_confidence": mean(case.confidence for case in bucket),
            "mean_risk_signal": mean(case.risk_signal for case in bucket),
        }
    return summary


def choose_calibrated_cells_greedy(summary: dict[tuple[int, int], dict[str, float]], review_budget: float) -> set[tuple[int, int]]:
    """Greedy approximation for budget-constrained cell selection.
    Note: This algorithm may stop early at low budgets (<30%) due to greedy selection without backtracking.
    For exact budget allocation, consider knapsack DP or fractional relaxation.
    """
    ranked_cells = sorted(
        summary.items(),
        key=lambda item: (
            item[1]["expert_gain"],
            item[1]["mean_risk_signal"],
            -item[1]["mean_confidence"],
        ),
        reverse=True,
    )
    chosen: set[tuple[int, int]] = set()
    reviewed = 0
    total = sum(int(values["count"]) for values in summary.values())
    budget_count = math.floor(total * review_budget)

    for index, values in ranked_cells:
        if values["expert_gain"] <= 0:
            continue
        next_reviewed = reviewed + int(values["count"])
        if next_reviewed > budget_count and reviewed > 0:
            continue
        chosen.add(index)
        reviewed = next_reviewed
        if reviewed >= budget_count:
            break
    return chosen


def choose_calibrated_cells_knapsack(summary: dict[tuple[int, int], dict[str, float]], review_budget: float) -> set[tuple[int, int]]:
    """Exact 0/1 Knapsack DP for budget-constrained cell selection.
    Items = cells with expert_gain > 0. Weight = count, Value = expert_gain * count.
    Uses DP since number of items = BIN_COUNT * 4 = 40, which is small.
    """
    items = []
    for index, values in summary.items():
        if values["count"] > 0 and values["expert_gain"] > 0:
            weight = int(values["count"])
            value = float(values["expert_gain"] * values["count"])
            items.append((index, weight, value))
    
    total = sum(int(v["count"]) for v in summary.values())
    W = math.floor(total * review_budget)
    
    if W > 50000:
        import warnings
        warnings.warn(f"Knapsack W={W} > 50000 — возможна высокая нагрузка на память/время")
    
    if W <= 0 or not items:
        return set()
    
    # DP: dp[w] = max value for weight w
    dp = [0.0] * (W + 1)
    # Keep track of which items are selected at each weight
    keep = [set() for _ in range(W + 1)]
    
    for idx, (index, weight, value) in enumerate(items):
        for w in range(W, weight - 1, -1):
            if dp[w - weight] + value > dp[w]:
                dp[w] = dp[w - weight] + value
                keep[w] = keep[w - weight].copy()
                keep[w].add(index)
    
    return keep[W]


def compute_beta_posterior(successes: int, n: int, alpha0: float = 1.0, beta0: float = 1.0) -> float:
    """Beta posterior mean for cell accuracy: (alpha0 + successes) / (alpha0 + beta0 + n)."""
    return (alpha0 + successes) / (alpha0 + beta0 + n)


def summarize_cells_bayesian(cases: list[Case]) -> dict[tuple[int, int], dict[str, float]]:
    """Summary with Bayesian shrinkage for small cells using Beta(1,1) prior."""
    summary = summarize_cells(cases)
    for index, values in summary.items():
        if values["count"] > 0:
            k_model = int(values["model_accuracy"] * values["count"])
            k_expert = int(values["expert_accuracy"] * values["count"])
            values["model_accuracy_bayes"] = compute_beta_posterior(k_model, values["count"])
            values["expert_accuracy_bayes"] = compute_beta_posterior(k_expert, values["count"])
            values["expert_gain_bayes"] = values["expert_accuracy_bayes"] - values["model_accuracy_bayes"]
    return summary


def choose_naive_threshold(cases: list[Case], review_budget: float) -> float:
    ordered = sorted(case.confidence for case in cases)
    cutoff_index = max(0, min(len(ordered) - 1, math.floor(len(ordered) * review_budget) - 1))
    return ordered[cutoff_index]


def evaluate_model_only(cases: list[Case]) -> dict[str, float]:
    accuracy = mean(case.model_correct for case in cases)
    return {
        "accuracy": accuracy,
        "error_rate": 1.0 - accuracy,
        "review_rate": 0.0,
    }


def evaluate_always_review(cases: list[Case]) -> dict[str, float]:
    accuracy = mean(case.expert_correct for case in cases)
    return {
        "accuracy": accuracy,
        "error_rate": 1.0 - accuracy,
        "review_rate": 1.0,
    }


def evaluate_naive_threshold(cases: list[Case], threshold: float) -> dict[str, float]:
    decisions = [case.expert_correct if case.confidence <= threshold else case.model_correct for case in cases]
    review_rate = mean(1 if case.confidence <= threshold else 0 for case in cases)
    accuracy = mean(decisions)
    deferred_accuracy = mean(
        case.expert_correct for case in cases if case.confidence <= threshold
    ) if any(case.confidence <= threshold for case in cases) else 0.0
    kept_accuracy = mean(
        case.model_correct for case in cases if case.confidence > threshold
    ) if any(case.confidence > threshold for case in cases) else 0.0
    return {
        "accuracy": accuracy,
        "error_rate": 1.0 - accuracy,
        "review_rate": review_rate,
        "deferred_accuracy": deferred_accuracy,
        "kept_accuracy": kept_accuracy,
        "threshold": threshold,
    }


def difference_metric(sample_cases: list[Case], calibrated_cells: set[tuple[int, int]], threshold: float) -> float:
    decisions_cal = [
        case.expert_correct if (confidence_bin(case.confidence), risk_bin(case.risk_signal)) in calibrated_cells else case.model_correct
        for case in sample_cases
    ]
    decisions_nav = [
        case.expert_correct if case.confidence <= threshold else case.model_correct
        for case in sample_cases
    ]
    return mean(decisions_cal) - mean(decisions_nav)


def bootstrap_diff_ci(
    cases: list[Case], 
    calibrated_cells: set[tuple[int, int]], 
    threshold: float, 
    iterations: int = 2000, 
    alpha: float = 0.05, 
    seed: int = 42
) -> tuple[float, float]:
    """Bootstrap CI using percentile method with increased iterations (2000 default)."""
    rng = random.Random(seed)
    n = len(cases)
    metrics = []
    for _ in range(iterations):
        sample = [cases[rng.randint(0, n - 1)] for _ in range(n)]
        metrics.append(difference_metric(sample, calibrated_cells, threshold))
    metrics.sort()
    lower = metrics[int((alpha / 2) * iterations)]
    upper = metrics[int((1 - alpha / 2) * iterations)]
    return lower, upper


def evaluate_calibrated(cases: list[Case], calibrated_cells: set[tuple[int, int]]) -> dict[str, float]:
    decisions = [
        case.expert_correct
        if (confidence_bin(case.confidence), risk_bin(case.risk_signal)) in calibrated_cells
        else case.model_correct
        for case in cases
    ]
    review_rate = mean(
        1 if (confidence_bin(case.confidence), risk_bin(case.risk_signal)) in calibrated_cells else 0
        for case in cases
    )
    accuracy = mean(decisions)
    deferred_cases = [
        case for case in cases if (confidence_bin(case.confidence), risk_bin(case.risk_signal)) in calibrated_cells
    ]
    kept_cases = [
        case for case in cases if (confidence_bin(case.confidence), risk_bin(case.risk_signal)) not in calibrated_cells
    ]
    return {
        "accuracy": accuracy,
        "error_rate": 1.0 - accuracy,
        "review_rate": review_rate,
        "deferred_accuracy": mean(case.expert_correct for case in deferred_cases) if deferred_cases else 0.0,
        "kept_accuracy": mean(case.model_correct for case in kept_cases) if kept_cases else 0.0,
    }


def run_seed_iteration(seed: int, n_train: int, n_test: int, budget: float, expert_mode: str = 'optimistic', selector: str = 'greedy', bootstrap_iterations: int = 2000):
    rng = random.Random(seed)
    calibration = build_dataset(rng, n_train, expert_mode)
    test = build_dataset(rng, n_test, expert_mode)

    summary = summarize_cells(calibration)
    
    # Select cells based on chosen algorithm
    if selector == 'knapsack':
        calibrated_cells = choose_calibrated_cells_knapsack(summary, budget)
    else:  # default greedy
        calibrated_cells = choose_calibrated_cells_greedy(summary, budget)
    
    naive_threshold = choose_naive_threshold(calibration, budget)

    calibrated_eval = evaluate_calibrated(test, calibrated_cells)
    naive_eval = evaluate_naive_threshold(test, naive_threshold)
    model_only_eval = evaluate_model_only(test)
    always_review_eval = evaluate_always_review(test)
    
    ci_lower, ci_upper = bootstrap_diff_ci(test, calibrated_cells, naive_threshold, iterations=bootstrap_iterations, seed=seed)

    return {
        "seed": seed,
        "diff_accuracy": calibrated_eval["accuracy"] - naive_eval["accuracy"],
        "diff_ci_95": [ci_lower, ci_upper],
        "policies": {
            "model_only": model_only_eval,
            "always_review": always_review_eval,
            "naive_threshold": naive_eval,
            "calibrated_defer": calibrated_eval,
        },
        "_calibration_data": calibration,
        "_test_data": test,
        "_summary": summary,
        "_calibrated_cells": calibrated_cells,
        "_naive_threshold": naive_threshold
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="MEDAI Deferral Simulation")
    parser.add_argument("--seed", type=int, default=20260501, help="Base random seed")
    parser.add_argument("--n_seeds", type=int, default=100, help="Number of seeds for sweep")
    parser.add_argument("--bootstrap_iterations", type=int, default=2000, help="Bootstrap iterations for CI (higher -> slower/more stable)")
    parser.add_argument("--n_train", type=int, default=6000, help="Calibration size")
    parser.add_argument("--n_test", type=int, default=12000, help="Test size")
    parser.add_argument("--budget", type=float, default=0.35, help="Review budget")
    parser.add_argument("--expert_mode", type=str, default='optimistic', 
                        help="Expert accuracy mode: 'optimistic', 'realistic', 'pessimistic', or 'heterogeneous'")
    parser.add_argument("--selector", type=str, default='greedy', 
                        help="Cell selection algorithm: 'greedy' or 'knapsack'")
    parser.add_argument("--out", type=str, default="non_oracle_defer_results_2026_05.json", help="Output JSON path")
    args = parser.parse_args()

    import statistics

    # attempt to record current git commit SHA and requirements hash before runs
    try:
        global_git_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        global_git_sha = "N/A"
    try:
        # canonicalize pip freeze output by sorting lines to produce a stable hash
        req_lines = subprocess.check_output([sys.executable, "-m", "pip", "freeze"], stderr=subprocess.DEVNULL).decode().splitlines()
        req_lines = sorted(l.strip() for l in req_lines if l.strip())
        req_txt = "\n".join(req_lines) + "\n"
        import hashlib
        requirements_hash = hashlib.sha256(req_txt.encode("utf-8")).hexdigest()
    except Exception:
        requirements_hash = "N/A"

    seed_results = []
    differences = []

    for offset in range(args.n_seeds):
        current_seed = args.seed + offset
        print(f"Running simulation for seed {current_seed} with mode {args.expert_mode}...")
        res = run_seed_iteration(current_seed, args.n_train, args.n_test, args.budget, args.expert_mode, args.selector, args.bootstrap_iterations)
        # attach per-seed provenance
        res["metadata"] = {
            "git_commit_sha": global_git_sha,
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            "python_version": sys.version,
            "seed": res.get("seed"),
            "requirements_hash": requirements_hash,
        }
        seed_results.append(res)
        differences.append(res["diff_accuracy"])

    mean_diff = statistics.mean(differences)
    std_diff = statistics.stdev(differences) if len(differences) > 1 else 0.0

    # For plots and detailed cell outputs, use the base seed
    base_res = seed_results[0]
    summary = base_res["_summary"]
    calibrated_cells = base_res["_calibrated_cells"]

    # Attempt to record current git commit SHA; tolerate non-git folders
    try:
        git_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        git_sha = "N/A"

    results = {
        "metadata": {
            "git_commit_sha": git_sha,
            "python_version": sys.version,
            "requirements_hash": requirements_hash,
            "timestamp": datetime.datetime.now().isoformat(),
            "args": vars(args)
        },
        "base_seed": args.seed,
        "n_seeds": args.n_seeds,
        "calibration_size": args.n_train,
        "test_size": args.n_test,
        "review_budget": args.budget,
        "simulation_config": {
            "expert_mode": args.expert_mode,
            "beta_alpha": BETA_ALPHA,
            "beta_beta": BETA_BETA,
            "risk_signal_formula": "clamp(0.18 + 0.55 * difficulty + rng.gauss(0.0, 0.11), 0.01, 0.99)",
            "confidence_formula": "clamp(0.91 - 0.52 * difficulty + rng.gauss(0.0, 0.08), 0.05, 0.99)",
            "model_accuracy_formula": "clamp(0.95 - 0.28 * difficulty - 0.23 * risk_signal, 0.46, 0.97)",
            "expert_accuracy_formula": {
                "optimistic": "clamp(0.79 + 0.07 * difficulty + 0.12 * risk_signal, 0.71, 0.96)",
                "realistic": "clamp(0.85 - 0.10 * difficulty + 0.05 * risk_signal, 0.70, 0.92)",
                "pessimistic": "clamp(0.80 - 0.15 * difficulty - 0.12 * risk_signal, 0.65, 0.88)",
                "heterogeneous": "mixture(optimistic, realistic, pessimistic)"
            }.get(args.expert_mode, "custom"),
        },
        "aggregated": {
            "mean_diff_accuracy": mean_diff,
            "std_diff_accuracy": std_diff
        },
        "seed_results": [
            {
                "seed": r["seed"],
                "diff_accuracy": r["diff_accuracy"],
                "diff_ci_95": r["diff_ci_95"],
                "policies": r["policies"],
                "metadata": r.get("metadata", {})
            }
            for r in seed_results
        ],
        "base_seed_calibration_cells": {
            f"confidence_{index[0]}_risk_{index[1]}": values for index, values in summary.items()
        },
        "base_seed_chosen_cells": [list(index) for index in sorted(calibrated_cells)],
        "selector_used": args.selector,
    }

    output_path = Path(args.out)
    # Ensure output directory exists
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    output_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    # Generate Reliability Diagram
    if _HAS_MATPLOTLIB:
        fig, ax = plt.subplots(figsize=(6, 5))
        confidences = [v["mean_confidence"] for v in summary.values() if v["count"] >= 5]
        accuracies = [v["model_accuracy"] for v in summary.values() if v["count"] >= 5]
        ax.scatter(confidences, accuracies, alpha=0.7)
        ax.plot([0, 1], [0, 1], "k--", label="Perfect Calibration")
        ax.set_xlabel("Confidence")
        ax.set_ylabel("Accuracy")
        ax.set_title("Reliability Diagram (Model Only)")
        ax.legend()
        fig.savefig(output_path.with_name("reliability_diagram.png"))
        plt.close(fig)
    else:
        print("matplotlib not available — skipping reliability diagram")

    # Generate Coverage vs Error Curve
    budgets = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    naive_errors = []
    calibrated_errors = []
    for b in budgets:
        n_thresh = choose_naive_threshold(base_res["_calibration_data"], b)
        naive_eval = evaluate_naive_threshold(base_res["_test_data"], n_thresh)
        naive_errors.append(naive_eval["error_rate"])
        
        # Use selected selector for calibrated cells
        if args.selector == 'knapsack':
            c_cells = choose_calibrated_cells_knapsack(summary, b)
        else:
            c_cells = choose_calibrated_cells_greedy(summary, b)
        calibrated_eval = evaluate_calibrated(base_res["_test_data"], c_cells)
        calibrated_errors.append(calibrated_eval["error_rate"])

    if _HAS_MATPLOTLIB:
        fig, ax = plt.subplots(figsize=(6, 5))
        coverages = [1.0 - b for b in budgets]
        ax.plot(coverages, naive_errors, "o-", label="Naive Threshold")
        ax.plot(coverages, calibrated_errors, "s-", label="Calibrated Deferral")
        ax.set_xlabel("Coverage (Model autonomy)")
        ax.set_ylabel("Error Rate")
        ax.set_title("Coverage vs Error Trade-off")
        ax.invert_xaxis()
        ax.legend()
        fig.savefig(output_path.with_name("coverage_vs_error.png"))
        plt.close(fig)
    else:
        print("matplotlib not available — skipping coverage vs error plot")

    print(json.dumps(results["aggregated"], indent=2, ensure_ascii=False))
    print(f"\nResults written to: {output_path}")
    print(f"Plots written to: {output_path.parent}")


if __name__ == "__main__":
    main()
