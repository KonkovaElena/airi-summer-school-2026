# Publish GitHub Release for an existing tag (requires GITHUB_TOKEN or gh CLI).
param(
    [string]$Tag = "v1.1.1",
    [string]$Repo = "KonkovaElena/airi-summer-school-2026"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$title = "$Tag — CI gates, provenance, frozen metrics (R=100)"
$body = @"
## Summary

- CI ``verify``: ``verify_release.py``, strict ``validate_analysis``, ``pytest`` (Python 3.13), then Docker smoke.
- Frozen metrics: protocol 1.1, canonical JSON ``artifacts/non_oracle_defer_results_2026_05_full_analysis.json``.
- Calibrated vs naive: **+0.24 pp** (95% CI [0.15, 0.33]; paired permutation *p* < 0.0001; Holm *p* < 0.001).

| Policy | Accuracy | Review rate |
|--------|----------|-------------|
| Calibrated deferral | 81.29% | 33.96% |
| Naive threshold | 81.05% | 34.92% |
| Model only | 71.87% | 0% |
| Always review | 87.52% | 100% |

Synthetic research code only — not clinical software. See [REPRODUCE.md](REPRODUCE.md).
"@

$gh = Get-Command gh -ErrorAction SilentlyContinue
if ($gh) {
    gh release create $Tag --repo $Repo --title $title --notes $body
    Write-Host "OK: release created via gh for $Tag"
    exit 0
}

$token = $env:GITHUB_TOKEN
if (-not $token) { $token = $env:GH_TOKEN }
if (-not $token) {
    Write-Error "Set GITHUB_TOKEN (repo scope) or install GitHub CLI (gh)."
}

$payload = @{
    tag_name = $Tag
    name = $title
    body = $body
    draft = $false
    prerelease = $false
    generate_release_notes = $false
} | ConvertTo-Json

$headers = @{
    Authorization = "Bearer $token"
    Accept = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2022-11-28"
}

Invoke-RestMethod -Method Post -Uri "https://api.github.com/repos/$Repo/releases" `
    -Headers $headers -Body $payload -ContentType "application/json; charset=utf-8"
Write-Host "OK: release created via API for $Tag"
