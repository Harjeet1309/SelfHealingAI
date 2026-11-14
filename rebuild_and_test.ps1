# Rebuild and Test Script
Write-Host "`n🔧 Rebuilding services with fixes..." -ForegroundColor Cyan

# Rebuild both services
docker-compose up -d --build api_service remediation_engine

Write-Host "`n⏳ Waiting for services to stabilize..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

Write-Host "`n✅ Services rebuilt. Ready to test!`n" -ForegroundColor Green

Write-Host "Test Steps:" -ForegroundColor Cyan
Write-Host "1. Inject fault: http://localhost:8000/dashboard → Click 'Execute Deadlock'" -ForegroundColor White
Write-Host "2. Trigger error: http://localhost:8000/ → Click 'Acquire Item'" -ForegroundColor White
Write-Host "3. Site should show 503 error and STAY broken" -ForegroundColor White
Write-Host "4. Wait 10-30 seconds for AI detection" -ForegroundColor White
Write-Host "5. Watch logs: docker logs remediation_engine --tail 20 -f" -ForegroundColor White
Write-Host "6. Site should recover ONLY after AI restart + health verification`n" -ForegroundColor White

Write-Host "Expected log sequence:" -ForegroundColor Yellow
Write-Host "  🔴 ERROR DETECTED: 503 DEADLOCK" -ForegroundColor Red
Write-Host "  ⚡ REMEDIATION: Restarting container" -ForegroundColor Yellow
Write-Host "  ✅ Health VERIFIED" -ForegroundColor Green
Write-Host "  ✅ Faults cleared (site works again)`n" -ForegroundColor Green
