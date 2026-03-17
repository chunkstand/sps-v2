# Stack Research

**Domain:** Permit case workflow and release bundle management
**Researched:** 2026-03-17
**Confidence:** MEDIUM

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.13.x | Primary runtime for services and workers | Stable, widely supported runtime with strong typing and async support; aligns with 2025+ ecosystem support. Confidence: HIGH. |
| FastAPI | 0.135.1 | API layer for case workflows and bundle services | High-performance ASGI framework with OpenAPI-first contracts and Pydantic data validation. Confidence: HIGH. |
| Temporal Server | 1.30.1 | Workflow orchestration for long-running permit cases | Durable execution with full event history, retries, and visibility for case workflows. Confidence: HIGH. |
| PostgreSQL | 18.3 | System of record for cases, manifests, and audit metadata | ACID guarantees, JSONB for flexible manifests, strong consistency for evidence trails. Confidence: HIGH. |
| Apache Kafka | 4.2.0 | Event log and integration backbone | Ordered, durable event stream for release bundle lifecycle and audit trails. Confidence: HIGH. |
| Amazon S3 API | 2006-03-01 | Object storage for release bundles and manifests | Versioned, immutable object storage with SDK support and integrity metadata. Confidence: HIGH. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| temporalio | 1.23.0 | Temporal Python SDK | Use for all workflow/activity code and durable task execution. Confidence: HIGH. |
| SQLAlchemy | 2.0.48 | ORM + query layer | Use for transactional domain writes and complex query composition. Confidence: HIGH. |
| Alembic | 1.18.4 | Schema migrations | Use for deterministic schema evolution across environments. Confidence: HIGH. |
| Pydantic | 2.12.5 | Data validation and settings | Use for strict request/response validation and manifest schema enforcement. Confidence: HIGH. |
| asyncpg | 0.31.0 | Async PostgreSQL driver | Use with FastAPI/async SQLAlchemy for high-throughput DB access. Confidence: HIGH. |
| boto3 | 1.42.70 | AWS SDK for S3 | Use for bundle/manifest storage, signed URL generation, and metadata tagging. Confidence: HIGH. |
| PyJWT | 2.12.1 | JWT validation | Use for strict JWT verification (aud, iss, exp, jti) in API gateways/services. Confidence: HIGH. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| pytest | Automated tests | Run unit + integration tests for workflows and bundle validation. |
| ruff | Lint + format | Enforce a single linting/formatting toolchain for Python. |
| mypy | Static typing | Enforce type safety for workflow contracts and manifest models. |

## Installation

```bash
# Core
pip install "fastapi==0.135.1" "temporalio==1.23.0" "SQLAlchemy==2.0.48"

# Supporting
pip install "alembic==1.18.4" "pydantic==2.12.5" "asyncpg==0.31.0" "boto3==1.42.70" "PyJWT==2.12.1"

# Dev dependencies
pip install -D pytest ruff mypy
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Temporal Server | Camunda 8 (Zeebe) | Choose when BPMN modeling by non-developers is a hard requirement and you can run the Elastic/Operate stack. |
| Apache Kafka | RabbitMQ | Choose when workloads are simple queues without ordering/audit log needs. |
| FastAPI | Django + DRF | Choose when you need a full monolithic admin surface and built-in auth/ORM conventions. |
| Amazon S3 API | MinIO | Choose for on-prem S3-compatible storage with the same object semantics. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Custom in-house workflow state machine | Hard to make durable, observable, and replayable; rewrites are common. | Temporal Server. |
| Cron-driven or DB-polling workflow steps | Loses deterministic history and makes retries/visibility brittle. | Temporal workflows and activities. |
| SQLite for primary case data | No HA, limited concurrency, and poor fit for multi-writer workflows. | PostgreSQL 18.3. |
| Storing bundles as DB blobs | Expensive storage/IO and weak lifecycle management for large artifacts. | S3-compatible object storage. |

## Stack Patterns by Variant

**If you need BPMN modeling for business users:**
- Use Camunda 8 instead of Temporal
- Because BPMN is the standard modeling language in regulated case workflows

**If you are on-prem or air-gapped:**
- Use MinIO for S3-compatible storage and Kafka in KRaft mode
- Because you still need versioned object storage and a durable event log without managed services

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| fastapi@0.135.1 | pydantic@2.x, python>=3.10 | FastAPI uses Pydantic v2 and requires Python 3.10+. |
| temporalio@1.23.0 | python>=3.10 | Temporal Python SDK requires Python 3.10+. |
| asyncpg@0.31.0 | postgresql@9.5-18 | asyncpg supports Postgres 9.5 through 18. |

## Sources

- https://www.python.org/downloads/ — Python 3.13/3.14 release status (HIGH)
- https://pypi.org/project/fastapi/ — FastAPI 0.135.1 version + Python support (HIGH)
- https://github.com/temporalio/temporal/releases/latest — Temporal Server 1.30.1 (HIGH)
- https://pypi.org/project/temporalio/ — Temporal Python SDK 1.23.0 (HIGH)
- https://www.postgresql.org/docs/current/ — PostgreSQL 18.3 docs (HIGH)
- https://kafka.apache.org/community/downloads/ — Kafka 4.2.0 supported release (HIGH)
- https://docs.aws.amazon.com/AmazonS3/latest/API/Welcome.html — S3 API version 2006-03-01 (HIGH)
- https://pypi.org/project/SQLAlchemy/ — SQLAlchemy 2.0.48 (HIGH)
- https://pypi.org/project/alembic/ — Alembic 1.18.4 (HIGH)
- https://pypi.org/project/pydantic/ — Pydantic 2.12.5 (HIGH)
- https://pypi.org/project/asyncpg/ — asyncpg 0.31.0 (HIGH)
- https://pypi.org/project/boto3/ — boto3 1.42.70 (HIGH)
- https://pypi.org/project/PyJWT/ — PyJWT 2.12.1 (HIGH)

---
*Stack research for: permit case workflow and release bundle management*
*Researched: 2026-03-17*
