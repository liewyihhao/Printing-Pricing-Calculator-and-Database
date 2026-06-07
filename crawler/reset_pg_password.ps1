# Resets the PostgreSQL 'postgres' superuser password on the local PG 18 instance.
# Run this in an ELEVATED PowerShell (Run as Administrator).
#
# It: backs up pg_hba.conf -> temporarily allows local trust auth -> sets a new
# password -> ALWAYS restores the original secure pg_hba.conf -> updates .env.
#
# New password set by this script:
$NewPassword = "Printoka#2026"

$ErrorActionPreference = "Stop"

# --- Guard: must be elevated, or we do nothing at all. ---
$isAdmin = ([Security.Principal.WindowsPrincipal] `
    [Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host ""
    Write-Host "NOT RUNNING AS ADMINISTRATOR." -ForegroundColor Red
    Write-Host "This window is a normal PowerShell. Close it and open an ELEVATED one:" -ForegroundColor Yellow
    Write-Host "  1. Press the Windows key, type:  powershell" -ForegroundColor Yellow
    Write-Host "  2. RIGHT-CLICK 'Windows PowerShell' -> 'Run as administrator' -> Yes" -ForegroundColor Yellow
    Write-Host "  3. The title bar must read 'Administrator: Windows PowerShell'" -ForegroundColor Yellow
    Write-Host "  4. Re-run the same command." -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

$Bin     = "C:\Program Files\PostgreSQL\18\bin"
$Data    = "C:\Program Files\PostgreSQL\18\data"
$Service = "postgresql-x64-18"
$Hba     = Join-Path $Data "pg_hba.conf"
$Backup  = Join-Path $Data "pg_hba.conf.printoka.bak"
$EnvFile = "C:\Users\User\OneDrive\Desktop\Printoka.com\crawler\.env"
$Psql    = Join-Path $Bin "psql.exe"

Write-Host "1/6 Backing up pg_hba.conf..." -ForegroundColor Cyan
Copy-Item $Hba $Backup -Force

try {
    Write-Host "2/6 Temporarily enabling local trust auth..." -ForegroundColor Cyan
    (Get-Content $Hba) -replace 'scram-sha-256', 'trust' | Set-Content $Hba -Encoding ascii
    Restart-Service $Service -Force
    Start-Sleep -Seconds 4

    Write-Host "3/6 Setting new password for 'postgres'..." -ForegroundColor Cyan
    $env:PGPASSWORD = ""
    & $Psql -U postgres -h 127.0.0.1 -d postgres -c "ALTER USER postgres PASSWORD '$NewPassword';"
    if ($LASTEXITCODE -ne 0) { throw "ALTER USER failed (exit $LASTEXITCODE)" }
}
finally {
    Write-Host "4/6 Restoring secure pg_hba.conf..." -ForegroundColor Cyan
    Copy-Item $Backup $Hba -Force
    Restart-Service $Service -Force
    Start-Sleep -Seconds 4
}

Write-Host "5/6 Verifying new password..." -ForegroundColor Cyan
$env:PGPASSWORD = $NewPassword
& $Psql -U postgres -h 127.0.0.1 -d postgres -c "SELECT 'password reset OK' AS result;"
if ($LASTEXITCODE -ne 0) { throw "Verification failed - new password did not work." }

Write-Host "6/6 Writing password into .env..." -ForegroundColor Cyan
if (Test-Path $EnvFile) {
    $content = Get-Content $EnvFile
    if ($content -match '^PGPASSWORD=') {
        $content = $content -replace '^PGPASSWORD=.*', "PGPASSWORD=$NewPassword"
    } else {
        $content += "PGPASSWORD=$NewPassword"
    }
    $content | Set-Content $EnvFile -Encoding utf8
}

Write-Host ""
Write-Host "DONE. postgres password is now: $NewPassword" -ForegroundColor Green
Write-Host "It has been written to crawler\.env. You can now return to Claude." -ForegroundColor Green
