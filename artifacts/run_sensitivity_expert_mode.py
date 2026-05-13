#!/usr/bin/env python3
"""Run expert_mode sensitivity (optimistic / realistic / pessimistic) at R=100."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ARTIFACTS = Path(__file__).resolve().parent
MODES = ('optimistic', 'realistic', 'pessimistic')
BASE_SEED = 20260501
N_SEEDS = 100
# Per-seed bootstrap in simulation only affects seed-level CIs; aggregate analysis re-bootstraps.
SIM_BOOTSTRAP_ITERATIONS = 200


def run_mode(mode: str) -> dict:
    summary_path = ARTIFACTS / 'sensitivity_expert_mode_2026_05.json'
    if summary_path.exists():
        existing = json.loads(summary_path.read_text(encoding='utf-8'))
        for m in existing.get('modes', []):
            if m.get('expert_mode') == mode:
                print(f'SKIP {mode} (already in {summary_path.name})', flush=True)
                return m

    out_json = ARTIFACTS / f'sensitivity_expert_{mode}_raw.json'
    if mode == 'optimistic' and (ARTIFACTS / 'non_oracle_defer_results_2026_05_full.json').exists():
        src = ARTIFACTS / 'non_oracle_defer_results_2026_05_full.json'
        data = json.loads(src.read_text(encoding='utf-8'))
    elif out_json.exists() and len(json.loads(out_json.read_text(encoding='utf-8')).get('seed_results', [])) >= N_SEEDS:
        data = json.loads(out_json.read_text(encoding='utf-8'))
    else:
        cmd = [
            sys.executable,
            str(ARTIFACTS / 'non_oracle_defer_simulation_2026_05.py'),
            '--seed', str(BASE_SEED),
            '--n_seeds', str(N_SEEDS),
            '--expert_mode', mode,
            '--bootstrap_iterations', str(SIM_BOOTSTRAP_ITERATIONS),
            '--out', str(out_json),
        ]
        print('RUN', ' '.join(cmd), flush=True)
        subprocess.run(cmd, check=True, cwd=ARTIFACTS)
        data = json.loads(out_json.read_text(encoding='utf-8'))

    analysis_base = ARTIFACTS / f'sensitivity_expert_{mode}_analysis'
    env = os.environ.copy()
    hash_path = ARTIFACTS / 'installed.txt.sha256'
    if hash_path.exists():
        env['REQUIREMENTS_HASH'] = hash_path.read_text(encoding='utf-8').strip()

    tmp_full = ARTIFACTS / f'sensitivity_expert_{mode}_full.json'
    tmp_full.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')

    acmd = [
        sys.executable,
        str(ARTIFACTS / 'compute_and_plot_results.py'),
        str(tmp_full),
        '-o', str(analysis_base),
        '--n_bootstrap', '5000',
        '--n_permutation', '10000',
        '--rng_seed', '0',
        '--frozen-run-id', f'sensitivity_{mode}_greedy_r100_202605',
    ]
    print('ANALYZE', ' '.join(acmd), flush=True)
    subprocess.run(acmd, check=True, cwd=ARTIFACTS, env=env)
    analysis = json.loads(analysis_base.with_suffix('.json').read_text(encoding='utf-8'))
    return {
        'expert_mode': mode,
        'n_seeds': len(data.get('seed_results', [])),
        'metrics': analysis.get('metrics', {}),
        'comparisons': [
            {
                'a': c.get('a'),
                'b': c.get('b'),
                'mean_diff': c.get('mean_diff'),
                'p_value': c.get('p_value'),
                'p_value_holm': c.get('p_value_holm'),
                'ci_95': c.get('ci_95'),
            }
            for c in analysis.get('comparisons', [])
        ],
    }


def main() -> None:
    summary = {
        'modes': [],
        'simulation_config': {
            'n_seeds': N_SEEDS,
            'base_seed': BASE_SEED,
            'review_budget': 0.35,
            'selector': 'greedy',
            'expert_modes': list(MODES),
            'simulation_bootstrap_iterations': SIM_BOOTSTRAP_ITERATIONS,
            'analysis_n_bootstrap': 5000,
            'analysis_n_permutation': 10000,
        },
    }
    for mode in MODES:
        summary['modes'].append(run_mode(mode))
    out = ARTIFACTS / 'sensitivity_expert_mode_2026_05.json'
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
    print('Wrote', out)


if __name__ == '__main__':
    main()
