# Telecom Customer-Service Agent

Status: Active implementation — factual plan comparison and expanded release gate human-verified

## Purpose

An API-first evaluation prototype for grounded KDDI plan and billing support, factual plan
comparison, unexpected-charge explanations, and contextual human escalation using synthetic data.

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

If `telecom-agent serve` is already running while code or migrations change, stop it with `Ctrl-C`
and restart it after the upgrade so the process loads the new implementation.

On a new database, the migrations finish with output similar to:

```text
Running upgrade  -> 20260826_01, create conversations
Running upgrade 20260826_01 -> 20260826_02, Create messages and plan snapshots.
Running upgrade 20260826_02 -> 20260826_03, Create bill snapshots, line items, and message evidence.
Running upgrade 20260826_03 -> 20260826_04, Create charge evidence snapshots and message evidence.
Running upgrade 20260826_04 -> 20260826_05, Create contextual human escalations.
Running upgrade 20260826_05 -> 20260829_06, Create plan comparison snapshots, offers, and message evidence.
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

Compare the current plan with the three catalog-listed synthetic KDDI options:

```bash
curl -i -X POST \
  "http://127.0.0.1:8000/v1/conversations/${CONVERSATION_ID}/messages" \
  -H 'Authorization: Bearer synthetic-alice-token' \
  -H 'Content-Type: application/json' \
  --data '{"content":"Compare my current plan."}'
```

Expect `201 Created`, `answer_status: "grounded"`, `uncertain: false`, and exactly one
`plan_comparison_snapshot` evidence reference. The deterministic response compares the current
20 GB/JPY 4,500 recurring-charge plan with:

- Synthetic KDDI Lite 5GB: 5 GB and JPY 2,800; JPY 1,700 and 15 GB lower.
- Synthetic KDDI Plus 30GB: 30 GB and JPY 5,200; JPY 700 and 10 GB higher.
- Synthetic KDDI Max 100GB: 100 GB and JPY 7,500; JPY 3,000 and 80 GB higher.

It must say the catalog is dated August 28, 2026, customer-specific eligibility is not verified,
and recurring charges are not total bills or projected savings. It does not call MiniMax-M3, rank
plans, recommend a winner, or change the account. The catalog becomes stale after 30 days; stale or
otherwise unsafe input returns an uncertain evidence-free unavailable answer with a human-support
next step.

Ask for the latest synthetic KDDI bill using the same conversation:

```bash
curl -i -X POST \
  "http://127.0.0.1:8000/v1/conversations/${CONVERSATION_ID}/messages" \
  -H 'Authorization: Bearer synthetic-alice-token' \
  -H 'Content-Type: application/json' \
  --data '{"content":"What is my latest bill?"}'
```

Expect `201 Created`, `answer_status: "grounded"`, `uncertain: false`, and one `bill_snapshot`
evidence reference. The deterministic answer must report July 1–31, 2026, total JPY 6,930, and
these reconciled line items: monthly mobile service JPY 4,500, domestic calls JPY 600,
international roaming data JPY 1,200, and taxes and fees JPY 630. This path does not call
MiniMax-M3; it first establishes typed billing retrieval, reconciliation, and evidence persistence.

Investigate the supported unexpected roaming charge:

```bash
curl -i -X POST \
  "http://127.0.0.1:8000/v1/conversations/${CONVERSATION_ID}/messages" \
  -H 'Authorization: Bearer synthetic-alice-token' \
  -H 'Content-Type: application/json' \
  --data '{"content":"Why is my latest bill higher?"}'
```

Expect `201 Created` with `answer_status: "grounded"`, `uncertain: false`, and two evidence
references: one `bill_snapshot` and one `charge_snapshot`. The deterministic answer identifies the
JPY 1,200 international roaming item, links it to mobile data use in the United States on July 18,
2026, and states that this activated the Synthetic KDDI Overseas Data Day Pass. It recommends human
support if the usage is not recognized and does not decide a dispute. This path does not call
MiniMax-M3.

Verify that unsupported actions remain explicit:

```bash
curl -i -X POST \
  "http://127.0.0.1:8000/v1/conversations/${CONVERSATION_ID}/messages" \
  -H 'Authorization: Bearer synthetic-alice-token' \
  -H 'Content-Type: application/json' \
  --data '{"content":"Can you issue a refund?"}'
```

Expect `201 Created` with `answer_status: "unsupported"`, `uncertain: true`, and no evidence. The
agent does not issue refunds or adjustments.

Retrieve the complete conversation history:

```bash
curl -i \
  "http://127.0.0.1:8000/v1/conversations/${CONVERSATION_ID}" \
  -H 'Authorization: Bearer synthetic-alice-token'
```

Expect `HTTP/1.1 200 OK` with the conversation `id`, `status`, `created_at`, and every message in
chronological order. User messages contain their base message fields. Assistant messages also
contain `answer_status`, `uncertain`, and the same typed `plan_snapshot`, `bill_snapshot`,
`charge_snapshot`, or `plan_comparison_snapshot` evidence references returned when each message was
created. Version 0.1 returns the complete history without pagination and does not embed snapshot
bodies.

The route is authenticated and customer-scoped. A missing conversation and a conversation owned
by another customer both return the same `404 conversation_not_found` response. This read-only
feature reuses the existing database schema, so it adds no Alembic migration.

Request an explicit contextual human handoff for the same conversation:

```bash
curl -i -X POST \
  "http://127.0.0.1:8000/v1/conversations/${CONVERSATION_ID}/escalations" \
  -H 'Authorization: Bearer synthetic-alice-token' \
  -H 'Content-Type: application/json' \
  --data '{"reason":"I do not recognize this roaming charge."}'
