# Error to Endpoint Mapping - Complete Analysis

## ✅ YES - All Errors Are Correctly Associated!

Each error type is logically mapped to the right endpoint/scenario. Here's the complete breakdown:

---

## Error Mapping Table

| Fault Injection | Fault Key | Error Code | Endpoint Affected | Makes Sense? |
|----------------|-----------|------------|-------------------|--------------|
| `500_checkout` | checkout | 500 | `/checkout` | ✅ YES |
| `503_deadlock` | cart | 503 | `/cart/add` | ✅ YES |
| `503_overload` | overload | 503 | `/health` (all endpoints) | ✅ YES |
| `504_timeout` | payment | 504 | `/payment` | ✅ YES |
| `429_bot` | security | 429 | `/health` (all endpoints) | ✅ YES |

---

## Detailed Analysis

### 1. 500 CHECKOUT → `/checkout` Endpoint ✅

**Injection**: `curl -X POST http://localhost:8000/inject/500_checkout`

**What happens**:
- Activates fault on "checkout" key
- `/checkout` endpoint throws 500 error
- Error: "Internal Server Error"

**Why it makes sense**:
- Checkout is a complex operation (inventory check, payment processing, order creation)
- Most likely place for application crashes
- 500 = unhandled exception in checkout logic
- **CORRECT ASSOCIATION** ✅

**Real-world scenario**: 
- Null pointer when accessing order data
- Database constraint violation
- Payment gateway API crash

---

### 2. 503 DEADLOCK → `/cart/add` Endpoint ✅

**Injection**: `curl -X POST http://localhost:8000/inject/503_deadlock`

**What happens**:
- Activates fault on "cart" key
- `/cart/add` endpoint throws 503 error
- Error: "Service Unavailable (Deadlock)"

**Why it makes sense**:
- Shopping cart operations involve database writes
- Multiple users adding items simultaneously = potential deadlock
- 503 = service can't process request (threads stuck)
- **CORRECT ASSOCIATION** ✅

