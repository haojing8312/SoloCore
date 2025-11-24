# TextLoom CI/CD Pipeline Documentation

This document describes the comprehensive CI/CD pipeline implementation for the TextLoom project.

## Overview

The CI/CD pipeline is designed with production-ready automation, security, and reliability in mind. It follows industry best practices for Python FastAPI applications with Celery workers.

## Pipeline Architecture

### 🔄 Continuous Integration (CI)

The CI pipeline runs on every push and pull request to main/develop branches:

**File**: `.github/workflows/ci.yml`

#### Jobs:
1. **Code Quality Checks**
   - Code formatting (black)
   - Import sorting (isort)
   - Linting (flake8)
   - Type checking (mypy)

2. **Security Scanning**
   - Dependency vulnerability scan (safety, pip-audit)
   - Secret detection
   - Security linting

3. **Testing**
   - Unit tests with coverage
   - Integration tests
   - Database migration tests
   - API endpoint tests

4. **Build Test**
   - Docker image build verification
   - Multi-platform support (amd64, arm64)

5. **Dependency Analysis**
   - Dependency tree generation
   - Outdated package detection

### 🚀 Continuous Deployment (CD)

The CD pipeline deploys to staging on main branch pushes and production on tagged releases:

**File**: `.github/workflows/cd.yml`

#### Jobs:
1. **Build and Push**
   - Multi-stage Docker builds
   - Container registry push (GHCR)
   - SBOM generation
   - Multi-platform images

2. **Deploy Staging**
   - Automatic deployment to staging environment
   - Health checks and validation
   - Monitoring setup

3. **Deploy Production**
   - Manual approval required
   - Blue-green deployment strategy
   - Rollback capabilities
   - Performance validation

### 🔒 Security Pipeline

Comprehensive security scanning runs daily and on code changes:

**File**: `.github/workflows/security.yml`

#### Security Scans:
1. **CodeQL Analysis** - Static code analysis
2. **Dependency Security** - Vulnerability scanning
3. **Container Security** - Image vulnerability scanning
4. **Secrets Detection** - Credential leak prevention
5. **Infrastructure Security** - Configuration scanning
6. **OSSF Scorecard** - Security posture assessment

### 📦 Dependency Management

Automated dependency updates with security focus:

**File**: `.github/workflows/dependency-update.yml`

#### Features:
- Weekly dependency updates
- Security vulnerability patches
- Automated testing of updates
- Pull request creation
- Dependency grouping

### 🏷️ Release Management

Automated release process with comprehensive validation:

**File**: `.github/workflows/release.yml`

#### Release Process:
1. **Version Validation** - Semantic versioning checks
2. **Build Artifacts** - Multi-platform images and packages
3. **Testing** - Comprehensive test suite
4. **Release Creation** - GitHub release with changelog
5. **Production Deployment** - Automated production rollout

## Key Features

### 🛡️ Security First
- **Zero hardcoded secrets** - All sensitive data via environment variables
- **Vulnerability scanning** - Daily security scans with automated alerts
- **SBOM generation** - Software Bill of Materials for compliance
- **Secret detection** - Prevents credential leaks in code

### 🔄 Zero-Downtime Deployments
- **Health checks** - Comprehensive service validation
- **Rollback capabilities** - Automatic rollback on failure
- **Blue-green strategy** - Seamless production updates
- **Load testing** - Performance validation

### 📊 Comprehensive Monitoring
- **Multi-environment support** - Dev, staging, production
- **Resource monitoring** - CPU, memory, disk usage
- **Service health** - API, database, Redis, Celery workers
- **Deployment reports** - Detailed deployment status

### 🐳 Container Optimization
- **Multi-stage builds** - Optimized image sizes
- **Security scanning** - Container vulnerability detection
- **Resource limits** - Proper resource allocation
- **Health checks** - Container-level health monitoring

## Configuration Files

### Environment Configuration
- **`.env.example`** - Comprehensive environment template
- **Environment-specific** - Dev, staging, production configs
- **Security-focused** - No hardcoded credentials

### Docker Configuration
- **`Dockerfile`** - Multi-stage production-ready builds
- **`.dockerignore`** - Optimized build context
- **`docker-compose.*.yml`** - Environment-specific orchestration

### Code Quality
- **`.flake8`** - Linting configuration
- **`pyproject.toml`** - Tool configuration (black, isort, mypy)
- **`pytest.ini`** - Test configuration

### Dependency Management
- **`.github/dependabot.yml`** - Automated dependency updates
- **Security grouping** - Critical updates prioritized
- **Version pinning** - Stable dependency management

## Deployment Environments

### Development
- **Local development** - Hot reload, debug mode
- **Feature branches** - Isolated testing
- **Mock services** - Simplified dependencies

### Staging
- **Production-like** - Similar to production configuration
- **Integration testing** - Full end-to-end validation
- **Performance testing** - Load and stress testing

