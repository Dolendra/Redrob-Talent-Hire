# Helper script to run the Streamlit app with OpenBLAS environment variables configured.
# This prevents "OpenBLAS error: Memory allocation still failed after 10 retries, giving up" on Windows.

Write-Host "Configuring OpenBLAS/OMP thread limits for Windows..." -ForegroundColor Cyan
$env:OPENBLAS_NUM_THREADS = "1"
$env:OMP_NUM_THREADS = "1"
$env:MKL_NUM_THREADS = "1"
$env:NUMEXPR_NUM_THREADS = "1"

if (Test-Path .venv) {
    Write-Host "Activating virtual environment (.venv)..." -ForegroundColor Cyan
    . .\.venv\Scripts\Activate.ps1
} else {
    Write-Host "Warning: .venv not found. Running with global python/streamlit." -ForegroundColor Yellow
}

Write-Host "Starting Streamlit..." -ForegroundColor Green
streamlit run app.py
