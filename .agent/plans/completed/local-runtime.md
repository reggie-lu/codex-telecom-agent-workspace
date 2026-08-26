# Local Runtime, Seed, and Health

## Goal

A developer can seed the approved synthetic customer, start the localhost API with one stable CLI
command, and verify API and PostgreSQL readiness through a health endpoint.

## Requirement References

- D-007 — Synthetic bearer authentication
- D-008 — Explicit development reset
- D-009 — Localhost-only runtime
- D-018 — SQLAlchemy, Alembic, and Psycopg
- `AGENTS.md` run/verification documentation and architecture-flow maintenance rules

## Non-Goals

- Container, Docker Compose, Kubernetes, Helm, or remote deployment.
- Production authentication, secrets, probes, or operational monitoring.
- Automatic migrations, destructive reset behavior, or startup data resets.
- Message handling, KDDI data retrieval, SambaNova calls, or escalation behavior.

## Current State

The API can be composed with PostgreSQL, but developers must seed a customer with raw SQL and start
Uvicorn through an inline Python command. There is no health endpoint or installed console command.

## Proposed Design

- Make the source package installable and expose a `telecom-agent` console command.
- Add `telecom-agent seed`, which reads `DATABASE_URL` and idempotently creates the approved
  Synthetic Alice identity while storing only its SHA-256 token hash.
- Add `telecom-agent serve`, which reads `DATABASE_URL`, composes the PostgreSQL application, and
  binds Uvicorn to `127.0.0.1:8000`.
- Add an unauthenticated `GET /health` endpoint backed by a narrow database-health port and
  PostgreSQL `SELECT 1` adapter.
- Dispose the SQLAlchemy engine during FastAPI lifespan shutdown.
- Fail CLI configuration clearly when `DATABASE_URL` is absent; never auto-load or invent secrets.

## Files Expected to Change

- `pyproject.toml` and `uv.lock`
- `src/telecom_agent/cli.py`
- Health domain/port, PostgreSQL adapter, API schema/route, and composition modules
- Focused CLI, API, and PostgreSQL integration tests
- `README.md`, `docs/ARCHITECTURE.md`, and later `docs/FEATURE_HISTORY.md`

## Test Strategy

- API: healthy database returns the approved `200` health contract without authentication.
- API: unavailable database returns the approved `503` health contract without leaking details.
- Unit: CLI reports missing `DATABASE_URL`, seed result, and stable localhost serve configuration.
- Integration: seeding is idempotent and persists the hash rather than the raw development token.
- Integration: PostgreSQL health adapter reports reachable and unreachable states safely.
- Full: pytest, Ruff, mypy, locked environment sync, and documented manual curl verification.

Tests will be written and observed failing before implementation.

## Implementation Steps

- [x] Confirm the public health response contract.
- [x] Add failing API health tests and implement the narrow health boundary.
- [x] Add failing PostgreSQL seed and health integration tests and implement adapters.
- [x] Add failing CLI tests and implement `seed` and `serve` commands.
- [x] Make the project package installable and regenerate the lock/environment.
- [x] Run targeted and full automated verification.
- [x] Replace temporary README commands and update the living architecture flow.
- [x] Record human verification results and move this plan to `completed/`.
- [x] Await human manual verification before recording CP-002, committing, or pushing.

## Open Questions

None.

## Decisions

- The CLI never runs migrations or resets data implicitly.
- Serve remains fixed to localhost port 8000 for this slice.
- The approved development token may be printed by the explicit seed command but is never persisted
  or logged by request handling.
- `GET /health` is unauthenticated and returns only `200 {"status":"ok","database":"ok"}` or
  `503 {"status":"unavailable","database":"unavailable"}`. It is localhost-only now and must
  remain internal rather than publicly routed in a future deployment.

## Discoveries

- The repository is currently configured as a non-package uv project, so a stable console command
  requires packaging metadata.
- A user-authored `7dcf895` commit now follows CP-001 and is preserved unchanged.
- The Homebrew PostgreSQL server was already available on port 55432 during final verification.
- The application database already contained Synthetic Alice from the earlier manual procedure; the
  new seed command correctly reported the idempotent existing state.

## Progress

Implementation, Codex verification, and the required human run-through are complete. CP-002 is
recorded and this plan is ready for archival.

## Verification

Completed commands:

```bash
uv sync --frozen
uv run pytest
uv run ruff check .
uv run mypy src tests
```

## Result

Implemented an installable `telecom-agent` CLI with idempotent `seed` and localhost-only `serve`
commands, an unauthenticated minimal PostgreSQL-aware `/health` endpoint, and graceful engine
disposal at shutdown. Replaced the temporary SQL and inline-Python runbook and updated the approved
architecture flow and decision record.

Verification on 2026-08-26:

- Full pytest with isolated PostgreSQL: 20 passed.
- Ruff: passed.
- Strict mypy: passed across 35 source files.
- Manual Codex check: seed reported the existing synthetic customer; `/health` returned the exact
  approved `200` body; conversation creation returned `201`; `Ctrl-C` completed graceful shutdown.
- Human verification: passed on 2026-08-26 using the documented seed, serve, health, and
  conversation workflow.
