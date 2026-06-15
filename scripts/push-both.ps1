# Push to GitHub AND HuggingFace Space
# Usage: .\scripts\push-both.ps1 "your commit message"

param(
    [string]$Message = "Update Redrob-Talent-Hire"
)

Set-Location $PSScriptRoot\..

$status = git status --porcelain
if (-not $status) {
    Write-Host "Nothing to commit."
} else {
    git add -A
    git commit -m $Message
}

Write-Host "Pushing to GitHub (origin)..."
git push origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host "GitHub push failed. Check: git remote -v" -ForegroundColor Red
    exit 1
}

Write-Host "Pushing to HuggingFace Space (hf)..."
git push hf main
if ($LASTEXITCODE -ne 0) {
    Write-Host "HF push failed. You may need: huggingface-cli login" -ForegroundColor Yellow
    exit 1
}

Write-Host "Done. GitHub + HF Space updated." -ForegroundColor Green
