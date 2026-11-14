# Complete Error Endpoint Analysis

## Overview
This document explains EXACTLY where each error occurs in your system and how the error injection works.

---

## Available Endpoints

### 1. `/cart/add` (POST) - "Acquire Item" Button
**What it does:** Adds item to cart  
**Errors that occur here:**
- ✅ **503 DEADLOCK** - When `cart` fault is active
- ✅ **503 OVERLOAD** - When `overload` fault is active
- ✅ **503 DB_LATENCY** - Cross-cutting fault (affects multiple endpoints)
- ✅ **503 LOCK_CONTENTION** - Cross-cutting fault
- ✅ **503 DEPENDENCY_RESET** - Cross-cutting fault

### 2. `/checkout` (POST) - "Complete Acquisition" Button
**What it does:** Processes checkout  
**Errors that occur here:**
- ✅ **500 CRASH** - When `checkout` fault is active
- ✅ **429 BOT DEFENSE** - When `security` fault is active
- ✅ **503 DB_LATENCY** - Cross-cutting fault
- ✅ **503 LOCK_CONTENTION** - Cross-cutting fault
- ✅ **503 DEPENDENCY_RESET** - Cross-cutting fault

### 3. `/payment` (POST) - "Verify Biometrics" Button
**What it does:** Processes payment  
**Errors that occur here:**
- ✅ **504 TIMEOUT** - When `payment` fault is active
- ✅ **504 DEPENDENCY_TIMEOUT** - Cross-cutting fault (payment provider slow)
- ✅ **503 DB_LATENCY** - Cross-cutting fault
- ✅ **503 DEPENDENCY_RESET** - Cross-cutting fault

---

## Error Injection Types

### Primary Faults (Isolated to ONE endpoint)

#### 1. **500 CRASH** (`checkout` fault)
- **Endpoint:** `/checkout` ONLY
- **Trigger:** `POST /inject/500_checkout`
- **Code Location:** `routes.py` line ~450
```python
if _is_fault_active("checkout"):
    raise HTTPException(status_code=500, detail="Checkout crash")
```

#### 2. **503 DEADLOCK** (`cart` fault)
- **Endpoint:** `/cart/add` ONLY
- **Trigger:** `POST /inject/503_deadlock`
- **Code Location:** `routes.py` line ~440
```python
if _is_fault_active("cart"):
    raise HTTPException(status_code=503, detail="Service Unavailable (Deadlock)")
```

#### 3. **503 OVERLOAD** (`overload` fault)
- **Endpoint:** `/cart/add` ONLY (but CPU spike is system-wide)
- **Trigger:** `POST /inject/503_overload`
- **Code Location:** `routes.py` line ~444
```python
if _is_fault_active("overload"):
    raise HTTPException(status_code=503, detail="Service Unavailable (Overloaded)")
```
- **Special:** Also starts a CPU burner thread to simulate high CPU

#### 4. **504 TIMEOUT** (`payment` fault)
- **Endpoint:** `/payment` ONLY
- **Trigger:** `POST /inject/504_timeout`
- **Code Location:** `routes.py` line ~467
```python
if _is_fault_active("payment"):
    await asyncio.sleep(4)
    raise HTTPException(status_code=504, detail="Gateway Timeout")
```

#### 5. **429 BOT DEFENSE** (`security` fault)
- **Endpoint:** `/checkout` ONLY
- **Trigger:** `POST /inject/429_bot`
- **Code Location:** `routes.py` line ~455
```python
if _is_fault_active("security"):
    raise HTTPException(status_code=429, detail="Too Many Requests — Bot Defense Active")
```

---

### Cross-Cutting Faults (Affect MULTIPLE endpoints)

#### 6. **DB_LATENCY** (`db_latency` fault)
- **Endpoints:** `/cart/add`, `/checkout`, `/payment`
- **Trigger:** `POST /inject/db_latency`
- **Code Location:** `routes.py` line ~360
```python
async def _maybe_apply_db_latency():
    if not _is_fault_active("db_latency"):
        return
    intensity = system_state["db_latency"]["intensity"]
    delay = random.uniform(0.25, 1.5) * intensity
    await asyncio.sleep(min(delay, 4.0))
```
- **Behavior:** Adds random delay (0.25s - 1.5s) to simulate slow database

#### 7. **LOCK_CONTENTION** (`lock_contention` fault)
- **Endpoints:** `/cart/add`, `/checkout`
- **Trigger:** `POST /inject/lock_contention`
- **Code Location:** `routes.py` line ~368
```python
async def _maybe_apply_lock_contention():
    if not _is_fault_active("lock_contention"):
        return
    intensity = system_state["lock_contention"]["intensity"]
    fail_probability = min(0.25 + (0.6 * intensity), 0.95)
    if random.random() < fail_probability:
        await asyncio.sleep(wait_delay)
        raise HTTPException(status_code=503, detail="Database lock wait timeout exceeded")
```
- **Behavior:** Probabilistic failure (25%-95% chance based on intensity)

