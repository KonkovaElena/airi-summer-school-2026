#!/usr/bin/env python3
"""Aggregate merged experiment results, compute statistics and produce figures.

Usage:
  python compute_and_plot_results.py <merged_results.json> -o <out_prefix>

Produces:
 - <out_prefix>.json  (summary metrics)
 - <out_prefix>_metrics.csv
 - <out_prefix>_accuracy.png
 - <out_prefix>_review_rate.png

Designed to be robust: uses a percentile bootstrap fallback if SciPy is unavailable.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone
import platform
import subprocess

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import textwrap


def load_merged(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def try_scipy_bootstrap(arr: np.ndarray, n_resamples: int, alpha: float, rng_seed: int | None = None):
    try:
        from scipy.stats import bootstrap
    except Exception:
        return None
    # scipy expects sequences of arrays; for paired use, we'll use simple mean
    data = (arr,)
    def stat(x):
        return np.mean(x, axis=0)

    kwargs = {
        'n_resamples': n_resamples,
        'confidence_level': 1-alpha,
        'method': 'bca',
    }
    if rng_seed is not None:
        kwargs['rng'] = np.random.default_rng(rng_seed)
    try:
        res = bootstrap(data, stat, **kwargs)
    except TypeError:
        if rng_seed is None:
            raise
        kwargs.pop('rng', None)
        kwargs['random_state'] = rng_seed
        res = bootstrap(data, stat, **kwargs)
    lo, hi = res.confidence_interval
    return float(lo), float(hi), np.asarray(res.bootstrap_distribution)


def percentile_bootstrap_ci(values: np.ndarray, n_resamples: int = 5000, alpha: float = 0.05, rng=None):
    rng = np.random.default_rng() if rng is None else rng
    values = np.asarray(values)
    n = len(values)
    if n == 0:
        return float('nan'), float('nan'), np.array([])
    # vectorized resampling
    samples = rng.choice(values, size=(n_resamples, n), replace=True)
    stat = samples.mean(axis=1)
    lo = np.percentile(stat, 100 * (alpha / 2.0))
    hi = np.percentile(stat, 100 * (1 - alpha / 2.0))
    return float(lo), float(hi), stat


def paired_sign_permutation_test(a: np.ndarray, b: np.ndarray, n_permutations: int = 10000, rng=None):
    rng = np.random.default_rng() if rng is None else rng
    diff = np.asarray(a) - np.asarray(b)
    obs = np.mean(diff)
    if len(diff) == 0:
        return float('nan')
    signs = rng.choice([-1, 1], size=(n_permutations, len(diff)))
    perm_means = (signs * diff).mean(axis=1)
    p = (np.sum(np.abs(perm_means) >= abs(obs)) + 1) / (n_permutations + 1)
    return float(p)


def cohen_d_paired(a: np.ndarray, b: np.ndarray):
    diff = np.asarray(a) - np.asarray(b)
    mean = np.mean(diff)
    sd = np.std(diff, ddof=1)
    if sd == 0:
        return float('nan')
    return float(mean / sd)


def json_sanitize(value):
    if isinstance(value, dict):
        return {k: json_sanitize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_sanitize(v) for v in value]
    if isinstance(value, tuple):
        return [json_sanitize(v) for v in value]
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        value = float(value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def main():
    p = argparse.ArgumentParser()
    p.add_argument('merged_json', help='Path to merged results JSON')
    p.add_argument('-o', '--out', required=True, help='Output prefix (file path without extension)')
    p.add_argument('--n_bootstrap', type=int, default=5000)
    p.add_argument('--n_permutation', type=int, default=10000)
    p.add_argument('--alpha', type=float, default=0.05)
    p.add_argument('--rng_seed', type=int, default=0)
    p.add_argument(
        '--include-bootstrap-blobs',
        action='store_true',
        help='Embed full bootstrap_distribution arrays in JSON (default: write .npy.gz sidecars)',
    )
    p.add_argument('--frozen-run-id', default='primary_optimistic_greedy_r100_202605')
    args = p.parse_args()

    rng = np.random.default_rng(args.rng_seed)

    data = load_merged(args.merged_json)
    seed_results = data.get('seed_results') or data.get('seeds') or []

    policies = ['model_only', 'naive_threshold', 'calibrated_defer', 'always_review']
    metrics = {}
    # collect arrays
    arrays = {pol: {'accuracy': [], 'review_rate': [], 'deferred_accuracy': []} for pol in policies}

    for s in seed_results:
        for pol in policies:
            # merged JSON nests policy outputs under the 'policies' key
            polv = s.get('policies', {}).get(pol, {})
            if not polv:
                # keep alignment but skip missing values
                arrays[pol]['accuracy'].append(None)
                arrays[pol]['review_rate'].append(None)
                arrays[pol]['deferred_accuracy'].append(None)
                continue
            arrays[pol]['accuracy'].append(polv.get('accuracy'))
            arrays[pol]['review_rate'].append(polv.get('review_rate'))
            arrays[pol]['deferred_accuracy'].append(polv.get('deferred_accuracy'))

    # convert to numpy and compute
    for pol in policies:
        acc = np.array([v for v in arrays[pol]['accuracy'] if v is not None], dtype=float)
        rr = np.array([v for v in arrays[pol]['review_rate'] if v is not None], dtype=float)
        da = np.array([v for v in arrays[pol]['deferred_accuracy'] if v is not None], dtype=float)

        mean = float(np.mean(acc)) if acc.size else float('nan')
        std = float(np.std(acc, ddof=1)) if acc.size > 1 else float('nan')

        # try SciPy BCa then percentile fallback
        sc_res = try_scipy_bootstrap(acc, n_resamples=args.n_bootstrap, alpha=args.alpha, rng_seed=args.rng_seed) if acc.size else None
        if sc_res is not None:
            lo, hi, boot_dist = sc_res
        else:
            lo, hi, boot_dist = percentile_bootstrap_ci(acc, n_resamples=args.n_bootstrap, alpha=args.alpha, rng=rng)

        metrics[pol] = {
            'n_seeds': int(acc.size),
            'mean_accuracy': mean,
            'std_accuracy': std,
            'ci_low': lo,
            'ci_high': hi,
            'mean_review_rate': float(np.mean(rr)) if rr.size else float('nan'),
            'mean_deferred_accuracy': float(np.mean(da)) if da.size else float('nan'),
        }

    # paired comparisons and permutation tests
    comparisons = []
    def safe_arr(pol):
        return np.array([v for v in arrays[pol]['accuracy'] if v is not None], dtype=float)

    out_dir_pre = os.path.dirname(args.out if args.out.endswith('.json') else args.out + '.json') or '.'
    pairs = [('calibrated_defer', 'naive_threshold'), ('calibrated_defer', 'model_only'), ('naive_threshold', 'model_only')]
    for a_pol, b_pol in pairs:
        a_arr = safe_arr(a_pol)
        b_arr = safe_arr(b_pol)
        # align lengths by seed order (we assume seeds are present for both)
        n = min(len(a_arr), len(b_arr))
        a_arr = a_arr[:n]
        b_arr = b_arr[:n]
        diffs = a_arr - b_arr
        mean_diff = float(np.mean(diffs)) if diffs.size else float('nan')
        # attempt BCa via SciPy, fallback to percentile bootstrap
        sc_res = try_scipy_bootstrap(diffs, n_resamples=args.n_bootstrap, alpha=args.alpha, rng_seed=args.rng_seed) if diffs.size else None
        if sc_res is not None:
            lo, hi, boot_dist = sc_res
        else:
            lo, hi, boot_dist = percentile_bootstrap_ci(diffs, n_resamples=args.n_bootstrap, alpha=args.alpha, rng=rng) if diffs.size else (float('nan'), float('nan'), np.array([]))

        pval = paired_sign_permutation_test(a_arr, b_arr, n_permutations=args.n_permutation, rng=rng) if diffs.size else float('nan')
        d = cohen_d_paired(a_arr, b_arr) if diffs.size else float('nan')
        entry = {
            'a': a_pol,
            'b': b_pol,
            'mean_diff': mean_diff,
            'ci_low': lo,
            'ci_high': hi,
            'p_value': pval,
            'cohen_d_paired': d,
            'n_bootstrap': args.n_bootstrap,
        }
        pair_key = f"{a_pol}_vs_{b_pol}"
        if args.include_bootstrap_blobs:
            entry['bootstrap_distribution'] = boot_dist.tolist() if hasattr(boot_dist, 'tolist') else []
        elif hasattr(boot_dist, 'size') and boot_dist.size:
            import gzip
            sidecar = os.path.join(out_dir_pre, f"bootstrap_{pair_key}.npy.gz")
            with gzip.open(sidecar, 'wb') as gz:
                gz.write(boot_dist.astype(np.float64).tobytes())
            meta_path = sidecar + '.meta.json'
            with open(meta_path, 'w', encoding='utf-8') as mf:
                json.dump({'length': int(boot_dist.size), 'dtype': 'float64'}, mf)
            entry['bootstrap_artifact'] = os.path.basename(sidecar)
            entry['bootstrap_artifact_meta'] = os.path.basename(meta_path)
        comparisons.append(entry)

    out = {
        'generated_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        'script': os.path.basename(__file__),
        'platform': platform.platform(),
        'python_version': platform.python_version(),
        'metrics': metrics,
        'comparisons': comparisons,
    }

    # try to include git sha if available in merged metadata, environment, or via git
    gitsha = data.get('git_sha') or data.get('run_metadata', {}).get('git_sha')
    if not gitsha:
        # allow CI or caller to override with environment variable
        gitsha = os.environ.get('GIT_SHA')
    if not gitsha:
        # Resolve SHA from this repository root (stop at LICENSE/CITATION.cff), not an outer monorepo
        merged_dir = os.path.dirname(os.path.abspath(args.merged_json))
        found = False
        cur = merged_dir
        for _ in range(8):
            if os.path.isdir(os.path.join(cur, '.git')) and (
                os.path.isfile(os.path.join(cur, 'LICENSE'))
                or os.path.isfile(os.path.join(cur, 'CITATION.cff'))
            ):
                try:
                    gitsha = subprocess.check_output(
                        ['git', 'rev-parse', '--short', 'HEAD'],
                        cwd=cur,
                        stderr=subprocess.DEVNULL,
                    ).decode().strip()
                    found = True
                    break
                except Exception:
                    pass
            parent = os.path.dirname(cur)
            if parent == cur:
                break
            cur = parent
        if not found:
            try:
                gitsha = subprocess.check_output(
                    ['git', 'rev-parse', '--short', 'HEAD'],
                    cwd=os.getcwd(),
                    stderr=subprocess.DEVNULL,
                ).decode().strip()
            except Exception:
                gitsha = 'N/A'
    out['git_sha'] = gitsha
    # record requirements hash if provided by CI or available as uploaded artifact
    req_hash = os.environ.get('REQUIREMENTS_HASH')
    if not req_hash:
        # try to read uploaded installed.txt.sha256 if present in workspace
        try:
            with open('installed.txt.sha256', 'r', encoding='utf-8') as fh:
                req_hash = fh.read().strip()
        except Exception:
            req_hash = 'N/A'
    out['requirements_hash'] = req_hash

    # record docker image digest if provided by CI or merged metadata
    docker_digest = os.environ.get('DOCKER_IMAGE_DIGEST')
    if not docker_digest:
        docker_digest = data.get('run_metadata', {}).get('docker_image_digest') or data.get('docker_image_digest')
    if not docker_digest:
        docker_digest = 'N/A'
    out['docker_image_digest'] = docker_digest

    # Record analysis configuration for reproducibility checks
    out['analysis_config'] = {
        'n_bootstrap': args.n_bootstrap,
        'n_permutation': args.n_permutation,
        'alpha': args.alpha,
        'rng_seed': args.rng_seed,
        'include_bootstrap_blobs': args.include_bootstrap_blobs,
    }
    out['protocol_version'] = '1.1'
    out['frozen_run_id'] = args.frozen_run_id
    merged_meta = data.get('metadata') or {}
    out['simulation_config'] = data.get('simulation_config') or merged_meta.get('simulation_config')

    # Holm multiple-testing correction for paired comparisons
    def holm_adjust(pvals):
        pvals = np.array(pvals, dtype=float)
        m = len(pvals)
        if m == 0:
            return []
        idx = np.argsort(pvals)
        sorted_p = pvals[idx]
        adj_sorted = np.empty(m, dtype=float)
        max_val = 0.0
        for j in range(m):
            val = (m - j) * sorted_p[j]
            if val > max_val:
                max_val = val
            adj_sorted[j] = min(max_val, 1.0)
        adjusted = np.empty(m, dtype=float)
        adjusted[idx] = adj_sorted
        return adjusted.tolist()

    pvals = [c.get('p_value', float('nan')) for c in comparisons]
    try:
        adjusted = holm_adjust(pvals)
        for c, adj in zip(comparisons, adjusted):
            c['p_value_holm'] = float(adj)
            c['significant_holm'] = (float(adj) < args.alpha)
    except Exception:
        pass

    out_json = args.out if args.out.endswith('.json') else args.out + '.json'
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(json_sanitize(out), f, indent=2, ensure_ascii=False, allow_nan=False)

    # CSV summary
    csv_lines = ["policy,n_seeds,mean_accuracy,std_accuracy,ci_low,ci_high,mean_review_rate,mean_deferred_accuracy"]
    for pol in policies:
        m = metrics[pol]
        csv_lines.append(','.join([pol, str(m['n_seeds']), f"{m['mean_accuracy']:.6f}", f"{m['std_accuracy']:.6f}" if not np.isnan(m['std_accuracy']) else 'nan', f"{m['ci_low']:.6f}", f"{m['ci_high']:.6f}", f"{m['mean_review_rate']:.6f}", f"{m['mean_deferred_accuracy']:.6f}"]))

    csv_out = args.out + '.metrics.csv' if not args.out.endswith('.metrics.csv') else args.out
    with open(csv_out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(csv_lines))

    # Figures
    out_dir = os.path.dirname(out_json) or '.'
    # Accuracy bar chart
    labels = ['Model only', 'Naive threshold', 'Calibrated defer', 'Always review']
    means = [metrics[p]['mean_accuracy'] for p in policies]
    ci_l = [metrics[p]['ci_low'] for p in policies]
    ci_h = [metrics[p]['ci_high'] for p in policies]
    lower_err = np.array(means) - np.array(ci_l)
    upper_err = np.array(ci_h) - np.array(means)
    yerr = np.vstack([lower_err, upper_err])

    fig, ax = plt.subplots(figsize=(6, 4), dpi=300)
    x = np.arange(len(labels))
    ax.bar(x, means, yerr=yerr, capsize=6, color=['#4C72B0', '#55A868', '#C44E52', '#8172B2'])
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=10)
    ax.set_ylabel('Accuracy')
    ax.set_ylim(0, 1)
    ax.set_title('Aggregated policy accuracy (mean ± 95% CI)')
    fig.tight_layout()
    acc_png = os.path.join(out_dir, os.path.basename(args.out) + '_accuracy.png')
    fig.savefig(acc_png, dpi=300)
    plt.close(fig)

    # Review-rate bar chart
    rr_means = [metrics[p]['mean_review_rate'] for p in policies]
    fig, ax = plt.subplots(figsize=(6, 4), dpi=300)
    ax.bar(x, rr_means, color=['#4C72B0', '#55A868', '#C44E52', '#8172B2'])
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=10)
    ax.set_ylabel('Review rate')
    ax.set_title('Aggregated review rates (mean)')
    fig.tight_layout()
    rr_png = os.path.join(out_dir, os.path.basename(args.out) + '_review_rate.png')
    fig.savefig(rr_png, dpi=300)
    plt.close(fig)

    # Additional diagnostics
    # Violin plot of per-seed accuracies
    def make_array(pol):
        return np.array([v for v in arrays[pol]['accuracy'] if v is not None], dtype=float)

    violin_data = [make_array(p) for p in policies]
    fig, ax = plt.subplots(figsize=(7, 4), dpi=300)
    parts = ax.violinplot(violin_data, showmeans=True)
    ax.set_xticks(np.arange(1, len(policies) + 1))
    ax.set_xticklabels(labels, rotation=10)
    ax.set_ylabel('Accuracy')
    ax.set_title('Per-seed accuracy distribution by policy')
    fig.tight_layout()
    violin_png = os.path.join(out_dir, os.path.basename(args.out) + '_violin_accuracy.png')
    violin_pdf = os.path.join(out_dir, os.path.basename(args.out) + '_violin_accuracy.pdf')
    fig.savefig(violin_png, dpi=300)
    fig.savefig(violin_pdf)
    plt.close(fig)

    # Scatter: calibrated_defer vs naive_threshold
    a = make_array('calibrated_defer')
    b = make_array('naive_threshold')
    common_n = min(len(a), len(b))
    if common_n > 0:
        fig, ax = plt.subplots(figsize=(5, 5), dpi=300)
        ax.scatter(b[:common_n], a[:common_n], alpha=0.6)
        m = min(min(a[:common_n]), min(b[:common_n]))
        M = max(max(a[:common_n]), max(b[:common_n]))
        ax.plot([m, M], [m, M], color='gray', linestyle='--')
        ax.set_xlabel('Naive threshold accuracy')
        ax.set_ylabel('Calibrated defer accuracy')
        ax.set_title('Per-seed calibrated vs naive')
        fig.tight_layout()
        scatter_png = os.path.join(out_dir, os.path.basename(args.out) + '_scatter_calibrated_vs_naive.png')
        scatter_pdf = os.path.join(out_dir, os.path.basename(args.out) + '_scatter_calibrated_vs_naive.pdf')
        fig.savefig(scatter_png, dpi=300)
        fig.savefig(scatter_pdf)
        plt.close(fig)

    # Histogram of differences (calibrated - naive)
    if len(a) and len(b):
        diffs = a[:common_n] - b[:common_n]
        fig, ax = plt.subplots(figsize=(6, 4), dpi=300)
        ax.hist(diffs, bins=25, color='#4C72B0', alpha=0.8)
        ax.axvline(np.mean(diffs), color='k', linestyle='--', label=f'mean={np.mean(diffs):.4f}')
        ax.set_xlabel('Calibrated - Naive (accuracy)')
        ax.set_title('Distribution of per-seed differences')
        ax.legend()
        fig.tight_layout()
        diff_png = os.path.join(out_dir, os.path.basename(args.out) + '_diff_hist_calibrated_minus_naive.png')
        diff_pdf = os.path.join(out_dir, os.path.basename(args.out) + '_diff_hist_calibrated_minus_naive.pdf')
        fig.savefig(diff_png, dpi=300)
        fig.savefig(diff_pdf)
        plt.close(fig)

    # LaTeX table for manuscript
    def write_latex_table(metrics, comparisons, path_tex):
        rows = []
        rows.append('\\begin{table}[ht]')
        rows.append('\\centering')
        rows.append('\\caption{Aggregated policy accuracies and review rates (mean ± 95\\% CI)}')
        rows.append('\\begin{tabular}{lrrr}')
        rows.append('\\hline')
        rows.append('Policy & Mean accuracy & 95\\% CI & Review rate\\\\')
        rows.append('\\hline')
        for pol, label in zip(policies, labels):
            m = metrics[pol]
            mean_pct = m['mean_accuracy'] * 100 if not np.isnan(m['mean_accuracy']) else float('nan')
            lo_pct = m['ci_low'] * 100 if not np.isnan(m['ci_low']) else float('nan')
            hi_pct = m['ci_high'] * 100 if not np.isnan(m['ci_high']) else float('nan')
            rr_pct = m['mean_review_rate'] * 100 if not np.isnan(m['mean_review_rate']) else float('nan')
            rows.append(f"{label} & {mean_pct:.2f}\\% & [{lo_pct:.2f}, {hi_pct:.2f}] & {rr_pct:.1f}\\%\\\\")
        rows.append('\\hline')
        rows.append('\\end{tabular}')
        rows.append('\\end{table}')
        with open(path_tex, 'w', encoding='utf-8') as f:
            f.write('\n'.join(rows))

    tex_path = os.path.join(out_dir, os.path.basename(args.out) + '_table.tex')
    write_latex_table(metrics, comparisons, tex_path)

    print('Additional figures:', violin_png, violin_pdf, scatter_png if common_n>0 else 'n/a', diff_png if len(a) and len(b) else 'n/a')

    # print short summary for CLI
    print('Wrote:', out_json)
    print('CSV:', csv_out)
    print('Figures:', acc_png, rr_png)


if __name__ == '__main__':
    main()
