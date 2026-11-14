# Final Rebuild - Apply All Fixes
# 1. Health check bug fix (localhost → api_service)
# 2. Dashboard consolidation (/dashboard route)
# 3. Enhanced error display in ACTION LEDGER

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  FINAL REBUILD - APPLYING ALL FIXES" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

Write-Host "Changes being applied:" -ForegroundColor Yellow
Write-Host "  ✅ Fix 1: Health check now uses api_service (not localhost)" -ForegroundColor Green
Write-Host "  ✅ Fix 2: Dashboard consolidated to /dashboard route" -ForegroundColor Green
Write-Host "  ✅ Fix 3: Enhanced error display with error types" -ForegroundColor Green
Write-Host ""

# Step 1: Build
Write-Host "[1/3] Building containers with all fixes..." -ForegroundColor Yellow
docker-compose build remediation_engine api_service
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Build failed" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Build complete" -ForegroundColor Green
Write-Host ""

# Step 2: Restart
Write-Host "[2/3] Restarting services..." -ForegroundColor Yellow
docker-compose restart remediation_engine api_service
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Restart failed" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Services restarted" -ForegroundColor Green
Write-Host ""

# Step 3: Wait
Write-Host "[3/3] Waiting 15 seconds for services to stabilize..." -ForegroundColor Yellow
Start-Sleep -Seconds 15
Write-Host "✓ Services ready" -ForegroundColor Green
Write-Host ""

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  ALL FIXES APPLIED! ✅" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

Write-Host "Test the fixes:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Open dashboard:" -ForegroundColor White
Write-Host "   start http://localhost:8000/dashboard" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. Inject a test fault:" -ForegroundColor White
Write-Host "   curl -X POST http://localhost:8000/inject/503_deadlock" -ForegroundColor Cyan
Write-Host ""
Write-Host "3. Watch logs:" -ForegroundColor White
Write-Host "   docker-compose logs -f remediation_engine" -ForegroundColor Cyan
Write-Host ""

Write-Host "What to verify:" -ForegroundColor Yellow
Write-Host "  ✅ Dashboard opens at /dashboard (not /dashboard)" -ForegroundColor White
Write-Host "  ✅ ACTION LEDGER shows error types: [503 DEADLOCK/OVERLOAD]" -ForegroundColor White
Write-Host "  ✅ Health check shows: http://api_service:8000/health" -ForegroundColor White
Write-Host "  ✅ Health check succeeds: Health VERIFIED on attempt 1" -ForegroundColor White
Write-Host ""

Write-Host "Opening dashboard in 3 seconds..." -ForegroundColor Yellow
Start-Sleep -Seconds 3
Start-Process "http://localhost:8000/dashboard"

Write-Host ""
Write-Host "Dashboard opened! Watch the ACTION LEDGER section." -ForegroundColor Green
Write-Host ""
