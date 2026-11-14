# Test Single Error Type - Interactive Guide
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("503_overload", "504_timeout", "500_crash")]
    [string]$ErrorType
)

$TOKEN = "changeme-local-dev"

# Error type configurations
$configs = @{
    "503_overload" = @{
        Name = "503 OVERLOAD (SAT)"
        Button = "Execute Overload"
        TestEndpoint = "/health"
        ExpectedStatus = 503
        ExpectedBehavior = "SUPPRESS (High CPU detected)"
        ShouldRestart = $false
        Description = "CPU saturation - AI should suppress restart and recommend scaling"
    }
    "504_timeout" = @{
        Name = "504 TIMEOUT"
        Button = "Execute Timeout"
        TestEndpoint = "/payment"
        ExpectedStatus = 504
        ExpectedBehavior = "RESTART (Clear stuck connections)"
        ShouldRestart = $true
        Description = "Gateway timeout - AI should restart to clear connections"
    }
    "500_crash" = @{
        Name = "500 CRASH"
        Button = "Execute App Crash"
        TestEndpoint = "/checkout"
        ExpectedStatus = 500
        ExpectedBehavior = "RESTART (Application crash)"
        ShouldRestart = $true
        Description = "Application crash - AI should restart container"
    }
}

$config = $configs[$ErrorType]

Write-Host "`n╔═══════════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                    TESTING: $($config.Name.PadRight(52))║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

Write-Host "`nDescription: $($config.Description)" -ForegroundColor Gray
Write-Host "Expected Behavior: $($config.ExpectedBehavior)" -ForegroundColor Yellow

# Step 0: Clear previous faults
Write-Host "`n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host "[STEP 0] Clearing previous faults..." -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray

try {
    $headers = @{ "Authorization" = "Bearer $TOKEN" }
    Invoke-RestMethod -Uri "http://localhost:8000/inject/reset?target=all" -Method Post -Headers $headers | Out-Null
    Write-Host "✅ Previous faults cleared" -ForegroundColor Green
    Start-Sleep -Seconds 3
} catch {
    Write-Host "⚠️  Could not clear faults: $($_.Exception.Message)" -ForegroundColor Yellow
}

# Step 1: Inject fault
Write-Host "`n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host "[STEP 1] Injecting $($config.Name) fault..." -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray

Write-Host "`n📋 Manual Action Required:" -ForegroundColor Cyan
Write-Host "   1. Open Dashboard: http://localhost:8000/dashboard" -ForegroundColor White
Write-Host "   2. Click the '$($config.Button)' button" -ForegroundColor White
Write-Host "   3. You should see confirmation in the dashboard" -ForegroundColor White

$continue = Read-Host "`nPress ENTER after you've clicked the button"

Write-Host "`nVerifying fault injection via API..." -ForegroundColor Gray
try {
    $headers = @{ "Authorization" = "Bearer $TOKEN" }
    $response = Invoke-RestMethod -Uri "http://localhost:8000/inject/$ErrorType" -Method Post -Headers $headers
    Write-Host "✅ Fault injected: $($response.message)" -ForegroundColor Green
} catch {
    Write-Host "⚠️  API injection failed, but dashboard injection may have worked" -ForegroundColor Yellow
}

Start-Sleep -Seconds 2

# Step 2: Verify fault is active
Write-Host "`n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host "[STEP 2] Verifying fault is active..." -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray

Write-Host "`n📋 Manual Action Required:" -ForegroundColor Cyan
Write-Host "   1. Open Shopping Site: http://localhost:8000/" -ForegroundColor White
Write-Host "   2. Try to trigger the error:" -ForegroundColor White
if ($ErrorType -eq "503_overload") {
    Write-Host "      - Just refresh the page or click any link" -ForegroundColor Gray
} elseif ($ErrorType -eq "504_timeout") {
    Write-Host "      - Add item to cart → Checkout → Try to complete payment" -ForegroundColor Gray
} elseif ($ErrorType -eq "500_crash") {
    Write-Host "      - Add item to cart → Checkout → Click 'Complete Acquisition'" -ForegroundColor Gray
}
Write-Host "   3. You should see a $($config.ExpectedStatus) error page" -ForegroundColor White

