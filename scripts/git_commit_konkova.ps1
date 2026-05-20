# Single-author commit helper (rejects Co-authored-by trailers). Usage:
#   powershell -File scripts/git_commit_konkova.ps1 -Message "fix(ci): ..."
param([Parameter(Mandatory = $true)][string]$Message)

$env:GIT_AUTHOR_NAME = "KonkovaElena"
$env:GIT_COMMITTER_NAME = "KonkovaElena"
$env:GIT_AUTHOR_EMAIL = "KonkovaElena@users.noreply.github.com"
$env:GIT_COMMITTER_EMAIL = "KonkovaElena@users.noreply.github.com"

$msgFile = Join-Path $env:TEMP ("gitmsg_{0}.txt" -f [guid]::NewGuid().ToString("N"))
[System.IO.File]::WriteAllText($msgFile, $Message.TrimEnd() + "`n", [System.Text.UTF8Encoding]::new($false))
try {
    & git.exe commit -F $msgFile --no-verify
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $body = & git.exe log -1 --format="%B"
    if ($body -match "Co-authored-by:") {
        Write-Error "Co-authored-by trailer detected; aborting."
        exit 1
    }
    Write-Host "OK:" (& git.exe log -1 --oneline)
} finally {
    Remove-Item -Force $msgFile -ErrorAction SilentlyContinue
}
