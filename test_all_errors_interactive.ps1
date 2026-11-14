# Interactive Error Testing Script
# Tests all error types one by one with user confirmation

$TOKEN = "changeme-local-dev"
$BASE_URL = "http://localhost:8000"

function Write-Step {
    param($Message, $Color = "Cyan")
    Write-Host "`n$('='*70)" -ForegroundColor $Color
    Write-Host $Message -ForegroundColor $Color
    Write-Host $('='*70)`n -ForegroundColor $Color
}

function Write-Action {
    param($Message)
    Write-Host "  ➤ $Message" -ForegroundColor Yellow
}

function Write-Success {
    param($Message)
    Write-Host "  ✅ $Message" -ForegroundColor Green
}

function Write-Error-Custom {
    param($Message)
    Write-Host "  ❌ $Message" -ForegroundColor Red
}

function Inject-Fault {
    param($FaultType, $Description)
    
    Write-Action "Injecting $Description..."
    try {
        $headers = @{
            "Authorization" = "Bearer $TOKEN"
        }
        $response = Invoke-RestMethod -Uri "$BASE_URL/inject/$FaultType" -Method Post -Headers $headers -TimeoutSec 10
        Write-Success "Fault injected: $($response.message)"
        return $true
    } catch {
        Write-Error-Custom "Failed to inject fault: $($_.Exception.Message)"
        return $false
    }
}

function Reset-Faults {
    Write-Action "Resetting all faults..."
    try {
        $headers = @{
            "Authorization" = "Bearer $TOKEN"
        }
        $response = Invoke-RestMethod -Uri "$BASE_URL/inject/reset?target=all" -Method Post -Headers $headers -TimeoutSec 10
        Write-Success "All faults cleared"
        return $true
    } catch {
        Write-Error-Custom "Failed to reset faults: $($_.Exception.Message)"
        return $false
    }
}

function Get-RecentLogs {
    param($Lines = 20)
    
    $logs = docker-compose logs remediation_engine --tail $Lines 2>&1 | Out-String
    return $logs
}

function Wait-ForDetection {
    param($ErrorType, $TimeoutSeconds = 60)
    
    Write-Action "Waiting for AI detection (max $TimeoutSeconds seconds)..."
    $startTime = Get-Date
    $detected = $false
    $remediated = $false
    $recovered = $false
    
    while (((Get-Date) - $startTime).TotalSeconds -lt $TimeoutSeconds) {
        $logs = Get-RecentLogs -Lines 30
        
        if ($logs -match "ERROR DETECTED.*$ErrorType" -or $logs -match "DIAGNOSIS") {
            if (-not $detected) {
                Write-Success "Error detected by AI!"
                $detected = $true
            }
        }
        
        if ($logs -match "REMEDIATION.*Restarting" -or $logs -match "ACTION") {
            if (-not $remediated) {
                Write-Success "Remediation action triggered!"
                $remediated = $true
            }
        }
        
        if ($logs -match "RECOVERY.*restored" -or $logs -match "Health VERIFIED") {
            if (-not $recovered) {
                Write-Success "Recovery verified!"
                $recovered = $true
                break
            }
        }
        
        Start-Sleep -Seconds 2
    }
    
    if ($recovered) {
        Write-Success "Complete healing cycle observed!"
        return $true
    } elseif ($remediated) {
        Write-Host "  ⚠️  Remediation triggered but recovery not yet confirmed" -ForegroundColor Yellow
        return $true
    } elseif ($detected) {
        Write-Host "  ⚠️  Error detected but remediation not triggered" -ForegroundColor Yellow
        return $false
    } else {
        Write-Error-Custom "No detection within timeout period"
        return $false
    }
}

function Test-ErrorType {
    param(
        $FaultType,
        $ErrorName,
        $Description,
        $TestEndpoint = "/cart/add"
    )
    
    Write-Step "Testing: $ErrorName" "Magenta"
    Write-Host "Description: $Description`n" -ForegroundColor Gray
    
    # Step 1: Inject fault
    if (-not (Inject-Fault -FaultType $FaultType -Description $ErrorName)) {
        Write-Error-Custom "Skipping test due to injection failure"
        return $false
    }
    
    # Step 2: Wait for user to trigger error
    Write-Host "`n📋 Manual Steps:" -ForegroundColor Cyan
    Write-Host "  1. Open shopping site: $BASE_URL/" -ForegroundColor White
    Write-Host "  2. Try to trigger the error (e.g., Add to Cart)" -ForegroundColor White
    Write-Host "  3. Observe the error page" -ForegroundColor White
    Write-Host "  4. Switch to dashboard: $BASE_URL/dashboard" -ForegroundColor White
    Write-Host "  5. Watch the Action Pulse logs`n" -ForegroundColor White
    
    $continue = Read-Host "Press ENTER when you've triggered the error and are ready to monitor"
    
    # Step 3: Monitor for detection and remediation
    $success = Wait-ForDetection -ErrorType $ErrorName -TimeoutSeconds 60
    
    # Step 4: Show recent logs
    Write-Host "`n📜 Recent Remediation Logs:" -ForegroundColor Cyan
    $logs = Get-RecentLogs -Lines 15
    $relevantLogs = $logs -split "`n" | Where-Object { 
        $_ -match "ERROR DETECTED|REMEDIATION|RECOVERY|DIAGNOSIS|ACTION|Health VERIFIED" 
    } | Select-Object -Last 10
    
    if ($relevantLogs) {
        $relevantLogs | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
    } else {
        Write-Host "  (No relevant logs found)" -ForegroundColor DarkGray
    }
    
    # Step 5: Verify recovery
    Write-Host "`n🔍 Verification:" -ForegroundColor Cyan
    Write-Host "  1. Go back to shopping site" -ForegroundColor White
    Write-Host "  2. Try the same action again" -ForegroundColor White
    Write-Host "  3. It should work normally now`n" -ForegroundColor White
    
    $verified = Read-Host "Did the site recover successfully? (y/n)"
    
    if ($verified -eq 'y') {
        Write-Success "Test PASSED: $ErrorName"
        return $true
    } else {
        Write-Error-Custom "Test FAILED: $ErrorName - Manual recovery may be needed"
        
        $reset = Read-Host "Do you want to manually reset faults? (y/n)"
        if ($reset -eq 'y') {
            Reset-Faults
        }
        return $false
    }
}

