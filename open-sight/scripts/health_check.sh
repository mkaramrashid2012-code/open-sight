#!/bin/bash
# OpenSight Private - System Health Check Script
# Enterprise-grade monitoring and diagnostics

set -e

echo "=========================================="
echo "OpenSight Private - System Health Check"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

check_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASS_COUNT++))
}

check_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAIL_COUNT++))
}

check_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    ((WARN_COUNT++))
}

# 1. Check Python version
echo "1. Checking Python environment..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    if [[ $(echo $PYTHON_VERSION | cut -d'.' -f1) -ge 3 ]] && [[ $(echo $PYTHON_VERSION | cut -d'.' -f2) -ge 10 ]]; then
        check_pass "Python version: $PYTHON_VERSION"
    else
        check_fail "Python version too old: $PYTHON_VERSION (requires 3.10+)"
    fi
else
    check_fail "Python3 not found"
fi

# 2. Check required packages
echo ""
echo "2. Checking required Python packages..."
REQUIRED_PACKAGES=("fastapi" "uvicorn" "sqlalchemy" "psycopg2" "opencv-python" "ultralytics" "numpy" "pydantic" "bcrypt" "aiohttp")

for package in "${REQUIRED_PACKAGES[@]}"; do
    if python3 -c "import $package" 2>/dev/null; then
        check_pass "Package installed: $package"
    else
        check_fail "Missing package: $package"
    fi
done

# 3. Check database connectivity
echo ""
echo "3. Checking database connectivity..."
if command -v docker &> /dev/null && docker ps | grep -q opensight_db; then
    check_pass "PostgreSQL container is running"
    
    # Try to connect
    if docker exec opensight_db pg_isready -U opensight -d opensight_db &>/dev/null; then
        check_pass "Database accepting connections"
    else
        check_warn "Database container running but not accepting connections"
    fi
else
    check_warn "Docker/PostgreSQL container not found (may be running locally)"
fi

# 4. Check directory structure
echo ""
echo "4. Checking directory structure..."
REQUIRED_DIRS=("backend/app" "backend/app/api" "backend/app/core" "backend/app/models" "backend/app/workers" "data/media" "data/clips" "data/thumbnails")

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "/workspace/open-sight/$dir" ]; then
        check_pass "Directory exists: $dir"
    else
        check_fail "Missing directory: $dir"
    fi
done

# 5. Check configuration
echo ""
echo "5. Checking configuration..."
if [ -f "/workspace/open-sight/.env" ]; then
    check_pass ".env configuration file exists"
    
    # Check for required variables
    REQUIRED_VARS=("DATABASE_URL" "SECRET_KEY" "API_KEY")
    for var in "${REQUIRED_VARS[@]}"; do
        if grep -q "^$var=" /workspace/open-sight/.env; then
            check_pass "Config variable set: $var"
        else
            check_warn "Missing config variable: $var"
        fi
    done
else
    check_warn ".env file not found (using defaults or environment variables)"
fi

# 6. Check API endpoints
echo ""
echo "6. Checking API availability..."
if command -v curl &> /dev/null; then
    if curl -s http://localhost:8000/health &>/dev/null; then
        check_pass "Health endpoint responding"
        
        RESPONSE=$(curl -s http://localhost:8000/health)
        if echo "$RESPONSE" | grep -q '"status":"healthy"'; then
            check_pass "System status: healthy"
        else
            check_warn "System status unknown"
        fi
    else
        check_warn "API not responding on port 8000 (may not be started)"
    fi
else
    check_warn "curl not available for API testing"
fi

# 7. Check system resources
echo ""
echo "7. Checking system resources..."

# Memory
MEM_AVAILABLE=$(free -m | awk '/^Mem:/ {print $7}')
MEM_TOTAL=$(free -m | awk '/^Mem:/ {print $2}')
if [ $MEM_AVAILABLE -gt 1024 ]; then
    check_pass "Memory available: ${MEM_AVAILABLE}MB / ${MEM_TOTAL}MB"
elif [ $MEM_AVAILABLE -gt 512 ]; then
    check_warn "Low memory available: ${MEM_AVAILABLE}MB / ${MEM_TOTAL}MB"
else
    check_fail "Critical: Very low memory: ${MEM_AVAILABLE}MB / ${MEM_TOTAL}MB"
fi

# Disk space
DISK_AVAILABLE=$(df -h /workspace | awk 'NR==2 {print $4}')
if [[ $DISK_AVAILABLE =~ ^([0-9]+) ]]; then
    DISK_NUM=${BASH_REMATCH[1]}
    if [ $DISK_NUM -gt 10 ]; then
        check_pass "Disk space available: $DISK_AVAILABLE"
    elif [ $DISK_NUM -gt 5 ]; then
        check_warn "Low disk space: $DISK_AVAILABLE"
    else
        check_fail "Critical: Very low disk space: $DISK_AVAILABLE"
    fi
fi

# CPU cores
CPU_CORES=$(nproc)
if [ $CPU_CORES -ge 4 ]; then
    check_pass "CPU cores: $CPU_CORES"
else
    check_warn "Limited CPU cores: $CPU_CORES (recommend 4+ for production)"
fi

# 8. Check GPU (optional)
echo ""
echo "8. Checking GPU acceleration (optional)..."
if command -v nvidia-smi &> /dev/null; then
    GPU_INFO=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits | head -1)
    check_pass "GPU detected: $GPU_INFO"
else
    check_warn "No NVIDIA GPU detected (CPU inference will be used)"
fi

# Summary
echo ""
echo "=========================================="
echo "Health Check Summary"
echo "=========================================="
echo -e "${GREEN}Passed:${NC} $PASS_COUNT"
echo -e "${RED}Failed:${NC} $FAIL_COUNT"
echo -e "${YELLOW}Warnings:${NC} $WARN_COUNT"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "${GREEN}✓ System health check PASSED${NC}"
    exit 0
else
    echo -e "${RED}✗ System health check FAILED${NC}"
    echo "Please address the failed checks above."
    exit 1
fi
