<!--
Sync Impact Report
==================
Version Change: 1.0.0 (Initial ratification)
Modified Principles: N/A (new constitution)
Added Sections:
  - Core Principles (6 principles)
  - Architecture Constraints
  - Quality Standards
  - Governance
Removed Sections: N/A
Templates Requiring Updates:
  ✅ plan-template.md - Updated with constitution check alignment
  ✅ spec-template.md - Aligned with feature requirements structure
  ✅ tasks-template.md - Updated with testing and dependency structure
  ⚠ Command files - No command-specific files found; skip for now
Follow-up TODOs: None
-->

# SoloCore Constitution

## Core Principles

### I. Monorepo Architecture (NON-NEGOTIABLE)

SoloCore MUST maintain a clear monorepo structure where each sub-project operates as an independent, self-contained unit with its own:
- Build system and dependency management
- Testing framework and test suite
- Documentation (including project-specific CLAUDE.md or README.md)
- Development and deployment workflows

**Rationale:** The monorepo contains multiple technology stacks (Python, Java, Node.js, Vue) that cannot share dependencies. Independence ensures each project can evolve without breaking others while benefiting from shared organizational structure and documentation.

**Rules:**
- Each sub-project MUST have its own isolated environment (e.g., Python venv, Node modules, Maven workspace)
- Cross-project dependencies MUST use versioned APIs or Git submodules, NEVER direct code imports
- Shared documentation (CLAUDE.md, README.md) MUST reflect all sub-projects accurately

### II. Configuration Safety (NON-NEGOTIABLE)

`.env` files containing production credentials MUST NEVER be modified without explicit user approval.

**Rationale:** Configuration changes can cause production outages, expose secrets, or break running services. The `.env.example` serves as the single source of truth for configuration templates.

**Rules:**
- Modifications to `.env` files MUST be preceded by user confirmation
- `.env.example` is the ONLY configuration template; NEVER create additional template files (e.g., `.env.template`, `env.example`)
- New configuration keys MUST be documented in `.env.example` with safe default values
- Sensitive values (passwords, API keys, tokens) MUST use environment variables, NEVER hard-coded

### III. Database Integrity (NON-NEGOTIABLE)

All database schema changes MUST follow a migration-first approach using the appropriate migration tool for each project.

**Rationale:** Direct database modifications without migrations lead to schema drift, deployment failures, and data loss. Migrations provide rollback capability and deployment repeatability.

**Rules:**
- TextLoom: Use Alembic (`alembic revision --autogenerate`, then `alembic upgrade head`)
- Easegen-Admin: Use Liquibase or Flyway as configured
- All migration files MUST be committed to version control
- Database changes MUST be tested in non-production environments first
- ORM models (e.g., SQLAlchemy `db_models.py`) are the single source of truth for schema

### IV. Async-First Development (TextLoom)

TextLoom MUST use `async`/`await` patterns throughout the application for all I/O operations.

**Rationale:** FastAPI is built on ASGI (async), and mixing sync and async code incorrectly causes blocking and performance degradation. Consistency ensures predictable behavior under load.

**Rules:**
- All database operations MUST use async session managers (e.g., `get_db_session()`)
- All HTTP clients MUST use async libraries (e.g., `httpx`, not `requests`)
- External API calls MUST be awaited or delegated to Celery tasks
- Thread isolation MUST be used when integrating synchronous libraries (e.g., Playwright)

### V. Testing Discipline

Features MUST be validated through multiple testing layers appropriate to their complexity and risk.

**Rationale:** Different testing layers catch different classes of bugs. Unit tests validate logic, integration tests validate component interaction, and E2E tests validate user journeys.

**Testing Layers:**
- **Unit Tests**: Fast, isolated tests of business logic (REQUIRED for core algorithms)
- **Contract Tests**: Validate API contracts and library interfaces (REQUIRED for public APIs)
- **Integration Tests**: Validate cross-component behavior (REQUIRED for database, external API, and service interactions)
- **E2E/Business Tests**: Validate complete user workflows (REQUIRED for critical user journeys)

