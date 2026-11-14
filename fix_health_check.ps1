# Fix Health Check Issue - FOUND THE BUG!
# inference.py had hardcoded localhost instead of using the environment variable

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  FIXING HEALTH CHECK BUG" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

Write-Host "Bug Found:" -ForegroundColor Red
Write-Host "  remediation_engine/ai/inference.py line 126" -ForegroundColor White
Write-Host "  Had: health_url_template='http://localhost:8000/health'" -ForegroundColor Red
Write-Host "  Fixed: health_url_template=None (uses env var)" -ForegroundColor Green
Write-Host ""

Write-Host "This caused health checks to fail after container restarts" -ForegroundColor Yellow
Write-Host "because 'localhost' inside a container refers to itself," -ForegroundColor Yellow
Write-Host "not the api_service container." -ForegroundColor Yellow
Write-Host ""

# Step 1: Rebuild remediation_engine
Write-Host "[1/3] Rebuilding remediation_engine with fix..." -ForegroundColor Yellow
docker-compose build remediation_engine
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to rebuild" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Rebuild complete" -ForegroundColor Green
Write-Host ""

# Step 2: Rebuild api_service (for dashboard enhancements)
Write-Host "[2/3] Rebuilding api_service with dashboard enhancements..." -ForegroundColor Yellow
docker-compose build api_service
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to rebuild" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Rebuild complete" -ForegroundColor Green
Write-Host ""

# Step 3: Restart services
Write-Host "[3/3] Restarting services..." -ForegroundColor Yellow
docker-compose restart remediation_engine api_service
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to restart" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Services restarted" -ForegroundColor Green
Write-Host ""

# Wait for services to stabilize
Write-Host "Waiting 15 seconds for services to stabilize..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  FIX APPLIED!" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Test the fix:" -ForegroundColor Yellow
Write-Host "  1. Inject a fault:" -ForegroundColor White
Write-Host "     curl -X POST http://localhost:8000/inject/503_deadlock" -ForegroundColor Cyan
Write-Host ""
Write-Host "  2. Watch logs:" -ForegroundColor White
Write-Host "     docker-compose logs -f remediation_engine" -ForegroundColor Cyan
Write-Host ""
Write-Host "  3. You should now see:" -ForegroundColor White
Write-Host "     POST-REMEDIATION: Verifying health at http://api_service:8000/health" -ForegroundColor Green
Write-Host "     POST-REMEDIATION: Health VERIFIED on attempt 1" -ForegroundColor Green
Write-Host ""
Write-Host "     Instead of:" -ForegroundColor White
Write-Host "     POST-REMEDIATION: Verifying health at http://localhost:8000/health" -ForegroundColor Red
Write-Host "     POST-REMEDIATION: Health check attempt 1 failed: Connection refused" -ForegroundColor Red
Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
