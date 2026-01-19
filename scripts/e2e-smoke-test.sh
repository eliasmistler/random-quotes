#!/bin/bash
# E2E Smoke Test for Random Quotes
# Starts Docker Compose, runs a full browser-based game test, then cleans up
#
# Usage:
#   ./scripts/e2e-smoke-test.sh               # Run headless (for CI)
#   ./scripts/e2e-smoke-test.sh --headed      # Run with visible browser (for local testing)
#   ./scripts/e2e-smoke-test.sh --debug       # Run headed with slow motion (500ms)
#   ./scripts/e2e-smoke-test.sh --interactive # Run headed with pause/resume on Ctrl-C (1000ms slowmo)
#   ./scripts/e2e-smoke-test.sh --slowmo=200  # Override slow motion delay (in ms)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Parse arguments
HEADED=false
SLOWMO=0
SLOWMO_OVERRIDE=""
INTERACTIVE=false
for arg in "$@"; do
    case $arg in
        --headed)
            HEADED=true
            ;;
        --debug)
            HEADED=true
            SLOWMO=500
            ;;
        --interactive)
            HEADED=true
            SLOWMO=1000
            INTERACTIVE=true
            ;;
        --slowmo=*)
            SLOWMO_OVERRIDE="${arg#*=}"
            ;;
    esac
done

# Apply slowmo override if specified
if [ -n "$SLOWMO_OVERRIDE" ]; then
    SLOWMO=$SLOWMO_OVERRIDE
fi

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${CYAN}[STEP]${NC} $1"
}

cleanup() {
    log_info "Cleaning up Docker Compose..."
    cd "$PROJECT_DIR"
    docker compose down --volumes --remove-orphans 2>/dev/null || true
}

# Trap to ensure cleanup runs on exit
trap cleanup EXIT

# ============================================
# STEP 1: Install Playwright dependencies
# ============================================
log_step "Installing Playwright dependencies..."
cd "$SCRIPT_DIR"

if [ ! -d "node_modules" ]; then
    npm install
fi

# Install Playwright browsers if needed
npx playwright install chromium --with-deps 2>/dev/null || npx playwright install chromium

# ============================================
# STEP 2: Start Docker Compose
# ============================================
log_step "Starting Docker Compose..."
cd "$PROJECT_DIR"

docker compose up --build -d

# ============================================
# STEP 3: Wait for services to be healthy
# ============================================
log_step "Waiting for services to become healthy..."

# Wait for backend to be healthy (max 60 seconds)
ATTEMPTS=0
MAX_ATTEMPTS=30
until docker compose ps backend | grep -q "healthy" || [ $ATTEMPTS -eq $MAX_ATTEMPTS ]; do
    ATTEMPTS=$((ATTEMPTS + 1))
    log_info "Waiting for backend... (attempt $ATTEMPTS/$MAX_ATTEMPTS)"
    sleep 2
done

if [ $ATTEMPTS -eq $MAX_ATTEMPTS ]; then
    log_error "Backend failed to become healthy"
    docker compose logs backend
    exit 1
fi
log_info "Backend is healthy!"

# Wait for frontend to be healthy (max 60 seconds)
ATTEMPTS=0
until docker compose ps frontend | grep -q "healthy" || [ $ATTEMPTS -eq $MAX_ATTEMPTS ]; do
    ATTEMPTS=$((ATTEMPTS + 1))
    log_info "Waiting for frontend... (attempt $ATTEMPTS/$MAX_ATTEMPTS)"
    sleep 2
done

if [ $ATTEMPTS -eq $MAX_ATTEMPTS ]; then
    log_error "Frontend failed to become healthy"
    docker compose logs frontend
    exit 1
fi
log_info "Frontend is healthy!"

# Quick verification
log_info "Verifying endpoints..."
curl -sf http://localhost/health > /dev/null && log_info "Frontend health OK"
curl -sf http://localhost:8000/api/health > /dev/null && log_info "Backend health OK"

# ============================================
# STEP 4: Run Playwright E2E Tests
# ============================================
log_step "Running Playwright E2E tests..."
cd "$SCRIPT_DIR"

# Set environment variables for Playwright
export HEADED
export SLOWMO
export INTERACTIVE

# Run tests
if [ "$HEADED" = true ]; then
    log_info "Running in HEADED mode (browser will be visible)"
    if [ "$SLOWMO" -gt 0 ]; then
        log_info "Slow motion enabled: ${SLOWMO}ms between actions"
    fi
fi

if [ "$INTERACTIVE" = true ]; then
    log_info "Running in INTERACTIVE mode - press Ctrl-C to pause, then Enter to resume"
fi

# Capture test exit code but don't exit immediately
set +e
npm run e2e
TEST_EXIT_CODE=$?
set -e

# ============================================
# STEP 5: Report results
# ============================================
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo ""
    log_info "========================================="
    log_info "E2E Smoke Test PASSED!"
    log_info "========================================="
else
    echo ""
    log_error "========================================="
    log_error "E2E Smoke Test FAILED!"
    log_error "========================================="

    # Show relevant logs on failure
    log_info "Docker Compose logs:"
    docker compose logs --tail=50
fi

exit $TEST_EXIT_CODE
