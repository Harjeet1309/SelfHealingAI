# Quick Fix Reference Card

## 🚀 Quick Start (Windows)

```powershell
# Apply all fixes automatically
.\apply_fixes.ps1
```

## 🚀 Quick Start (Linux/Mac)

```bash
# Apply all fixes automatically
./apply_fixes.sh
```

---

## 📋 Manual Fix Checklist

### ✅ Fix 1: Enable Corroboration
**File:** `remediation_engine/ai/inference.py` (line 58)
```python
AI_REQUIRE_CORROBORATION = _env_bool("AI_REQUIRE_CORROBORATION", True)  # Changed from False
```

### ✅ Fix 2: Correct Threshold Multiplier
**File:** `remediation_engine/ai/inference.py` (line 59)
```python
AI_THRESHOLD_MULTIPLIER = _env_float("AI_THRESHOLD_MULTIPLIER", 1.5)  # Changed from 1.1
```

### ✅ Fix 3: Add Docker Capability
**File:** `docker-compose.yml` (under api_service)
```yaml
api_service:
  # ... existing config ...
  cap_add:
    - SYS_PTRACE  # NEW: Enables metrics collection
```

### ✅ Fix 4: Enhanced Error Handling
**File:** `api_service/app/middleware.py`
- Changed silent `except: pass` to explicit error logging
- Added PermissionError detection
- Provides actionable fix instructions

---

## 🧪 Validation Commands

### Test Metrics Collection
```powershell
docker exec -it api_service python /app/validate_metrics_fix.py
```

### Check Memory Metric
```powershell
curl http://localhost:8000/metrics | Select-String "process_memory_mb"
# Expected: process_memory_mb 245.6 (non-zero)
```

### Check Connection Metric
```powershell
curl http://localhost:8000/metrics | Select-String "process_active_connections"
# Expected: process_active_connections 18.0 (non-zero)
```

### Verify AI Configuration
```powershell
docker-compose logs remediation_engine | Select-String "AI Engine initialized"
# Expected: [V4] AI Engine initialized. input_size=5, threshold=0.047100
```

---

## 🔄 Deployment Steps

1. **Stop containers**
   ```powershell
   docker-compose down
   ```

2. **Verify fixes applied**
   ```powershell
   # Check inference.py
   Select-String "AI_REQUIRE_CORROBORATION.*True" remediation_engine/ai/inference.py
   Select-String "AI_THRESHOLD_MULTIPLIER.*1.5" remediation_engine/ai/inference.py
   
   # Check docker-compose.yml
   Select-String "SYS_PTRACE" docker-compose.yml
   ```

3. **Rebuild and start**
   ```powershell
   docker-compose up --build -d
   ```

4. **Wait for startup**
   ```powershell
   Start-Sleep -Seconds 30
   ```

5. **Validate**
   ```powershell
   docker exec -it api_service python /app/validate_metrics_fix.py
   ```

---

## 🐛 Troubleshooting

### Problem: Memory metric still shows 0.0

**Check 1:** Verify capability is added
```powershell
docker inspect api_service | Select-String "SYS_PTRACE"
```

**Check 2:** Rebuild container
```powershell
docker-compose down
docker-compose up --build -d
```

**Check 3:** Check logs for permission errors
```powershell
docker-compose logs api_service | Select-String "METRICS WARNING"
```

### Problem: AI triggers on idle periods

**Check:** Verify corroboration is enabled
```powershell
docker-compose logs remediation_engine | Select-String "Corroborated"
# Should show: Corroborated: ✅ YES (only when traffic + errors present)
```

### Problem: Too many false positives

**Check:** Verify threshold multiplier
```powershell
docker-compose logs remediation_engine | Select-String "threshold="
# Should show threshold around 0.047 (not 0.126)
```

---

## 📊 Expected Behavior

### Before Fixes
```
📊 METRICS:
  memory_mb: 0.0000           ❌
  active_connections: 0.0000  ❌

🧠 AI: Triggers on idle       ❌
🎯 Threshold: Too sensitive   ❌
```

### After Fixes
```
📊 METRICS:
  memory_mb: 245.3000         ✅
  active_connections: 18.0000 ✅

🧠 AI: Requires corroboration ✅
🎯 Threshold: Balanced        ✅
```

---

## 🔙 Rollback

If issues occur:

```powershell
# Stop containers
docker-compose down

# Restore from backup (replace TIMESTAMP with your backup folder)
Copy-Item backup_TIMESTAMP\* .

# Restart
docker-compose up -d
```

---

## 📞 Quick Help

### View all logs
```powershell
docker-compose logs -f
```

### View specific service
```powershell
docker-compose logs -f remediation_engine
docker-compose logs -f api_service
```

### Restart specific service
```powershell
docker-compose restart api_service
docker-compose restart remediation_engine
```

### Check container status
```powershell
docker-compose ps
```

---

## ✅ Success Indicators

After applying fixes, you should see:

1. ✅ Memory metric > 0 MB
2. ✅ Connection metric > 0
3. ✅ AI requires traffic + errors to trigger
4. ✅ Threshold around 0.047 (not 0.126)
5. ✅ No permission errors in logs
6. ✅ Dashboard shows live metrics

---

## 📚 Related Files

- `FIXES_APPLIED.md` - Detailed fix documentation
- `validate_metrics_fix.py` - Validation script
- `apply_fixes.ps1` - Automated deployment (Windows)
- `apply_fixes.sh` - Automated deployment (Linux/Mac)
- `IMPLEMENTATION_GUIDE.md` - Original recommendations

---

**Last Updated:** February 25, 2026
**Status:** Production Ready ✅
