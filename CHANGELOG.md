# Changelog

All notable changes to this repository are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and [Semantic Versioning](https://semver.org/).

## [1.1.1] - 2026-05-20

### Fixed

- CI: `verify` job runs `verify_release`, strict `validate_analysis`, and `pytest` before Docker smoke (Python 3.13).
- CI: GitHub Actions on Node 24 (`checkout@v6`, `setup-python@v6`, `build-push-action@v7`, `upload-artifact@v5`).
- `CITATION.cff`: version 1.1.1, `preferred-citation` (Verma & Nalisnick 2022).
- `REPRODUCE.md`: inline hash commands for Linux and Windows; smoke docs aligned with `make smoke` (3 seeds quick / 10 seeds extended).
- Canonical JSON `git_sha` matches frozen data commit on `main` (`0f4340c`); README separates raw permutation *p* and Holm-corrected *p*.
- Tests: `test_validate_analysis.py` uses standalone repo root (`parents[1]`, not monorepo path).
- Tags `v1.0.0` / `v1.1.0` / `v1.1.1` on `main` without Cursor co-author.

## [1.1.0] - 2026-05-20

### Added

- Frozen protocol **1.1**: `artifacts/non_oracle_defer_results_2026_05_full_analysis.json` (R=100).
- Analysis pipeline: `merge_experiment_results.py`, `compute_and_plot_results.py`, bootstrap sidecars.
- Sensitivity summary: `artifacts/sensitivity_expert_mode_2026_05.json`.
- `scripts/validate_analysis.py`, `tests/` (7 tests), `REPRODUCE.md`.
- CI: validate JSON + pytest before Docker smoke run.
- Documentation: `docs/PROTOCOL.md`, `docs/ARCHITECTURE.md`, `FAIR_SOFTWARE.md`.
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `Makefile`.

### Changed

- README metrics aligned with analysis JSON (81.29 / 81.05 / 71.87%).
- Removed legacy fix/audit scripts from repository root.

### Removed

- Obsolete manual encoding fix scripts and draft audit guides from public tree.

## [1.0.0] - 2026-05-01

### Added

- Initial simulation, Docker image, and CI workflow (`repro.yml`).
- `CITATION.cff`, MIT `LICENSE`.

[1.1.1]: https://github.com/KonkovaElena/airi-summer-school-2026/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/KonkovaElena/airi-summer-school-2026/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/KonkovaElena/airi-summer-school-2026/releases/tag/v1.0.0
