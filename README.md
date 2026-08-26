# Telecom Customer-Service Agent

Status: Active implementation — conversation creation complete

## Purpose

An API-first evaluation prototype for grounded KDDI plan and billing support, unexpected-charge
explanations, and contextual human escalation using synthetic customer data.

## Development

Prerequisites: Python 3.12+, `uv`, and local PostgreSQL.

```bash
uv sync
uv run pytest
uv run ruff check .
uv run mypy src tests
```

## Local PostgreSQL Setup

This workspace uses the Homebrew PostgreSQL 14 cluster on port `55432`, because the default port
`5432` is unavailable locally. Start it with:

```bash
/opt/homebrew/bin/pg_ctl \
  -D /opt/homebrew/var/postgresql@14 \
  -l /private/tmp/codex-telecom-postgres.log \
  -o "-p 55432" start
```

Create the application database once. An "already exists" error is harmless if it was created
previously.

```bash
/opt/homebrew/bin/createdb \
  -h 127.0.0.1 \
  -p 55432 \
  telecom_agent
```

Copy the example configuration and load it into the current shell:

```bash
cp .env.example .env
set -a
source .env
set +a
```

Copying `.env` alone does not load it. Alembic requires `DATABASE_URL` to be exported in the shell.
The untracked `.env` file may be edited when local credentials or ports differ.

Apply the database schema:

```bash
uv run alembic upgrade head
```

The first migration should finish with output similar to:

```text
Running upgrade  -> 20260826_01, create conversations
```

To stop the local server later without deleting its data:

```bash
/opt/homebrew/bin/pg_ctl -D /opt/homebrew/var/postgresql@14 stop
```

The first implemented vertical slice is `POST /v1/conversations`. It authenticates a synthetic
customer by a hashed bearer token and persists a distinct open conversation. The API is composed
with PostgreSQL through `telecom_agent.api.composition.create_postgres_app`; a dedicated local seed
command and server entry point are intentionally deferred to the next implementation slice.

## Manual API Verification

The following is the temporary manual procedure until dedicated seed and server commands are
implemented.

Seed the synthetic customer used by the API examples. This command is safe to repeat because the
token hash is unique and conflicts are ignored.

```bash
/opt/homebrew/bin/psql \
  -h 127.0.0.1 \
  -p 55432 \
  -d telecom_agent \
  -c "INSERT INTO synthetic_customers
      (id, display_name, token_hash, created_at)
      VALUES (
        '10000000-0000-0000-0000-000000000001',
        'Synthetic Alice',
        'e148705fb631632c8914aec8a43431a540891345f0700c2ca4f45db551765ebc',
        NOW()
      )
      ON CONFLICT (token_hash) DO NOTHING;"
```

The stored hash corresponds to this development-only bearer token:

```text
synthetic-alice-token
```

Start the API from the repository root:

```bash
DATABASE_URL='postgresql+psycopg://bowenl@127.0.0.1:55432/telecom_agent' \
PYTHONPATH=src \
uv run python -c '
import os
import uvicorn
from telecom_agent.api.composition import create_postgres_app

app = create_postgres_app(os.environ["DATABASE_URL"])
uvicorn.run(app, host="127.0.0.1", port=8000)
'
```

In another terminal, create a conversation:

```bash
curl -i -X POST http://127.0.0.1:8000/v1/conversations \
  -H 'Authorization: Bearer synthetic-alice-token'
```

Expect `HTTP/1.1 201 Created` and a JSON body containing a generated `id`, `open` status, and UTC
`created_at` timestamp. Verify the authentication failure contract separately:

```bash
curl -i -X POST http://127.0.0.1:8000/v1/conversations
```

Expect `HTTP/1.1 401 Unauthorized`, a `WWW-Authenticate: Bearer` header, and the stable
`unauthorized` error envelope. Stop the API with `Ctrl-C` in its terminal.

Optionally confirm the persisted conversation:

```bash
/opt/homebrew/bin/psql \
  -h 127.0.0.1 \
  -p 55432 \
  -d telecom_agent \
  -c "SELECT id, customer_id, status, created_at
      FROM conversations
      ORDER BY created_at DESC
      LIMIT 5;"
```

To include PostgreSQL integration coverage, create an isolated test database once and set
`TEST_DATABASE_URL` when running the suite:

```bash
/opt/homebrew/bin/createdb -h 127.0.0.1 -p 55432 telecom_agent_test
TEST_DATABASE_URL=postgresql+psycopg://bowenl@127.0.0.1:55432/telecom_agent_test uv run pytest
```

Never commit `.env` or real credentials.

## Project Documentation

- `docs/PRODUCT.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS.md`
- `docs/FEATURE_HISTORY.md`
