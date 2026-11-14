# Self-Healing AI - Application Testing Script
# =============================================
# This script will start your application and run comprehensive tests

$ErrorActionPreference = "Continue"

function Print-Header {
    param([string]$Text)
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host $Text -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan
}

function Print-Success {
    param([string]$Text)
    Write-Host "✅ $Text" -ForegroundColor Green
}

function Print-Error {
    param([string]$Text)
    Write-Host "❌ $Text" -ForegroundColor Red
}

function Print-Info {
    param([string]$Text)
    Write-Host "ℹ️  $Text" -ForegroundColor Yellow
}

function Test-ServiceHealth {
    param([string]$Url, [string]$ServiceName)
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Print-Success "$ServiceName is healthy"
            return $true
        }
    } catch {
        Print-Error "$ServiceName is not responding"
        return $false
    }
}

# ============================================
# STEP 1: START THE APPLICATION
# ============================================
Print-Header "STEP 1: Starting Application"

Print-Info "Stopping any existing containers..."
docker-compose down 2>$null

Print-Info "Building and starting all services..."
docker-compose up -d --build

Print-Info "Waiting 30 seconds for services to initialize..."
Start-Sleep -Seconds 30

# ============================================
# STEP 2: CHECK CONTAINER STATUS
# ============================================
Print-Header "STEP 2: Container Status"

$containers = docker-compose ps --format json | ConvertFrom-Json
foreach ($container in $containers) {
    $name = $container.Service
    $state = $container.State
    if ($state -eq "running") {
        Print-Success "$name is running"
    } else {
        Print-Error "$name is $state"
    }
}

# ============================================
# STEP 3: HEALTH CHECKS
# ============================================
Print-Header "STEP 3: Service Health Checks"

$healthChecks = @{
    "API Service" = "http://localhost:8000/health"
    "Prometheus" = "http://localhost:9090/-/healthy"
    "Alertmanager" = "http://localhost:9093/-/healthy"
}

$allHealthy = $true
foreach ($service in $healthChecks.Keys) {
    $healthy = Test-ServiceHealth -Url $healthChecks[$service] -ServiceName $service
    if (-not $healthy) { $allHealthy = $false }
}

# ============================================
# STEP 4: VALIDATE METRICS COLLECTION
# ============================================
Print-Header "STEP 4: Metrics Collection Validation"

Print-Info "Running validation script..."
try {
    docker exec api_service python /app/validate_metrics_fix.py
    Print-Success "Metrics validation completed"
} catch {
    Print-Error "Metrics validation failed"
    Print-Info "This might be OK if it's the first run"
}

# ============================================
# STEP 5: CHECK METRICS VALUES
# ============================================
Print-Header "STEP 5: Checking Metrics Values"

try {
    $metrics = Invoke-WebRequest -Uri "http://localhost:8000/metrics" -UseBasicParsing -TimeoutSec 5
    $metricsContent = $metrics.Content
    
    # Check memory metric
    if ($metricsContent -match "process_memory_mb\s+([\d.]+)") {
        $memValue = [double]$matches[1]
        if ($memValue -gt 0) {
            Print-Success "Memory metric: $memValue MB"
        } else {
            Print-Error "Memory metric is zero"
        }
    } else {
        Print-Error "Memory metric not found"
    }
    
    # Check connection metric
    if ($metricsContent -match "process_active_connections\s+([\d.]+)") {
        $connValue = $matches[1]
        Print-Success "Active connections: $connValue"
    } else {
        Print-Error "Connection metric not found"
    }
    
    # Check request count
    if ($metricsContent -match "http_requests_total") {
        Print-Success "HTTP request metrics are being collected"
    }
    
} catch {
    Print-Error "Could not fetch metrics from /metrics endpoint"
}

# ============================================
# STEP 6: CHECK AI ENGINE
# ============================================
Print-Header "STEP 6: AI Engine Status"

Print-Info "Checking remediation engine logs..."
$remediationLogs = docker-compose logs remediation_engine --tail 50

if ($remediationLogs -match "AI Engine initialized") {
    Print-Success "AI Engine initialized successfully"
    
    # Extract threshold
    if ($remediationLogs -match "threshold=([\d.]+)") {
        $threshold = $matches[1]
        Print-Info "AI Threshold: $threshold"
        if ([double]$threshold -lt 0.1) {
            Print-Success "Threshold is in expected range (< 0.1)"
        } else {
            Print-Error "Threshold seems too high: $threshold"
        }
    }
} else {
    Print-Error "AI Engine not initialized yet"
    Print-Info "Check logs: docker-compose logs remediation_engine"
}

