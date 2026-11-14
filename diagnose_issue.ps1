# Diagnostic Script - Find Why Health Check Fails

Write-Host "`n=== DIAGNOSTIC REPORT ===" -ForegroundColor Cyan

# 1. Check if api_service is running
Write-Host "`n[1] Container Status:" -ForegroundColor Yellow
docker ps --filter "name=api_service" --format "{{.Names}}: {{.Status}}"

# 2. Check if health endpoint responds
Write-Host "`n[2] Health Endpoint (normal):" -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5
    Write-Host "  Status: $($response.StatusCode)" -ForegroundColor Green
    Write-Host "  Body: $($response.Content)" -ForegroundColor Gray
} catch {
    Write-Host "  Error: $($_.Exception.Response.StatusCode) - $($_.Exception.Message)" -ForegroundColor Red
}

# 3. Check if health endpoint with bypass responds
Write-Host "`n[3] Health Endpoint (with bypass_faults=true):" -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health?bypass_faults=true" -UseBasicParsing -TimeoutSec 5
    Write-Host "  Status: $($response.StatusCode)" -ForegroundColor Green
    Write-Host "  Body: $($response.Content)" -ForegroundColor Gray
} catch {
    Write-Host "  Error: $($_.Exception.Response.StatusCode) - $($_.Exception.Message)" -ForegroundColor Red
}

# 4. Check fault state
Write-Host "`n[4] Current Fault State:" -ForegroundColor Yellow
$faultState = docker exec api_service cat /app/logs/fault_state.json 2>&1
Write-Host "  $faultState" -ForegroundColor Gray

# 5. Check recent api_service logs
Write-Host "`n[5] Recent API Service Logs:" -ForegroundColor Yellow
docker logs api_service --tail 20 2>&1 | Select-String "health|fault|503" | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }

# 6. Check if bypass parameter is being received
Write-Host "`n[6] Testing Parameter Parsing:" -ForegroundColor Yellow
Write-Host "  Making request with bypass_faults=true..." -ForegroundColor Gray
try {
    Invoke-WebRequest -Uri "http://localhost:8000/health?bypass_faults=true" -UseBasicParsing -TimeoutSec 5 | Out-Null
    Start-Sleep -Seconds 1
    $logs = docker logs api_service --tail 5 2>&1 | Out-String
    if ($logs -match "bypass") {
        Write-Host "  ✅ Parameter is being logged" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Parameter not visible in logs" -ForegroundColor Red
    }
} catch {
    Write-Host "  Request failed" -ForegroundColor Red
}

# 7. Check remediation engine logs
Write-Host "`n[7] Recent Remediation Logs:" -ForegroundColor Yellow
docker logs remediation_engine --tail 15 2>&1 | Select-String "health|bypass|503" | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }

Write-Host "`n=== END DIAGNOSTIC ===" -ForegroundColor Cyan
