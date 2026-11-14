# Test All Error Types - Comprehensive Verification
$TOKEN = "changeme-local-dev"

function Test-ErrorType {
    param(
        [string]$ErrorType,
        [string]$FaultName,
        [string]$TestEndpoint,
        [string]$ExpectedBehavior,
        [int]$ExpectedStatus
    )
    
    Write-Host "`n$('='*80)" -ForegroundColor Cyan
    Write-Host "Testing: $ErrorType" -ForegroundColor Cyan
    Write-Host "Expected: $ExpectedBehavior" -ForegroundColor Gray
    Write-Host $('='*80) -ForegroundColor Cyan
    
    # Step 1: Clear existing faults
    Write-Host "`n[1] Clearing previous faults..." -ForegroundColor Yellow
    try {
        $headers = @{ "Authorization" = "Bearer $TOKEN" }
        Invoke-RestMethod -Uri "http://localhost:8000/inject/reset?target=all" -Method Post -Headers $headers | Out-Null
        Start-Sleep -Seconds 3
        Write-Host "    ✅ Cleared" -ForegroundColor Green
    } catch {
        Write-Host "    ⚠️  Could not clear: $($_.Exception.Message)" -ForegroundColor Yellow
    }
    
    # Step 2: Inject fault
    Write-Host "`n[2] Injecting $ErrorType fault..." -ForegroundColor Yellow
    try {
        $headers = @{ "Authorization" = "Bearer $TOKEN" }
        $response = Invoke-RestMethod -Uri "http://localhost:8000/inject/$FaultName" -Method Post -Headers $headers
        Write-Host "    ✅ Injected: $($response.message)" -ForegroundColor Green
    } catch {
        Write-Host "    ❌ Failed: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
    
    Start-Sleep -Seconds 2
    
    # Step 3: Verify fault is active
    Write-Host "`n[3] Verifying fault is active..." -ForegroundColor Yellow
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000$TestEndpoint" -Method Post -UseBasicParsing -ErrorAction Stop
        Write-Host "    ❌ PROBLEM: Endpoint returned $($response.StatusCode) - Fault not active!" -ForegroundColor Red
        return $false
    } catch {
        $actualStatus = [int]$_.Exception.Response.StatusCode
        if ($actualStatus -eq $ExpectedStatus) {
            Write-Host "    ✅ Fault active: Got expected $ExpectedStatus error" -ForegroundColor Green
        } else {
            Write-Host "    ⚠️  Got $actualStatus instead of expected $ExpectedStatus" -ForegroundColor Yellow
        }
    }
    
    # Step 4: Monitor AI detection and remediation
    Write-Host "`n[4] Monitoring AI detection and remediation (max 60 seconds)..." -ForegroundColor Yellow
    
    $startTime = Get-Date
    $detected = $false
    $remediated = $false
    $verified = $false
    $suppressed = $false
    
    while (((Get-Date) - $startTime).TotalSeconds -lt 60) {
        $logs = docker logs remediation_engine --tail 30 2>&1 | Out-String
        
        if (($logs -match "ERROR DETECTED.*$ErrorType" -or $logs -match "DIAGNOSIS") -and -not $detected) {
            Write-Host "    ✅ AI detected error!" -ForegroundColor Green
            $detected = $true
        }
        
        if ($logs -match "SUPPRESS.*SCALING" -and -not $suppressed) {
            Write-Host "    ✅ AI suppressed restart (overload detected)" -ForegroundColor Green
            $suppressed = $true
            break
        }
        
        if ($logs -match "REMEDIATION.*Restarting" -and -not $remediated) {
            Write-Host "    ✅ AI triggered remediation!" -ForegroundColor Green
            $remediated = $true
        }
        
        if ($logs -match "Health VERIFIED" -and -not $verified) {
            Write-Host "    ✅ Health verification passed!" -ForegroundColor Green
            $verified = $true
            break
        }
        
        Start-Sleep -Seconds 2
    }
    
    # Step 5: Verify outcome
    Write-Host "`n[5] Verifying outcome..." -ForegroundColor Yellow
    Start-Sleep -Seconds 3
    
    if ($ExpectedBehavior -match "SUPPRESS") {
        if ($suppressed) {
            Write-Host "    ✅ Correctly suppressed (no restart)" -ForegroundColor Green
            # Manual reset needed for overload
            Write-Host "    ℹ️  Manually resetting (overload requires manual intervention)..." -ForegroundColor Cyan
            try {
                $headers = @{ "Authorization" = "Bearer $TOKEN" }
                Invoke-RestMethod -Uri "http://localhost:8000/inject/reset?target=all" -Method Post -Headers $headers | Out-Null
            } catch {}
            return $true
        } else {
            Write-Host "    ❌ Should have been suppressed but wasn't" -ForegroundColor Red
            return $false
        }
    } else {
        if ($verified) {
            # Check if site recovered
            try {
                $response = Invoke-WebRequest -Uri "http://localhost:8000$TestEndpoint" -Method Post -UseBasicParsing -ErrorAction Stop
                Write-Host "    ✅ Site recovered successfully!" -ForegroundColor Green
                return $true
            } catch {
                Write-Host "    ❌ Site still broken: $($_.Exception.Response.StatusCode)" -ForegroundColor Red
                return $false
            }
        } else {
            Write-Host "    ⚠️  Health verification did not complete in time" -ForegroundColor Yellow
            return $false
        }
    }
}

