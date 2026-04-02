# PostgreSQL 18 - Eksik initdb ve servis kurulum düzeltmesi
# Bu script Admin olarak çalıştırılmalıdır

$pgBin  = "C:\Program Files\PostgreSQL\18\bin"
$pgData = "C:\Program Files\PostgreSQL\18\data"
$svcName = "postgresql-x64-18"
$svcUser = "NT AUTHORITY\NetworkService"
$pwFile  = "$env:TEMP\pg_pw_temp.txt"

Write-Host "=== PostgreSQL 18 Kurulum Düzeltme ===" -ForegroundColor Cyan

# 1. Admin kontrolü
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "HATA: Bu script Admin olarak çalıştırılmalıdır!" -ForegroundColor Red
    Write-Host "Çözüm: PowerShell'i sağ tık -> 'Yönetici olarak çalıştır' ile açın ve tekrar çalıştırın." -ForegroundColor Yellow
    exit 1
}

# 2. Şifreyi oku
$password = Read-Host "PostgreSQL postgres kullanıcısının şifresi" -AsSecureString
$plainPw = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($password)
)

# 3. Geçici şifre dosyası oluştur
$plainPw | Out-File -FilePath $pwFile -Encoding ascii -NoNewline
Write-Host "Şifre dosyası olusturuldu." -ForegroundColor Gray

# 4. Data dizini kontrolü - boşsa temizle
$existing = Get-ChildItem $pgData -Force -ErrorAction SilentlyContinue
if ($existing.Count -gt 0) {
    Write-Host "UYARI: Data dizini boş değil ($($existing.Count) öğe). Temizleniyor..." -ForegroundColor Yellow
    Remove-Item "$pgData\*" -Recurse -Force -ErrorAction SilentlyContinue
}

# 5. initdb - veritabanını başlat
Write-Host "`nAdım 1: Veritabanı başlatılıyor (initdb)..." -ForegroundColor Cyan
$initResult = & "$pgBin\initdb.exe" `
    -D $pgData `
    -U postgres `
    --pwfile=$pwFile `
    -E UTF8 `
    --locale=Turkish_Turkey.1254 `
    --auth-local=scram-sha-256 `
    --auth-host=scram-sha-256 2>&1

if ($LASTEXITCODE -ne 0) {
    # Locale hatası olabilir, UTF-8 ile tekrar dene
    Write-Host "Türkçe locale hatası, standart locale ile tekrar deneniyor..." -ForegroundColor Yellow
    $initResult = & "$pgBin\initdb.exe" `
        -D $pgData `
        -U postgres `
        --pwfile=$pwFile `
        -E UTF8 `
        --locale=en_US.UTF-8 `
        --auth-local=scram-sha-256 `
        --auth-host=scram-sha-256 2>&1
}

Write-Host $initResult

if ($LASTEXITCODE -ne 0) {
    Remove-Item $pwFile -Force -ErrorAction SilentlyContinue
    Write-Host "`nHATA: initdb başarısız oldu!" -ForegroundColor Red
    exit 1
}
Write-Host "Adım 1 TAMAM: Veritabanı başlatıldı." -ForegroundColor Green

# 6. Geçici şifre dosyasını sil
Remove-Item $pwFile -Force -ErrorAction SilentlyContinue

# 7. NetworkService için data dizini izinleri
Write-Host "`nAdım 2: Servis hesabı izinleri ayarlanıyor..." -ForegroundColor Cyan
$acl = Get-Acl $pgData
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
    "NT AUTHORITY\NetworkService", "FullControl", "ContainerInherit,ObjectInherit", "None", "Allow"
)
$acl.SetAccessRule($rule)
Set-Acl $pgData $acl
Write-Host "Adım 2 TAMAM: İzinler ayarlandı." -ForegroundColor Green

# 8. Servisi kaydet
Write-Host "`nAdım 3: Windows servisi kaydediliyor..." -ForegroundColor Cyan
$regResult = & "$pgBin\pg_ctl.exe" register `
    -N $svcName `
    -U $svcUser `
    -D $pgData `
    -w 2>&1
Write-Host $regResult

if ($LASTEXITCODE -ne 0) {
    Write-Host "UYARI: Servis kaydı başarısız. Manuel başlatma denenecek." -ForegroundColor Yellow
} else {
    Write-Host "Adım 3 TAMAM: Servis kaydedildi." -ForegroundColor Green
}

# 9. Servisi başlat
Write-Host "`nAdım 4: Servis başlatılıyor..." -ForegroundColor Cyan
try {
    Start-Service $svcName -ErrorAction Stop
    Write-Host "Adım 4 TAMAM: Servis başlatıldı." -ForegroundColor Green
} catch {
    Write-Host "Servis ile başlatma başarısız, pg_ctl ile deneniyor..." -ForegroundColor Yellow
    $startResult = & "$pgBin\pg_ctl.exe" start -D $pgData -w 2>&1
    Write-Host $startResult
}

# 10. Doğrulama
Start-Sleep -Seconds 3
Write-Host "`n=== Doğrulama ===" -ForegroundColor Cyan
$svc = Get-Service $svcName -ErrorAction SilentlyContinue
if ($svc -and $svc.Status -eq 'Running') {
    Write-Host "SERVIS: CALISIYOR ($svcName)" -ForegroundColor Green
} else {
    Write-Host "SERVIS: CALISMIYOR veya BULUNAMADI" -ForegroundColor Red
}

Write-Host "`n=== Kurulum Tamamlandi ===" -ForegroundColor Cyan
Write-Host "Baglanti bilgileri:" -ForegroundColor White
Write-Host "  Host    : localhost" -ForegroundColor White
Write-Host "  Port    : 5432" -ForegroundColor White
Write-Host "  Kullanici: postgres" -ForegroundColor White
Write-Host "  URL     : postgresql://postgres:SIFRENIZ@localhost:5432/attendance_prod" -ForegroundColor Yellow
Write-Host "`nSonraki adim: attendance_prod veritabanini olusturun:" -ForegroundColor Cyan
Write-Host "  & '$pgBin\psql.exe' -U postgres -h localhost -c ""CREATE DATABASE attendance_prod;""" -ForegroundColor White
