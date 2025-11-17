#!/bin/bash

################################################################################
# MyWave Production Deployment Checklist Script
# 
# This script automates the pre-deployment verification process
# Run this before deploying to production
#
# Usage: ./scripts/deployment_checklist.sh
################################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_WARNED=0

# Functions
check_pass() {
    echo -e "${GREEN}✅ PASS${NC}: $1"
    ((CHECKS_PASSED++))
}

check_fail() {
    echo -e "${RED}❌ FAIL${NC}: $1"
    ((CHECKS_FAILED++))
}

check_warn() {
    echo -e "${YELLOW}⚠️  WARN${NC}: $1"
    ((CHECKS_WARNED++))
}

echo "=================================="
echo "MyWave Deployment Checklist"
echo "=================================="
echo ""

# ============================================================================
# 1. CODE & TESTS
# ============================================================================
echo "1. CODE & TESTS"
echo "---"

# Run tests
echo "Running test suite..."
if pytest tests/ -q --tb=short > /dev/null 2>&1; then
    check_pass "All tests passing"
else
    check_fail "Tests failing - run 'pytest tests/ -v' for details"
fi

# Git status
echo "Checking git status..."
if [ -z "$(git status --porcelain)" ]; then
    check_pass "Git working directory clean"
else
    check_fail "Uncommitted changes exist - run 'git status'"
fi

# Branch check
echo "Checking git branch..."
if [ "$(git rev-parse --abbrev-ref HEAD)" = "main" ] || [ "$(git rev-parse --abbrev-ref HEAD)" = "master" ]; then
    check_pass "On main/master branch"
else
    check_warn "Not on main branch: $(git rev-parse --abbrev-ref HEAD)"
fi

echo ""

# ============================================================================
# 2. CONFIGURATION
# ============================================================================
echo "2. CONFIGURATION"
echo "---"

# Environment variables
echo "Checking environment variables..."
required_vars=(
    "FLASK_ENV"
    "SECRET_KEY"
    "DATABASE_URL"
)

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        check_fail "Missing environment variable: $var"
    else
        check_pass "Environment variable set: $var"
    fi
done

# .env file
if [ -f ".env.production" ]; then
    check_pass ".env.production file exists"
else
    check_warn ".env.production file not found - using environment variables"
fi

echo ""

# ============================================================================
# 3. DATABASE
# ============================================================================
echo "3. DATABASE"
echo "---"

# Database connectivity
echo "Testing database connection..."
if python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.session.execute('SELECT 1')" 2>/dev/null; then
    check_pass "Database connection successful"
else
    check_fail "Database connection failed"
fi

# Migrations
echo "Checking migrations..."
if [ -d "migrations/versions" ] && [ "$(ls migrations/versions | wc -l)" -gt 0 ]; then
    check_pass "Migration files exist: $(ls migrations/versions | wc -l) files"
else
    check_warn "No migration files found"
fi

echo ""

# ============================================================================
# 4. DEPENDENCIES
# ============================================================================
echo "4. DEPENDENCIES"
echo "---"

# Check critical packages
echo "Checking Python packages..."
packages=(
    "flask"
    "flask_sqlalchemy"
    "flask_cors"
    "cryptography"
)

for package in "${packages[@]}"; do
    if python -c "import $package" 2>/dev/null; then
        check_pass "Package installed: $package"
    else
        check_fail "Package missing: $package - run 'pip install -r requirements.txt'"
    fi
done

echo ""

# ============================================================================
# 5. SECURITY
# ============================================================================
echo "5. SECURITY"
echo "---"

# Check for hardcoded secrets
echo "Checking for hardcoded secrets..."
if grep -r "password=" . --include="*.py" 2>/dev/null | grep -v "# " | grep -v ".env.sample" | grep -v "requirements.txt"; then
    check_warn "Possible hardcoded secrets found - review manually"
else
    check_pass "No obvious hardcoded secrets detected"
fi

# Check for debug mode
echo "Checking Flask config..."
if python -c "from app import create_app; app = create_app('production'); print(app.debug)" 2>/dev/null | grep -q "False"; then
    check_pass "Debug mode disabled"
else
    check_warn "Debug mode may be enabled - verify in config"
fi

# Check SECRET_KEY
if [ ${#SECRET_KEY} -ge 32 ]; then
    check_pass "SECRET_KEY long enough: ${#SECRET_KEY} chars"
else
    check_fail "SECRET_KEY too short: ${#SECRET_KEY} chars (minimum 32)"
fi

echo ""

# ============================================================================
# 6. DOCKER (if applicable)
# ============================================================================
echo "6. DOCKER"
echo "---"

if command -v docker &> /dev/null; then
    # Check Dockerfile
    if [ -f "Dockerfile" ]; then
        check_pass "Dockerfile exists"
    else
        check_fail "Dockerfile not found"
    fi
    
    # Check docker-compose
    if [ -f "docker-compose.yml" ]; then
        check_pass "docker-compose.yml exists"
    else
        check_warn "docker-compose.yml not found"
    fi
else
    check_warn "Docker not installed - skipping Docker checks"
fi

echo ""

# ============================================================================
# 7. DOCUMENTATION
# ============================================================================
echo "7. DOCUMENTATION"
echo "---"

docs=(
    "docs/API.md"
    "docs/DEPLOYMENT.md"
    "docs/SECURITY.md"
    "docs/QA_TESTING.md"
)

for doc in "${docs[@]}"; do
    if [ -f "$doc" ]; then
        check_pass "Documentation exists: $doc"
    else
        check_fail "Documentation missing: $doc"
    fi
done

echo ""

# ============================================================================
# SUMMARY
# ============================================================================
echo "=================================="
echo "SUMMARY"
echo "=================================="
echo -e "${GREEN}✅ Passed${NC}:  $CHECKS_PASSED"
echo -e "${RED}❌ Failed${NC}:  $CHECKS_FAILED"
echo -e "${YELLOW}⚠️  Warned${NC}:  $CHECKS_WARNED"
echo ""

# Final decision
if [ $CHECKS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ READY FOR DEPLOYMENT${NC}"
    exit 0
else
    echo -e "${RED}❌ DEPLOYMENT BLOCKED - Fix $CHECKS_FAILED issues above${NC}"
    exit 1
fi
