# Test All Error Types
# Verifies each error type has correct logic and remediation

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  TESTING ALL ERROR TYPES" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$headers = @{ "Authorization" = "Bearer changeme-local-dev" }

# Test 1: 500 Crash
Write-Host "[1/5] Testing 500 CRASH..." -ForegroundColor Yellow
Write-Host "  Expected: Restart container (state corruption)" -ForegroundColor Gray
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/inject/500_checkout" -Method POST -Headers $headers -UseBasicParsing
    Write-Host "  ✓ Fault injected" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Failed: $_" -ForegroundColor Red
}
Write-Host "  Waiting 30 seconds for remediation..." -ForegroundColor Gray
Start-Sleep -Seconds 30
Write-Host ""

# Test 2: 503 Deadlock
Write-Host "[2/5] Testing 503 DEADLOCK..." -ForegroundColor Yellow
Write-Host "  Expected: Restart container (low CPU = deadlock)" -ForegroundColor Gray
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/inject/503_deadlock" -Method POST -Headers $headers -UseBasicParsing
    Write-Host "  ✓ Fault injected" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Failed: $_" -ForegroundColor Red
}
Write-Host "  Waiting 30 seconds for remediation..." -ForegroundColor Gray
Start-Sleep -Seconds 30
Write-Host ""

# Test 3: 503 Overload
Write-Host "[3/5] Testing 503 OVERLOAD..." -ForegroundColor Yellow
Write-Host "  Expected: SUPPRESS restart (high CPU = needs scaling)" -ForegroundColor Gray
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/inject/503_overload" -Method POST -Headers $headers -UseBasicParsing
    Write-Host "  ✓ Fault injected" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Failed: $_" -ForegroundColor Red
}
Write-Host "  Waiting 30 seconds for AI analysis..." -ForegroundColor Gray
Start-Sleep -Seconds 30
Write-Host ""

# Test 4: 504 Timeout
Write-Host "[4/5] Testing 504 TIMEOUT..." -ForegroundColor Yellow
Write-Host "  Expected: Restart container (clear connections)" -ForegroundColor Gray
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/inject/504_timeout" -Method POST -Headers $headers -UseBasicParsing
    Write-Host "  ✓ Fault injected" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Failed: $_" -ForegroundColor Red
}
Write-Host "  Waiting 30 seconds for remediation..." -ForegroundColor Gray
Start-Sleep -Seconds 30
Write-Host ""

# Test 5: 429 Bot Attack
Write-Host "[5/5] Testing 429 BOT ATTACK..." -ForegroundColor Yellow
Write-Host "  Expected: LOG ONLY (no restart needed)" -ForegroundColor Gray
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/inject/429_bot" -Method POST -Headers $headers -UseBasicParsing
    Write-Host "  ✓ Fault injected" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Failed: $_" -ForegroundColor Red
}
Write-Host "  Waiting 10 seconds..." -ForegroundColor Gray
Start-Sleep -Seconds 10
Write-Host ""

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  ALL TESTS COMPLETE" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

Write-Host "Review the logs to verify correct behavior:" -ForegroundColor Yellow
Write-Host "  docker-compose logs --tail=200 remediation_engine" -ForegroundColor Cyan
Write-Host ""

Write-Host "What to look for:" -ForegroundColor Yellow
Write-Host "  ✓ [500 CRASH] → ACTION: Restarting" -ForegroundColor White
Write-Host "  ✓ [503 DEADLOCK/OVERLOAD] (low CPU) → ACTION: Restarting" -ForegroundColor White
Write-Host "  ✓ [503 DEADLOCK/OVERLOAD] (high CPU) → SUPPRESS restart" -ForegroundColor White
Write-Host "  ✓ [504 TIMEOUT] → ACTION: Restarting" -ForegroundColor White
Write-Host "  ✓ [429 BOT ATTACK] → LOG ONLY" -ForegroundColor White
Write-Host "  ✓ Health VERIFIED on attempt 1 (for restarts)" -ForegroundColor White
Write-Host ""

Write-Host "Check dashboard:" -ForegroundColor Yellow
Write-Host "  http://localhost:8000/dashboard" -ForegroundColor Cyan
Write-Host "  Look at ACTION LEDGER for error types and actions" -ForegroundColor Gray
Write-Host ""
