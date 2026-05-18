# Pipeline architecture

```mermaid
flowchart LR
  sim["non_oracle_defer_simulation_2026_05.py"]
  raw["*_full.json per seed batches"]
  merge["merge_experiment_results.py"]
  full["non_oracle_defer_results_2026_05_full.json"]
  agg["compute_and_plot_results.py"]
  out["*_full_analysis.json + figures"]
  val["scripts/validate_analysis.py"]

  sim --> raw --> merge --> full --> agg --> out --> val
```

## Layers

1. **Simulation** (`artifacts/`) — generates per-seed metrics; records `pip freeze` hash when requested.
2. **Merge** — deduplicates seeds, attaches provenance metadata.
3. **Analysis** — bootstrap CIs, paired permutation tests, Holm correction; large bootstrap arrays in `.npy.gz` sidecars.
4. **Validation** — schema and provenance checks for CI.

## Containers

- **Docker** (`artifacts/Dockerfile`, Python 3.11-slim, hash-pinned requirements) — CI smoke (1 seed).
- **Host** — full R=100 rebuild per [REPRODUCE.md](../REPRODUCE.md).

## What is not in this repo

Application PDFs and private drafts (`AIRI_*.md`) live outside git per [.gitignore](../.gitignore).