# Main Test Execution
Write-Host "`n" -NoNewline
Write-Host "╔═══════════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                    COMPREHENSIVE ERROR TYPE TESTING                           ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

$results = @()

# Test 1: 503 Deadlock (IDLE)
$result = Test-ErrorType `
    -ErrorType "503 DEADLOCK" `
    -FaultName "503_deadlock" `
    -TestEndpoint "/cart/add" `
    -ExpectedBehavior "AI should RESTART container" `
    -ExpectedStatus 503
$results += @{ Name = "503 Deadlock (IDLE)"; Passed = $result }

Start-Sleep -Seconds 5

# Test 2: 503 Overload (SAT)
$result = Test-ErrorType `
    -ErrorType "503 OVERLOAD" `
    -FaultName "503_overload" `
    -TestEndpoint "/health" `
    -ExpectedBehavior "AI should SUPPRESS (high CPU = scale, not restart)" `
    -ExpectedStatus 503
$results += @{ Name = "503 Overload (SAT)"; Passed = $result }

Start-Sleep -Seconds 5

# Test 3: 504 Timeout
$result = Test-ErrorType `
    -ErrorType "504 TIMEOUT" `
    -FaultName "504_timeout" `
    -TestEndpoint "/payment" `
    -ExpectedBehavior "AI should RESTART container" `
    -ExpectedStatus 504
$results += @{ Name = "504 Timeout"; Passed = $result }

Start-Sleep -Seconds 5

# Test 4: 500 Crash
$result = Test-ErrorType `
    -ErrorType "500 CRASH" `
    -FaultName "500_checkout" `
    -TestEndpoint "/checkout" `
    -ExpectedBehavior "AI should RESTART container" `
    -ExpectedStatus 500
$results += @{ Name = "500 Crash"; Passed = $result }

# Final Summary
Write-Host "`n" -NoNewline
Write-Host "╔═══════════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                              TEST SUMMARY                                     ║" -ForegroundColor Green
Write-Host "╚═══════════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Green

$passed = ($results | Where-Object { $_.Passed }).Count
$total = $results.Count

Write-Host "`nResults: $passed/$total tests passed`n" -ForegroundColor $(if ($passed -eq $total) { "Green" } else { "Yellow" })

$results | ForEach-Object {
    $status = if ($_.Passed) { "✅ PASS" } else { "❌ FAIL" }
    $color = if ($_.Passed) { "Green" } else { "Red" }
    Write-Host "  $status - $($_.Name)" -ForegroundColor $color
}

Write-Host "`n" -NoNewline
Write-Host "╔═══════════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                           DETAILED ANALYSIS                                   ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

Write-Host "`nExpected Behaviors:" -ForegroundColor Yellow
Write-Host "  • 503 Deadlock (IDLE)  → AI detects → Restarts container → Verifies health → Clears fault" -ForegroundColor White
Write-Host "  • 503 Overload (SAT)   → AI detects → Checks CPU (high) → Suppresses restart → Logs 'scale needed'" -ForegroundColor White
Write-Host "  • 504 Timeout          → AI detects → Restarts container → Verifies health → Clears fault" -ForegroundColor White
Write-Host "  • 500 Crash            → AI detects → Restarts container → Verifies health → Clears fault" -ForegroundColor White

Write-Host "`nKey Differences:" -ForegroundColor Yellow
Write-Host "  • Deadlock vs Overload: Both are 503, but AI checks CPU to distinguish" -ForegroundColor White
Write-Host "    - Low CPU = Deadlock → Restart" -ForegroundColor Gray
Write-Host "    - High CPU = Overload → Suppress (scale needed)" -ForegroundColor Gray

Write-Host "`nDashboard Metrics to Check:" -ForegroundColor Yellow
Write-Host "  • Total Detections: Should be 4 (one for each test)" -ForegroundColor White
Write-Host "  • Precision: Should be 90-100% (all restarts were correct)" -ForegroundColor White
Write-Host "  • Recall: Should be 90-100% (caught all real errors)" -ForegroundColor White
Write-Host "  • Error Breakdown: Should show distribution across 500/503/504" -ForegroundColor White

if ($passed -eq $total) {
    Write-Host "`n🎉 ALL TESTS PASSED! Your self-healing AI is working correctly!" -ForegroundColor Green
    Write-Host "   The system demonstrates REAL healing across all error types.`n" -ForegroundColor Green
} else {
    Write-Host "`n⚠️  Some tests failed. Check the logs above for details." -ForegroundColor Yellow
    Write-Host "   Run: docker logs remediation_engine --tail 100`n" -ForegroundColor Gray
}