### Production
- **High availability** - Multiple replicas
- **Resource optimization** - Proper limits and requests
- **Monitoring** - Full observability stack
- **Backup strategy** - Data protection

## Scripts and Tools

### Health Checking
```bash
# Comprehensive health check
./scripts/healthcheck.sh

# Individual service checks
./scripts/healthcheck.sh api
./scripts/healthcheck.sh redis
./scripts/healthcheck.sh database
```

### Deployment Validation
```bash
# Pre-deployment checks
./scripts/deployment-check.sh pre-check

# Post-deployment validation
./scripts/deployment-check.sh post-check

# Full deployment validation
./scripts/deployment-check.sh validate

# Rollback if needed
./scripts/deployment-check.sh rollback
```

## Security Best Practices

### 1. Environment Variables
- All secrets via environment variables
- No hardcoded credentials
- Environment-specific configurations

### 2. Container Security
- Non-root user execution
- Minimal base images
- Regular security updates

### 3. Network Security
- CORS configuration
- API authentication
- Rate limiting

### 4. Dependency Security
- Regular vulnerability scans
- Automated security updates
- Dependency pinning

## Monitoring and Alerting

### Application Monitoring
- **Health endpoints** - Service status monitoring
- **Performance metrics** - Response times, throughput
- **Error tracking** - Exception monitoring
- **Resource usage** - CPU, memory, disk

### Infrastructure Monitoring
- **Container health** - Docker container status
- **Service discovery** - Service availability
- **Network monitoring** - Connectivity checks
- **Storage monitoring** - Disk usage, database health

### Alerting
- **Deployment failures** - Immediate notification
- **Security vulnerabilities** - Critical alerts
- **Performance degradation** - Threshold-based alerts
- **Service outages** - Real-time notifications

## Usage Examples

### Local Development
```bash
# Install dependencies
uv sync --dev

# Run development server
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run tests
pytest tests/ -v

# Code quality checks
uv run black .
uv run isort .
uv run flake8 .
uv run mypy .
```

### Docker Development
```bash
# Build development image
docker build --target development -t textloom:dev .

# Run with docker-compose
docker-compose up -d

# Check service health
./scripts/healthcheck.sh
```

### Production Deployment
```bash
# Set environment variables
export DATABASE_URL="postgresql://..."
export REDIS_PASSWORD="..."
export SECRET_KEY="..."

# Deploy production
docker-compose -f docker-compose.production.yml up -d

# Validate deployment
./scripts/deployment-check.sh validate

# Monitor services
docker-compose -f docker-compose.production.yml ps
```

### CI/CD Triggers

#### Automatic Triggers
- **Push to main** → Deploy to staging
- **Tagged release** → Deploy to production
- **Pull requests** → Run CI pipeline
- **Daily** → Security scans
- **Weekly** → Dependency updates

#### Manual Triggers
- **Production deployment** → Via GitHub Actions
- **Rollback** → Via deployment scripts
- **Security scans** → On-demand
- **Performance tests** → Load testing

## Troubleshooting

### Common Issues

#### Build Failures
- Check dependency conflicts
- Verify environment variables
- Review Docker build logs

#### Test Failures
- Ensure test database is running
- Check test environment configuration
- Review test logs

#### Deployment Issues
- Verify environment variables
- Check service health
- Review deployment logs

#### Security Scan Failures
- Update vulnerable dependencies
- Review security scan reports
- Address critical vulnerabilities

### Debug Commands
```bash
# Check container logs
docker-compose logs -f [service]

# Test health endpoints
curl http://localhost:8000/health

# Check resource usage
docker stats

# Monitor Celery workers
docker-compose exec worker celery -A celery_config inspect active

# Database connection test
docker-compose exec api python -c "from models.database import test_connection; test_connection()"
```

## Contributing to CI/CD

### Adding New Tests
1. Add test files to `tests/` directory
2. Update test configuration if needed
3. Ensure tests pass in CI environment

### Modifying Deployment
1. Update deployment scripts in `scripts/`
2. Test changes in staging environment
3. Update documentation

### Security Improvements
1. Review security scan results
2. Update security configurations
3. Test security controls

### Performance Optimization
1. Profile application performance
2. Update resource limits
3. Optimize container images

## Best Practices Summary

1. **Security First** - Never commit secrets, scan regularly
2. **Test Everything** - Comprehensive test coverage
3. **Automate All** - No manual deployment steps
4. **Monitor Continuously** - Real-time observability
5. **Fail Fast** - Early detection of issues
6. **Document Changes** - Keep documentation updated
7. **Review Regularly** - Continuous improvement

This CI/CD pipeline provides a robust, secure, and scalable deployment solution for the TextLoom project, following industry best practices and ensuring high availability and reliability in production environments.