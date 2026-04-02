param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('backup', 'restore', 'verify')]
    [string]$Mode,

    [string]$ProjectRoot = '',
    [string]$BackupDir,
    [string]$RestoreDir,
    [switch]$IncludeQrAssets
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if (-not $ProjectRoot) {
    $ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
}

function Get-FileSha256 {
    param([Parameter(Mandatory = $true)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "File not found: $Path"
    }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
}

function New-Backup {
    $timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $backupRoot = Join-Path $ProjectRoot 'backups'
    $targetDir = if ($BackupDir) { $BackupDir } else { Join-Path $backupRoot ("drill_" + $timestamp) }

    $instanceDir = Join-Path $ProjectRoot 'instance'
    $dbPath = Join-Path $instanceDir 'attendance.db'
    if (-not (Test-Path -LiteralPath $dbPath)) {
        throw "Primary DB not found: $dbPath"
    }

    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null

    $dbBackupPath = Join-Path $targetDir 'attendance.db'
    Copy-Item -LiteralPath $dbPath -Destination $dbBackupPath -Force

    $migrationsSrc = Join-Path $ProjectRoot 'migrations'
    if (Test-Path -LiteralPath $migrationsSrc) {
        Copy-Item -LiteralPath $migrationsSrc -Destination (Join-Path $targetDir 'migrations') -Recurse -Force
    }

    if ($IncludeQrAssets.IsPresent) {
        foreach ($relativePath in @('static/qrcodes', 'static/qr_codes')) {
            $src = Join-Path $ProjectRoot $relativePath
            if (Test-Path -LiteralPath $src) {
                $dest = Join-Path $targetDir $relativePath
                New-Item -ItemType Directory -Path (Split-Path -Parent $dest) -Force | Out-Null
                Copy-Item -LiteralPath $src -Destination $dest -Recurse -Force
            }
        }
    }

    $manifestPath = Join-Path $targetDir 'manifest.txt'
    $hash = Get-FileSha256 -Path $dbBackupPath
    $backupTimeUtc = (Get-Date).ToUniversalTime().ToString('o')
    @(
        "backup_time_utc=$backupTimeUtc",
        "project_root=$ProjectRoot",
        "db_file=attendance.db",
        "db_sha256=$hash"
    ) | Set-Content -LiteralPath $manifestPath -Encoding UTF8

    Write-Output "BACKUP_OK $targetDir"
}

function Restore-Backup {
    if (-not $BackupDir) {
        throw 'BackupDir is required for restore mode.'
    }
    if (-not (Test-Path -LiteralPath $BackupDir)) {
        throw "BackupDir not found: $BackupDir"
    }

    $backupDbPath = Join-Path $BackupDir 'attendance.db'
    if (-not (Test-Path -LiteralPath $backupDbPath)) {
        throw "Backup DB not found: $backupDbPath"
    }

    $targetDir = if ($RestoreDir) {
        $RestoreDir
    } else {
        Join-Path $ProjectRoot (Join-Path 'restore_drill' (Split-Path -Leaf $BackupDir))
    }

    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null

    $restoredDbPath = Join-Path $targetDir 'attendance.db'
    Copy-Item -LiteralPath $backupDbPath -Destination $restoredDbPath -Force

    $backupMigrations = Join-Path $BackupDir 'migrations'
    if (Test-Path -LiteralPath $backupMigrations) {
        Copy-Item -LiteralPath $backupMigrations -Destination (Join-Path $targetDir 'migrations') -Recurse -Force
    }

    Write-Output "RESTORE_OK $targetDir"
}

function Verify-Restore {
    if (-not $BackupDir) {
        throw 'BackupDir is required for verify mode.'
    }
    if (-not $RestoreDir) {
        throw 'RestoreDir is required for verify mode.'
    }

    $backupDbPath = Join-Path $BackupDir 'attendance.db'
    $restoredDbPath = Join-Path $RestoreDir 'attendance.db'

    $backupHash = Get-FileSha256 -Path $backupDbPath
    $restoreHash = Get-FileSha256 -Path $restoredDbPath

    if ($backupHash -ne $restoreHash) {
        throw "VERIFY_FAIL Hash mismatch. backup=$backupHash restore=$restoreHash"
    }

    Write-Output "VERIFY_OK backup_sha256=$backupHash"
}

switch ($Mode) {
    'backup' { New-Backup }
    'restore' { Restore-Backup }
    'verify' { Verify-Restore }
    default { throw "Unsupported mode: $Mode" }
}
