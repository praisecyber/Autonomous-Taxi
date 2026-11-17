# Native Windows PC setup. No accounts, firewall rules, trust-store changes or tasks
# are created. Existing data and Caddy binaries are never silently replaced.
[CmdletBinding()]
param(
    [switch]$DownloadCaddy,
    [string]$RestoreBackup,
    [string]$LanAddress,
    [switch]$Start
)
$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'Run this helper in PowerShell on the Windows server PC.' }
$repo = Split-Path $PSScriptRoot -Parent
Set-Location $repo
$python = Join-Path $repo '.venv\Scripts\python.exe'
$database = Join-Path $repo 'runtime\taxi.sqlite3'
$caddy = Join-Path $repo 'runtime\tools\caddy.exe'
if ($RestoreBackup) {
    $RestoreBackup = (Resolve-Path -LiteralPath $RestoreBackup).Path
    if (-not (Test-Path -LiteralPath $RestoreBackup -PathType Leaf)) { throw 'Backup must be a file.' }
    if (Test-Path -LiteralPath $database) { throw 'Database already exists; restore to a separate directory instead of overwriting it.' }
}
if (-not (Test-Path -LiteralPath $python)) {
    py -3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.12 with the Windows py launcher first.' }
}
& $python -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else 1)'
if ($LASTEXITCODE -ne 0) { throw 'Use a Python 3.12 Windows virtual environment. Existing environments were not deleted.' }
& $python -m pip install -e '.[dev]'
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
if ($DownloadCaddy) {
    if (Test-Path -LiteralPath $caddy) { throw 'Caddy already exists. Verify it manually; this helper will not replace it.' }
    if ($env:PROCESSOR_ARCHITECTURE -ne 'AMD64' -and $env:PROCESSOR_ARCHITEW6432 -ne 'AMD64') {
        throw 'The verified download is Windows x64 only; install a verified matching binary manually on other architectures.'
    }
    $temporary = Join-Path ([IO.Path]::GetTempPath()) ([Guid]::NewGuid().ToString())
    New-Item -ItemType Directory -Path $temporary | Out-Null
    try {
        $archive = Join-Path $temporary 'caddy.zip'
        [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -UseBasicParsing -Uri 'https://github.com/caddyserver/caddy/releases/download/v2.10.2/caddy_2.10.2_windows_amd64.zip' -OutFile $archive
        # Pinned to the official release's published SHA-512 checksum.
        $expected = '88347875f0cd4b5e26bb39cd1f359613f932d54158d560e03244004d1ba6e61aae0cd625ba7c913bd46df096ef973fef2249396b0bb81143414378cb4447aeb8'
        if ((Get-FileHash -LiteralPath $archive -Algorithm SHA512).Hash.ToLowerInvariant() -ne $expected) { throw 'Caddy archive checksum mismatch.' }
        Expand-Archive -LiteralPath $archive -DestinationPath (Join-Path $temporary 'unpacked')
        New-Item -ItemType Directory -Path (Split-Path $caddy -Parent) -Force | Out-Null
        # Exclusive file copy refuses to overwrite a competing new executable.
        [IO.File]::Copy((Join-Path $temporary 'unpacked\caddy.exe'), $caddy, $false)
    } finally {
        Remove-Item -LiteralPath $temporary -Recurse -Force
    }
}
if ($RestoreBackup) {
    & $python -m taxi.manage restore --source $RestoreBackup --output $database
    if ($LASTEXITCODE -ne 0) { throw 'Restore failed; original backup was preserved.' }
}
if (-not (Test-Path -LiteralPath $database)) {
    throw 'Original database is missing. Re-run with -RestoreBackup pointing to your protected taxi backup. No replacement accounts were created.'
}
$arguments = @((Join-Path $repo 'scripts\start_pc_server.py'))
if ($LanAddress) { $arguments += @('--lan-address', $LanAddress) }
& $python @arguments --check
if ($LASTEXITCODE -ne 0) { throw 'PC preflight failed. Resolve it before starting.' }
Write-Host 'Dependencies and preflight are ready. Verify private data, LAN client trust and firewall scope on this PC.'
if ($Start) {
    & $python @arguments
    if ($LASTEXITCODE -ne 0) { throw 'PC server exited with an error; inspect runtime\tls-pc logs.' }
} else {
    Write-Host 'Server not started. Re-run this helper with -Start after reviewing the settings.'
}
