# TalentDNA — Windows setup (recommended: use a venv)
Set-Location $PSScriptRoot

if (-not (Test-Path .venv)) {
    python -m venv .venv
    Write-Host "Created .venv"
}

.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

Write-Host ""
Write-Host "Done. Activate anytime with: .\.venv\Scripts\Activate.ps1"
Write-Host "Precompute: python scripts/precompute_embeddings.py --candidates data/candidates.jsonl --save-model"
Write-Host "Rank:       python rank.py --candidates candidates.jsonl --out output/submission.csv --validate"