**Rules:**
- New features MUST include tests appropriate to their risk level
- API changes MUST include contract tests before merging
- Breaking changes MUST be validated by updating existing tests
- Tests MUST be runnable in CI/CD pipelines without manual intervention

### VI. Documentation Standards

Every sub-project MUST maintain comprehensive, up-to-date documentation covering setup, development, and architecture.

**Rationale:** SoloCore targets both developers (who need technical documentation) and creators (who need usage documentation). Good documentation enables self-service and reduces support burden.

**Required Documentation:**
- **README.md**: User-facing quick start and feature overview
- **CLAUDE.md**: Developer-facing technical guide for AI assistants and contributors
- **API Documentation**: OpenAPI/Swagger for APIs (TextLoom, Easegen-Admin)
- **Architecture Docs**: Design decisions, data flow, and component diagrams (in `docs/` or sub-project `docs/`)

**Rules:**
- Documentation MUST be updated in the same PR as code changes
- Examples in documentation MUST be tested and functional
- Deprecated features MUST be marked clearly with migration paths

## Architecture Constraints

### Modularity

- Sub-projects MUST NOT directly import code from other sub-projects
- Shared functionality MUST be extracted to independent libraries or services
- Inter-project communication MUST use documented APIs or message queues

### Technology Stack Boundaries

Each sub-project has an approved technology stack that MUST NOT be mixed without justification:
- **TextLoom**: Python 3.11+, FastAPI, Celery, PostgreSQL, Redis
- **Easegen-Admin**: Java 17+, Spring Boot 3.x, MyBatis-Plus, MySQL, Redis
- **Easegen-Front**: Vue 3, TypeScript, Vite, Element Plus, Pinia
- **Editly**: Node.js 18+, FFmpeg

**Exceptions:** Cross-stack integration MUST use standard protocols (REST APIs, message queues, shared storage).

### Security Boundaries

- Authentication MUST use JWT tokens with appropriate expiration
- API endpoints MUST validate all inputs using framework validation (Pydantic, Bean Validation)
- Internal/test-only endpoints MUST be protected by environment-specific tokens
- CORS MUST be explicitly configured; NEVER use wildcard `*` in production

## Quality Standards

### Code Quality

- All code MUST pass project-specific linters before merging:
  - TextLoom: `black`, `isort`, `mypy`, `flake8`
  - Easegen-Admin: Checkstyle, SpotBugs (as configured)
  - Easegen-Front: ESLint, Prettier, Stylelint
- Complexity violations MUST be justified in the PR description
- Dead code and unused imports MUST be removed

### Performance Expectations

- **TextLoom API**: P95 latency <500ms for non-video endpoints
- **Video Processing**: Progress updates MUST be pushed at least every 5 seconds during processing
- **Celery Tasks**: Long-running tasks (>30s) MUST update progress and support cancellation
- **Database**: Queries returning >1000 rows MUST use pagination
- **Frontend**: Initial page load <3 seconds on standard broadband

### Error Handling

- User-facing errors MUST include actionable error messages
- System errors MUST be logged with sufficient context for debugging
- Failed background tasks MUST be retryable with exponential backoff
- Database transaction failures MUST trigger automatic rollback

## Governance

This constitution supersedes all other project practices and conventions. Any code review, design decision, or implementation MUST be validated against these principles.

### Amendment Process

1. Proposed changes MUST be documented in a GitHub issue with justification
2. Amendments MUST be discussed and approved by project maintainers
3. Breaking changes (MAJOR version) MUST include a migration guide
4. Constitution updates MUST be propagated to dependent templates (plan, spec, tasks)

### Compliance Review

- All pull requests MUST include a constitution compliance statement
- Design documents (specs, plans) MUST include a "Constitution Check" section
- Violations MUST be justified with "Complexity Tracking" evidence

### Versioning

This constitution follows semantic versioning:
- **MAJOR**: Backward-incompatible governance changes (e.g., removing a principle, changing NON-NEGOTIABLE rules)
- **MINOR**: New principles or sections added
- **PATCH**: Clarifications, typo fixes, non-semantic refinements

**Version**: 1.0.0 | **Ratified**: 2025-11-26 | **Last Amended**: 2025-11-26