$continue = Read-Host "`nDid you see the $($config.ExpectedStatus) error? (y/n)"

if ($continue -ne 'y') {
    Write-Host "❌ Fault may not be active. Check dashboard logs." -ForegroundColor Red
    exit
}

Write-Host "✅ Fault is active - site is broken as expected" -ForegroundColor Green

# Step 3: Monitor AI detection and remediation
Write-Host "`n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host "[STEP 3] Monitoring AI detection and remediation..." -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray

Write-Host "`n📋 Watch the Dashboard 'Action Pulse' section (bottom right)" -ForegroundColor Cyan
Write-Host "   You should see logs appearing within 10-30 seconds..." -ForegroundColor White
Write-Host "`n   Monitoring remediation engine logs (60 seconds max)..." -ForegroundColor Gray

$startTime = Get-Date
$detected = $false
$remediated = $false
$verified = $false
$suppressed = $false
$lastLog = ""

while (((Get-Date) - $startTime).TotalSeconds -lt 60) {
    $logs = docker logs remediation_engine --tail 30 2>&1 | Out-String
    
    # Detection
    if (($logs -match "ERROR DETECTED" -or $logs -match "DIAGNOSIS") -and -not $detected) {
        Write-Host "`n   ✅ [$(((Get-Date) - $startTime).TotalSeconds.ToString('F0'))s] AI DETECTED ERROR!" -ForegroundColor Green
        $detected = $true
        
        # Extract and show the detection message
        $detectionLine = $logs -split "`n" | Where-Object { $_ -match "ERROR DETECTED|DIAGNOSIS" } | Select-Object -Last 1
        if ($detectionLine) {
            Write-Host "      $detectionLine" -ForegroundColor Gray
        }
    }
    
    # Suppression (for overload)
    if ($logs -match "SUPPRESS.*SCALING" -and -not $suppressed) {
        Write-Host "`n   ✅ [$(((Get-Date) - $startTime).TotalSeconds.ToString('F0'))s] AI SUPPRESSED RESTART (High CPU detected)" -ForegroundColor Green
        $suppressed = $true
        Write-Host "      This is correct - overload needs scaling, not restart" -ForegroundColor Gray
        break
    }
    
    # Remediation
    if ($logs -match "REMEDIATION.*Restarting" -and -not $remediated) {
        Write-Host "`n   ✅ [$(((Get-Date) - $startTime).TotalSeconds.ToString('F0'))s] AI TRIGGERED REMEDIATION!" -ForegroundColor Green
        $remediated = $true
        Write-Host "      Container is being restarted..." -ForegroundColor Gray
    }
    
    # Health verification
    if ($logs -match "Health VERIFIED" -and -not $verified) {
        Write-Host "`n   ✅ [$(((Get-Date) - $startTime).TotalSeconds.ToString('F0'))s] HEALTH VERIFICATION PASSED!" -ForegroundColor Green
        $verified = $true
        Write-Host "      Faults are being cleared..." -ForegroundColor Gray
    }
    
    # Recovery
    if ($logs -match "RECOVERY.*restored" -and $verified) {
        Write-Host "`n   ✅ [$(((Get-Date) - $startTime).TotalSeconds.ToString('F0'))s] RECOVERY COMPLETED!" -ForegroundColor Green
        break
    }
    
    Start-Sleep -Seconds 2
}

# Step 4: Verify outcome
Write-Host "`n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host "[STEP 4] Verifying outcome..." -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray

