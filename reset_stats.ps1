# Reset AI Performance Stats
Write-Host "Resetting AI Performance Statistics..." -ForegroundColor Cyan

# Stop the services
Write-Host "`nStopping services..." -ForegroundColor Yellow
docker-compose stop api_service remediation_engine

# Delete the stats file
Write-Host "`nDeleting stats file..." -ForegroundColor Yellow
if (Test-Path "logs/dashboard_stats.json") {
    Remove-Item "logs/dashboard_stats.json" -Force
    Write-Host "Stats file deleted" -ForegroundColor Green
}

# Delete the remediation log
Write-Host "`nClearing remediation logs..." -ForegroundColor Yellow
if (Test-Path "logs/remediation.log") {
    Remove-Item "logs/remediation.log" -Force
    Write-Host "Remediation log cleared" -ForegroundColor Green
}

# Restart services
Write-Host "`nRestarting services..." -ForegroundColor Yellow
docker-compose up -d --build remediation_engine api_service

Write-Host "`nWaiting 30 seconds for services..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

# Check stats
Write-Host "`nChecking new stats..." -ForegroundColor Yellow
$stats = Invoke-WebRequest -Uri "http://localhost:8000/ai/stats" -UseBasicParsing | ConvertFrom-Json
Write-Host "Total Detections: $($stats.total_detections)" -ForegroundColor White
Write-Host "Precision: $([math]::Round($stats.precision * 100, 1))%" -ForegroundColor White
Write-Host "Recall: $([math]::Round($stats.recall * 100, 1))%" -ForegroundColor White

Write-Host "`nReset Complete!" -ForegroundColor Green
Write-Host "Health check improved: 15 retries x 3s = 45s total" -ForegroundColor Cyan