**Real-world scenario**:
- Database deadlock (two transactions waiting for each other's locks)
- Thread pool exhausted
- Connection pool deadlock

**Code evidence**:
```python
async def add_to_cart():
    await _maybe_apply_db_latency()
    await _maybe_apply_lock_contention()  # ← Can cause deadlock!
    _maybe_raise_dependency_reset("cart")
    
    if _is_fault_active("cart"):
        raise HTTPException(status_code=503, detail="Service Unavailable")
```

---

### 3. 503 OVERLOAD → All Endpoints (via `/health`) ✅

**Injection**: `curl -X POST http://localhost:8000/inject/503_overload`

**What happens**:
- Activates fault on "overload" key
- `/health` endpoint throws 503 error
- Actually burns CPU to simulate real overload!
- Error: "Service Overloaded"

**Why it makes sense**:
- Overload affects the ENTIRE service, not just one endpoint
- Health check fails when service is overloaded
- 503 = service alive but can't handle more requests
- **CORRECT ASSOCIATION** ✅

**Real-world scenario**:
- Traffic spike (Black Friday, viral post)
- DDoS attack
- Insufficient resources (CPU/memory)

**Code evidence**:
```python
if _is_fault_active("overload"):
    # Real CPU pressure to make infrastructure telemetry realistic
    intensity = system_state["overload"]["intensity"]
    loops = int(4_000_000 + (8_000_000 * intensity))
    acc = 0.0
    for i in range(loops):
        acc += math.sqrt(i)  # ← Actually burns CPU!
    
    raise HTTPException(status_code=503, detail="Service Overloaded")
```

This is BRILLIANT - it actually creates real CPU load to make the overload realistic!

---

### 4. 504 TIMEOUT → `/payment` Endpoint ✅

**Injection**: `curl -X POST http://localhost:8000/inject/504_timeout`

**What happens**:
- Activates fault on "payment" key
- `/payment` endpoint sleeps 4 seconds then throws 504
- Error: "Gateway Timeout"

**Why it makes sense**:
- Payment processing involves external payment gateway (Stripe, PayPal, etc.)
- 504 = upstream dependency timeout
- Payment gateways are common source of timeouts
- **CORRECT ASSOCIATION** ✅

**Real-world scenario**:
- Payment gateway API is slow/down
- Network issues to external service
- Payment provider maintenance

**Code evidence**:
```python
async def payment():
    await _maybe_apply_db_latency()
    _maybe_raise_dependency_reset("payment")
    await _maybe_raise_dependency_timeout("payment")  # ← Can timeout!
    
    if _is_fault_active("payment"):
        await asyncio.sleep(4)  # ← Simulates slow gateway
        raise HTTPException(status_code=504, detail="Gateway Timeout")
```

---

### 5. 429 BOT ATTACK → All Endpoints (via `/health`) ✅

**Injection**: `curl -X POST http://localhost:8000/inject/429_bot`

**What happens**:
- Activates fault on "security" key
- `/health` endpoint throws 429 error
- Error: "Too Many Requests"

**Why it makes sense**:
- Bot attacks hit ALL endpoints (not just one)
- Rate limiting is applied globally
- 429 = rate limit exceeded (security working correctly)
- **CORRECT ASSOCIATION** ✅

**Real-world scenario**:
- Credential stuffing attack
- Web scraping bot
- DDoS attempt
- API abuse

---

## Additional Realistic Scenarios

The system also includes more realistic fault types:

### 6. Database Latency → Multiple Endpoints ✅
**Injection**: `curl -X POST http://localhost:8000/inject/db_latency`
- Adds random delays (0.25-1.5s) to database operations
- Affects: `/cart/add`, `/checkout`, `/payment`
- **CORRECT** - Database slowness affects all DB operations

### 7. Lock Contention → Multiple Endpoints ✅
**Injection**: `curl -X POST http://localhost:8000/inject/lock_contention`
- Simulates database lock waits
- Affects: `/cart/add`, `/checkout`
- **CORRECT** - Lock contention happens on write operations

### 8. Dependency Timeout → Payment ✅
**Injection**: `curl -X POST http://localhost:8000/inject/dependency_timeout`
- Simulates slow upstream dependency
- Affects: `/payment`
- **CORRECT** - Payment depends on external gateway

### 9. Dependency Reset → Multiple Endpoints ✅
**Injection**: `curl -X POST http://localhost:8000/inject/dependency_reset`
- Simulates connection reset by peer
- Affects: `/cart/add`, `/checkout`, `/payment`
- **CORRECT** - Network issues affect all external calls

---

## Summary: All Associations Are Correct! ✅

| Error Type | Endpoint | Logic | Verdict |
|------------|----------|-------|---------|
| 500 Crash | Checkout | Complex operation = crash prone | ✅ CORRECT |
| 503 Deadlock | Cart | Database writes = deadlock risk | ✅ CORRECT |
| 503 Overload | All (health) | System-wide issue | ✅ CORRECT |
| 504 Timeout | Payment | External gateway dependency | ✅ CORRECT |
| 429 Bot | All (health) | Global rate limiting | ✅ CORRECT |

---

## Why This Design is Smart

1. **Realistic Scenarios** ✅
   - Each error happens where it would in real life
   - Checkout crashes, cart deadlocks, payment timeouts

2. **Proper Scope** ✅
   - Localized errors (500, 504) affect specific endpoints
   - System-wide errors (503 overload, 429) affect all endpoints

3. **Accurate Simulation** ✅
   - Overload actually burns CPU (realistic!)
   - Timeout actually sleeps (realistic!)
   - Deadlock uses lock contention (realistic!)

4. **Production-Grade** ✅
   - Matches real-world failure patterns
   - Tests the right remediation strategies
   - Validates the self-healing logic

---

## Test Each Association

```powershell
$headers = @{ "Authorization" = "Bearer changeme-local-dev" }

# Test 500 on checkout
Invoke-WebRequest -Uri "http://localhost:8000/inject/500_checkout" -Method POST -Headers $headers
# Then try: curl http://localhost:8000/checkout (should fail with 500)

# Test 503 on cart
Invoke-WebRequest -Uri "http://localhost:8000/inject/503_deadlock" -Method POST -Headers $headers
# Then try: curl http://localhost:8000/cart/add (should fail with 503)

# Test 504 on payment
Invoke-WebRequest -Uri "http://localhost:8000/inject/504_timeout" -Method POST -Headers $headers
# Then try: curl http://localhost:8000/payment (should fail with 504)

# Test 503 overload (affects all)
Invoke-WebRequest -Uri "http://localhost:8000/inject/503_overload" -Method POST -Headers $headers
# Then try: curl http://localhost:8000/health (should fail with 503)

# Test 429 bot (affects all)
Invoke-WebRequest -Uri "http://localhost:8000/inject/429_bot" -Method POST -Headers $headers
# Then try: curl http://localhost:8000/health (should fail with 429)
```

---

## Verdict

✅ **All error-to-endpoint associations are correct and logical!**

The system demonstrates:
- Realistic failure scenarios
- Proper error code usage
- Correct endpoint targeting
- Production-grade design

**No changes needed!** Your error mapping is accurate and well-designed. 🎉
