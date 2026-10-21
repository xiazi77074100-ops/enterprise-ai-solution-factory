# Human time log for the experiment (docs/experiment/preregistration.md §5, M1/M2).
# Run "start" when you begin working yourself and "stop" when you stop; the minutes (rounded up to 5) are written to
# HUMAN_TIME_LOG.csv. Time while only the AI is working and you are away does not count: stop, then start again.
#
#   pwsh scripts/timelog.ps1 start -Arm baseline -Task CR-1 -Activity prompting
#   pwsh scripts/timelog.ps1 stop  -Note "added the anti-social-forces clause"
#   pwsh scripts/timelog.ps1 status
param(
    [Parameter(Mandatory = $true, Position = 0)][ValidateSet("start", "stop", "status")][string]$Command,
    [ValidateSet("baseline", "factory", "shared")][string]$Arm = "factory",
    [string]$Task = "P4",
    [ValidateSet("analysis", "prompting", "code_review", "debugging", "test_design", "integration", "qa", "reporting", "waiting")]
    [string]$Activity = "prompting",
    [string]$Note = "",
    [string]$Person = $env:USERNAME
)
$ErrorActionPreference = "Stop"
$log = Join-Path (Split-Path -Parent $PSScriptRoot) "HUMAN_TIME_LOG.csv"
$state = Join-Path $env:TEMP "easf-timelog.json"

switch ($Command) {
    "start" {
        if (Test-Path $state) { throw "A timer is already running ($((Get-Content $state -Raw))). Run stop first." }
        @{ start = (Get-Date).ToString("o"); arm = $Arm; task = $Task; activity = $Activity } | ConvertTo-Json -Compress |
            Set-Content -Path $state -Encoding utf8
        Write-Host "Started: $Arm / $Task / $Activity at $(Get-Date -Format 'HH:mm')"
    }
    "stop" {
        if (-not (Test-Path $state)) { throw "No timer is running. Run start first." }
        $s = Get-Content $state -Raw | ConvertFrom-Json
        $minutes = [math]::Ceiling(((Get-Date) - [datetime]$s.start).TotalMinutes / 5) * 5
        $date = ([datetime]$s.start).ToString("yyyy-MM-dd")
        $text = ($Note -replace '[,\r\n]', ' ').Trim()
        $line = "$date,$Person,$($s.arm),P4,$($s.task),$($s.activity),$minutes,$text"
        Add-Content -Path $log -Value $line -Encoding utf8
        Remove-Item $state
        Write-Host "Recorded $minutes min: $line"
    }
    "status" {
        if (Test-Path $state) {
            $s = Get-Content $state -Raw | ConvertFrom-Json
            Write-Host "Running since $(([datetime]$s.start).ToString('HH:mm')): $($s.arm) / $($s.task) / $($s.activity)"
        } else { Write-Host "No timer is running." }
    }
}