# Main Test Execution
Write-Step "Self-Healing AI - Interactive Error Testing" "Green"
Write-Host "This script will guide you through testing all error types.`n" -ForegroundColor White
Write-Host "Prerequisites:" -ForegroundColor Yellow
Write-Host "  ✓ All Docker containers running" -ForegroundColor Gray
Write-Host "  ✓ Dashboard open in browser: $BASE_URL/dashboard" -ForegroundColor Gray
Write-Host "  ✓ Shopping site open in another tab: $BASE_URL/`n" -ForegroundColor Gray

$ready = Read-Host "Are you ready to begin? (y/n)"
if ($ready -ne 'y') {
    Write-Host "Exiting. Run the script again when ready." -ForegroundColor Yellow
    exit
}

# Test Results Tracking
$results = @()

# Test 1: 503 Deadlock
$result = Test-ErrorType `
    -FaultType "503_deadlock" `
    -ErrorName "503 DEADLOCK" `
    -Description "Simulates application deadlock (low CPU, high latency)" `
    -TestEndpoint "/cart/add"
$results += @{ Name = "503 Deadlock"; Passed = $result }

Start-Sleep -Seconds 5

# Test 2: 503 Overload
$result = Test-ErrorType `
    -FaultType "503_overload" `
    -ErrorName "503 OVERLOAD" `
    -Description "Simulates CPU saturation (should be suppressed, not restarted)" `
    -TestEndpoint "/health"
$results += @{ Name = "503 Overload"; Passed = $result }

Start-Sleep -Seconds 5

# Test 3: 504 Timeout
$result = Test-ErrorType `
    -FaultType "504_timeout" `
    -ErrorName "504 TIMEOUT" `
    -Description "Simulates gateway timeout (slow dependency)" `
    -TestEndpoint "/payment"
$results += @{ Name = "504 Timeout"; Passed = $result }

Start-Sleep -Seconds 5

# Test 4: 500 Crash
$result = Test-ErrorType `
    -FaultType "500_checkout" `
    -ErrorName "500 CRASH" `
    -Description "Simulates application crash" `
    -TestEndpoint "/checkout"
$results += @{ Name = "500 Crash"; Passed = $result }

# Final Summary
Write-Step "Test Summary" "Green"
$passed = ($results | Where-Object { $_.Passed }).Count
$total = $results.Count

Write-Host "Results: $passed/$total tests passed`n" -ForegroundColor $(if ($passed -eq $total) { "Green" } else { "Yellow" })

$results | ForEach-Object {
    $status = if ($_.Passed) { "✅ PASS" } else { "❌ FAIL" }
    $color = if ($_.Passed) { "Green" } else { "Red" }
    Write-Host "  $status - $($_.Name)" -ForegroundColor $color
}

Write-Host "`n📊 Check dashboard for final metrics:" -ForegroundColor Cyan
Write-Host "  - Total Detections" -ForegroundColor Gray
Write-Host "  - Precision / Recall" -ForegroundColor Gray
Write-Host "  - Error breakdown chart`n" -ForegroundColor Gray

Write-Host "Testing complete! 🎉`n" -ForegroundColor Green
