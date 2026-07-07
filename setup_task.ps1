$ErrorActionPreference = "Stop"

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$scriptPath = Join-Path $projectDir "checkin.py"

$venvPython = Join-Path $projectDir ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $pythonExe = $venvPython
} else {
    $pythonExe = "python"
}

$envPath = Join-Path $projectDir ".env"
$runTime = "09:00"
if (Test-Path $envPath) {
    $lines = Get-Content $envPath
    foreach ($line in $lines) {
        if ($line -match '^RUN_TIME\s*=\s*(.+)$') {
            $runTime = $Matches[1].Trim()
            break
        }
    }
}

if ($runTime -notmatch '^(\d{1,2}):(\d{2})$') {
    throw "Invalid RUN_TIME format: $runTime (expected HH:MM)"
}
$hour = [int]$Matches[1]
$minute = [int]$Matches[2]
$runTime = "{0:D2}:{1:D2}" -f $hour, $minute

$taskName = "RailgunAutoCheckin"

$action = New-ScheduledTaskAction `
    -Execute $pythonExe `
    -Argument "$scriptPath" `
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
