# Reproducing AIRI defer experiments (standalone repo)

Canonical metrics: `artifacts/non_oracle_defer_results_2026_05_full_analysis.json` (protocol 1.1, R=100).

## Quick verify

```bash
python scripts/validate_analysis.py artifacts/non_oracle_defer_results_2026_05_full_analysis.json --strict-provenance
pytest -q
```

## Frozen protocol

| Parameter | Value |
|-----------|-------|
| Seeds R | 100 |
| Review budget | 0.35 |
| Expert mode | optimistic |
| Selector | greedy |
| Analysis bootstrap / permutation / seed | 5000 / 10000 / 0 |

## Full rebuild (from batch JSON files)

Requires batch files `non_oracle_defer_results_batch_01.json` … `05` (generate locally or obtain from maintainer).

```bash
cd artifacts
python merge_experiment_results.py \
  non_oracle_defer_results_batch_01.json \
  non_oracle_defer_results_batch_02.json \
  non_oracle_defer_results_batch_03.json \
  non_oracle_defer_results_batch_04.json \
  non_oracle_defer_results_batch_05.json \
  -o non_oracle_defer_results_2026_05_full.json

pip freeze | sort -u > installed.txt
# Linux: sha256sum installed.txt | awk '{print $1}' > installed.txt.sha256
# Windows: see GITHUB_REPO_AUDIT for PowerShell hash command

export REQUIREMENTS_HASH=$(cat installed.txt.sha256)   # or set in PowerShell

python compute_and_plot_results.py non_oracle_defer_results_2026_05_full.json \
  -o non_oracle_defer_results_2026_05_full_analysis \
  --n_bootstrap 5000 --n_permutation 10000 --rng_seed 0

cd ..
python scripts/validate_analysis.py artifacts/non_oracle_defer_results_2026_05_full_analysis.json --strict-provenance
```

## Smoke run (10 seeds)

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r artifacts/requirements.txt --require-hashes
python artifacts/non_oracle_defer_simulation_2026_05.py --seed 20260501 --n_seeds 10 --out artifacts/batch_results_local.json
```

## Docker (CI parity)

```bash
cd artifacts
docker build -t airi-defer-sim:latest .
mkdir -p out
docker run --rm -v "$(pwd)/out:/app/out" airi-defer-sim:latest \
  python non_oracle_defer_simulation_2026_05.py --seed 20260501 --out out/results.json
```

## Sensitivity (expert modes)

```bash
cd artifacts
python run_sensitivity_expert_mode.py
```

Output: `sensitivity_expert_mode_2026_05.json` (committed summary).
