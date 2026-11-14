# Rebuild Docker Containers - Self-Healing AI System
# This script stops, rebuilds, and restarts all containers with the latest code changes

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  REBUILDING DOCKER CONTAINERS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Stop and remove existing containers
Write-Host "[1/5] Stopping existing containers..." -ForegroundColor Yellow
docker-compose down 2>&1 | Out-Null
Write-Host "Done - Containers stopped" -ForegroundColor Green
Write-Host ""

# Step 2: Remove old images
Write-Host "[2/5] Removing old containers..." -ForegroundColor Yellow
docker-compose rm -f 2>&1 | Out-Null
Write-Host "Done - Old containers removed" -ForegroundColor Green
Write-Host ""

# Step 3: Build new images with no cache
Write-Host "[3/5] Building new images (this may take a few minutes)..." -ForegroundColor Yellow
docker-compose build --no-cache
if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed! Check the error messages above." -ForegroundColor Red
    exit 1
}
Write-Host "Done - Images built successfully" -ForegroundColor Green
Write-Host ""

# Step 4: Start containers
Write-Host "[4/5] Starting containers..." -ForegroundColor Yellow
docker-compose up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to start containers!" -ForegroundColor Red
    exit 1
}
Write-Host "Done - Containers started" -ForegroundColor Green
Write-Host ""

# Step 5: Wait for services to be ready
Write-Host "[5/5] Waiting for services to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 15
Write-Host "Done - Services should be ready" -ForegroundColor Green
Write-Host ""

Write-Host "========================================" -ForegroundColor Green
Write-Host "  REBUILD COMPLETE!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Services are now running:" -ForegroundColor Cyan
Write-Host "  API Service:        http://localhost:8000" -ForegroundColor White
Write-Host "  Dashboard:          http://localhost:8000/dashboard" -ForegroundColor White
Write-Host "  Prometheus:         http://localhost:9090" -ForegroundColor White
Write-Host "  Grafana:            http://localhost:3000" -ForegroundColor White
Write-Host "  Alertmanager:       http://localhost:9093" -ForegroundColor White
Write-Host ""
Write-Host "Useful commands:" -ForegroundColor Cyan
Write-Host "  View logs:          docker-compose logs -f" -ForegroundColor White
Write-Host "  View API logs:      docker-compose logs -f api_service" -ForegroundColor White
Write-Host "  View AI logs:       docker-compose logs -f remediation_engine" -ForegroundColor White
Write-Host "  Stop all:           docker-compose down" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Open http://localhost:8000 to see the store" -ForegroundColor White
Write-Host "  2. Open http://localhost:8000/dashboard to inject errors" -ForegroundColor White
Write-Host "  3. Test the error isolation fix!" -ForegroundColor White
Write-Host ""
