#!/usr/bin/env python3
"""Merge multiple batch JSON result files from the non-oracle deferral simulation.

Usage:
  python merge_experiment_results.py <in1.json> [in2.json ...] -o out.json

The script concatenates `seed_results` arrays, recomputes aggregated mean/std
for `diff_accuracy` and writes a merged JSON to the output path.
"""
import sys
import json
import argparse
import glob
import datetime
from statistics import mean, stdev


def expand_inputs(inputs):
    files = []
    for p in inputs:
        if any(c in p for c in "*?["):
            files.extend(sorted(glob.glob(p)))
        else:
            files.append(p)
    return files


def main():
    p = argparse.ArgumentParser()
    p.add_argument("inputs", nargs="+", help="Input JSON files or glob patterns")
    p.add_argument("-o", "--out", required=True, help="Output merged JSON file")
    args = p.parse_args()

    files = expand_inputs(args.inputs)
    if not files:
        print("No input files found", file=sys.stderr)
        sys.exit(2)

    merged = None
    seed_results = []
    input_git_shas = set()
    input_files_info = []
    consistency_warnings = []
    for f in files:
        with open(f, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        # record file-level info
        meta = data.get("metadata", {})
        sha = meta.get("git_commit_sha") or meta.get("git_sha") or "N/A"
        input_git_shas.add(sha)
        input_files_info.append({"file": f, "git_commit_sha": sha})
        if merged is None:
            # take metadata and config from first file
            merged = {
                "metadata": data.get("metadata", {}),
                "base_seed": data.get("base_seed", None),
                "n_seeds": 0,
                "calibration_size": data.get("calibration_size"),
                "test_size": data.get("test_size"),
                "review_budget": data.get("review_budget"),
                "simulation_config": data.get("simulation_config", {}),
                "seed_results": [],
                "base_seed_calibration_cells": data.get("base_seed_calibration_cells", {}),
            }
        # validate per-file structure and seed entries
        if "seed_results" not in data or not isinstance(data["seed_results"], list):
            print(f"ERROR: file {f} missing 'seed_results' array", file=sys.stderr)
            sys.exit(3)
        for s in data.get("seed_results", []):
            if not isinstance(s, dict):
                print(f"ERROR: invalid seed entry in {f}: not an object", file=sys.stderr)
                sys.exit(4)
            if "seed" not in s:
                print(f"ERROR: seed entry missing 'seed' in file {f}", file=sys.stderr)
                sys.exit(5)
            if "policies" not in s:
                print(f"ERROR: seed {s.get('seed')} in file {f} missing 'policies'", file=sys.stderr)
                sys.exit(6)
        seed_results.extend(data.get("seed_results", []))

    # recompute aggregated
    diffs = [s.get("diff_accuracy") for s in seed_results if s.get("diff_accuracy") is not None]
    agg = {}
    if diffs:
        agg["mean_diff_accuracy"] = mean(diffs)
        try:
            agg["std_diff_accuracy"] = stdev(diffs) if len(diffs) > 1 else None
        except Exception:
            agg["std_diff_accuracy"] = None
    else:
        agg["mean_diff_accuracy"] = None
        agg["std_diff_accuracy"] = None

    merged["seed_results"] = seed_results
    merged["n_seeds"] = len(seed_results)
    merged["aggregated"] = agg
    merged["merged_timestamp"] = datetime.datetime.now().isoformat()
    # record inputs and git SHAs
    merged.setdefault("metadata", {})
    # Do not inherit misleading per-batch args (e.g. n_seeds=10) after multi-file merge
    if "args" in merged["metadata"]:
        merged["metadata"]["args"] = {
            "merged_from_files": len(files),
            "total_seeds": len(seed_results),
            "note": "Per-batch args omitted; see input_files and simulation_config.",
        }
    merged["metadata"]["input_files"] = input_files_info
    # Treat 'N/A' as missing — require at least one non-N/A SHA for a positive consistency signal
    non_na_shas = sorted([s for s in input_git_shas if s and s != "N/A"])
    merged["metadata"]["input_git_commit_shas"] = sorted(list(input_git_shas))
    merged["metadata"]["consistent_git_sha"] = (len(non_na_shas) <= 1 and len(non_na_shas) > 0)
    merged["metadata"]["missing_git_shas"] = len(non_na_shas) == 0
    merged["metadata"]["protocol_version"] = "1.1"
    merged["metadata"]["frozen_run_id"] = "primary_optimistic_greedy_r100_202605"

    # consistency checks for key config fields across files
    # (base_seed, calibration_size, test_size, review_budget)
    base_seeds = set()
    calib_sizes = set()
    test_sizes = set()
    budgets = set()
    for f in files:
        try:
            d = json.load(open(f, "r", encoding="utf-8"))
        except Exception:
            continue
        base_seeds.add(d.get("base_seed"))
        calib_sizes.add(d.get("calibration_size"))
        test_sizes.add(d.get("test_size"))
        budgets.add(d.get("review_budget"))
    if len(base_seeds) > 1:
        consistency_warnings.append(f"inconsistent base_seed across inputs: {sorted(base_seeds)}")
    if len(calib_sizes) > 1:
        consistency_warnings.append(f"inconsistent calibration_size across inputs: {sorted(calib_sizes)}")
    if len(test_sizes) > 1:
        consistency_warnings.append(f"inconsistent test_size across inputs: {sorted(test_sizes)}")
    if len(budgets) > 1:
        consistency_warnings.append(f"inconsistent review_budget across inputs: {sorted(budgets)}")
    if consistency_warnings:
        merged["metadata"]["consistency_warnings"] = consistency_warnings

    # detect duplicate seeds
    seen = set()
    dupes = set()
    for s in seed_results:
        sid = s.get("seed")
        if sid in seen:
            dupes.add(sid)
        seen.add(sid)
    if dupes:
        print(f"ERROR: duplicate seed IDs found across inputs: {sorted(list(dupes))}", file=sys.stderr)
        sys.exit(7)

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(merged, fh, indent=2, ensure_ascii=False)

    print("Merged {} files -> {} ({} seeds)".format(len(files), args.out, len(seed_results)))


if __name__ == "__main__":
    main()
