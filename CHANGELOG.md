# Changelog

All notable changes to this repository are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and [Semantic Versioning](https://semver.org/).

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

[1.1.0]: https://github.com/KonkovaElena/airi-summer-school-2026/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/KonkovaElena/airi-summer-school-2026/releases/tag/v1.0.0
