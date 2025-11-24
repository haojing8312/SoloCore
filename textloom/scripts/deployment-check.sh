#!/bin/bash
set -e

# Deployment validation script for TextLoom
# Performs comprehensive checks before and after deployment

# Configuration
ENVIRONMENT=${ENVIRONMENT:-staging}
TARGET_HOST=${DEPLOYMENT_HOST:-localhost}
TARGET_PORT=${DEPLOYMENT_PORT:-8000}
TIMEOUT=${DEPLOYMENT_TIMEOUT:-60}
MAX_RETRIES=${DEPLOYMENT_RETRIES:-10}

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging
log() {
    echo -e "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

error() {
    log "${RED}ERROR: $1${NC}"
}

warning() {
    log "${YELLOW}WARNING: $1${NC}"
}

success() {
    log "${GREEN}SUCCESS: $1${NC}"
}

info() {
    log "${BLUE}INFO: $1${NC}"
}

# Check if required tools are available
check_dependencies() {
    info "Checking required tools..."
    
    local required_tools=("curl" "docker" "docker-compose")
    local missing_tools=()
    
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        fi
    done
    
    if [ ${#missing_tools[@]} -gt 0 ]; then
        error "Missing required tools: ${missing_tools[*]}"
        exit 1
    fi
    
    success "All required tools are available"
}

# Pre-deployment checks
pre_deployment_checks() {
    info "Running pre-deployment checks..."
    
    # Check environment variables
    local required_vars=()
    case "$ENVIRONMENT" in
        "production")
            required_vars=("DATABASE_URL" "REDIS_PASSWORD" "SECRET_KEY" "OPENAI_API_KEY")
            ;;
        "staging")
            required_vars=("DATABASE_URL" "REDIS_PASSWORD" "SECRET_KEY")
            ;;
    esac
    
    local missing_vars=()
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        error "Missing required environment variables: ${missing_vars[*]}"
        return 1
    fi
    
    # Check Docker daemon
    if ! docker info >/dev/null 2>&1; then
        error "Docker daemon is not running"
        return 1
    fi
    
    # Check available disk space (require at least 2GB)
    local available_space=$(df / | tail -1 | awk '{print $4}')
    if [ "$available_space" -lt 2097152 ]; then  # 2GB in KB
        warning "Low disk space: $(($available_space / 1024))MB available"
    fi
    
    # Check available memory (require at least 2GB)
    local available_memory=$(free -m | awk 'NR==2{print $7}')
    if [ "$available_memory" -lt 2048 ]; then
        warning "Low available memory: ${available_memory}MB"
    fi
    
    success "Pre-deployment checks passed"
}

# Database migration check
check_database_migrations() {
    info "Checking database migrations..."
    
    # Create a temporary container to run migration check
    local temp_container="textloom-migration-check-$$"
    
    if docker run --rm --name "$temp_container" \
        -e DATABASE_URL="$DATABASE_URL" \
        -v "$(pwd):/app" \
        -w /app \
        python:3.11-slim \
        bash -c "pip install -q alembic asyncpg psycopg2-binary && python -c 'import alembic.config; alembic.config.main([\"check\"])'" >/dev/null 2>&1; then
        success "Database migrations are up to date"
    else
        warning "Database migration check failed or migrations needed"
        return 1
    fi
}

# Service health check with retry
wait_for_service() {
    local service_name="$1"
    local health_url="$2"
    local expected_status="${3:-200}"
    
    info "Waiting for $service_name to become healthy..."
    
    local retry_count=0
    while [ $retry_count -lt $MAX_RETRIES ]; do
        if curl -f -s --connect-timeout 5 "$health_url" >/dev/null 2>&1; then
            success "$service_name is healthy"
            return 0
        fi
        
        retry_count=$((retry_count + 1))
        if [ $retry_count -lt $MAX_RETRIES ]; then
            info "Attempt $retry_count/$MAX_RETRIES failed, retrying in 5 seconds..."
            sleep 5
        fi
    done
    
    error "$service_name failed to become healthy after $MAX_RETRIES attempts"
    return 1
}

# Check container health
check_container_health() {
    local container_pattern="$1"
    
    info "Checking health of containers matching: $container_pattern"
    
    local containers=$(docker ps --filter "name=$container_pattern" --format "{{.Names}}")
    
    if [ -z "$containers" ]; then
        error "No containers found matching pattern: $container_pattern"
        return 1
    fi
    
    local unhealthy_containers=()
    for container in $containers; do
        local health_status=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "unknown")
        
        case "$health_status" in
            "healthy")
                success "Container $container is healthy"
                ;;
            "starting")
                warning "Container $container is still starting"
                ;;
            "unhealthy")
                error "Container $container is unhealthy"
                unhealthy_containers+=("$container")
                ;;
            "unknown")
                warning "Container $container has no health check"
                ;;
        esac
    done
    
    if [ ${#unhealthy_containers[@]} -gt 0 ]; then
        error "Unhealthy containers: ${unhealthy_containers[*]}"
        return 1
    fi
    
    return 0
}

# Test API endpoints
test_api_endpoints() {
    info "Testing API endpoints..."
    
    local base_url="http://$TARGET_HOST:$TARGET_PORT"
    local endpoints=(
        "/health:200"
        "/:200"
    )
    
    for endpoint_spec in "${endpoints[@]}"; do
        local endpoint="${endpoint_spec%:*}"
        local expected_status="${endpoint_spec#*:}"
        local url="$base_url$endpoint"
        
        info "Testing $url (expecting HTTP $expected_status)"
        
        local response_code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 "$url" || echo "000")
        
        if [ "$response_code" = "$expected_status" ]; then
            success "✓ $endpoint returned HTTP $response_code"
        else
            error "✗ $endpoint returned HTTP $response_code (expected $expected_status)"
            return 1
        fi
    done
    
    success "All API endpoints are responding correctly"
}

