#!/bin/bash
set -e

# Health check script for TextLoom services
# This script can be used in Docker containers or for monitoring

# Configuration
HOST=${HEALTH_CHECK_HOST:-localhost}
PORT=${HEALTH_CHECK_PORT:-8000}
TIMEOUT=${HEALTH_CHECK_TIMEOUT:-10}
RETRIES=${HEALTH_CHECK_RETRIES:-3}
INTERVAL=${HEALTH_CHECK_INTERVAL:-5}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Check if curl is available
if ! command -v curl &> /dev/null; then
    log "${RED}ERROR: curl is not installed${NC}"
    exit 1
fi

# Function to check HTTP endpoint
check_http_endpoint() {
    local url=$1
    local name=$2
    local expected_status=${3:-200}
    
    log "Checking $name at $url..."
    
    for i in $(seq 1 $RETRIES); do
        response=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout $TIMEOUT "$url" 2>/dev/null || echo "000")
        
        if [ "$response" = "$expected_status" ]; then
            log "${GREEN}✓ $name is healthy (HTTP $response)${NC}"
            return 0
        else
            log "${YELLOW}⚠ $name check failed (attempt $i/$RETRIES) - HTTP $response${NC}"
            if [ $i -lt $RETRIES ]; then
                sleep $INTERVAL
            fi
        fi
    done
    
    log "${RED}✗ $name is unhealthy after $RETRIES attempts${NC}"
    return 1
}

# Function to check service with JSON response
check_json_endpoint() {
    local url=$1
    local name=$2
    local expected_field=$3
    local expected_value=$4
    
    log "Checking $name JSON endpoint at $url..."
    
    for i in $(seq 1 $RETRIES); do
        response=$(curl -s --connect-timeout $TIMEOUT "$url" 2>/dev/null || echo "{}")
        
        if echo "$response" | grep -q "$expected_field"; then
            actual_value=$(echo "$response" | grep -o "\"$expected_field\"[^,}]*" | cut -d'"' -f4)
            if [ "$actual_value" = "$expected_value" ]; then
                log "${GREEN}✓ $name is healthy ($expected_field: $actual_value)${NC}"
                return 0
            else
                log "${YELLOW}⚠ $name returned unexpected value: $actual_value (expected: $expected_value)${NC}"
            fi
        else
            log "${YELLOW}⚠ $name check failed (attempt $i/$RETRIES) - Invalid response${NC}"
        fi
        
        if [ $i -lt $RETRIES ]; then
            sleep $INTERVAL
        fi
    done
    
    log "${RED}✗ $name is unhealthy after $RETRIES attempts${NC}"
    return 1
}

# Function to check Redis connectivity
check_redis() {
    local redis_host=${REDIS_HOST:-localhost}
    local redis_port=${REDIS_PORT:-6379}
    
    log "Checking Redis connectivity at $redis_host:$redis_port..."
    
    # Check if redis-cli is available
    if command -v redis-cli &> /dev/null; then
        if redis-cli -h "$redis_host" -p "$redis_port" ping >/dev/null 2>&1; then
            log "${GREEN}✓ Redis is responding${NC}"
            return 0
        else
            log "${RED}✗ Redis is not responding${NC}"
            return 1
        fi
    else
        # Fallback to telnet/nc if available
        if command -v nc &> /dev/null; then
            if echo "PING" | nc -w $TIMEOUT "$redis_host" "$redis_port" | grep -q "PONG"; then
                log "${GREEN}✓ Redis is responding (via nc)${NC}"
                return 0
            else
                log "${RED}✗ Redis is not responding${NC}"
                return 1
            fi
        else
            log "${YELLOW}⚠ Cannot check Redis - no redis-cli or nc available${NC}"
            return 1
        fi
    fi
}

# Function to check database connectivity
check_database() {
    local db_url=${DATABASE_URL}
    
    if [ -z "$db_url" ]; then
        log "${YELLOW}⚠ DATABASE_URL not set, skipping database check${NC}"
        return 0
    fi
    
    log "Checking database connectivity..."
    
    # Extract connection details from DATABASE_URL
    # Format: postgresql://user:pass@host:port/dbname
    if echo "$db_url" | grep -q "postgresql://"; then
        if command -v psql &> /dev/null; then
            if psql "$db_url" -c "SELECT 1;" >/dev/null 2>&1; then
                log "${GREEN}✓ Database is accessible${NC}"
                return 0
            else
                log "${RED}✗ Database is not accessible${NC}"
                return 1
            fi
        else
            log "${YELLOW}⚠ Cannot check database - psql not available${NC}"
            return 1
        fi
    else
        log "${YELLOW}⚠ Unsupported database URL format${NC}"
        return 1
    fi
}

# Main health check function
main() {
    local exit_code=0
    
    log "Starting TextLoom health check..."
    log "Target: http://$HOST:$PORT"
    log "Timeout: ${TIMEOUT}s, Retries: $RETRIES, Interval: ${INTERVAL}s"
    echo
    
    # Check main API health endpoint
    if ! check_json_endpoint "http://$HOST:$PORT/health" "API Health" "status" "healthy"; then
        exit_code=1
    fi
    
    # Check basic API responsiveness
    if ! check_http_endpoint "http://$HOST:$PORT/" "API Root"; then
        exit_code=1
    fi
    
    # Check Redis if in production environment
    if [ "${ENVIRONMENT:-}" != "test" ]; then
        if ! check_redis; then
            exit_code=1
        fi
        
        # Check database connectivity
        if ! check_database; then
            exit_code=1
        fi
    fi
    
    echo
    if [ $exit_code -eq 0 ]; then
        log "${GREEN}✓ All health checks passed${NC}"
    else
        log "${RED}✗ Some health checks failed${NC}"
    fi
    
    exit $exit_code
}

# Handle script arguments
case "${1:-main}" in
    "api")
        check_http_endpoint "http://$HOST:$PORT/health" "API Health"
        ;;
    "redis")
        check_redis
        ;;
    "database")
        check_database
        ;;
    "all"|"main")
        main
        ;;
    *)
        echo "Usage: $0 [api|redis|database|all]"
        echo "  api      - Check API health endpoint only"
        echo "  redis    - Check Redis connectivity only" 
        echo "  database - Check database connectivity only"
        echo "  all      - Check all services (default)"
        echo ""
        echo "Environment variables:"
        echo "  HEALTH_CHECK_HOST     - Target host (default: localhost)"
        echo "  HEALTH_CHECK_PORT     - Target port (default: 8000)"
        echo "  HEALTH_CHECK_TIMEOUT  - Connection timeout (default: 10)"
        echo "  HEALTH_CHECK_RETRIES  - Number of retries (default: 3)"
        echo "  HEALTH_CHECK_INTERVAL - Interval between retries (default: 5)"
        echo "  REDIS_HOST           - Redis host (default: localhost)"
        echo "  REDIS_PORT           - Redis port (default: 6379)"
        echo "  DATABASE_URL         - Database connection URL"
        exit 1
        ;;
esac