# Contributing

Thank you for your interest. This repository is primarily a **frozen reproducibility artifact** for AIRI 2026; large protocol changes should be discussed in an issue first.

## Development setup

```bash
git clone https://github.com/KonkovaElena/airi-summer-school-2026.git
cd airi-summer-school-2026
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r artifacts/requirements.txt --require-hashes
pip install pytest numpy scipy
```

## Verify before a PR

```bash
make verify
# or: python scripts/verify_release.py && pytest -q
```

## Commit guidelines

- One logical change per commit.
- If metrics change, update `docs/PROTOCOL.md`, `CHANGELOG.md`, and regenerate `*_full_analysis.json` with documented commands in `REPRODUCE.md`.
- Do not commit application drafts (`AIRI_*.md`) or PDFs.

## Pull requests

- Describe what changed and how you verified it.
- CI must pass (validate + pytest + Docker smoke).

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) and [SECURITY.md](SECURITY.md).
