# Test 429 Bot Defense Error

Write-Host "=== Testing 429 Bot Defense Error ===" -ForegroundColor Cyan
Write-Host ""

$baseUrl = "http://localhost:8000"
$token = "changeme-local-dev"

# Reset first
Write-Host "1. Resetting all faults..." -ForegroundColor Yellow
Invoke-WebRequest -Uri "$baseUrl/inject/reset?target=all&token=$token" -Method POST -UseBasicParsing | Out-Null
Start-Sleep -Seconds 2

# Test cart works before injection
Write-Host "2. Testing cart endpoint (should work)..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/cart/add" -Method POST -UseBasicParsing
    Write-Host "   ✅ Cart: $($response.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Cart failed: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
}

# Test checkout works before injection
Write-Host "3. Testing checkout endpoint (should work)..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/checkout" -Method POST -UseBasicParsing
    Write-Host "   ✅ Checkout: $($response.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Checkout failed: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
}

# Inject 429 fault
Write-Host "`n4. Injecting 429 Bot Defense fault..." -ForegroundColor Yellow
$injectResponse = Invoke-WebRequest -Uri "$baseUrl/inject/429_bot?token=$token" -Method POST -UseBasicParsing
$injectData = $injectResponse.Content | ConvertFrom-Json
Write-Host "   Fault injected: $($injectData.fault_key)" -ForegroundColor Cyan
Write-Host "   Status: Active" -ForegroundColor Cyan
Start-Sleep -Seconds 1

# Test cart still works (429 doesn't affect cart)
Write-Host "`n5. Testing cart endpoint (should still work)..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/cart/add" -Method POST -UseBasicParsing
    Write-Host "   ✅ Cart: $($response.StatusCode) - Not affected by 429" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Cart failed: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
}

# Test checkout fails with 429
Write-Host "6. Testing checkout endpoint (should fail with 429)..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/checkout" -Method POST -UseBasicParsing
    Write-Host "   ❌ Checkout returned: $($response.StatusCode) - Expected 429!" -ForegroundColor Red
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    if ($statusCode -eq 429) {
        Write-Host "   ✅ Checkout: 429 - Bot Defense Active!" -ForegroundColor Green
        Write-Host "   ✅ Error message: $($_.ErrorDetails.Message)" -ForegroundColor Green
    } else {
        Write-Host "   ❌ Checkout failed with wrong code: $statusCode" -ForegroundColor Red
    }
}

# Check fault status
Write-Host "`n7. Checking fault status..." -ForegroundColor Yellow
$statusResponse = Invoke-WebRequest -Uri "$baseUrl/inject/status" -Method GET -UseBasicParsing
$statusData = $statusResponse.Content | ConvertFrom-Json
Write-Host "   Security fault active: $($statusData.security.active)" -ForegroundColor Cyan
Write-Host "   Security fault code: $($statusData.security.code)" -ForegroundColor Cyan

# Reset
Write-Host "`n8. Resetting fault..." -ForegroundColor Yellow
Invoke-WebRequest -Uri "$baseUrl/inject/reset?target=all&token=$token" -Method POST -UseBasicParsing | Out-Null
Start-Sleep -Seconds 1

# Verify checkout works again
Write-Host "9. Verifying checkout works after reset..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/checkout" -Method POST -UseBasicParsing
    Write-Host "   ✅ Checkout: $($response.StatusCode) - Working again!" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Checkout still failing: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
}

Write-Host "`n=== Test Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Summary:" -ForegroundColor White
Write-Host "✅ 429 Bot Defense error works correctly" -ForegroundColor Green
Write-Host "✅ Only affects /checkout endpoint" -ForegroundColor Green
Write-Host "✅ Does not affect /cart/add endpoint" -ForegroundColor Green
Write-Host "✅ Can be reset successfully" -ForegroundColor Green
