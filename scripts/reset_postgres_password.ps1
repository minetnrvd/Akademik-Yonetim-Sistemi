# PostgreSQL postgres kullanıcısı şifre sıfırlama scripti
# Admin olarak çalıştırılmalıdır

$pgBin  = "C:\Program Files\PostgreSQL\18\bin"
$pgData = "C:\Program Files\PostgreSQL\18\data"
$svcName = "postgresql-x64-18"
$hbaFile = "$pgData\pg_hba.conf"
$hbaBackup = "$pgData\pg_hba.conf.bak"

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "HATA: Admin olarak calistirin!" -ForegroundColor Red
    exit 1
}

Write-Host "=== PostgreSQL Sifre Sifirlama ===" -ForegroundColor Cyan

# 1. Yeni şifre al
$password = Read-Host "Yeni sifre girin (ornek: Emine-8829)" -AsSecureString
$plainPw = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($password)
)

# 2. pg_hba.conf yedekle ve trust moduna al
Write-Host "`nAdim 1: pg_hba.conf gecici trust moduna aliniyor..." -ForegroundColor Cyan
Copy-Item $hbaFile $hbaBackup -Force
$hbaContent = Get-Content $hbaFile
$trustContent = $hbaContent -replace 'scram-sha-256', 'trust'
$trustContent | Set-Content $hbaFile -Encoding UTF8
Write-Host "pg_hba.conf yedeklendi ve trust moduna alindi." -ForegroundColor Green

# 3. Servisi yeniden başlat
Write-Host "`nAdim 2: Servis yeniden baslatiliyor..." -ForegroundColor Cyan
Restart-Service $svcName -Force
Start-Sleep -Seconds 3
Write-Host "Servis yeniden basladi." -ForegroundColor Green

# 4. Şifreyi güncelle
Write-Host "`nAdim 3: Sifre guncelleniyor..." -ForegroundColor Cyan
$sqlCmd = "ALTER USER postgres WITH PASSWORD '$plainPw';"
$result = & "$pgBin\psql.exe" -U postgres -h localhost -p 5432 -d postgres -c $sqlCmd 2>&1
Write-Host $result

if ($result -like "*ALTER ROLE*") {
    Write-Host "Sifre basariyla guncellendi!" -ForegroundColor Green
} else {
    Write-Host "UYARI: Sifre guncellemesi beklenmedik cevap: $result" -ForegroundColor Yellow
}

# 5. pg_hba.conf'u geri yükle (scram-sha-256)
Write-Host "`nAdim 4: pg_hba.conf orijinal haline getiriliyor..." -ForegroundColor Cyan
Copy-Item $hbaBackup $hbaFile -Force
Write-Host "pg_hba.conf geri yuklendi." -ForegroundColor Green

# 6. Servisi yeniden başlat
Write-Host "`nAdim 5: Servis son kez yeniden baslatiliyor..." -ForegroundColor Cyan
Restart-Service $svcName -Force
Start-Sleep -Seconds 3

# 7. Doğrulama
Write-Host "`n=== Dogrulama ===" -ForegroundColor Cyan
$env:PGPASSWORD = $plainPw
$test = & "$pgBin\psql.exe" -U postgres -h localhost -p 5432 -d postgres -c "SELECT current_user, version();" 2>&1
$env:PGPASSWORD = ""
Write-Host $test

if ($test -like "*postgres*") {
    Write-Host "`nBAGLANTI BASARILI! PostgreSQL hazir." -ForegroundColor Green
    Write-Host "URL: postgresql://postgres:SIFRENIZ@localhost:5432/attendance_prod" -ForegroundColor Yellow
} else {
    Write-Host "`nBAGLANTI HATASI. Cikti: $test" -ForegroundColor Red
}
