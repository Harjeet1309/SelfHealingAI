# Deployment Checklist

## Pre-Deployment Verification

- [ ] All fixes verified in code
  - [ ] `AI_REQUIRE_CORROBORATION = True` in inference.py
  - [ ] `AI_THRESHOLD_MULTIPLIER = 1.5` in inference.py
  - [ ] `cap_add: [SYS_PTRACE]` in docker-compose.yml
  - [ ] Enhanced error handling in middleware.py

- [ ] Backup created
  - [ ] Current docker-compose.yml backed up
  - [ ] Current inference.py backed up
  - [ ] Current middleware.py backed up

## Deployment Steps

- [ ] Stop containers: `docker-compose down`
- [ ] Rebuild images: `docker-compose build --no-cache`
- [ ] Start services: `docker-compose up -d`
- [ ] Wait 30 seconds for startup

## Post-Deployment Validation

- [ ] Run validation script
  ```powershell
  docker exec -it api_service python /app/validate_metrics_fix.py
  ```
  Expected: All tests pass ✅

- [ ] Check memory metric
  ```powershell
  curl http://localhost:8000/metrics | Select-String "process_memory_mb"
  ```
  Expected: Non-zero value (200-400 MB)

- [ ] Check connection metric
  ```powershell
  curl http://localhost:8000/metrics | Select-String "process_active_connections"
  ```
  Expected: Non-zero value (10-50 connections)

- [ ] Verify AI configuration
  ```powershell
  docker-compose logs remediation_engine | Select-String "AI Engine initialized"
  ```
  Expected: `threshold=0.047100` (not 0.126)

- [ ] Check service health
  - [ ] API Service: http://localhost:8000/health
  - [ ] Prometheus: http://localhost:9090/-/healthy
  - [ ] Dashboard: http://localhost:8000/dashboard

## Functional Testing

- [ ] Test normal operation (no faults)
  ```powershell
  for ($i=1; $i -le 20; $i++) { curl -s http://localhost:8000/products | Out-Null }
  ```
  Expected: No AI triggers, metrics updating

- [ ] Test fault injection (500 crash)
  ```powershell
  curl -X POST http://localhost:8000/inject/500_checkout
  for ($i=1; $i -le 30; $i++) { curl -s -X POST http://localhost:8000/checkout | Out-Null }
  ```
  Expected: AI detects within 10-20 seconds, triggers restart

- [ ] Test overload suppression (503 high CPU)
  ```powershell
  curl -X POST http://localhost:8000/inject/503_overload
  for ($i=1; $i -le 50; $i++) { curl -s http://localhost:8000/health | Out-Null }
  ```
  Expected: AI detects but SUPPRESSES restart (high CPU)

- [ ] Test idle period (no false positives)
  ```powershell
  # Wait 5 minutes with no traffic
  Start-Sleep -Seconds 300
  docker-compose logs remediation_engine | Select-String "ANOMALY"
  ```
  Expected: No anomaly triggers during idle

## Monitoring (First 24 Hours)

- [ ] Hour 1: Check logs every 15 minutes
- [ ] Hour 2-4: Check logs every 30 minutes
- [ ] Hour 4-24: Check logs every 2 hours

### Key Metrics to Monitor

- [ ] Memory metric stays non-zero
- [ ] Connection metric stays non-zero
- [ ] No false positives during idle
- [ ] Real faults detected correctly
- [ ] Overload suppression working
- [ ] Cooldown enforced (60s between restarts)

## Rollback Plan (If Needed)

- [ ] Stop containers: `docker-compose down`
- [ ] Restore backup files
- [ ] Restart: `docker-compose up -d`
- [ ] Document issues encountered

## Success Criteria

- [ ] All validation tests pass
- [ ] Metrics show non-zero values
- [ ] AI requires corroboration
- [ ] Threshold is balanced (1.5x)
- [ ] No permission errors in logs
- [ ] Dashboard shows live data
- [ ] Fault injection works correctly
- [ ] No false positives during idle
- [ ] Overload suppression works

## Sign-Off

- [ ] Deployment completed by: _______________
- [ ] Date/Time: _______________
- [ ] All tests passed: YES / NO
- [ ] Issues encountered: _______________
- [ ] Monitoring plan in place: YES / NO

---

**Status:** Ready for deployment ✅
**Risk Level:** LOW
**Estimated Downtime:** 2-3 minutes
**Rollback Time:** < 5 minutes
