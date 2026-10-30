# Register one current-user task on the Windows PC. No passwords, admin elevation,
# firewall changes or immediate service launch. Use -WhatIf to review first.
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('Server', 'Backup')][string]$Kind,
    [string]$LanAddress,
    [string]$BackupAt
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$python = Join-Path $repo '.venv\Scripts\python.exe'
$data = Join-Path $repo 'runtime'
if (-not (Test-Path $python -PathType Leaf)) { throw 'Create the Windows virtual environment first.' }
if (-not (Test-Path (Join-Path $data 'taxi.sqlite3') -PathType Leaf)) { throw 'Restore or provision the database first.' }
$user = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$name = "PROBIX-$Kind"
if (Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue) {
    throw "Task $name already exists. Review it rather than silently replacing it."
}
if ($Kind -eq 'Server') {
    if ($BackupAt) { throw 'BackupAt applies only to Backup tasks.' }
    $script = Join-Path $repo 'scripts\start_pc_server.py'
    $arguments = '"' + $script + '"'
    if ($LanAddress) {
        $ip = [System.Net.IPAddress]::Parse($LanAddress)
        if ($ip.AddressFamily -ne [System.Net.Sockets.AddressFamily]::InterNetwork) { throw 'Use a private IPv4 LAN address.' }
        $arguments += ' --lan-address ' + $ip.ToString()
    }
    if (-not (Test-Path (Join-Path $data 'tools\caddy.exe') -PathType Leaf)) { throw 'Install the verified Windows Caddy binary first.' }
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $user
} else {
    if ($LanAddress) { throw 'LanAddress applies only to Server tasks.' }
    if ($BackupAt -notmatch '^([01][0-9]|2[0-3]):[0-5][0-9]$') { throw 'Supply BackupAt as local PC time HH:mm.' }
    $clock = [DateTime]::ParseExact($BackupAt, 'HH:mm', [Globalization.CultureInfo]::InvariantCulture)
    $trigger = New-ScheduledTaskTrigger -Daily -At ([DateTime]::Today.Add($clock.TimeOfDay))
    $script = Join-Path $repo 'scripts\backup_checkpoint.py'
    $arguments = '"' + $script + '" --source "' + (Join-Path $data 'taxi.sqlite3') + '" --directory "' + (Join-Path $data 'backups\checkpoints') + '"'
}
$action = New-ScheduledTaskAction -Execute $python -Argument $arguments -WorkingDirectory $repo
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero)
if ($PSCmdlet.ShouldProcess($name, "Register current-user $Kind task; no immediate launch")) {
    Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Principal $principal -Settings $settings | Out-Null
    Write-Host "Registered $name. Requires this user to be signed in. Inspect task history and LastTaskResult."
}
