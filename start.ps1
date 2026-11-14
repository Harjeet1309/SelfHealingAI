# Quick Start Script - Self-Healing AI Application
# =================================================
# This script starts the application and opens the dashboard

Write-Host "`n🚀 Starting Self-Healing AI Application...`n" -ForegroundColor Cyan

# Stop any existing containers
Write-Host "Stopping existing containers..." -ForegroundColor Yellow
docker-compose down 2>$null

# Start all services
Write-Host "Starting all services (this may take 2-3 minutes)...`n" -ForegroundColor Yellow
docker-compose up -d --build

# Wait for services to initialize
Write-Host "Waiting for services to initialize..." -ForegroundColor Yellow
for ($i = 30; $i -gt 0; $i--) {
    Write-Host "`rTime remaining: $i seconds..." -NoNewline -ForegroundColor Gray
    Start-Sleep -Seconds 1
}
Write-Host "`n"

# Check if services are running
Write-Host "Checking service status...`n" -ForegroundColor Yellow
$apiHealthy = $false
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ API Service is running" -ForegroundColor Green
        $apiHealthy = $true
    }
} catch {
    Write-Host "❌ API Service is not responding yet" -ForegroundColor Red
}

# Display URLs
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Application Started Successfully!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "📱 Access Points:" -ForegroundColor White
Write-Host "   Main Application:  http://localhost:8000" -ForegroundColor White
Write-Host "   AI Dashboard:      http://localhost:8000/dashboard" -ForegroundColor White
Write-Host "   Prometheus:        http://localhost:9090" -ForegroundColor White
Write-Host "   Grafana:           http://localhost:3001`n" -ForegroundColor White

Write-Host "📊 Quick Commands:" -ForegroundColor White
Write-Host "   View logs:         docker-compose logs -f" -ForegroundColor Gray
Write-Host "   Stop app:          docker-compose down" -ForegroundColor Gray
Write-Host "   Run tests:         .\test_application.ps1`n" -ForegroundColor Gray

# Open dashboard in browser
if ($apiHealthy) {
    Write-Host "🌐 Opening AI Dashboard in your browser...`n" -ForegroundColor Cyan
    Start-Sleep -Seconds 2
    Start-Process "http://localhost:8000/dashboard"
} else {
    Write-Host "⚠️  Services may still be initializing. Wait 30 more seconds and try:" -ForegroundColor Yellow
    Write-Host "   http://localhost:8000/dashboard`n" -ForegroundColor White
}

Write-Host "✨ Ready to go! Explore the dashboard and try fault injection.`n" -ForegroundColor Green
