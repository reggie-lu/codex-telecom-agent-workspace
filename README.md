# Telecom Customer-Service Agent

Status: Active implementation — guarded SambaNova current-plan generation awaiting human verification

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
Set `SAMBANOVA_API_KEY` in `.env` before serving the API. Keep
`SAMBANOVA_MODEL=MiniMax-M3` to test the approved model; the application never substitutes another
model. The `serve` command exits with a list of missing variable names, without printing values, if
any SambaNova setting is empty.

Apply the database schema:

```bash
uv run alembic upgrade head
```

On a new database, the migrations finish with output similar to:

```text
Running upgrade  -> 20260826_01, create conversations
Running upgrade 20260826_01 -> 20260826_02, Create messages and plan snapshots.
```

To stop PostgreSQL later without deleting its data:

```bash
/opt/homebrew/bin/pg_ctl -D /opt/homebrew/var/postgresql@14 stop
```

Seed the approved synthetic development customer. This command is idempotent and stores only the
token hash:

```bash
uv run telecom-agent seed
```

Expect either `Created Synthetic Alice` or `Synthetic Alice already exists`, followed by the
development-only token.

Start the API from the repository root:

```bash
uv run telecom-agent serve
```

The server binds only to `http://127.0.0.1:8000`. Stop it gracefully with `Ctrl-C`.

## Manual API Verification

With `uv run telecom-agent serve` running, verify PostgreSQL readiness from another terminal:

```bash
curl -i http://127.0.0.1:8000/health
```

Expect `HTTP/1.1 200 OK` and exactly:

```json
{"status":"ok","database":"ok"}
```

The endpoint is intentionally unauthenticated but contains no sensitive details. It is reachable
only through localhost and must remain internal rather than publicly routed in any future
deployment.

In another terminal, create a conversation:

```bash
curl -i -X POST http://127.0.0.1:8000/v1/conversations \
  -H 'Authorization: Bearer synthetic-alice-token'
```

Expect `HTTP/1.1 201 Created` and a JSON body containing a generated `id`, `open` status, and UTC
`created_at` timestamp. Copy its `id` into the shell used for the remaining requests:

```bash
CONVERSATION_ID='<paste-conversation-id>'
```

Ask for the current synthetic KDDI plan:

```bash
curl -i -X POST \
  "http://127.0.0.1:8000/v1/conversations/${CONVERSATION_ID}/messages" \
  -H 'Authorization: Bearer synthetic-alice-token' \
  -H 'Content-Type: application/json' \
  --data '{"content":"What is my current plan?"}'
```

Expect `HTTP/1.1 201 Created`. A successful MiniMax-M3 response must have
`answer_status: "grounded"`, `uncertain: false`, and one `plan_snapshot` evidence reference. Its
wording may vary, but it must include exactly these canonical values: `Synthetic KDDI 5G 20GB`,
`20 GB`, `JPY 4,500`, and `August 1, 2026`. This request proves the configured model endpoint was
used because the production server has no grounded-answer fallback.

If the configured endpoint rejects `MiniMax-M3`, the key is invalid, both provider attempts fail,
or output fails the grounding guard, expect `201 Created` with `answer_status: "unavailable"`,
`uncertain: true`, no evidence, and this safe message:

```text
I can’t generate a grounded answer right now. Please try again later or request human support.
```

The API intentionally does not expose provider exception details. Check the configured model name
in the SambaNova account before changing it; do not silently use another model.

Verify safe handling of a question outside the implemented slice:

```bash
curl -i -X POST \
  "http://127.0.0.1:8000/v1/conversations/${CONVERSATION_ID}/messages" \
  -H 'Authorization: Bearer synthetic-alice-token' \
  -H 'Content-Type: application/json' \
  --data '{"content":"Why is my bill higher?"}'
```

Expect `201 Created` with `answer_status: "unsupported"`, `uncertain: true`, no evidence, and a
clear statement that billing support is not implemented yet. This path does not call SambaNova.

Verify the authentication failure contract separately:

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

Confirm the persisted message exchange:

```bash
/opt/homebrew/bin/psql \
  -h 127.0.0.1 \
  -p 55432 \
  -d telecom_agent \
  -c "SELECT role, answer_status, uncertain, content, created_at
      FROM messages
      WHERE conversation_id = '${CONVERSATION_ID}'
      ORDER BY created_at;"
```

To include PostgreSQL integration coverage, create an isolated test database once and set
`TEST_DATABASE_URL` when running the suite:

```bash
/opt/homebrew/bin/createdb -h 127.0.0.1 -p 55432 telecom_agent_test
TEST_DATABASE_URL=postgresql+psycopg://bowenl@127.0.0.1:55432/telecom_agent_test uv run pytest
```

Never commit `.env` or real credentials.

## Automated and Live Verification

Ordinary tests use a deterministic fake at the model port and never access SambaNova:

```bash
TEST_DATABASE_URL=postgresql+psycopg://bowenl@127.0.0.1:55432/telecom_agent_test \
  uv run pytest
uv run ruff check .
uv run mypy src tests
```

The current-plan curl request above is the opt-in live smoke test. Run it only after loading `.env`
and starting `uv run telecom-agent serve`; it uses the configured SambaNova account and may incur
provider usage. Stop the server with `Ctrl-C` after verification. Never put an API key directly in
a command or commit it to the repository.

## Project Documentation

- `docs/PRODUCT.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS.md`
- `docs/FEATURE_HISTORY.md`
