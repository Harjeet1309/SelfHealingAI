# Quick System Verification Script
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Self-Healing AI System Verification" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check 1: All containers running
Write-Host "[1/5] Checking Docker containers..." -ForegroundColor Yellow
$containers = docker-compose ps --format json | ConvertFrom-Json
$expected = @("api_service", "prometheus", "alertmanager", "remediation_engine", "chaos_engine", "toxiproxy", "watchdog", "grafana")
$running = $containers | Where-Object { $_.State -eq "running" }

if ($running.Count -eq $expected.Count) {
    Write-Host "  ✅ All $($expected.Count) containers running" -ForegroundColor Green
} else {
    Write-Host "  ❌ Only $($running.Count)/$($expected.Count) containers running" -ForegroundColor Red
    $containers | Format-Table Name, State, Status
}

# Check 2: Shopping site accessible
Write-Host "`n[2/5] Checking Shopping Site (http://localhost:8000/)..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/" -TimeoutSec 5 -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "  ✅ Shopping site is accessible" -ForegroundColor Green
    }
} catch {
    Write-Host "  ❌ Shopping site not accessible: $($_.Exception.Message)" -ForegroundColor Red
}

# Check 3: Dashboard accessible
Write-Host "`n[3/5] Checking Dashboard (http://localhost:8000/dashboard)..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/dashboard" -TimeoutSec 5 -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "  ✅ Dashboard is accessible" -ForegroundColor Green
    }
} catch {
    Write-Host "  ❌ Dashboard not accessible: $($_.Exception.Message)" -ForegroundColor Red
}

# Check 4: AI monitoring active
Write-Host "`n[4/5] Checking AI Monitoring Loop..." -ForegroundColor Yellow
$logs = docker-compose logs remediation_engine --tail 5 2>&1 | Out-String
if ($logs -match "MONITORING PULSE" -and $logs -match "AI STATUS: HEALTHY") {
    Write-Host "  ✅ AI monitoring loop is active and healthy" -ForegroundColor Green
} else {
    Write-Host "  ❌ AI monitoring loop not detected" -ForegroundColor Red
}

# Check 5: Prometheus scraping
Write-Host "`n[5/5] Checking Prometheus (http://localhost:9090/)..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:9090/api/v1/targets" -TimeoutSec 5 -UseBasicParsing
    $targets = ($response.Content | ConvertFrom-Json).data.activeTargets
    $apiTarget = $targets | Where-Object { $_.labels.job -eq "api_service" }
    
    if ($apiTarget.health -eq "up") {
        Write-Host "  ✅ Prometheus is scraping api_service" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  Prometheus target status: $($apiTarget.health)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ❌ Prometheus not accessible: $($_.Exception.Message)" -ForegroundColor Red
}

# Summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "System Status Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Shopping Site:  http://localhost:8000/" -ForegroundColor White
Write-Host "Dashboard:      http://localhost:8000/dashboard" -ForegroundColor White
Write-Host "Prometheus:     http://localhost:9090/" -ForegroundColor White
Write-Host "Grafana:        http://localhost:3001/" -ForegroundColor White
Write-Host "Alertmanager:   http://localhost:9093/" -ForegroundColor White
Write-Host "`n✨ System is ready for testing!" -ForegroundColor Green
Write-Host "`nNext steps:" -ForegroundColor Cyan
Write-Host "1. Open http://localhost:8000/dashboard in your browser" -ForegroundColor White
Write-Host "2. Click 'Execute Deadlock' to inject 503 error" -ForegroundColor White
Write-Host "3. Watch the Action Pulse logs for detection and remediation" -ForegroundColor White
Write-Host "4. Verify recovery on the shopping site" -ForegroundColor White
Write-Host "`nFor detailed testing guide, see: COMPLETE_TEST_GUIDE.md`n" -ForegroundColor Yellow
