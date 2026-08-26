# Approved Python Skeleton

## Goal

Create the approved Python/FastAPI project structure and reproducible `uv` dependency environment
without implementing telecom application behavior.

## Requirement References

- Approved `docs/ARCHITECTURE.md`
- D-001 through D-019

## Non-Goals

- No API routes or schemas.
- No domain entities or services.
- No PostgreSQL schema or migration.
- No synthetic KDDI dataset.
- No SambaNova calls.
- No frontend, containers, cloud resources, or CI/CD.

## Current State

The repository contains only the approved project knowledge system and an empty tests directory.
Python 3.13.5 and uv 0.8.17 are available locally.

## Proposed Design

Create package and test boundaries matching the approved architecture. Configure dependencies and
verification tools in `pyproject.toml`, resolve them into `uv.lock`, and keep every package empty
until a behavior has an approved test-first implementation plan.

## Files Expected to Change

- `pyproject.toml`
- `uv.lock`
- `.python-version`
- `.gitignore`
- `.env.example`
- `alembic.ini`
- `src/telecom_agent/**/__init__.py`
- `tests/*/.gitkeep`
- `evals/README.md`
- `evals/cases/.gitkeep`
- `migrations/README.md`
- `README.md`

## Test Strategy

- Verify the package imports.
- Verify pytest can collect the empty skeleton without configuration errors.
- Run Ruff against the created Python package.
- Run mypy against the created Python package.
- Verify Alembic and the OpenAI SDK are importable.

## Implementation Steps

- [x] Inspect approved documentation and local tooling.
- [x] Create the approved directory boundaries.
- [x] Add project metadata and empty package markers.
- [x] Resolve dependencies with `uv lock` and `uv sync`.
- [x] Run verification commands.
- [x] Record results and move this plan to `completed/`.

## Open Questions

None for the skeleton. Exact API, domain, database, and evaluation behavior remains intentionally
deferred to feature-specific plans.

## Decisions

- Use Python `>=3.12` while running locally on Python 3.13.5.
- Keep the project non-packaged during the empty skeleton phase; pytest and mypy point to `src`.

## Discoveries

- The local uv version reports a 2025 build date but supports the required dependency groups.
- The Homebrew uv binary panics inside the restricted sandbox while probing macOS network
  configuration. Resolution and one `uv run` check succeeded outside that restriction; direct
  project-local executables worked offline inside it.
- During completion, the pre-existing project knowledge files unexpectedly disappeared from the
  workspace. No recoverable copy was present, so they were reconstructed from the approved
  conversation record before completion.

## Progress

The approved skeleton, lockfile, local environment, and smoke test are complete. No application
behavior has been added.

## Verification

Planned commands:

```bash
uv sync
PYTHONPATH=src uv run python -c "import telecom_agent"
uv run pytest
uv run ruff check .
uv run mypy src
uv run python -c "import alembic, openai, psycopg, sqlalchemy"
```

Results:

- `uv run --frozen pytest`: 1 passed.
- `.venv/bin/ruff check .`: passed.
- `.venv/bin/mypy src tests`: passed with no issues in 11 source files.
- Project and dependency import smoke: passed.
- `.venv/bin/alembic --help`: passed.

## Result

- Created the approved source, adapter, API, test, evaluation, and migration boundaries.
- Added approved runtime and development dependencies and generated `uv.lock`.
- Added one package-import smoke test; no product behavior or application interfaces were created.
- Added safe environment placeholders and ignored local credentials and environments.
- Restored and verified the approved project knowledge system after the unexpected disappearance.
- Remaining work begins with a separately approved feature plan and test-first behavior.
