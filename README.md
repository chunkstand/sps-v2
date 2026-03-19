# SPS

SPS is a FastAPI + Temporal application for managing permit-case intake, review, evidence, submission, release bundles, and operational controls.

This repository is now application-first. The code that runs the system lives under `src/sps`, the API surface is mounted from `src/sps/api`, and the test suite under `tests` exercises the runtime behavior directly.

## Application areas

- API routes for cases, reviews, evidence, releases, overrides, emergencies, and admin governance flows
- Temporal workflows for permit-case progression and submission handling
- Postgres-backed persistence via SQLAlchemy + Alembic
- S3-compatible evidence storage
- Release-bundle generation and blocker validation
- Runtime adapter slices for jurisdiction-specific behavior

## Project layout

- `src/sps/` application code
- `tests/` unit and integration coverage
- `alembic/` database migrations
- `scripts/` operational verification and local helper scripts
- `tools/` integrity and maintenance utilities
- `docker-compose.yml` local Postgres, Temporal, and MinIO stack

## Legacy spec assets

The repo still contains legacy spec-package material under `sps_full_spec_package/` plus supporting root-level reference directories such as `specs/`, `model/`, `invariants/`, and `runbooks/`. Those assets are now supporting inputs for release-bundle validation and compliance-oriented features, not the identity of the repository itself.

## Getting started

1. Install the locked dev environment: `uv sync --extra dev --frozen`
2. Start local services: `docker compose up -d`
3. Run the API: `uv run uvicorn sps.api.main:app --reload`
4. Run unit tests: `uv run pytest -m "unit"`

More local workflow detail lives in `README-DEV.md`.
