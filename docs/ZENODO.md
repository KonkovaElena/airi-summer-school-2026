# Archiving on Zenodo (recommended)

GitHub alone is not a long-term archive. For citable releases:

1. Enable [Zenodo–GitHub integration](https://docs.github.com/en/archiving-a-github-repository/referencing-and-citing-content) for `KonkovaElena/airi-summer-school-2026`.
2. Create a GitHub Release `v1.1.0` matching [CHANGELOG.md](../CHANGELOG.md).
3. Zenodo will mint a **DOI**; add it to `CITATION.cff`:

```yaml
doi: 10.5281/zenodo.XXXXXXX
```

4. Cite: software (this repo) + [Verma & Nalisnick, ICML 2022](https://arxiv.org/abs/2202.03673) as in `preferred-citation`.

Until DOI exists, cite the repository URL and commit SHA:

`https://github.com/KonkovaElena/airi-summer-school-2026/tree/<commit-sha>`