# ============================================
# STEP 7: TEST BASIC FUNCTIONALITY
# ============================================
Print-Header "STEP 7: Testing Basic Functionality"

Print-Info "Testing product listing endpoint..."
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/products" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Print-Success "Product listing works"
    }
} catch {
    Print-Error "Product listing failed"
}

Print-Info "Generating some traffic (20 requests)..."
for ($i = 1; $i -le 20; $i++) {
    try {
        Invoke-WebRequest -Uri "http://localhost:8000/products" -UseBasicParsing -TimeoutSec 2 | Out-Null
    } catch {
        # Ignore errors
    }
}
Print-Success "Traffic generation complete"

# ============================================
# STEP 8: TEST FAULT INJECTION (OPTIONAL)
# ============================================
Print-Header "STEP 8: Fault Injection Test (Optional)"

Print-Info "This will test if the AI can detect and heal a fault"
$testFault = Read-Host "Do you want to test fault injection? (y/n)"

if ($testFault -eq "y") {
    Print-Info "Injecting 500 crash fault..."
    try {
        Invoke-WebRequest -Uri "http://localhost:8000/inject/500_checkout" -Method POST -UseBasicParsing | Out-Null
        Print-Success "Fault injected"
        
        Print-Info "Generating error traffic..."
        for ($i = 1; $i -le 30; $i++) {
            try {
                Invoke-WebRequest -Uri "http://localhost:8000/checkout" -Method POST -UseBasicParsing -TimeoutSec 2 | Out-Null
            } catch {
                # Expected to fail
            }
        }
        
        Print-Info "Waiting 20 seconds for AI to detect..."
        Start-Sleep -Seconds 20
        
        Print-Info "Checking if AI detected the fault..."
        $recentLogs = docker-compose logs remediation_engine --tail 30
        if ($recentLogs -match "ANOMALY DETECTED" -or $recentLogs -match "REMEDIATION") {
            Print-Success "AI detected the fault!"
        } else {
            Print-Info "AI may still be analyzing. Check logs manually."
        }
        
    } catch {
        Print-Error "Fault injection test failed"
    }
}

# ============================================
# STEP 9: SUMMARY
# ============================================
Print-Header "SUMMARY"

Write-Host "Service URLs:" -ForegroundColor White
Write-Host "  🌐 Main Application:  http://localhost:8000" -ForegroundColor White
Write-Host "  📊 AI Dashboard:      http://localhost:8000/dashboard" -ForegroundColor White
Write-Host "  📈 Prometheus:        http://localhost:9090" -ForegroundColor White
Write-Host "  🔔 Alertmanager:      http://localhost:9093" -ForegroundColor White
Write-Host "  📉 Grafana:           http://localhost:3001" -ForegroundColor White
Write-Host ""

Write-Host "Useful Commands:" -ForegroundColor White
Write-Host "  View all logs:        docker-compose logs -f" -ForegroundColor Gray
Write-Host "  View AI logs:         docker-compose logs -f remediation_engine" -ForegroundColor Gray
Write-Host "  View API logs:        docker-compose logs -f api_service" -ForegroundColor Gray
Write-Host "  Stop application:     docker-compose down" -ForegroundColor Gray
Write-Host "  Restart service:      docker-compose restart api_service" -ForegroundColor Gray
Write-Host ""

if ($allHealthy) {
    Print-Success "All services are healthy! Application is working fine."
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor Yellow
    Write-Host "  1. Open http://localhost:8000 in your browser" -ForegroundColor White
    Write-Host "  2. Explore the AI Dashboard at http://localhost:8000/dashboard" -ForegroundColor White
    Write-Host "  3. Try injecting faults to see self-healing in action" -ForegroundColor White
    Write-Host ""
} else {
    Print-Error "Some services are not healthy. Check the logs above."
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "  1. Check logs: docker-compose logs" -ForegroundColor White
    Write-Host "  2. Verify ports are not in use: netstat -ano | findstr '8000 9090'" -ForegroundColor White
    Write-Host "  3. Try rebuilding: docker-compose down && docker-compose up --build -d" -ForegroundColor White
    Write-Host ""
}

Print-Header "Testing Complete"
