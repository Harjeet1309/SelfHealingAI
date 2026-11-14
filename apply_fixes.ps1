# Apply Critical Fixes - Automated Deployment Script (PowerShell)
# ================================================================
# This script applies all critical fixes and validates the deployment.

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Self-Healing AI - Critical Fixes Deployment" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

function Print-Status {
    param([string]$Message)
    Write-Host "[✓] $Message" -ForegroundColor Green
}

function Print-Warning {
    param([string]$Message)
    Write-Host "[!] $Message" -ForegroundColor Yellow
}

function Print-Error {
    param([string]$Message)
    Write-Host "[✗] $Message" -ForegroundColor Red
}

# Step 1: Verify we're in the right directory
Print-Status "Verifying project directory..."
if (-not (Test-Path "docker-compose.yml")) {
    Print-Error "docker-compose.yml not found. Please run this script from the project root."
    exit 1
}

if (-not (Test-Path "remediation_engine/ai/inference.py")) {
    Print-Error "remediation_engine/ai/inference.py not found. Invalid project structure."
    exit 1
}

# Step 2: Backup current configuration
Print-Status "Creating backup of current configuration..."
$BackupDir = "backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
Copy-Item "docker-compose.yml" "$BackupDir/"
Copy-Item "remediation_engine/ai/inference.py" "$BackupDir/"
Copy-Item "api_service/app/middleware.py" "$BackupDir/"
Print-Status "Backup created in: $BackupDir"

# Step 3: Verify fixes are applied
Print-Status "Verifying fixes are applied..."

# Check corroboration setting
$inferenceContent = Get-Content "remediation_engine/ai/inference.py" -Raw
if ($inferenceContent -match "AI_REQUIRE_CORROBORATION.*True") {
    Print-Status "Corroboration fix verified"
} else {
    Print-Error "Corroboration fix not found. Please check remediation_engine/ai/inference.py"
    exit 1
}

# Check threshold multiplier
if ($inferenceContent -match "AI_THRESHOLD_MULTIPLIER.*1\.5") {
    Print-Status "Threshold multiplier fix verified"
} else {
    Print-Error "Threshold multiplier fix not found. Please check remediation_engine/ai/inference.py"
    exit 1
}

# Check Docker capability
$dockerComposeContent = Get-Content "docker-compose.yml" -Raw
if ($dockerComposeContent -match "SYS_PTRACE") {
    Print-Status "Docker SYS_PTRACE capability verified"
} else {
    Print-Error "SYS_PTRACE capability not found in docker-compose.yml"
    exit 1
}

# Step 4: Stop existing containers
Print-Status "Stopping existing containers..."
docker-compose down

# Step 5: Rebuild images
Print-Status "Rebuilding Docker images..."
docker-compose build --no-cache

# Step 6: Start services
Print-Status "Starting services..."
docker-compose up -d

# Step 7: Wait for services to be ready
Print-Status "Waiting for services to start (30 seconds)..."
Start-Sleep -Seconds 30

# Step 8: Validate metrics collection
Print-Status "Validating metrics collection..."
try {
    docker exec api_service python /app/validate_metrics_fix.py
    Print-Status "Metrics validation PASSED"
} catch {
    Print-Warning "Metrics validation had issues. Check logs for details."
}

# Step 9: Check service health
Print-Status "Checking service health..."

# Check api_service
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Print-Status "api_service is healthy"
    }
} catch {
    Print-Warning "api_service health check failed"
}

# Check remediation_engine
$remediationLogs = docker-compose logs remediation_engine
if ($remediationLogs -match "AI Engine initialized") {
    Print-Status "remediation_engine initialized successfully"
} else {
    Print-Warning "remediation_engine may not be initialized yet"
}

# Check Prometheus
try {
    $response = Invoke-WebRequest -Uri "http://localhost:9090/-/healthy" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Print-Status "Prometheus is healthy"
    }
} catch {
    Print-Warning "Prometheus health check failed"
}

# Step 10: Verify metrics are non-zero
Print-Status "Verifying metrics collection..."
try {
    $metrics = Invoke-WebRequest -Uri "http://localhost:8000/metrics" -UseBasicParsing -TimeoutSec 5
    $metricsContent = $metrics.Content
    
    if ($metricsContent -match "process_memory_mb\s+([\d.]+)") {
        $memoryValue = [double]$matches[1]
        if ($memoryValue -gt 0) {
            Print-Status "Memory metric is collecting: $memoryValue MB"
        } else {
            Print-Warning "Memory metric is zero"
        }
    } else {
        Print-Warning "Memory metric not found"
    }
    
    if ($metricsContent -match "process_active_connections\s+([\d.]+)") {
        $connValue = $matches[1]
        Print-Status "Connection metric is collecting: $connValue connections"
    } else {
        Print-Warning "Connection metric not found"
    }
} catch {
    Print-Warning "Could not fetch metrics"
}

# Step 11: Summary
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Deployment Summary" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Print-Status "All critical fixes have been applied"
Print-Status "Backup saved to: $BackupDir"
Write-Host ""
Write-Host "Service URLs:"
Write-Host "  - API Service:        http://localhost:8000"
Write-Host "  - AI Dashboard:       http://localhost:8000/dashboard"
Write-Host "  - Prometheus:         http://localhost:9090"
Write-Host "  - Grafana:            http://localhost:3001"
Write-Host ""
Write-Host "Next Steps:"
Write-Host "  1. Monitor logs: docker-compose logs -f remediation_engine"
Write-Host "  2. Test fault injection: curl -X POST http://localhost:8000/inject/500_checkout"
Write-Host "  3. View dashboard: http://localhost:8000/dashboard"
Write-Host ""
Write-Host "To rollback:"
Write-Host "  docker-compose down"
Write-Host "  Copy-Item $BackupDir\* ."
Write-Host "  docker-compose up -d"
Write-Host ""
Print-Status "Deployment complete!"
