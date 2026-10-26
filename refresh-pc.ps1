# Refresh the rugby calendar from a home PC, which Gainline does not block like GitHub runners.
# Scheduled every 6 hours by Task Scheduler; GitHub's run stays on as the fallback.
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

function Run {
    & $args[0] $args[1..($args.Count - 1)]
    if ($LASTEXITCODE) { throw "$($args -join ' ') exited with $LASTEXITCODE" }
}

Write-Output "== $(Get-Date -Format o)"
Run git pull --rebase --quiet
Run .venv\Scripts\python.exe merge.py
Run git add rugby.ics status.json sources
git diff --cached --quiet
if ($LASTEXITCODE) {
    Run git commit --quiet -m 'Refresh combined rugby fixtures'
    Run git pull --rebase --quiet
    Run git push --quiet
}
