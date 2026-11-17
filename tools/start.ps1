$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path -LiteralPath '.env')) {
    Copy-Item -LiteralPath '.env.example' -Destination '.env'
}
python manage.py migrate
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python manage.py seed_demo
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if (-not (Test-Path -LiteralPath 'evaluation/results.json')) {
    python manage.py evaluate
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
Write-Host 'RiskOps em http://127.0.0.1:8000 | demo / DEMO_PASSWORD (padrão: demo-local-2026)'
python manage.py runserver 127.0.0.1:8000