# Load testing (basic)
basic_load_test() {
    info "Running basic load test..."
    
    local base_url="http://$TARGET_HOST:$TARGET_PORT"
    local concurrent_requests=5
    local total_requests=20
    
    info "Sending $total_requests requests with $concurrent_requests concurrent connections"
    
    # Simple load test using curl
    local success_count=0
    local failure_count=0
    
    for i in $(seq 1 $total_requests); do
        if curl -f -s --connect-timeout 5 "$base_url/health" >/dev/null 2>&1; then
            success_count=$((success_count + 1))
        else
            failure_count=$((failure_count + 1))
        fi
        
        # Small delay to prevent overwhelming
        sleep 0.1
    done
    
    local success_rate=$((success_count * 100 / total_requests))
    
    if [ $success_rate -ge 95 ]; then
        success "Load test passed: $success_rate% success rate ($success_count/$total_requests)"
    else
        error "Load test failed: $success_rate% success rate ($success_count/$total_requests)"
        return 1
    fi
}

# Resource usage check
check_resource_usage() {
    info "Checking resource usage..."
    
    # Check Docker container resource usage
    local containers=$(docker ps --filter "name=textloom" --format "{{.Names}}")
    
    if [ -z "$containers" ]; then
        warning "No TextLoom containers found"
        return 0
    fi
    
    for container in $containers; do
        local stats=$(docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" "$container")
        info "Resource usage for $container:"
        echo "$stats" | tail -n +2
    done
    
    # Check overall system resources
    info "System resource usage:"
    echo "Memory: $(free -h | grep '^Mem:' | awk '{print $3 "/" $2 " (" $3/$2*100 "%)"}')"
    echo "Disk: $(df -h / | tail -1 | awk '{print $3 "/" $2 " (" $5 ")"}')"
    echo "Load: $(uptime | awk -F'load average:' '{print $2}')"
}

# Generate deployment report
generate_report() {
    local status="$1"
    local report_file="deployment-report-$(date +%Y%m%d-%H%M%S).json"
    
    info "Generating deployment report: $report_file"
    
    cat > "$report_file" << EOF
{
  "deployment": {
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "environment": "$ENVIRONMENT",
    "target_host": "$TARGET_HOST",
    "target_port": "$TARGET_PORT",
    "status": "$status"
  },
  "system": {
    "disk_usage": "$(df -h / | tail -1 | awk '{print $5}')",
    "memory_usage": "$(free | grep '^Mem:' | awk '{printf "%.1f%%", $3/$2*100}')",
    "load_average": "$(uptime | awk -F'load average:' '{print $2}' | xargs)"
  },
  "containers": [
$(docker ps --filter "name=textloom" --format '    {"name": "{{.Names}}", "status": "{{.Status}}", "image": "{{.Image}}"}' | paste -sd,)
  ],
  "version": {
    "image_tag": "${IMAGE_TAG:-unknown}",
    "git_commit": "$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')"
  }
}
EOF
    
    success "Deployment report saved to: $report_file"
}

# Rollback function
rollback_deployment() {
    error "Deployment validation failed, initiating rollback..."
    
    if [ -f "docker-compose.yml" ]; then
        info "Stopping current deployment..."
        docker-compose down --remove-orphans
        
        # If backup exists, restore it
        if [ -f "docker-compose.backup.yml" ]; then
            info "Restoring from backup..."
            mv docker-compose.backup.yml docker-compose.yml
            docker-compose up -d
        fi
    fi
    
    error "Rollback completed"
}

# Main deployment validation
main() {
    local command="${1:-validate}"
    
    case "$command" in
        "pre-check")
            check_dependencies
            pre_deployment_checks
            ;;
        "post-check")
            wait_for_service "API" "http://$TARGET_HOST:$TARGET_PORT/health"
            check_container_health "textloom"
            test_api_endpoints
            basic_load_test
            check_resource_usage
            generate_report "success"
            ;;
        "validate")
            info "Starting deployment validation for $ENVIRONMENT environment"
            
            # Pre-deployment checks
            if ! check_dependencies || ! pre_deployment_checks; then
                generate_report "pre_check_failed"
                exit 1
            fi
            
            # Post-deployment checks
            if ! wait_for_service "API" "http://$TARGET_HOST:$TARGET_PORT/health" || \
               ! check_container_health "textloom" || \
               ! test_api_endpoints; then
                generate_report "validation_failed"
                if [ "${AUTO_ROLLBACK:-false}" = "true" ]; then
                    rollback_deployment
                fi
                exit 1
            fi
            
            # Optional load test
            if [ "${SKIP_LOAD_TEST:-false}" != "true" ]; then
                basic_load_test || warning "Load test failed but continuing"
            fi
            
            check_resource_usage
            generate_report "success"
            success "Deployment validation completed successfully"
            ;;
        "rollback")
            rollback_deployment
            ;;
        *)
            echo "Usage: $0 [pre-check|post-check|validate|rollback]"
            echo "  pre-check  - Run pre-deployment checks only"
            echo "  post-check - Run post-deployment checks only"
            echo "  validate   - Run complete validation (default)"
            echo "  rollback   - Rollback deployment"
            echo ""
            echo "Environment variables:"
            echo "  ENVIRONMENT         - Target environment (staging/production)"
            echo "  DEPLOYMENT_HOST     - Target host (default: localhost)"
            echo "  DEPLOYMENT_PORT     - Target port (default: 8000)"
            echo "  DEPLOYMENT_TIMEOUT  - Timeout in seconds (default: 60)"
            echo "  DEPLOYMENT_RETRIES  - Max retries (default: 10)"
            echo "  AUTO_ROLLBACK       - Auto rollback on failure (default: false)"
            echo "  SKIP_LOAD_TEST      - Skip load testing (default: false)"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"