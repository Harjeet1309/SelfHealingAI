# Test 504 Timeout Isolation
# Verify that 504 fault only affects payment endpoint, not cart

$TOKEN = "changeme-local-dev"
$headers = @{ "Authorization" = "Bearer $TOKEN" }

Write-Host "`n=== Testing 504 Timeout Fault Isolation ===" -ForegroundColor Cyan

# Step 1: Clear all faults
Write-Host "`n[1] Clearing all faults..." -ForegroundColor Yellow
Invoke-RestMethod -Uri "http://localhost:8000/inject/reset?target=all" -Method Post -Headers $headers | Out-Null
Write-Host "✅ Faults cleared" -ForegroundColor Green

# Step 2: Inject 504 timeout fault
Write-Host "`n[2] Injecting 504_timeout fault..." -ForegroundColor Yellow
$result = Invoke-RestMethod -Uri "http://localhost:8000/inject/504_timeout" -Method Post -Headers $headers
Write-Host "✅ Fault injected: $($result.fault_key)" -ForegroundColor Green

# Step 3: Test cart endpoint (should work - NOT affected by payment fault)
Write-Host "`n[3] Testing /cart/add endpoint (should work)..." -ForegroundColor Yellow
try {
    $cartResponse = Invoke-WebRequest -Uri "http://localhost:8000/cart/add" -Method Post -ErrorAction Stop
    Write-Host "✅ Cart endpoint works! Status: $($cartResponse.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "❌ Cart endpoint failed! Status: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
    Write-Host "   This is WRONG - cart should not be affected by 504_timeout fault" -ForegroundColor Red
}

# Step 4: Test payment endpoint (should fail with 504)
Write-Host "`n[4] Testing /payment endpoint (should fail with 504)..." -ForegroundColor Yellow
try {
    $paymentResponse = Invoke-WebRequest -Uri "http://localhost:8000/payment" -Method Post -ErrorAction Stop
    Write-Host "⚠️  Payment endpoint worked! This is WRONG - it should return 504" -ForegroundColor Yellow
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    if ($statusCode -eq 504) {
        Write-Host "✅ Payment endpoint correctly returns 504!" -ForegroundColor Green
    } else {
        Write-Host "❌ Payment endpoint returned $statusCode (expected 504)" -ForegroundColor Red
    }
}

# Step 5: Clear fault
Write-Host "`n[5] Clearing fault..." -ForegroundColor Yellow
Invoke-RestMethod -Uri "http://localhost:8000/inject/reset?target=all" -Method Post -Headers $headers | Out-Null
Write-Host "✅ Test complete" -ForegroundColor Green

Write-Host "`n=== Summary ===" -ForegroundColor Cyan
Write-Host "504_timeout fault should ONLY affect /payment endpoint" -ForegroundColor White
Write-Host "If /cart/add also failed, there's a bug in the fault isolation" -ForegroundColor White