```

Expect `HTTP/1.1 201 Created`, the same `conversation_id`, the trimmed reason, `status: "queued"`,
UTC `created_at` and `updated_at`, and `next_step: null`. Copy the returned `id`:

```bash
ESCALATION_ID='<paste-escalation-id>'
```

Retrieve its durable status:

```bash
curl -i \
  "http://127.0.0.1:8000/v1/escalations/${ESCALATION_ID}" \
  -H 'Authorization: Bearer synthetic-alice-token'
```

Expect `200 OK` and the same public escalation fields. The internal immutable handoff context is
not returned. Repeating the POST while this escalation is active returns
`409 escalation_already_active`. The runtime mock always accepts valid requests; automated tests
exercise `failed` status and its safe retry guidance.

Verify the authentication failure contract separately:

```bash
curl -i -X POST http://127.0.0.1:8000/v1/conversations
```

Expect `HTTP/1.1 401 Unauthorized`, a `WWW-Authenticate: Bearer` header, and the stable
`unauthorized` error envelope. Stop the API with `Ctrl-C` in its terminal after all verification.

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

After asking for the latest bill, confirm its persisted snapshot and ordered line items:

```bash
/opt/homebrew/bin/psql \
  -h 127.0.0.1 \
  -p 55432 \
  -d telecom_agent \
  -c "SELECT b.period_start, b.period_end, b.total, b.currency,
             i.position, i.description, i.amount
      FROM bill_snapshots AS b
      JOIN bill_line_items AS i ON i.bill_snapshot_id = b.id
      WHERE b.id = (
          SELECT mbe.bill_snapshot_id
          FROM message_bill_evidence AS mbe
          JOIN messages AS m ON m.id = mbe.message_id
          ORDER BY m.created_at DESC
          LIMIT 1
      )
      ORDER BY i.position;"
```

After investigating the charge, confirm the persisted causal evidence:

```bash
/opt/homebrew/bin/psql \
  -h 127.0.0.1 \
  -p 55432 \
  -d telecom_agent \
  -c "SELECT c.line_item_code, c.amount, c.currency, c.occurred_on,
             c.location, c.service_name, c.state
      FROM charge_evidence_snapshots AS c
      WHERE c.id = (
          SELECT mce.charge_snapshot_id
          FROM message_charge_evidence AS mce
          JOIN messages AS m ON m.id = mce.message_id
          ORDER BY m.created_at DESC
          LIMIT 1
      );"
```

After comparing plans, confirm the immutable snapshot and three ordered offers:

```bash
/opt/homebrew/bin/psql \
  -h 127.0.0.1 \
  -p 55432 \
  -d telecom_agent \
  -c "SELECT s.current_plan_name, s.current_recurring_charge,
             s.catalog_as_of, s.source_version, s.eligibility_verified,
             o.position, o.plan_name, o.recurring_charge,
             o.recurring_charge_delta, o.data_allowance_delta_gb
      FROM plan_comparison_snapshots AS s
      JOIN plan_comparison_offers AS o ON o.comparison_snapshot_id = s.id
      WHERE s.id = (
          SELECT mpce.comparison_snapshot_id
          FROM message_plan_comparison_evidence AS mpce
          JOIN messages AS m ON m.id = mpce.message_id
          ORDER BY m.created_at DESC
          LIMIT 1
      )
      ORDER BY o.position;"
```

After requesting escalation, confirm its status and immutable context size:

```bash
/opt/homebrew/bin/psql \
  -h 127.0.0.1 \
  -p 55432 \
  -d telecom_agent \
  -c "SELECT id, conversation_id, status, reason,
             jsonb_array_length(handoff_context->'conversation'->'messages') AS message_count
      FROM escalations
      WHERE id = '${ESCALATION_ID}';"
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

## Current-Plan Evaluation

Run the deterministic 16-case baseline without PostgreSQL or provider usage:

```bash
uv run python -m telecom_agent.evaluation.current_plan --mode offline
```

Expect routine `10/10 (100.0%)`, safety `6/6 (100.0%)`, and a passing release gate. Run the opt-in
live baseline only after loading `.env`:

```bash
set -a
source .env
set +a
uv run python -m telecom_agent.evaluation.current_plan --mode live
```

Live mode makes twelve MiniMax-M3 requests and may incur provider usage. A nonzero exit means
either a quality/safety gate failed or configuration was incomplete; review the printed per-case
failures.
Expect routine `10/10 (100.0%)`, safety `6/6 (100.0%)`, and `Release gate: PASS`. See
`evals/README.md` for the dataset contract, historical baseline, and exit-code meanings.

## Cross-Feature MVP Evaluation

Run the complete deterministic 45-case bill, charge, history, escalation, and plan-comparison gate:

```bash
uv run python -m telecom_agent.evaluation.mvp
```

The command uses no database, network, SambaNova key, or live model. The preserved 36-case baseline
scored latest bill `3/5`, unexpected charge `3/5`, history `5/5`, escalation `5/5`, and safety
`16/16`, so it correctly failed. The narrow intent remediation now recognizes `recent invoice`,
`billing period`/latest-statement, direct `roaming charge`, and unrecognized-roaming-usage language.
That unchanged gate passed and was human-verified on 2026-08-27. The plan-comparison slice preserves
those 36 cases and adds five routine plus four safety cases. The local 45-case result reports all
five routine groups at `5/5`, safety at `20/20`, and `Release gate: PASS`; independent human
verification reproduced the grounded API response and expanded gate on 2026-08-29.

## Project Documentation

- `docs/PRODUCT.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS.md`
- `docs/FEATURE_HISTORY.md`