#### 8. **DEPENDENCY_TIMEOUT** (`dependency_timeout` fault)
- **Endpoints:** `/payment` ONLY
- **Trigger:** `POST /inject/dependency_timeout`
- **Code Location:** `routes.py` line ~393
```python
async def _maybe_raise_dependency_timeout(component: str):
    if not _is_fault_active("dependency_timeout"):
        return
    intensity = system_state["dependency_timeout"]["intensity"]
    await asyncio.sleep(min(1.8 + (3.0 * intensity), 7.0))
    raise HTTPException(status_code=504, detail=f"{component} upstream timeout")
```
- **Behavior:** Adds 1.8s - 7s delay then raises 504

#### 9. **DEPENDENCY_RESET** (`dependency_reset` fault)
- **Endpoints:** `/cart/add`, `/checkout`, `/payment`
- **Trigger:** `POST /inject/dependency_reset`
- **Code Location:** `routes.py` line ~383
```python
def _maybe_raise_dependency_reset(component: str):
    if not _is_fault_active("dependency_reset"):
        return
    intensity = system_state["dependency_reset"]["intensity"]
    fail_probability = min(0.2 + (0.65 * intensity), 0.95)
    if random.random() < fail_probability:
        raise HTTPException(status_code=503, detail=f"{component} upstream connection reset by peer")
```
- **Behavior:** Probabilistic failure (20%-95% chance)

---

## Frontend Error Display Logic

### Page-Specific Error Overlays

The frontend uses `page_faults` parameter to control which errors show overlays on which pages:

#### Store Page (`/`) - "Acquire Item" button
```python
return get_base_layout(content, state, "home", page_faults=[503])
```
- **Shows overlay for:** 503 errors only (cart deadlock, overload)
- **Hides overlay for:** 500, 504, 429 errors

#### Cart Page (`/cart`) - "Proceed to Review" button
```python
return get_base_layout(content, state, "home", page_faults=[503])
```
- **Shows overlay for:** 503 errors only
- **Hides overlay for:** 500, 504, 429 errors

#### Checkout Review Page (`/checkout-page`) - "Complete Acquisition" button
```python
return get_base_layout(content, state, "home", page_faults=[500])
```
- **Shows overlay for:** 500 errors only (checkout crash)
- **Hides overlay for:** 503, 504, 429 errors

#### Payment Page (`/payment-page`) - "Verify Biometrics" button
```python
return get_base_layout(content, state, "home", page_faults=[504])
```
- **Shows overlay for:** 504 errors only (payment timeout)
- **Hides overlay for:** 500, 503, 429 errors

---

## The Problem You Identified

### Issue: "All errors occurring at Add to Cart"

**Root Cause:** The error overlay logic was NOT properly filtering by page.

**What was happening:**
1. You inject a 500 CRASH fault (checkout error)
2. The fault becomes active globally
3. You're on the Store page (/) clicking "Acquire Item" → calls `/cart/add`
4. `/cart/add` doesn't have the checkout fault check, so it succeeds
5. BUT the page overlay was showing 500 error because it wasn't checking `page_faults`

**The Fix Applied:**
The `get_base_layout()` function now checks:
```python
show_overlay = (
    state["status"] == "FAULT" and
    (page_faults is None or active_code in page_faults)
)
```

This ensures:
- Store page ONLY shows overlays for 503 errors
- Checkout page ONLY shows overlays for 500 errors
- Payment page ONLY shows overlays for 504 errors

---

## How to Test Each Error

### Test 500 CRASH (Checkout)
1. Go to store page → Click "Acquire Item"
2. Click "Proceed to Review" 
3. **Inject:** `curl -X POST http://localhost:8000/inject/500_checkout`
4. Click "Complete Acquisition" → **500 error overlay appears**

### Test 503 DEADLOCK (Cart)
1. Go to store page
2. **Inject:** `curl -X POST http://localhost:8000/inject/503_deadlock`
3. Click "Acquire Item" → **503 error overlay appears**

### Test 503 OVERLOAD (Cart)
1. Go to store page
2. **Inject:** `curl -X POST http://localhost:8000/inject/503_overload`
3. Click "Acquire Item" → **503 error overlay appears**

### Test 504 TIMEOUT (Payment)
1. Go through cart → checkout
2. **Inject:** `curl -X POST http://localhost:8000/inject/504_timeout`
3. Click "Verify Biometrics" → **504 error overlay appears**

### Test 429 BOT DEFENSE (Checkout)
1. Go to store → cart → checkout review
2. **Inject:** `curl -X POST http://localhost:8000/inject/429_bot`
3. Click "Complete Acquisition" → **429 error (no overlay, just error response)**

---

## Summary

✅ **Each error NOW occurs at the CORRECT endpoint**  
✅ **Error overlays NOW show on the CORRECT pages**  
✅ **Cross-cutting faults affect multiple endpoints as designed**  
✅ **Primary faults are isolated to their specific endpoints**

The system is working as intended. The confusion was due to the overlay display logic not filtering by page-specific fault codes.
