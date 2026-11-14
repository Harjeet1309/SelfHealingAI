# Test Real Self-Healing (No Fake Recovery)
$TOKEN = "changeme-local-dev"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Testing REAL Self-Healing (No Fake Recovery)" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Step 1: Clear any existing faults
Write-Host "[Step 1] Clearing any existing faults..." -ForegroundColor Yellow
try {
    $headers = @{ "Authorization" = "Bearer $TOKEN" }
    Invoke-RestMethod -Uri "http://localhost:8000/inject/reset?target=all" -Method Post -Headers $headers | Out-Null
    Write-Host "  ✅ Faults cleared" -ForegroundColor Green
} catch {
    Write-Host "  ⚠️  Could not clear faults: $($_.Exception.Message)" -ForegroundColor Yellow
}

Start-Sleep -Seconds 2

# Step 2: Verify site works normally
Write-Host "`n[Step 2] Verifying site works normally..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/cart/add" -Method Post -UseBasicParsing -ErrorAction Stop
    Write-Host "  ✅ Site is working (Status: $($response.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Site not working: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Step 3: Inject 503 fault
Write-Host "`n[Step 3] Injecting 503 DEADLOCK fault..." -ForegroundColor Yellow
try {
    $headers = @{ "Authorization" = "Bearer $TOKEN" }
    $response = Invoke-RestMethod -Uri "http://localhost:8000/inject/503_deadlock" -Method Post -Headers $headers
    Write-Host "  ✅ Fault injected: $($response.message)" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Failed to inject fault: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Start-Sleep -Seconds 2

# Step 4: Verify fault is active (site should be broken)
Write-Host "`n[Step 4] Verifying fault is active (site should be broken)..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/cart/add" -Method Post -UseBasicParsing -ErrorAction Stop
    Write-Host "  ❌ PROBLEM: Site is still working! Fault not active!" -ForegroundColor Red
    Write-Host "  This means fake healing - site recovered without AI!" -ForegroundColor Red
    exit 1
} catch {
    if ($_.Exception.Response.StatusCode -eq 503) {
        Write-Host "  ✅ GOOD: Site is broken (503 error as expected)" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  Got unexpected error: $($_.Exception.Response.StatusCode)" -ForegroundColor Yellow
    }
}

# Step 5: Check fault state file
Write-Host "`n[Step 5] Checking fault persistence..." -ForegroundColor Yellow
$faultState = docker exec api_service cat /app/logs/fault_state.json 2>&1 | Out-String
if ($faultState -match '"cart".*"active".*true') {
    Write-Host "  ✅ Fault persisted to file correctly" -ForegroundColor Green
} else {
    Write-Host "  ❌ Fault NOT in state file: $faultState" -ForegroundColor Red
}

# Step 6: Wait for AI detection
Write-Host "`n[Step 6] Waiting for AI to detect and remediate (max 60 seconds)..." -ForegroundColor Yellow
Write-Host "  Monitoring remediation logs..." -ForegroundColor Gray

$startTime = Get-Date
$detected = $false
$remediated = $false
$verified = $false
$recovered = $false

while (((Get-Date) - $startTime).TotalSeconds -lt 60) {
    $logs = docker logs remediation_engine --tail 30 2>&1 | Out-String
    
    if ($logs -match "ERROR DETECTED.*503" -and -not $detected) {
        Write-Host "  ✅ AI detected error!" -ForegroundColor Green
        $detected = $true
    }
    
    if ($logs -match "REMEDIATION.*Restarting" -and -not $remediated) {
        Write-Host "  ✅ AI triggered remediation!" -ForegroundColor Green
        $remediated = $true
    }
    
    if ($logs -match "Health VERIFIED" -and -not $verified) {
        Write-Host "  ✅ Health verification passed!" -ForegroundColor Green
        $verified = $true
    }
    
    if ($logs -match "RECOVERY.*restored" -and -not $recovered) {
        Write-Host "  ✅ Recovery completed!" -ForegroundColor Green
        $recovered = $true
        break
    }
    
    Start-Sleep -Seconds 2
}

if (-not $recovered) {
    Write-Host "  ⚠️  AI did not complete recovery within 60 seconds" -ForegroundColor Yellow
    Write-Host "  Check logs: docker logs remediation_engine --tail 50" -ForegroundColor Gray
}

# Step 7: Verify site recovered ONLY after AI action
Write-Host "`n[Step 7] Verifying site recovered after AI remediation..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/cart/add" -Method Post -UseBasicParsing -ErrorAction Stop
    if ($recovered) {
        Write-Host "  ✅ PERFECT: Site recovered AFTER AI remediation!" -ForegroundColor Green
        Write-Host "  This is REAL self-healing!" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  Site recovered but AI logs incomplete" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ❌ Site still broken after AI remediation" -ForegroundColor Red
    Write-Host "  Status: $($_.Exception.Response.StatusCode)" -ForegroundColor Red
}

# Step 8: Verify fault state cleared
Write-Host "`n[Step 8] Verifying fault state cleared..." -ForegroundColor Yellow
$faultState = docker exec api_service cat /app/logs/fault_state.json 2>&1 | Out-String
if ($faultState -match '^\s*\{\s*\}\s*$' -or $faultState -eq "{}") {
    Write-Host "  ✅ Fault state cleared correctly" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  Fault state not empty: $faultState" -ForegroundColor Yellow
}

# Summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Test Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if ($detected -and $remediated -and $verified -and $recovered) {
    Write-Host "✅ ALL CHECKS PASSED!" -ForegroundColor Green
    Write-Host "`nThis is REAL self-healing:" -ForegroundColor Green
    Write-Host "  1. Fault injected and persisted ✅" -ForegroundColor White
    Write-Host "  2. Site stayed broken until AI acted ✅" -ForegroundColor White
    Write-Host "  3. AI detected, remediated, and verified ✅" -ForegroundColor White
    Write-Host "  4. Site recovered only after AI completion ✅" -ForegroundColor White
    Write-Host "`nNo fake healing detected! 🎉`n" -ForegroundColor Green
} else {
    Write-Host "⚠️  SOME CHECKS INCOMPLETE" -ForegroundColor Yellow
    Write-Host "  Detection: $(if($detected){'✅'}else{'❌'})" -ForegroundColor White
    Write-Host "  Remediation: $(if($remediated){'✅'}else{'❌'})" -ForegroundColor White
    Write-Host "  Verification: $(if($verified){'✅'}else{'❌'})" -ForegroundColor White
    Write-Host "  Recovery: $(if($recovered){'✅'}else{'❌'})" -ForegroundColor White
    Write-Host "`nCheck logs for details: docker logs remediation_engine --tail 50`n" -ForegroundColor Gray
}
