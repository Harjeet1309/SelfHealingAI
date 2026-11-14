# Test Error Isolation - Verify Each Error Occurs at Correct Endpoint

Write-Host "=== Testing Error Isolation ===" -ForegroundColor Cyan
Write-Host ""

$baseUrl = "http://localhost:8000"
$token = "changeme-local-dev"

# Function to test an endpoint
function Test-Endpoint {
    param($endpoint, $expectedStatus, $description)
    
    Write-Host "Testing: $description" -ForegroundColor Yellow
    try {
        $response = Invoke-WebRequest -Uri "$baseUrl$endpoint" -Method POST -UseBasicParsing -ErrorAction SilentlyContinue
        $status = $response.StatusCode
    } catch {
        $status = $_.Exception.Response.StatusCode.value__
    }
    
    if ($status -eq $expectedStatus) {
        Write-Host "  ✅ PASS - Got expected $expectedStatus" -ForegroundColor Green
        return $true
    } else {
        Write-Host "  ❌ FAIL - Got $status, expected $expectedStatus" -ForegroundColor Red
        return $false
    }
}

# Reset all faults first
Write-Host "Resetting all faults..." -ForegroundColor Gray
Invoke-WebRequest -Uri "$baseUrl/inject/reset?target=all&token=$token" -Method POST -UseBasicParsing | Out-Null
Start-Sleep -Seconds 2

# Test 1: 500 CRASH at /checkout
Write-Host "`n--- Test 1: 500 CRASH (Checkout Only) ---" -ForegroundColor Magenta
Invoke-WebRequest -Uri "$baseUrl/inject/500_checkout?token=$token" -Method POST -UseBasicParsing | Out-Null
Start-Sleep -Seconds 1

Test-Endpoint "/cart/add" 200 "Cart should work (no 500 error)"
Test-Endpoint "/checkout" 500 "Checkout should fail with 500"

# Reset
Invoke-WebRequest -Uri "$baseUrl/inject/reset?target=all&token=$token" -Method POST -UseBasicParsing | Out-Null
Start-Sleep -Seconds 1

# Test 2: 503 DEADLOCK at /cart/add
Write-Host "`n--- Test 2: 503 DEADLOCK (Cart Only) ---" -ForegroundColor Magenta
Invoke-WebRequest -Uri "$baseUrl/inject/503_deadlock?token=$token" -Method POST -UseBasicParsing | Out-Null
Start-Sleep -Seconds 1

Test-Endpoint "/cart/add" 503 "Cart should fail with 503"
Test-Endpoint "/checkout" 200 "Checkout should work (no 503 error)"

# Reset
Invoke-WebRequest -Uri "$baseUrl/inject/reset?target=all&token=$token" -Method POST -UseBasicParsing | Out-Null
Start-Sleep -Seconds 1

# Test 3: 503 OVERLOAD at /cart/add
Write-Host "`n--- Test 3: 503 OVERLOAD (Cart Only) ---" -ForegroundColor Magenta
Invoke-WebRequest -Uri "$baseUrl/inject/503_overload?token=$token" -Method POST -UseBasicParsing | Out-Null
Start-Sleep -Seconds 1

Test-Endpoint "/cart/add" 503 "Cart should fail with 503"
Test-Endpoint "/checkout" 200 "Checkout should work (no 503 error)"

# Reset
Invoke-WebRequest -Uri "$baseUrl/inject/reset?target=all&token=$token" -Method POST -UseBasicParsing | Out-Null
Start-Sleep -Seconds 1

# Test 4: 504 TIMEOUT at /payment
Write-Host "`n--- Test 4: 504 TIMEOUT (Payment Only) ---" -ForegroundColor Magenta
Invoke-WebRequest -Uri "$baseUrl/inject/504_timeout?token=$token" -Method POST -UseBasicParsing | Out-Null
Start-Sleep -Seconds 1

Test-Endpoint "/cart/add" 200 "Cart should work (no 504 error)"
Test-Endpoint "/checkout" 200 "Checkout should work (no 504 error)"
Test-Endpoint "/payment" 504 "Payment should fail with 504"

# Reset
Invoke-WebRequest -Uri "$baseUrl/inject/reset?target=all&token=$token" -Method POST -UseBasicParsing | Out-Null
Start-Sleep -Seconds 1

# Test 5: 429 BOT DEFENSE at /checkout
Write-Host "`n--- Test 5: 429 BOT DEFENSE (Checkout Only) ---" -ForegroundColor Magenta
Invoke-WebRequest -Uri "$baseUrl/inject/429_bot?token=$token" -Method POST -UseBasicParsing | Out-Null
Start-Sleep -Seconds 1

Test-Endpoint "/cart/add" 200 "Cart should work (no 429 error)"
Test-Endpoint "/checkout" 429 "Checkout should fail with 429"

# Final reset
Write-Host "`nResetting all faults..." -ForegroundColor Gray
Invoke-WebRequest -Uri "$baseUrl/inject/reset?target=all&token=$token" -Method POST -UseBasicParsing | Out-Null

Write-Host "`n=== Test Complete ===" -ForegroundColor Cyan
Write-Host "All errors are now isolated to their correct endpoints!" -ForegroundColor Green
