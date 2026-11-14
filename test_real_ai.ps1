# Test Real AI Detection and Remediation

Write-Host "`n=== TESTING REAL AI DETECTION ===" -ForegroundColor Cyan

Write-Host "`n1. Waiting 45 seconds for AI warmup..." -ForegroundColor Yellow
Start-Sleep -Seconds 45

Write-Host "`n2. Checking AI is running..." -ForegroundColor Yellow
$aiLogs = docker-compose logs remediation_engine --tail 5
if ($aiLogs -match "AI Engine initialized") {
    Write-Host "AI Engine is running" -ForegroundColor Green
} else {
    Write-Host "AI Engine not initialized!" -ForegroundColor Red
    exit 1
}

Write-Host "`n3. Injecting 503 deadlock fault..." -ForegroundColor Yellow
$inject = Invoke-WebRequest -Method POST -Headers @{"Authorization"="Bearer changeme-local-dev"} -Uri http://localhost:8000/inject/503_deadlock -UseBasicParsing | ConvertFrom-Json
Write-Host "Fault injected: $($inject.fault_key)" -ForegroundColor Green

Write-Host "`n4. Waiting 30 seconds for errors to accumulate..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

Write-Host "`n5. Checking if errors are being generated..." -ForegroundColor Yellow
$metrics = curl -UseBasicParsing http://localhost:8000/metrics | Select-String "http_errors_total"
if ($metrics) {
    Write-Host "Errors are being generated!" -ForegroundColor Green
    $metrics | Select-Object -First 3
} else {
    Write-Host "No errors found!" -ForegroundColor Red
}

Write-Host "`n6. Checking AI detection (next 60 seconds)..." -ForegroundColor Yellow
$startTime = Get-Date
$detected = $false

while (((Get-Date) - $startTime).TotalSeconds -lt 60) {
    $logs = docker-compose logs remediation_engine --tail 10
    if ($logs -match "ERROR DETECTED|REMEDIATION") {
        Write-Host "AI DETECTED THE ERROR!" -ForegroundColor Green
        $detected = $true
        break
    }
    $elapsed = [int]((Get-Date) - $startTime).TotalSeconds
    Write-Host "Waiting... ($elapsed seconds)" -ForegroundColor Gray
    Start-Sleep -Seconds 5
}

if (-not $detected) {
    Write-Host "AI did not detect the error in 60 seconds" -ForegroundColor Red
    Write-Host "`nLast AI logs:" -ForegroundColor Yellow
    docker-compose logs remediation_engine --tail 20
}

Write-Host "`n=== TEST COMPLETE ===" -ForegroundColor Cyan
