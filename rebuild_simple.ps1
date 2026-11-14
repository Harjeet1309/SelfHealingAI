# Simple Docker Rebuild Script
Write-Host "=== Stopping containers ===" -ForegroundColor Yellow
docker-compose down

Write-Host "`n=== Removing old images ===" -ForegroundColor Yellow
docker-compose rm -f

Write-Host "`n=== Building fresh containers ===" -ForegroundColor Yellow
docker-compose build --no-cache

Write-Host "`n=== Starting containers ===" -ForegroundColor Yellow
docker-compose up -d

Write-Host "`n=== Waiting for services to be ready ===" -ForegroundColor Yellow
Start-Sleep -Seconds 10

Write-Host "`n=== Checking container status ===" -ForegroundColor Green
docker-compose ps

Write-Host "`n=== Done! ===" -ForegroundColor Green
Write-Host "Access the application at: http://localhost:8000" -ForegroundColor Cyan
Write-Host "Access the dashboard at: http://localhost:8000/dashboard" -ForegroundColor Cyan
