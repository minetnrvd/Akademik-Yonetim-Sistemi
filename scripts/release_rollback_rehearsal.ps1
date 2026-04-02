param(
    [string]$ProjectRoot = '',
    [switch]$IncludeQrAssets,
    [double]$UatAvgThresholdMs = 8.0
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if (-not $ProjectRoot) {
    $ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
}

$scriptBackup = Join-Path $ProjectRoot 'scripts\backup_restore_drill.ps1'
$scriptUat = Join-Path $ProjectRoot 'scripts\uat_checklist.py'
$testFile = Join-Path $ProjectRoot 'tests\test_permissions.py'
$pythonExe = Join-Path $ProjectRoot '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $scriptBackup)) { throw "Missing script: $scriptBackup" }
if (-not (Test-Path -LiteralPath $scriptUat)) { throw "Missing script: $scriptUat" }
if (-not (Test-Path -LiteralPath $testFile)) { throw "Missing test file: $testFile" }
if (-not (Test-Path -LiteralPath $pythonExe)) { throw "Missing Python executable: $pythonExe" }

$reportDir = Join-Path $ProjectRoot 'project_notes\release'
New-Item -ItemType Directory -Path $reportDir -Force | Out-Null
$stamp = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH-mm-ssZ')
$reportPath = Join-Path $reportDir ("release_rollback_rehearsal_" + $stamp + ".json")

$result = [ordered]@{
    started_at_utc = (Get-Date).ToUniversalTime().ToString('o')
    status = 'running'
    steps = @()
}

function Add-Step {
    param(
        [string]$Name,
        [bool]$Passed,
        [string]$Detail
    )
    $script:result.steps += [ordered]@{
        name = $Name
        passed = $Passed
        detail = $Detail
    }
}

function Invoke-AndCapture {
    param(
        [string]$Name,
        [string]$Command
    )

    $prevErrorAction = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $output = Invoke-Expression "$Command 2>&1" | ForEach-Object { "$_" } | Out-String
    $exitCode = 0
    if (Get-Variable -Name LASTEXITCODE -Scope Global -ErrorAction SilentlyContinue) {
        $exitCode = $global:LASTEXITCODE
    }
    $ErrorActionPreference = $prevErrorAction
    return [ordered]@{ name = $Name; output = $output.Trim(); exit_code = $exitCode }
}

try {
    $backupCmd = "& `"$scriptBackup`" -Mode backup -ProjectRoot `"$ProjectRoot`"" + ($(if ($IncludeQrAssets.IsPresent) { ' -IncludeQrAssets' } else { '' }))
    $backupRun = Invoke-AndCapture -Name 'backup' -Command $backupCmd

    if ($backupRun.exit_code -ne 0 -or -not ($backupRun.output -match 'BACKUP_OK\s+(.+)$')) {
        Add-Step -Name 'Backup creation' -Passed $false -Detail $backupRun.output
        throw 'Backup step failed.'
    }

    $backupDir = $Matches[1].Trim()
    Add-Step -Name 'Backup creation' -Passed $true -Detail "backup_dir=$backupDir"

    $releaseTestCmd = "& `"$pythonExe`" -m unittest `"$testFile`""
    $releaseTestRun = Invoke-AndCapture -Name 'release_tests' -Command $releaseTestCmd
    $testsPassed = ($releaseTestRun.exit_code -eq 0)
    Add-Step -Name 'Release regression tests' -Passed $testsPassed -Detail $releaseTestRun.output
    if (-not $testsPassed) { throw 'Regression tests failed during rehearsal.' }

    $uatCmd = "& `"$pythonExe`" `"$scriptUat`" --avg-threshold-ms $UatAvgThresholdMs"
    $uatRun = Invoke-AndCapture -Name 'release_uat' -Command $uatCmd
    $uatPassed = ($uatRun.exit_code -eq 0 -and $uatRun.output -match 'Pass rate:\s+\d+/\d+')
    Add-Step -Name 'Release UAT smoke' -Passed $uatPassed -Detail $uatRun.output
    if (-not $uatPassed) { throw 'UAT smoke failed during rehearsal.' }

    $restoreCmd = "& `"$scriptBackup`" -Mode restore -ProjectRoot `"$ProjectRoot`" -BackupDir `"$backupDir`""
    $restoreRun = Invoke-AndCapture -Name 'rollback_restore' -Command $restoreCmd
    if ($restoreRun.exit_code -ne 0 -or -not ($restoreRun.output -match 'RESTORE_OK\s+(.+)$')) {
        Add-Step -Name 'Rollback restore' -Passed $false -Detail $restoreRun.output
        throw 'Restore step failed.'
    }

    $restoreDir = $Matches[1].Trim()
    Add-Step -Name 'Rollback restore' -Passed $true -Detail "restore_dir=$restoreDir"

    $verifyCmd = "& `"$scriptBackup`" -Mode verify -ProjectRoot `"$ProjectRoot`" -BackupDir `"$backupDir`" -RestoreDir `"$restoreDir`""
    $verifyRun = Invoke-AndCapture -Name 'rollback_verify' -Command $verifyCmd
    $verifyPassed = ($verifyRun.exit_code -eq 0 -and $verifyRun.output -match 'VERIFY_OK')
    Add-Step -Name 'Rollback verify hash' -Passed $verifyPassed -Detail $verifyRun.output
    if (-not $verifyPassed) { throw 'Rollback verification failed.' }

    $result.status = 'ok'
}
catch {
    if ($result.status -ne 'ok') {
        $result.status = 'failed'
    }
    $result.error = $_.Exception.Message
}
finally {
    $result.finished_at_utc = (Get-Date).ToUniversalTime().ToString('o')
    $json = $result | ConvertTo-Json -Depth 6
    Set-Content -LiteralPath $reportPath -Value $json -Encoding UTF8
    Write-Output "REHEARSAL_REPORT $reportPath"
    Write-Output "REHEARSAL_STATUS $($result.status)"
}

if ($result.status -ne 'ok') {
    exit 1
}
