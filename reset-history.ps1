# reset-history.ps1 — squash all git history into a single commit and force-push.
# ALWAYS sync main with GitHub FIRST: this script force-pushes, so running it on a stale
# clone would permanently discard commits made remotely (e.g. by the ChatGPT scheduled
# task committing via the GitHub connector). If the sync fails, ABORT — never rewrite
# history from a stale or conflicted clone.

git checkout main
if ($LASTEXITCODE -ne 0) { Write-Host "ABORT: cannot switch to main branch." -ForegroundColor Red; exit 1 }

git fetch origin main
if ($LASTEXITCODE -ne 0) { Write-Host "ABORT: git fetch failed - cannot confirm latest remote state." -ForegroundColor Red; exit 1 }

git pull --rebase --autostash origin main
if ($LASTEXITCODE -ne 0) { Write-Host "ABORT: git pull failed - refusing to rewrite history from a stale/conflicted clone. Resolve manually and re-run." -ForegroundColor Red; exit 1 }

Write-Host "OK: main is up to date with origin - proceeding with history reset." -ForegroundColor Green

git checkout --orphan fresh-main
git add -A
git commit -m "Initial commit"
git branch -D main
git branch -m main
git push --force -u origin main
