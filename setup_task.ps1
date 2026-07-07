$ErrorActionPreference = "Stop"

$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "Please run this script as Administrator."
    exit 1
}

$projectDir = $PSScriptRoot
$scriptPath = Join-Path $projectDir "checkin.py"

$venvPython = Join-Path $projectDir ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $pythonExe = $venvPython
} else {
    $pythonExe = "python"
}

if (-not (Test-Path $pythonExe)) {
    Write-Error "Python executable not found: $pythonExe"
    exit 1
}

if (-not (Test-Path $scriptPath)) {
    Write-Error "Checkin script not found: $scriptPath"
    exit 1
}

$envPath = Join-Path $projectDir ".env"
$runTime = "09:00"
if (Test-Path $envPath) {
    $lines = Get-Content $envPath
    foreach ($line in $lines) {
        $trimmed = $line.Trim()
        if ($trimmed -eq "" -or $trimmed.StartsWith("#")) {
            continue
        }
        $parts = $trimmed.Split("=", 2)
        if ($parts.Length -eq 2 -and $parts[0].Trim() -eq "RUN_TIME") {
            $runTime = $parts[1].Trim()
            break
        }
    }
}

if ($runTime -notmatch '^(\d{1,2}):(\d{2})$') {
    throw "Invalid RUN_TIME format: $runTime (expected HH:MM)"
}
$hour = [int]$Matches[1]
$minute = [int]$Matches[2]

if ($hour -lt 0 -or $hour -gt 23) {
    throw "Invalid RUN_TIME hour: $hour (expected 0-23)"
}
if ($minute -lt 0 -or $minute -gt 59) {
    throw "Invalid RUN_TIME minute: $minute (expected 0-59)"
}

$runTime = "{0:D2}:{1:D2}" -f $hour, $minute

$taskName = "RailgunAutoCheckin"

$action = New-ScheduledTaskAction `
    -Execute $pythonExe `
    -Argument "`"$scriptPath`"" `
    -WorkingDirectory $projectDir

$trigger = New-ScheduledTaskTrigger -Daily -At $runTime

$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd

$principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Force

Write-Host "Scheduled task created successfully:"
Write-Host "  Task name: $taskName"
Write-Host "  Run time:  $runTime"
Write-Host "  Project:   $projectDir"
Write-Host "  Python:    $pythonExe"
