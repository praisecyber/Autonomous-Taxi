$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw 'Install Node.js 22+ for the frontend.' }
py -3.10 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw 'Python 3.10 is required for this helper. Check py --list.' }
& .\.venv\Scripts\python.exe -m pip install -e '.[dev]'
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
Write-Host 'Backend terminal: .\.venv\Scripts\python.exe -m taxi'
Write-Host 'Frontend terminal: node frontend/server.mjs'
Write-Host 'Open the frontend on port 3000; backend API listens on port 8000.'
