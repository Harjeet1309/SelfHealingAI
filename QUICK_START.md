# Quick Start Guide

## 🚀 One-Command Start

```powershell
.\start.ps1
```

This will:
- ✅ Stop any existing containers
- ✅ Build and start all services
- ✅ Wait for initialization
- ✅ Open the dashboard in your browser

---

## 🧪 Run Complete Tests

```powershell
.\test_application.ps1
```

This will:
- ✅ Start the application
- ✅ Check all services
- ✅ Validate metrics collection
- ✅ Test basic functionality
- ✅ Optionally test fault injection

---

## 📋 Manual Commands

### Start Application
```powershell
docker-compose up -d --build
```

### Stop Application
```powershell
docker-compose down
```

### View Logs
```powershell
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f remediation_engine
```

### Check Status
```powershell
docker-compose ps
```

---

## 🌐 Access Points

| Service | URL | Description |
|---------|-----|-------------|
| **Main App** | http://localhost:8000 | Luxury boutique storefront |
| **AI Dashboard** | http://localhost:8000/dashboard | Real-time monitoring & Dashboard |
| **Prometheus** | http://localhost:9090 | Metrics database |
| **Grafana** | http://localhost:3001 | Advanced dashboards |
| **Alertmanager** | http://localhost:9093 | Alert management |

---

## ✅ Quick Health Check

```powershell
# Check API health
curl http://localhost:8000/health

# Check metrics
curl http://localhost:8000/metrics | Select-String "process_memory_mb"

# Validate everything
docker exec -it api_service python /app/validate_metrics_fix.py
```

---

## 🔥 Test Fault Injection

### Inject a Crash (500)
```powershell
curl -X POST http://localhost:8000/inject/500_checkout
```

### Inject Overload (503)
```powershell
curl -X POST http://localhost:8000/inject/503_overload
```

### Clear All Faults
```powershell
curl -X POST "http://localhost:8000/inject/reset?target=all"
```

---

## 📊 What to Expect

### Normal Operation
- 🟢 AI Status: HEALTHY
- 📈 Metrics updating every 5 seconds
- 📊 Dashboard showing live data
- 🔄 No anomalies detected

### During Fault
- 🔴 AI Status: ANOMALY DETECTED
- ⚡ Remediation triggered
- 🔄 Container restarts automatically
- ✅ Recovery verified

---

## 🐛 Quick Troubleshooting

### Services won't start?
```powershell
# Check if ports are in use
netstat -ano | findstr "8000 9090"

# Try full rebuild
docker-compose down
docker-compose up --build -d
```

### Metrics showing zero?
```powershell
# Verify fixes applied
Select-String "SYS_PTRACE" docker-compose.yml

# Rebuild if needed
docker-compose down
docker-compose up --build -d
```

### Dashboard not loading?
```powershell
# Check API logs
docker-compose logs api_service

# Restart service
docker-compose restart api_service
```

---

## 📚 Documentation

| File | Purpose |
|------|---------|
| `HOW_TO_RUN.md` | Detailed step-by-step guide |
| `test_application.ps1` | Automated testing script |
| `FIXES_APPLIED.md` | Complete fix documentation |
| `PROJECT_DOCUMENTATION.md` | Full system architecture |

---

## 🎯 Success Checklist

- [ ] All containers running (`docker-compose ps`)
- [ ] API responds to /health
- [ ] Metrics show non-zero values
- [ ] Dashboard loads and updates
- [ ] AI engine initialized
- [ ] Fault injection works

---

## 💡 Pro Tips

1. **Always check logs first**
   ```powershell
   docker-compose logs -f remediation_engine
   ```

2. **Monitor the AI dashboard**
   - Open http://localhost:8000/dashboard
   - Watch real-time telemetry
   - Review action logs

3. **Test different scenarios**
   - Try various fault types
   - Observe AI responses
   - Verify self-healing

4. **Use the validation script**
   ```powershell
   docker exec -it api_service python /app/validate_metrics_fix.py
   ```

---

**Need more help?** See `HOW_TO_RUN.md` for detailed instructions.

**Ready to deploy?** See `DEPLOYMENT_CHECKLIST.md` for production steps.
