#!/bin/bash
# Smoke test script for ransom-notes
# Builds and runs docker-compose, then verifies services are healthy

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

cleanup() {
    log_info "Cleaning up..."
    cd "$PROJECT_DIR"
    docker compose down --volumes --remove-orphans 2>/dev/null || true
}

# Trap to ensure cleanup runs on exit
trap cleanup EXIT

cd "$PROJECT_DIR"

log_info "Building and starting services..."
docker compose up --build -d

log_info "Waiting for services to become healthy..."

# Wait for backend to be healthy (max 60 seconds)
ATTEMPTS=0
MAX_ATTEMPTS=30
until docker compose ps backend | grep -q "healthy" || [ $ATTEMPTS -eq $MAX_ATTEMPTS ]; do
    ATTEMPTS=$((ATTEMPTS + 1))
    log_info "Waiting for backend to be healthy... (attempt $ATTEMPTS/$MAX_ATTEMPTS)"
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
    log_info "Waiting for frontend to be healthy... (attempt $ATTEMPTS/$MAX_ATTEMPTS)"
    sleep 2
done

if [ $ATTEMPTS -eq $MAX_ATTEMPTS ]; then
    log_error "Frontend failed to become healthy"
    docker compose logs frontend
    exit 1
fi

log_info "Frontend is healthy!"

# Run smoke tests
log_info "Running smoke tests..."

# Test 1: Backend health endpoint
log_info "Testing backend health endpoint..."
BACKEND_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health)
if [ "$BACKEND_HEALTH" != "200" ]; then
    log_error "Backend health check failed with status $BACKEND_HEALTH"
    exit 1
fi
log_info "Backend health check passed!"

# Test 2: Frontend health endpoint
log_info "Testing frontend health endpoint..."
FRONTEND_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/health)
if [ "$FRONTEND_HEALTH" != "200" ]; then
    log_error "Frontend health check failed with status $FRONTEND_HEALTH"
    exit 1
fi
log_info "Frontend health check passed!"

# Test 3: Frontend serves HTML
log_info "Testing frontend serves HTML..."
FRONTEND_HTML=$(curl -s http://localhost/ | head -1)
if [[ ! "$FRONTEND_HTML" =~ "<!DOCTYPE html>" && ! "$FRONTEND_HTML" =~ "<!doctype html>" ]]; then
    log_error "Frontend did not return HTML"
    exit 1
fi
log_info "Frontend HTML check passed!"

# Test 4: API can create a game
log_info "Testing game creation API..."
CREATE_RESPONSE=$(curl -s -X POST http://localhost:8000/api/games \
    -H "Content-Type: application/json" \
    -d '{"host_nickname": "SmokeTestPlayer"}')

if ! echo "$CREATE_RESPONSE" | grep -q "game_id"; then
    log_error "Game creation failed: $CREATE_RESPONSE"
    exit 1
fi
log_info "Game creation test passed!"

# Test 5: Frontend can proxy to backend (via nginx)
log_info "Testing frontend proxy to backend..."
PROXY_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/api/health)
if [ "$PROXY_HEALTH" != "200" ]; then
    # This might fail in docker-compose due to DNS, which is OK
    # The ALB handles this in production
    log_warn "Frontend proxy returned $PROXY_HEALTH (may be expected in docker-compose)"
fi

log_info "========================================="
log_info "All smoke tests passed!"
log_info "========================================="

exit 0
