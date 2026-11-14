#!/bin/bash
# Apply Critical Fixes - Automated Deployment Script
# ==================================================
# This script applies all critical fixes and validates the deployment.

set -e  # Exit on any error

echo "=========================================="
echo "Self-Healing AI - Critical Fixes Deployment"
echo "=========================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Step 1: Verify we're in the right directory
print_status "Verifying project directory..."
if [ ! -f "docker-compose.yml" ]; then
    print_error "docker-compose.yml not found. Please run this script from the project root."
    exit 1
fi

if [ ! -f "remediation_engine/ai/inference.py" ]; then
    print_error "remediation_engine/ai/inference.py not found. Invalid project structure."
    exit 1
fi

# Step 2: Backup current configuration
print_status "Creating backup of current configuration..."
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp docker-compose.yml "$BACKUP_DIR/"
cp remediation_engine/ai/inference.py "$BACKUP_DIR/"
cp api_service/app/middleware.py "$BACKUP_DIR/"
print_status "Backup created in: $BACKUP_DIR"

# Step 3: Verify fixes are applied
print_status "Verifying fixes are applied..."

# Check corroboration setting
if grep -q "AI_REQUIRE_CORROBORATION.*True" remediation_engine/ai/inference.py; then
    print_status "Corroboration fix verified"
else
    print_error "Corroboration fix not found. Please check remediation_engine/ai/inference.py"
    exit 1
fi

# Check threshold multiplier
if grep -q "AI_THRESHOLD_MULTIPLIER.*1.5" remediation_engine/ai/inference.py; then
    print_status "Threshold multiplier fix verified"
else
    print_error "Threshold multiplier fix not found. Please check remediation_engine/ai/inference.py"
    exit 1
fi

# Check Docker capability
if grep -q "SYS_PTRACE" docker-compose.yml; then
    print_status "Docker SYS_PTRACE capability verified"
else
    print_error "SYS_PTRACE capability not found in docker-compose.yml"
    exit 1
fi

# Step 4: Stop existing containers
print_status "Stopping existing containers..."
docker-compose down

# Step 5: Rebuild images
print_status "Rebuilding Docker images..."
docker-compose build --no-cache

# Step 6: Start services
print_status "Starting services..."
docker-compose up -d

# Step 7: Wait for services to be ready
print_status "Waiting for services to start (30 seconds)..."
sleep 30

# Step 8: Validate metrics collection
print_status "Validating metrics collection..."
if docker exec api_service python /app/validate_metrics_fix.py; then
    print_status "Metrics validation PASSED"
else
    print_warning "Metrics validation had issues. Check logs for details."
fi

# Step 9: Check service health
print_status "Checking service health..."

# Check api_service
if curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
    print_status "api_service is healthy"
else
    print_warning "api_service health check failed"
fi

# Check remediation_engine
if docker-compose logs remediation_engine | grep -q "AI Engine initialized"; then
    print_status "remediation_engine initialized successfully"
else
    print_warning "remediation_engine may not be initialized yet"
fi

# Check Prometheus
if curl -s -f http://localhost:9090/-/healthy > /dev/null 2>&1; then
    print_status "Prometheus is healthy"
else
    print_warning "Prometheus health check failed"
fi

# Step 10: Verify metrics are non-zero
print_status "Verifying metrics collection..."
MEMORY_METRIC=$(curl -s http://localhost:8000/metrics | grep "^process_memory_mb " | awk '{print $2}')
CONN_METRIC=$(curl -s http://localhost:8000/metrics | grep "^process_active_connections " | awk '{print $2}')

if [ -n "$MEMORY_METRIC" ] && [ "$(echo "$MEMORY_METRIC > 0" | bc)" -eq 1 ]; then
    print_status "Memory metric is collecting: ${MEMORY_METRIC} MB"
else
    print_warning "Memory metric is zero or not found: ${MEMORY_METRIC}"
fi

if [ -n "$CONN_METRIC" ]; then
    print_status "Connection metric is collecting: ${CONN_METRIC} connections"
else
    print_warning "Connection metric not found"
fi

# Step 11: Summary
echo ""
echo "=========================================="
echo "Deployment Summary"
echo "=========================================="
echo ""
print_status "All critical fixes have been applied"
print_status "Backup saved to: $BACKUP_DIR"
echo ""
echo "Service URLs:"
echo "  - API Service:        http://localhost:8000"
echo "  - AI Dashboard:       http://localhost:8000/dashboard"
echo "  - Prometheus:         http://localhost:9090"
echo "  - Grafana:            http://localhost:3001"
echo ""
echo "Next Steps:"
echo "  1. Monitor logs: docker-compose logs -f remediation_engine"
echo "  2. Test fault injection: curl -X POST http://localhost:8000/inject/500_checkout"
echo "  3. View dashboard: http://localhost:8000/dashboard"
echo ""
echo "To rollback:"
echo "  docker-compose down"
echo "  cp $BACKUP_DIR/* ."
echo "  docker-compose up -d"
echo ""
print_status "Deployment complete!"
