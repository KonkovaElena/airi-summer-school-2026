# AIRI 2026: Learning to Defer Simulation

Synthetic-data evaluation framework for empirical uncertainty calibration and selective prediction ("Learning to Defer") under constrained expert budgets.

## Requirements

- Python >= 3.9
- `matplotlib==3.9.2` (for plot generation)

## Execution

### Docker (Recommended)
```bash
docker build -t airi-defer-sim:latest .
mkdir -p out
docker run --rm -v $(pwd)/out:/app/out airi-defer-sim:latest python non_oracle_defer_simulation_2026_05.py --seed 20260501 --out out/results.json
```

### Local Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python non_oracle_defer_simulation_2026_05.py --seed 20260501
```

## Outputs

- `non_oracle_defer_results_2026_05.json` — Raw metric JSON.
- `reliability_diagram.png` — Empirical accuracy versus predicted confidence. Validates selective prediction routing against ideal calibration ($y=x$). Note: Cells with $N < 5$ are excluded to remove high-variance outliers. The observed pattern of points lying above the diagonal (accuracy > confidence) in the 0.4–0.7 range indicates classical under-confidence of the simulated model; this is a methodologically important property that allows calibrated selective prediction to yield significant gains over naive thresholding.
- `coverage_vs_error.png` — Empirical error rate mapped against coverage. Benchmarks the risk-conditioned deferral policy against baseline confidence thresholding. Note that at low review budgets (high coverage $> 0.70$), the naive threshold marginally outperforms calibrated deferral due to a greedy selection failure under data scarcity. Specifically, at budgets $< 20\%$, the policy relies on high-confidence boundary cells which often contain few samples, leading to unstable empirical accuracy estimates. Their weight in the overall budget is small, but their impact on the error rate at high coverage is disproportionate. In the frozen R=100 aggregate, calibrated deferral reaches 81.29% mean accuracy at 33.96% review rate, compared with 81.05% at 34.92% review rate for the naive threshold.

*Note: the deferral policy may include calibration cells with fewer than 5 samples; these contribute marginally to the review budget and do not affect primary results.*

## Expert Simulation

The simulation models the human decision-maker as an **optimistic non-oracle expert**. The formula `expert_accuracy = clamp(0.79 + 0.07*difficulty + 0.12*risk_signal, 0.71, 0.96)` assumes that the expert performs better when the risk signal is high. While counter-intuitive for real clinical settings (where high risk often implies harder cases for both model and human), this optimistic assumption is mathematically useful for isolating and demonstrating the theoretical bounds of the learning-to-defer framework in a synthetic environment.

## Analysis provenance and reproducibility

The aggregated analysis reported in the repository was produced from the merged experiment file:

- `artifacts/non_oracle_defer_results_2026_05_full.json` (R = 100 seeds)

Aggregation and statistical analysis were performed with `compute_and_plot_results.py` (in this `artifacts/` folder). The command used to reproduce the published figures and tables is:

```bash
cd artifacts
python compute_and_plot_results.py non_oracle_defer_results_2026_05_full.json \
  -o non_oracle_defer_results_2026_05_full_analysis \
  --n_bootstrap 5000 --n_permutation 10000 --rng_seed 0
```

See [REPRODUCE.md](../REPRODUCE.md) for merge + `requirements_hash` setup.

Produced files (analysis):

- `non_oracle_defer_results_2026_05_full_analysis.json` — aggregated summary and comparison statistics
- `non_oracle_defer_results_2026_05_full_analysis.metrics.csv` — per-policy CSV summary
- `non_oracle_defer_results_2026_05_full_analysis_accuracy.png` — mean accuracy ± 95% CI
- `non_oracle_defer_results_2026_05_full_analysis_review_rate.png` — mean review rates

Environment notes (recorded at aggregation time):

- Python: 3.13.7
- Key packages: `matplotlib==3.9.2` (plotting), `numpy` (array ops). `scipy` is optional — if present the analysis script will use SciPy's BCa bootstrap; otherwise it falls back to a percentile bootstrap implementation.

Statistical methods (short):

- 95% confidence intervals: 5,000 bootstrap resamples (BCa if SciPy available; percentile bootstrap fallback used for the recorded run). See Efron & Tibshirani (1993) and Davison & Hinkley (1997).
- Hypothesis tests: paired permutation (sign) test with 10,000 permutations for paired comparisons across seeds.
- Effect size: paired Cohen's d on per-seed differences (reported for completeness; interpret with caution in deterministic synthetic setups).

Recommended citation / reading (methodology):

- Efron, B., & Tibshirani, R. J. (1993). An Introduction to the Bootstrap. Chapman & Hall/CRC.
- Davison, A. C., & Hinkley, D. V. (1997). Bootstrap Methods and Their Application. Cambridge University Press.
- Demsar, J. (2006). Statistical Comparisons of Classifiers over Multiple Data Sets. Journal of Machine Learning Research, 7, 1–30. http://jmlr.org/papers/volume7/demsar06a/demsar06a.pdf
- SciPy bootstrap docs: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html
- Good, P. (2000). Permutation Tests: A Practical Guide to Resampling Methods for Testing Hypotheses (optional background).
