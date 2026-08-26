# Feature Checkpoint History

This ledger records human-verified development checkpoints. A checkpoint is not a production
release: it preserves working increments, verification evidence, architecture progress, and known
limitations while the prototype evolves.

## Big Picture

| Stage | Scope | Status |
| --- | --- | --- |
| Foundation | Project structure, typed boundaries, local PostgreSQL, migrations | Implemented |
| Conversation entry | Authenticate a synthetic customer and create a conversation | Human verified |
| Customer support | Messages, plan and bill explanations, unexpected-charge investigation | Agreed, not implemented |
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
