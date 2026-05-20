# Verification notes (2026-05-20)

Status of common review findings for the **standalone** repository
`airi-summer-school-2026`. Items that refer to the parent monorepo
(`.github/workflows/experiment-matrix.yml`, `scripts/generate_sbom.sh`) apply
only when working inside the larger `plans` workspace.

| Finding | Priority | Status in this repo |
|---------|----------|-------------------|
| Non-deterministic `pip freeze` hash | High | **Resolved** — `requirements_hash` = SHA-256 of `artifacts/requirements.txt`; see [REPRODUCE.md](../REPRODUCE.md). |
| `pytest` collects foreign tests when run from monorepo root | High | **Mitigated** — `pytest.ini` + `pyproject.toml` set `testpaths = tests`; CI runs `pytest tests`. |
| Large `bootstrap_distribution` inside JSON | Medium | **Resolved** — canonical analysis uses `.npy.gz` sidecars (`include_bootstrap_blobs: false`). |
| `git_sha` = `N/A` treated as valid | Medium | **Mitigated** — frozen JSON uses repo commit `0f4340c`; strict validation rejects `N/A`. |
| Population vs sample standard deviation | Medium | **Consistent** — analysis uses `ddof=1`; merge uses `statistics.stdev` (sample). |
| `installed.txt` path in CI aggregator | Medium | **N/A here** — this repo’s CI does not run the monorepo matrix aggregator. |
| SBOM / cosign signing | Low | **Out of scope** for v1.1.1; optional future work. |
| `datetime.utcnow()` deprecation | Low | **Not present** in current analysis/simulation scripts. |
| Windows hash commands in docs | Low | **Documented** — PowerShell examples in [REPRODUCE.md](../REPRODUCE.md). |

## Recommended local commands

```bash
make verify
# or explicitly:
pytest tests -q
python scripts/verify_release.py
```

When developing inside the parent monorepo, always `cd` into this repository
before running `pytest` or release gates.