if ($config.ShouldRestart) {
    # Should have restarted and recovered
    if ($verified) {
        Write-Host "`n✅ AI completed full remediation cycle!" -ForegroundColor Green
        Write-Host "`n📋 Manual Verification:" -ForegroundColor Cyan
        Write-Host "   1. Go back to the shopping site" -ForegroundColor White
        Write-Host "   2. Try the same action that caused the error" -ForegroundColor White
        Write-Host "   3. It should work normally now" -ForegroundColor White
        
        $recovered = Read-Host "`nDid the site recover? (y/n)"
        
        if ($recovered -eq 'y') {
            Write-Host "`n🎉 TEST PASSED!" -ForegroundColor Green
            Write-Host "   - Fault injected ✅" -ForegroundColor White
            Write-Host "   - Site broke ✅" -ForegroundColor White
            Write-Host "   - AI detected ✅" -ForegroundColor White
            Write-Host "   - AI restarted container ✅" -ForegroundColor White
            Write-Host "   - Health verified ✅" -ForegroundColor White
            Write-Host "   - Site recovered ✅" -ForegroundColor White
            Write-Host "`n   This is REAL self-healing!" -ForegroundColor Green
        } else {
            Write-Host "`n⚠️  TEST INCOMPLETE" -ForegroundColor Yellow
            Write-Host "   AI completed remediation but site may need more time" -ForegroundColor Gray
            Write-Host "   Check: docker logs api_service --tail 20" -ForegroundColor Gray
        }
    } else {
        Write-Host "`n⚠️  TEST INCOMPLETE" -ForegroundColor Yellow
        Write-Host "   Detection: $(if($detected){'✅'}else{'❌'})" -ForegroundColor White
        Write-Host "   Remediation: $(if($remediated){'✅'}else{'❌'})" -ForegroundColor White
        Write-Host "   Verification: $(if($verified){'✅'}else{'❌'})" -ForegroundColor White
        Write-Host "`n   Check logs: docker logs remediation_engine --tail 50" -ForegroundColor Gray
    }
} else {
    # Should have been suppressed (overload)
    if ($suppressed) {
        Write-Host "`n✅ AI correctly suppressed restart!" -ForegroundColor Green
        Write-Host "   This is the correct behavior for overload (high CPU)" -ForegroundColor Gray
        Write-Host "`n📋 Manual Reset Required:" -ForegroundColor Cyan
        Write-Host "   Overload requires scaling, not restart. Clearing fault manually..." -ForegroundColor White
        
        try {
            $headers = @{ "Authorization" = "Bearer $TOKEN" }
            Invoke-RestMethod -Uri "http://localhost:8000/inject/reset?target=all" -Method Post -Headers $headers | Out-Null
            Write-Host "   ✅ Fault cleared manually" -ForegroundColor Green
        } catch {
            Write-Host "   ⚠️  Could not clear fault" -ForegroundColor Yellow
        }
        
        Write-Host "`n🎉 TEST PASSED!" -ForegroundColor Green
        Write-Host "   - Fault injected ✅" -ForegroundColor White
        Write-Host "   - Site broke ✅" -ForegroundColor White
        Write-Host "   - AI detected ✅" -ForegroundColor White
        Write-Host "   - AI checked CPU (high) ✅" -ForegroundColor White
        Write-Host "   - AI suppressed restart ✅" -ForegroundColor White
        Write-Host "   - Recommended scaling ✅" -ForegroundColor White
        Write-Host "`n   This is SMART self-healing!" -ForegroundColor Green
    } else {
        Write-Host "`n⚠️  TEST INCOMPLETE" -ForegroundColor Yellow
        Write-Host "   AI should have suppressed restart but didn't" -ForegroundColor Gray
        Write-Host "   Check if CPU simulation is working" -ForegroundColor Gray
    }
}

# Show recent logs
Write-Host "`n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host "[LOGS] Recent Remediation Engine Logs:" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray

$recentLogs = docker logs remediation_engine --tail 15 2>&1 | Out-String
$recentLogs -split "`n" | Where-Object { 
    $_ -match "ERROR DETECTED|REMEDIATION|RECOVERY|DIAGNOSIS|Health VERIFIED|SUPPRESS" 
} | Select-Object -Last 10 | ForEach-Object {
    Write-Host "   $_" -ForegroundColor Gray
}

Write-Host "`n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "Test complete for $($config.Name)" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`n" -ForegroundColor Cyan
