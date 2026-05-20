# FAIR software alignment (May 2026)

Checklist based on [TU Delft FAIR software](https://tu-delft-dcc.github.io/docs/software/fair_software/checklist.html) and [The Turing Way — reproducibility](https://book.the-turing-way.org/reproducible-research/reproducible-research.html).

| Practice | Status | Evidence |
|----------|--------|----------|
| Version control (git) | Done | GitHub `main` |
| Public repository | Done | Open MIT repo |
| README | Done | [README.md](README.md) |
| LICENSE | Done | [LICENSE](LICENSE) |
| CITATION.cff | Done | [CITATION.cff](CITATION.cff) + `preferred-citation` (Verma & Nalisnick 2022) |
| Dependency lockfile | Done | `artifacts/requirements.txt` (hashes) |
| Installation / run docs | Done | [REPRODUCE.md](REPRODUCE.md), [artifacts/README.md](artifacts/README.md) |
| Container | Done | [artifacts/Dockerfile](artifacts/Dockerfile) |
| Unit / integration tests | Done | [tests/](tests/) |
| CI | Done | `verify` job (`verify_release`, strict validate, pytest) then `docker-smoke` — [.github/workflows/repro.yml](.github/workflows/repro.yml) |
| Frozen protocol doc | Done | [docs/PROTOCOL.md](docs/PROTOCOL.md) |
| Provenance in analysis JSON | Done | `requirements_hash`, `protocol_version`, `frozen_run_id` |
| CONTRIBUTING + CoC | Done | This repo root |
| DOI (Zenodo) | Planned | [docs/ZENODO.md](docs/ZENODO.md) |
| API reference / Sphinx | N/A | Single-script research artifact |

**Findable:** URL, keywords, CITATION.cff.  
**Accessible:** MIT, standard formats (JSON, CSV, PNG).  
**Interoperable:** JSON metrics; Docker; Python 3.11+.  
**Reusable:** LICENSE, REPRODUCE, pinned deps, tagged releases (see CHANGELOG).
