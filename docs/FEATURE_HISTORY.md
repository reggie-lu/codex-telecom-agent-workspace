# Feature Checkpoint History

This ledger records human-verified development checkpoints. A checkpoint is not a production
release: it preserves working increments, verification evidence, architecture progress, and known
limitations while the prototype evolves.

## Big Picture

| Stage | Scope | Status |
| --- | --- | --- |
| Foundation | Project structure, typed boundaries, local PostgreSQL, migrations | Implemented |
| Conversation entry | Authenticate a synthetic customer and create a conversation | Human verified |
| Local operations | Stable seed, serve, health, and graceful-shutdown workflow | Human verified |
| Current-plan support | Grounded plan messages with typed evidence and safe limitations | Human verified |
| Billing support | Latest-bill and unexpected-charge investigation | Agreed, not implemented |
| Human escalation | Contextual mock escalation and status tracking | Agreed, not implemented |
| Evaluation | Routine scoring and release-blocking safety cases | Agreed, not implemented |
| Packaging | Docker development runtime | Deferred; requires approval |
| Deployment | Kubernetes or Helm deployment | Deferred; requires approval |

## Checkpoints

### CP-001 — Conversation Creation

- Recorded: 2026-08-26 14:13 JST
- Classification: Human-verified development checkpoint; not a production release
- Branch: `main`
- Remote: `origin`
- Implementation commit: `1fa1b3c2a506b0f7a1e499fe4155f97f9edbd803`
- Commit time: 2026-08-26 14:14:17 JST
- Remote status: Included in the `origin/main` checkpoint push associated with this record

Big-picture contribution: establishes the authenticated conversation entry point and PostgreSQL
persistence foundation required by all later support flows.

Feature breakdown:

- `POST /v1/conversations` accepts no body and requires a synthetic bearer token.
- Valid authentication returns `201 Created` with a unique conversation UUID, `open` status, and a
  UTC creation timestamp.
- Missing or invalid authentication returns the approved `401 Unauthorized` envelope and bearer
  challenge.
- Only SHA-256 token hashes are stored; raw bearer tokens are not persisted.
- SQLAlchemy repositories persist customer ownership and conversations through the initial Alembic
  migration.

Verification evidence:

- Codex verification: 10 pytest tests passed with PostgreSQL integration enabled; Ruff and strict
  mypy passed.
- Human verification: local migration completed and the manually started API successfully created a
  conversation using `synthetic-alice-token`.
- Reproduction steps: see `README.md`, sections **Local PostgreSQL Setup** and **Manual API
  Verification**.

Known limitations:

- Synthetic development identities only; no real KDDI authentication or customer data.
- Seed and server startup still use temporary manual commands.
- Message handling, plan and billing retrieval, model calls, escalation, and evaluation are not yet
  implemented.
- Runtime is localhost-only; Docker and Kubernetes remain deferred.

### CP-002 — Local Runtime, Seed, and Health

- Recorded: 2026-08-26 14:41 JST
- Classification: Human-verified development checkpoint; not a production release
- Branch: `main`
- Remote: `origin`
- Implementation commit: `93b7acc45cb6cc7c410ffbacbe53e6f9da52b99d`
- Commit time: 2026-08-26 14:41:49 JST
- Remote status: Included in the `origin/main` checkpoint push associated with this record

Big-picture contribution: replaces temporary local SQL and inline Python with a stable development
runtime that can later be packaged behind Docker and Kubernetes without changing core services.

Feature breakdown:

- `uv run telecom-agent seed` idempotently creates the approved Synthetic Alice identity and stores
  only its token hash.
- `uv run telecom-agent serve` composes PostgreSQL adapters and starts FastAPI only on
  `127.0.0.1:8000`.
- Unauthenticated internal `GET /health` reports only API/database availability using the approved
  `200` or `503` contract.
- FastAPI lifespan shutdown disposes the SQLAlchemy engine cleanly.
- The project is installable through uv and no longer needs `PYTHONPATH` or inline Python to run.

Verification evidence:

- Codex verification: 20 pytest tests passed with PostgreSQL integration enabled; Ruff and strict
  mypy passed.
- Codex manual verification: idempotent seed succeeded, `/health` returned the approved `200` body,
  conversation creation returned `201`, and `Ctrl-C` completed graceful shutdown.
- Human verification: the documented seed, serve, health, and conversation workflow was completed
  successfully on 2026-08-26.
- Reproduction steps: see `README.md`, sections **Local PostgreSQL Setup** and **Manual API
  Verification**.

Known limitations:

- The health endpoint is localhost-only and must not be publicly routed if the service is deployed.
- The development seed is fixed to one synthetic customer; reset tooling is not implemented.
- Database migrations remain an explicit Alembic command rather than a CLI subcommand or deployment
  job.
- Docker, Kubernetes, production identity, and production operations remain deferred.

### CP-003 — Grounded Current-Plan Messaging

- Recorded: 2026-08-26 15:12 JST
- Classification: Human-verified development checkpoint; not a production release
- Branch: `main`
- Remote: `origin`
- Implementation commit: `64884c0be8570371c2de0e0b5da6ad6d90d25d68`
- Commit time: 2026-08-26 15:12:49 JST
- Remote status: Included in the `origin/main` checkpoint push associated with this record

Big-picture contribution: establishes the first customer-facing support answer with typed evidence,
privacy-preserving ownership checks, explicit uncertainty, and safe unsupported behavior.

Feature breakdown:

- `POST /v1/conversations/{conversation_id}/messages` persists and returns a user/assistant exchange.
- Synthetic Alice's current plan is retrieved from a deterministic Synthetic KDDI adapter.
- The grounded answer references a persisted plan snapshot containing 20 GB, JPY 4,500, and an
  August 1, 2026 effective date.
- Missing plan data produces an explicit unavailable answer without invented facts.
- Unsupported billing questions produce an explicit unsupported answer without invented facts.
- Cross-customer and missing conversations share the same privacy-preserving `404` response.
- Migration `20260826_02` adds messages, plan snapshots, and typed evidence links.

Verification evidence:

- Codex verification: 37 pytest tests passed with PostgreSQL integration enabled; Ruff and strict
  mypy passed.
- Codex manual verification: the existing database upgraded forward, the grounded and unsupported
  requests returned their approved `201` contracts, and graceful shutdown passed.
- Human verification: both deterministic responses were reproduced and confirmed on 2026-08-26.
- Reproduction steps: see `README.md`, section **Manual API Verification**.

Known limitations:

- Responses are deterministic templates using synthetic mock data; SambaNova `MiniMax-M3` is not
  called in this checkpoint.
- The deterministic intent matcher supports current-plan phrasing only.
- Latest-bill, unexpected-charge, escalation, and conversation-history retrieval remain
  unimplemented.
- Docker, Kubernetes, real KDDI data, and production authentication remain deferred.
