# Complete Demo Startup Script
# Starts all services + background traffic for realistic metrics

Write-Host "`n╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     Self-Healing AI System - Demo Startup                    ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

# Step 1: Start Docker services
Write-Host "[1/3] Starting Docker services..." -ForegroundColor Yellow
docker-compose up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker startup failed" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Docker services started" -ForegroundColor Green
Write-Host "`nWaiting for services to initialize..." -ForegroundColor Gray
Start-Sleep -Seconds 15

# Step 2: Verify services are healthy
Write-Host "`n[2/3] Verifying services..." -ForegroundColor Yellow

$services = @(
    @{Name="API Service"; URL="http://localhost:8000/health"},
    @{Name="Prometheus"; URL="http://localhost:9090/-/healthy"},
    @{Name="Dashboard"; URL="http://localhost:8000/dashboard"}
)

foreach ($service in $services) {
    try {
        $response = Invoke-WebRequest -Uri $service.URL -TimeoutSec 5 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Host "  ✅ $($service.Name)" -ForegroundColor Green
        }
    } catch {
        Write-Host "  ⚠️  $($service.Name) - Not ready yet" -ForegroundColor Yellow
    }
}

# Step 3: Start traffic generator
Write-Host "`n[3/3] Starting background traffic generator..." -ForegroundColor Yellow
Write-Host "This generates baseline metrics for the dashboard`n" -ForegroundColor Gray

# Check if Python is available
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Using: $pythonVersion" -ForegroundColor Gray
    
    Write-Host "`nStarting traffic generator (2 req/s baseline)..." -ForegroundColor Cyan
    Write-Host "Press Ctrl+C to stop the traffic generator`n" -ForegroundColor Gray
    
    # Run traffic generator (this will block)
    python traffic_generator.py
    
} catch {
    Write-Host "⚠️  Python not found. Skipping traffic generator." -ForegroundColor Yellow
    Write-Host "   Metrics will only populate when you manually use the site.`n" -ForegroundColor Gray
}

Write-Host "`n╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                    DEMO READY                                 ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

Write-Host "Access Points:" -ForegroundColor White
Write-Host "  Dashboard:     http://localhost:8000/dashboard" -ForegroundColor Cyan
Write-Host "  Shopping Site: http://localhost:8000/" -ForegroundColor Cyan
Write-Host "  Prometheus:    http://localhost:9090/" -ForegroundColor Cyan
Write-Host "  Grafana:       http://localhost:3000/ (admin/admin)`n" -ForegroundColor Cyan

Write-Host "Next Steps:" -ForegroundColor White
Write-Host "  1. Open dashboard in browser" -ForegroundColor Gray
Write-Host "  2. Inject a fault (click any error button)" -ForegroundColor Gray
Write-Host "  3. Watch AI detect and remediate" -ForegroundColor Gray
Write-Host "  4. Observe metrics spike and recover`n" -ForegroundColor Gray
