# Verify All Errors Work Correctly
# Tests each error type and checks the logs for correct behavior

$headers = @{ "Authorization" = "Bearer changeme-local-dev" }

Write-Host "`n═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  VERIFYING ALL 5 ERROR TYPES" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════`n" -ForegroundColor Cyan

# Test 1: 500 CRASH
Write-Host "[1/5] 500 CRASH (Checkout)" -ForegroundColor Yellow
Write-Host "  Expected: Restart container" -ForegroundColor Gray
Invoke-WebRequest -Uri "http://localhost:8000/inject/500_checkout" -Method POST -Headers $headers -UseBasicParsing | Out-Null
Write-Host "  ✓ Injected - waiting 30s..." -ForegroundColor Green
Start-Sleep -Seconds 30
$logs = docker-compose logs --tail=100 remediation_engine | Select-String -Pattern "500 CRASH"
if ($logs) {
    Write-Host "  ✓ Found in logs:" -ForegroundColor Green
    $logs | Select-Object -Last 2 | ForEach-Object { Write-Host "    $($_.Line)" -ForegroundColor Gray }
} else {
    Write-Host "  ✗ NOT found in logs!" -ForegroundColor Red
}
Write-Host ""

# Reset
Invoke-WebRequest -Uri "http://localhost:8000/inject/reset?target=all" -Method POST -Headers $headers -UseBasicParsing | Out-Null
Start-Sleep -Seconds 10

# Test 2: 503 DEADLOCK
Write-Host "[2/5] 503 DEADLOCK (Cart)" -ForegroundColor Yellow
Write-Host "  Expected: Restart container (low CPU)" -ForegroundColor Gray
Invoke-WebRequest -Uri "http://localhost:8000/inject/503_deadlock" -Method POST -Headers $headers -UseBasicParsing | Out-Null
Write-Host "  ✓ Injected - waiting 30s..." -ForegroundColor Green
Start-Sleep -Seconds 30
$logs = docker-compose logs --tail=100 remediation_engine | Select-String -Pattern "503 DEADLOCK"
if ($logs) {
    Write-Host "  ✓ Found in logs:" -ForegroundColor Green
    $logs | Select-Object -Last 2 | ForEach-Object { Write-Host "    $($_.Line)" -ForegroundColor Gray }
} else {
    Write-Host "  ✗ NOT found in logs!" -ForegroundColor Red
}
Write-Host ""

# Reset
Invoke-WebRequest -Uri "http://localhost:8000/inject/reset?target=all" -Method POST -Headers $headers -UseBasicParsing | Out-Null
Start-Sleep -Seconds 10

# Test 3: 503 OVERLOAD
Write-Host "[3/5] 503 OVERLOAD (System-wide)" -ForegroundColor Yellow
Write-Host "  Expected: SUPPRESS restart (high CPU)" -ForegroundColor Gray
Invoke-WebRequest -Uri "http://localhost:8000/inject/503_overload" -Method POST -Headers $headers -UseBasicParsing | Out-Null
Write-Host "  ✓ Injected - waiting 30s..." -ForegroundColor Green
Start-Sleep -Seconds 30
$logs = docker-compose logs --tail=100 remediation_engine | Select-String -Pattern "OVERLOAD|SUPPRESS"
if ($logs) {
    Write-Host "  ✓ Found in logs:" -ForegroundColor Green
    $logs | Select-Object -Last 2 | ForEach-Object { Write-Host "    $($_.Line)" -ForegroundColor Gray }
} else {
    Write-Host "  ✗ NOT found in logs!" -ForegroundColor Red
}
Write-Host ""

# Reset
Invoke-WebRequest -Uri "http://localhost:8000/inject/reset?target=all" -Method POST -Headers $headers -UseBasicParsing | Out-Null
Start-Sleep -Seconds 10

# Test 4: 504 TIMEOUT
Write-Host "[4/5] 504 TIMEOUT (Payment)" -ForegroundColor Yellow
Write-Host "  Expected: Restart container" -ForegroundColor Gray
Invoke-WebRequest -Uri "http://localhost:8000/inject/504_timeout" -Method POST -Headers $headers -UseBasicParsing | Out-Null
Write-Host "  ✓ Injected - waiting 30s..." -ForegroundColor Green
Start-Sleep -Seconds 30
$logs = docker-compose logs --tail=100 remediation_engine | Select-String -Pattern "504 TIMEOUT"
if ($logs) {
    Write-Host "  ✓ Found in logs:" -ForegroundColor Green
    $logs | Select-Object -Last 2 | ForEach-Object { Write-Host "    $($_.Line)" -ForegroundColor Gray }
} else {
    Write-Host "  ✗ NOT found in logs!" -ForegroundColor Red
}
Write-Host ""

# Reset
Invoke-WebRequest -Uri "http://localhost:8000/inject/reset?target=all" -Method POST -Headers $headers -UseBasicParsing | Out-Null
Start-Sleep -Seconds 10

# Test 5: 429 BOT
Write-Host "[5/5] 429 BOT ATTACK (Security)" -ForegroundColor Yellow
Write-Host "  Expected: LOG ONLY (no restart)" -ForegroundColor Gray
Invoke-WebRequest -Uri "http://localhost:8000/inject/429_bot" -Method POST -Headers $headers -UseBasicParsing | Out-Null
Write-Host "  ✓ Injected - waiting 15s..." -ForegroundColor Green
Start-Sleep -Seconds 15
$logs = docker-compose logs --tail=100 remediation_engine | Select-String -Pattern "429|BOT"
if ($logs) {
    Write-Host "  ✓ Found in logs:" -ForegroundColor Green
    $logs | Select-Object -Last 2 | ForEach-Object { Write-Host "    $($_.Line)" -ForegroundColor Gray }
} else {
    Write-Host "  ✗ NOT found in logs!" -ForegroundColor Red
}
Write-Host ""

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  TEST COMPLETE" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Review full logs:" -ForegroundColor Yellow
Write-Host "  docker-compose logs --tail=500 remediation_engine | more" -ForegroundColor Cyan
Write-Host ""
Write-Host "Check dashboard:" -ForegroundColor Yellow
Write-Host "  http://localhost:8000/dashboard" -ForegroundColor Cyan
Write-Host ""
