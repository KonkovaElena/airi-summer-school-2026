# Frozen experimental protocol (v1.1)

**Identifier:** `primary_optimistic_greedy_r100_202605`  
**Canonical output:** `artifacts/non_oracle_defer_results_2026_05_full_analysis.json`

## Design

| Parameter | Value |
|-----------|-------|
| Independent seeds R | 100 |
| Calibration set size | 6,000 |
| Test set size | 12,000 |
| Nominal review budget | 0.35 |
| Expert mode | optimistic |
| Cell selector | greedy (0/1 knapsack optional via CLI) |
| Bootstrap (per seed in simulation) | 2,000 |
| Analysis bootstrap / permutation / RNG | 5,000 / 10,000 / 0 |

## Policies

| Key | Description |
|-----|-------------|
| `model_only` | No deferral |
| `naive_threshold` | Per-seed confidence threshold tuned to budget |
| `calibrated_defer` | Histogram calibration + risk signal |
| `always_review` | Expert on all cases |

## Primary endpoints (frozen run)

| Comparison | Mean diff (pp) | 95% CI | p (paired perm.) |
|------------|----------------|--------|------------------|
| calibrated_defer vs naive_threshold | +0.24 | [0.15, 0.33] | < 0.0001 |
| calibrated_defer vs model_only | +9.42 | — | < 0.0001 |

Mean accuracies (%): model_only 71.87; naive 81.05; calibrated 81.29; always_review 87.52.

## Sensitivity (expert mode)

See `artifacts/sensitivity_expert_mode_2026_05.json`. Realistic expert: +0.13 pp (Holm p ≈ 0.004). Pessimistic: no significant gain.

## Limitations

Synthetic generative model; optimistic expert may overstate deferral gains. Not IRB/clinical data.

## Reproduce

See [REPRODUCE.md](../REPRODUCE.md) and [ARCHITECTURE.md](ARCHITECTURE.md).
