# Test Enhanced Error Display
# This script tests the enhanced error type display in both terminal and dashboard

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  ENHANCED ERROR DISPLAY TEST" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Step 1: Restart services
Write-Host "[1/5] Restarting services to apply changes..." -ForegroundColor Yellow
docker-compose restart api_service remediation_engine
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to restart services" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Services restarted" -ForegroundColor Green
Write-Host ""

# Step 2: Wait for services to stabilize
Write-Host "[2/5] Waiting 15 seconds for services to stabilize..." -ForegroundColor Yellow
Start-Sleep -Seconds 15
Write-Host "✓ Services ready" -ForegroundColor Green
Write-Host ""

# Step 3: Open dashboard
Write-Host "[3/5] Opening dashboard in browser..." -ForegroundColor Yellow
Write-Host "    Dashboard URL: http://localhost:8000/dashboard" -ForegroundColor Cyan
Write-Host "    Look for: ACTION LEDGER section (bottom left)" -ForegroundColor Cyan
Start-Process "http://localhost:8000/dashboard"
Start-Sleep -Seconds 3
Write-Host "✓ Dashboard opened" -ForegroundColor Green
Write-Host ""

# Step 4: Show log monitoring command
Write-Host "[4/5] To watch terminal logs, run this in another window:" -ForegroundColor Yellow
Write-Host "    docker-compose logs -f remediation_engine" -ForegroundColor Cyan
Write-Host ""

# Step 5: Test different error types
Write-Host "[5/5] Testing different error types..." -ForegroundColor Yellow
Write-Host ""

$tests = @(
    @{Name="500 CRASH"; Endpoint="500_checkout"; Wait=30},
    @{Name="503 DEADLOCK"; Endpoint="503_deadlock"; Wait=30},
    @{Name="504 TIMEOUT"; Endpoint="504_timeout"; Wait=30}
)

foreach ($test in $tests) {
    Write-Host "  Testing: $($test.Name)" -ForegroundColor Cyan
    Write-Host "    Injecting fault..." -ForegroundColor Gray
    
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/inject/$($test.Endpoint)" -Method POST -ErrorAction Stop
        Write-Host "    ✓ Fault injected" -ForegroundColor Green
    } catch {
        Write-Host "    ✗ Failed to inject fault: $_" -ForegroundColor Red
        continue
    }
    
    Write-Host "    Waiting $($test.Wait) seconds for AI to detect and remediate..." -ForegroundColor Gray
    Start-Sleep -Seconds $test.Wait
    
    Write-Host "    ✓ Test complete" -ForegroundColor Green
    Write-Host ""
}

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  TEST COMPLETE!" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "What to check:" -ForegroundColor Yellow
Write-Host "  1. Dashboard ACTION LEDGER shows error types with colored badges" -ForegroundColor White
Write-Host "     Example: [500 CRASH] 🔴 ERROR DETECTED: ..." -ForegroundColor White
Write-Host ""
Write-Host "  2. Terminal logs show error types with emojis" -ForegroundColor White
Write-Host "     Run: docker-compose logs -f remediation_engine" -ForegroundColor Cyan
Write-Host ""
Write-Host "  3. Color coding:" -ForegroundColor White
Write-Host "     - Red background = Error detected" -ForegroundColor Red
Write-Host "     - Gold background = Remediation action" -ForegroundColor Yellow
Write-Host "     - Green background = Recovery confirmed" -ForegroundColor Green
Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
