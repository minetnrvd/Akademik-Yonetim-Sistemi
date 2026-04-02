$ErrorActionPreference = 'Stop'

$appPath = Join-Path $PSScriptRoot 'app.py'
$templatesPath = Join-Path $PSScriptRoot 'templates'

if (-not (Test-Path $appPath)) {
    Write-Error "app.py not found"
}

if (-not (Test-Path $templatesPath)) {
    Write-Error "templates folder not found"
}

$app = Get-Content $appPath -Raw
$templates = Get-ChildItem $templatesPath -Filter *.html | Get-Content -Raw

$dictKeys = [System.Collections.Generic.HashSet[string]]::new()
foreach ($m in [regex]::Matches($app, '''([a-z0-9_]+)''\s*:\s*(''([^'']*)''|"([^"]*)")')) {
    [void]$dictKeys.Add($m.Groups[1].Value)
}

$usedTpl = [System.Collections.Generic.HashSet[string]]::new()
foreach ($m in [regex]::Matches($templates, "\bt\('([a-z0-9_]+)'")) {
    [void]$usedTpl.Add($m.Groups[1].Value)
}

$usedApp = [System.Collections.Generic.HashSet[string]]::new()
foreach ($m in [regex]::Matches($app, "_t\('([a-z0-9_]+)'")) {
    [void]$usedApp.Add($m.Groups[1].Value)
}

$allUsed = [System.Collections.Generic.HashSet[string]]::new()
foreach ($k in $usedTpl) { [void]$allUsed.Add($k) }
foreach ($k in $usedApp) { [void]$allUsed.Add($k) }

$missing = $allUsed | Where-Object { -not $dictKeys.Contains($_) } | Sort-Object

# Heuristic: likely hardcoded text node in templates.
$hardcoded = @()
foreach ($file in Get-ChildItem $templatesPath -Filter *.html) {
    $lines = Get-Content $file.FullName
    for ($i = 0; $i -lt $lines.Count; $i++) {
        $line = $lines[$i]
        if ($line -match '>\s*[A-Za-z][^<{]*<' -and $line -notmatch "\bt\('") {
            $hardcoded += "{0}:{1}: {2}" -f $file.Name, ($i + 1), $line.Trim()
        }
    }
}

Write-Host "i18n key count: $($dictKeys.Count)"
Write-Host "used key count: $($allUsed.Count)"
Write-Host "missing key count: $($missing.Count)"

if ($missing.Count -gt 0) {
    Write-Host "\nMissing keys:" -ForegroundColor Yellow
    $missing | ForEach-Object { Write-Host "- $_" }
}

if ($hardcoded.Count -gt 0) {
    Write-Host "\nPotential hardcoded strings:" -ForegroundColor Yellow
    $hardcoded | Select-Object -First 100 | ForEach-Object { Write-Host "- $_" }
}

if ($missing.Count -eq 0) {
    Write-Host "\ni18n check passed." -ForegroundColor Green
    exit 0
}

exit 1
