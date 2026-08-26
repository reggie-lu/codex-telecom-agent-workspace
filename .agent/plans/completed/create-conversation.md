# Create a Conversation

## Goal

An authenticated synthetic customer can create an empty support conversation through
`POST /v1/conversations`, and the conversation is persisted in local PostgreSQL under that customer.

## Requirement References

- Approved conversation-centric API in `docs/ARCHITECTURE.md`
- D-007 — Synthetic bearer authentication
- D-008 — Explicit development reset
- D-012 — Explicit persistent types
- D-013 — Conversation-centric API
- D-018 — SQLAlchemy, Alembic, and Psycopg

## Non-Goals

- Sending or retrieving messages.
- Plan, bill, or charge retrieval.
- SambaNova calls.
- Escalation creation or state transitions.
- Conversation closing, reopening, listing, or deletion.
- Production authentication or real KDDI accounts.

## Current State

The vertical slice is complete. Domain and service behavior, the FastAPI contract, PostgreSQL
repositories, application composition, and the initial Alembic migration are implemented and
verified together.

## Proposed Design

- Add an `OPEN` conversation status and a framework-independent conversation domain entity.
- Add a narrow conversation repository port and a create-conversation service.
- Add SQLAlchemy records for synthetic customers and conversations only.
- Store a one-way SHA-256 hash for synthetic bearer-token lookup; never store the raw token.
- Add the first Alembic migration with customer ownership, UUID keys, UTC timestamps, foreign keys,
  and indexes required by this endpoint.
- Add a FastAPI bearer-auth dependency and conversation route.
- Wire dependencies in one application-composition module without a generic container framework.

## Files Expected to Change

- `src/telecom_agent/domain/conversations.py`
- `src/telecom_agent/ports/conversations.py`
- `src/telecom_agent/services/create_conversation.py`
- `src/telecom_agent/adapters/postgres/models.py`
- `src/telecom_agent/adapters/postgres/repositories.py`
- `src/telecom_agent/api/auth.py`
- `src/telecom_agent/api/schemas.py`
- `src/telecom_agent/api/app.py`
- Alembic environment and initial revision files
- Focused unit, API, and PostgreSQL integration tests
- `.env.example` and README development instructions if needed

## Test Strategy

- Unit: creation produces an open conversation owned by the authenticated customer.
- Unit: repository failure is surfaced without falsely reporting success.
- API: missing or invalid bearer token returns `401` with a bearer challenge.
- API: a valid synthetic token returns `201` and the approved response schema.
- API: repeated requests create distinct conversations because idempotency is deferred.
- Integration: PostgreSQL persists the conversation under the correct customer UUID.
- Integration: raw bearer tokens are not stored.
- Migration: upgrade creates the initial schema from an empty test database.

Tests will be written and observed failing before implementation.

## Implementation Steps

- [x] Confirm the public request, response, error, and idempotency contract.
- [x] Obtain approval before starting or configuring a local PostgreSQL service if needed.
- [x] Add failing domain and service tests.
- [x] Implement minimum domain, port, and service behavior.
- [x] Add failing API authentication and response tests.
- [x] Implement minimum FastAPI route and composition.
- [x] Add failing PostgreSQL repository and migration tests.
- [x] Implement models, repository, Alembic environment, and initial migration.
- [x] Run targeted tests, then full pytest, Ruff, and mypy.
- [x] Update durable documentation only for approved or discovered contract changes.
- [x] Record results and move the plan to `completed/`.

## Open Questions

None.

## Decisions

- No request body; return `201` with `id`, `status`, and `created_at` only.
- Missing or invalid tokens use the approved `401` envelope and bearer challenge.
- Each successful request creates a distinct conversation; idempotency is deferred.

## Discoveries

- `psql` and `pg_isready` are installed at `/opt/homebrew/bin`.
- The existing Homebrew PostgreSQL 14 cluster could not use occupied port 5432, so verification used
  an isolated `telecom_agent_test` database on temporary localhost port 55432.
- The sandbox blocks local TCP database access; PostgreSQL integration verification therefore ran
  with the approved elevated test command.

## Progress

All test-first implementation steps and verification checks are complete.

## Verification

Completed commands:

```bash
uv run pytest tests/unit
uv run pytest tests/api
uv run pytest tests/integration
uv run pytest
uv run ruff check .
uv run mypy src tests
```

## Result

Implemented the approved authenticated conversation-creation contract. The service creates an open,
customer-owned UUID conversation; authentication looks up only a SHA-256 token hash; SQLAlchemy
persists it transactionally; and Alembic creates the constrained customer and conversation schema.

Verification on 2026-08-26:

- `pytest`: 10 passed, including three PostgreSQL integration tests.
- `ruff check .`: passed.
- `mypy src tests`: passed with no issues across 29 source files.
