$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
py -3.10 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw 'Python 3.10 is required for this helper. Check py --list.' }
& .\.venv\Scripts\python.exe -m pip install -e '.[dev]'
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
Write-Host 'Setup complete. Run: .\.venv\Scripts\python.exe -m taxi'
