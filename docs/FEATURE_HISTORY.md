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
| Model integration | Guarded SambaNova MiniMax-M3 wording for current-plan answers | Human verified |
| Billing support | Latest-bill and unexpected-charge investigation | Human verified for approved synthetic scenarios |
| Conversation history | Customer-scoped ordered messages and typed evidence references | Human verified |
| Human escalation | Contextual mock escalation and status tracking | Human verified |
| Evaluation | Current-plan routine and release-blocking safety baseline | Human verified; current-plan gates pass |
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

### CP-004 — Guarded SambaNova Current-Plan Generation

- Recorded: 2026-08-26 15:36 JST
- Classification: Human-verified development checkpoint; not a production release
- Branch: `main`
- Remote: `origin`
- Implementation commit: `ea8e18aa5ca0e4ca6c25eea30c414beef4086d50`
- Commit time: 2026-08-26 15:36:24 JST
- Remote status: Included in the `origin/main` checkpoint push associated with this record

Big-picture contribution: introduces the first live language-model boundary while preserving typed
account facts, explicit evidence, deterministic missing-data behavior, and bounded failure handling.

Feature breakdown:

- Supported current-plan questions are worded by the configured SambaNova `MiniMax-M3` deployment
  through the OpenAI-compatible chat-completions API.
- Only the customer question and four canonical plan display values are sent to the model; internal
  customer, conversation, message, snapshot, and evidence identifiers are excluded.
- The OpenAI SDK uses a 30-second timeout and zero SDK retries. The adapter performs at most one
  retry for timeout, rate-limit, or server failures and never substitutes another model.
- Generated text is accepted only when it is non-empty, bounded, contains every canonical value,
  and introduces no additional numeric occurrence.
- Rejected output or terminal provider failure is discarded and persisted as a safe unavailable
  exchange. Unsupported and missing-plan requests remain deterministic and model-free.
- Ordinary tests use an offline deterministic generator; the README documents the explicit live
  smoke workflow and safe failure result.

Verification evidence:

- Codex verification: 53 pytest tests passed with PostgreSQL integration enabled; Ruff and strict
  mypy passed across 48 source files.
- Codex live verification: the configured SambaNova endpoint accepted `MiniMax-M3`; the localhost
  API returned `201 grounded`, `uncertain: false`, all four canonical values, and one plan-snapshot
  evidence reference, followed by graceful shutdown.
- Human verification: the same documented current-plan request returned the approved grounded
  response and typed evidence on 2026-08-26.
- Reproduction steps: see `README.md`, sections **Manual API Verification** and **Automated and Live
  Verification**.

Known limitations:

- MiniMax-M3 currently words only the current-plan explanation; billing, charges, roaming, savings,
  comparisons, escalation, and conversation-history use remain unimplemented.
- Customer and plan facts remain synthetic; this is not connected to real KDDI accounts or APIs.
- The output guard is rule-based and does not replace the planned semantic evaluation suite.
- Model provenance is configured by the server and is not yet returned as public message metadata.
- Docker, Kubernetes, production identity, and public deployment remain deferred.

### CP-005 — Current-Plan Evaluation Baseline

- Recorded: 2026-08-26 17:30 JST
- Classification: Human-verified development checkpoint; not a production release
- Branch: `main`
- Remote: `origin`
- Implementation commit: `41fe7eab846c3140ad50309178dcbca0859ae98a`
- Commit time: 2026-08-26 17:30:58 JST
- Remote status: Included in the `origin/main` checkpoint push associated with this record

Big-picture contribution: establishes reproducible routine-quality and release-blocking safety
measurement before expanding the agent to billing and unexpected-charge behavior.

Feature breakdown:

- A versioned JSONL dataset defines 10 routine current-plan cases and 6 safety/adversarial cases.
- Deterministic graders check answer status, uncertainty, typed evidence count, required facts, and
  prohibited claims without introducing a judge model.
- Routine and safety scores remain separate: routine requires at least 80%, safety requires 100%,
  and any safety failure blocks the release gate.
- Offline mode uses deterministic generators and requires no provider, database, or customer data.
- Live mode uses configured `MiniMax-M3` for ten eligible cases while preserving deterministic
  missing-data, unsupported-intent, and injected-output guard scenarios.
- Per-case diagnostics and process exit codes distinguish a passing run, a failed gate, and missing
  live configuration.
- The baseline exposed and fixed terminal-punctuation intent matching while preserving two broader
  paraphrase gaps as explicit regression cases.

Verification evidence:

- Codex verification: 63 pytest tests passed with PostgreSQL integration enabled; Ruff and strict
  mypy passed across 51 source files.
- Codex offline evaluation: routine 8/10 (80%, pass), safety 6/6 (100%, pass), release gate pass.
- Codex live evaluation: routine 7/10 (70%, fail), safety 6/6 (100%, pass), release gate fail.
- Human verification: the documented live command reproduced the same three failing routine cases,
  7/10 routine score, 6/6 safety score, and blocked release gate on 2026-08-26.
- Reproduction steps: see `README.md`, section **Current-Plan Evaluation**, and `evals/README.md`.

Known limitations:

- This checkpoint verifies the evaluator, not production readiness; the live routine release gate
  is intentionally recorded as failed.
- Natural requests phrased as monthly data or mobile service are not recognized by the current
  deterministic intent matcher.
- The recurring-charge live case was safely rejected by the current grounding guard and needs
  targeted diagnosis before changing the prompt or guard.
- Evaluation covers only current-plan support. Billing, unexpected-charge, history, escalation,
  and semantic-quality rubrics remain unimplemented.
- Customer data is synthetic, and Docker, Kubernetes, production identity, and deployment remain
  deferred.

### CP-006 — Current-Plan Quality Remediation

- Recorded: 2026-08-26 17:43 JST
- Classification: Human-verified development checkpoint; not a production release
- Branch: `main`
- Remote: `origin`
- Implementation commit: `c48b3072bfd1cc4d9532714b7f66f5d2dbfa7b89`
- Commit time: 2026-08-26 17:43:29 JST
- Remote status: Included in the `origin/main` checkpoint push associated with this record

Big-picture contribution: turns the first current-plan live evaluation from a correctly blocked
baseline into a fully passing, human-verified quality gate without weakening its safety contract.

Feature breakdown:

- The deterministic intent matcher now recognizes natural questions containing `how much data` or
  `mobile service`, closing both recorded paraphrase gaps.
- The recurring-charge failure was traced to MiniMax-M3 returning only the requested price. The
  prompt now requires all four canonical values exactly once even when one fact is requested.
- The deterministic grounding guard, 16-case dataset, 80% routine threshold, and 100% safety
  threshold remain unchanged.
- Offline and opt-in live evaluation now both pass all 10 routine and all 6 safety cases.
- Runbooks, the architecture flow, durable decisions, learning notes, and the project blog record
  the remediation and its verification procedure.

Verification evidence:

- Codex verification: 65 pytest tests passed with PostgreSQL integration enabled; Ruff and strict
  mypy passed across 51 source files.
- Codex offline evaluation: routine 10/10 (100%, pass), safety 6/6 (100%, pass), release gate pass.
- Codex live evaluation: routine 10/10 (100%, pass), safety 6/6 (100%, pass), release gate pass.
- Human verification: the documented live command independently reproduced 10/10 routine, 6/6
  safety, and a passing release gate on 2026-08-26.
- Reproduction steps: see `README.md`, section **Current-Plan Evaluation**, and `evals/README.md`.

Known limitations:

- Evaluation and implementation still cover only current-plan support. Billing, unexpected-charge,
  roaming, savings, comparisons, history, and human escalation remain unimplemented.
- Intent matching remains a deliberately narrow deterministic phrase matcher rather than a general
  semantic classifier.
- Customer and plan data remain synthetic, and the grounding guard remains rule-based.
- Docker, Kubernetes, production KDDI identity/data, public deployment, and production operations
  remain deferred.

### CP-007 — Grounded Latest-Bill Summary

- Recorded: 2026-08-26 18:14 JST
- Classification: Human-verified development checkpoint; not a production release
- Branch: `main`
- Remote: `origin`
- Implementation commit: `6fdae739b94b7f1834a2dc906a278ff9fb6e2cbc`
- Commit time: 2026-08-26 18:14:16 JST
- Remote status: Included in the `origin/main` checkpoint push associated with this record

Big-picture contribution: establishes typed, reconciled latest-bill evidence as the factual
foundation required before the agent can investigate an unexpected charge.

Feature breakdown:

- Direct latest-bill questions use the existing authenticated conversation message endpoint.
- The synthetic KDDI adapter returns the approved July 1–31, 2026 bill totaling JPY 6,930 with four
  ordered line items that reconcile exactly to the total.
- The service validates the billing period, currency, source, nonnegative values, nonempty line
  items, and exact decimal reconciliation before producing a grounded answer.
- Migration `20260826_03` adds typed bill snapshots, ordered line items, and message-to-bill
  evidence. The complete exchange is persisted atomically.
- Missing or inconsistent billing data returns a safe unavailable answer without amounts or
  evidence. Unexpected-charge questions remain explicitly unsupported.
- The orchestration class is now named `SendSupportMessageService` because it handles both current
  plan and latest-bill intents.

Verification evidence:

- Codex verification: 73 pytest tests passed with PostgreSQL integration enabled; Ruff and strict
  mypy passed across 55 source files.
- Migration verification: `20260826_03` upgraded the local database to head, and `alembic check`
  reported no new upgrade operations.
- Codex localhost verification: conversation creation and latest-bill submission both returned
  `201`; the answer was grounded, certain, exact, and referenced one `bill_snapshot`.
- Existing current-plan regression gate: routine 10/10, safety 6/6, release gate pass in offline
  mode.
- Human verification: the documented API request independently returned the approved period,
  total, four line items, grounded status, false uncertainty, and typed evidence on 2026-08-26.
- Reproduction steps: see `README.md`, sections **Manual API Verification** and the persisted bill
  query following it.

Known limitations:

- The latest-bill response is deterministic; it does not call MiniMax-M3 and has no dedicated
  billing evaluation dataset yet.
- Unexpected-charge identification and explanation remain unimplemented, including why the
  international roaming data item appeared.
- Conversation-history retrieval and human escalation remain unimplemented.
- Customer and bill data are synthetic; real KDDI identity, APIs, compliance, and operations remain
  deferred.
- Docker, Kubernetes, and public deployment remain deferred.

### CP-008 — Grounded Unexpected-Charge Investigation

- Recorded: 2026-08-26 18:34 JST
- Classification: Human-verified development checkpoint; not a production release
- Branch: `main`
- Remote: `origin`
- Implementation commit: `c8c415d5d1dbbba14b01efe367d3045403bb808e`
- Commit time: 2026-08-26 18:34:55 JST
- Remote status: Included in the `origin/main` checkpoint push associated with this record

Big-picture contribution: completes the first evidence-backed billing investigation while keeping
factual explanation separate from dispute judgment, refunds, and escalation.

Feature breakdown:

- Diagnostic high-bill and unexpected-charge questions identify the approved JPY 1,200
  international-roaming item; ambiguous `this charge` references request clarification.
- A grounded cause requires a reconciled bill and confirmed charge evidence matching stable item
  code, description, amount, currency, and event date within the billing period.
- The approved evidence links United States mobile-data use on July 18, 2026 to automatic activation
  of the Synthetic KDDI Overseas Data Day Pass.
- Missing evidence identifies only the billed item and states that the cause is unknown. Stale or
  conflicting evidence is explicitly flagged and never reused as a current explanation.
- Migration `20260826_04` adds typed charge-evidence snapshots and message links. Bill, charge,
  messages, and evidence relationships are persisted atomically.
- The response recommends human support for unrecognized usage and explicitly declines to decide a
  billing dispute. Refund and adjustment requests remain unsupported.
- The current-plan unsupported-intent safety case now uses a refund request because high-bill
  questions became an implemented intent; its size, threshold, and safety purpose are unchanged.

Verification evidence:

- Codex verification: 85 pytest tests passed with PostgreSQL integration enabled; Ruff and strict
  mypy passed across 59 source files.
- Migration verification: `20260826_04` upgraded the local database to head, and `alembic check`
  reported no model/migration drift.
- Existing current-plan regression gate: routine 10/10, safety 6/6, release gate pass in offline
  mode with the updated unsupported-refund case.
- Human localhost verification: after restarting the server, the documented request returned the
  approved cause, `grounded`, `uncertain: false`, one `bill_snapshot`, one `charge_snapshot`, and the
  nonjudgmental human-support next step on 2026-08-26.
- Reproduction steps: see `README.md`, section **Manual API Verification**, including the persisted
  charge-evidence query.

Known limitations:

- Investigation covers only the approved roaming scenario; it is not a general charge classifier.
- Wording is deterministic and no dedicated billing/charge evaluation dataset exists yet.
- The agent recommends human support but the contextual escalation API remains unimplemented.
- The agent cannot issue refunds, adjustments, plan changes, or dispute decisions.
- Customer, bill, and usage evidence are synthetic; real KDDI identity, APIs, compliance, and
  operations remain deferred.
- Docker, Kubernetes, and public deployment remain deferred.

### CP-009 — Customer-Scoped Conversation History

- Recorded: 2026-08-26 19:49 JST
- Classification: Human-verified development checkpoint; not a production release
- Branch: `main`
- Remote: `origin`
- Implementation commit: `be9cf47b68d3d912205df4cd393d71937fc8e7bc`
- Commit time: 2026-08-26 19:49:44 JST
- Remote status: Included in the `origin/main` checkpoint push associated with this record

Big-picture contribution: establishes the trusted conversation read boundary needed to include
customer questions, agent answers, and supporting evidence in a later human-escalation handoff.

Feature breakdown:

- Authenticated `GET /v1/conversations/{conversation_id}` returns conversation metadata and the
  complete message history for the owning synthetic customer.
- Messages are ordered by UTC creation time with UUID as a deterministic tiebreaker.
- User messages expose their base fields. Assistant messages additionally expose answer status,
  uncertainty, and typed plan, bill, or charge evidence references.
- The PostgreSQL adapter bulk-loads the three evidence-link types and reconstructs them without
  changing message order or embedding snapshot bodies.
- Missing and cross-customer conversations share `404 conversation_not_found`, with ownership
  enforced in the read query itself.
- Empty owned conversations return `200 OK` with `messages: []`. The existing schema is sufficient,
  so this read-only feature requires no migration.

Verification evidence:

- Codex verification: all 92 pytest tests passed with PostgreSQL integration enabled; Ruff and
  strict mypy passed.
- PostgreSQL integration created three exchanges and retrieved six ordered messages with plan,
  bill, and bill-plus-charge evidence in the expected positions.
- Existing current-plan regression gate: routine 10/10, safety 6/6, release gate pass in offline
  mode.
- Human localhost verification: after restarting the server, retrieval of owned conversation
  `f384cd7f-9707-4f88-ba3f-2dbe75bb15cb` returned `200 OK`, correct `open` metadata, and
  `messages: []` on 2026-08-26.
- Reproduction steps: see `README.md`, section **Manual API Verification**.

Known limitations:

- Version 0.1 returns complete history without pagination, filtering, search, or retention controls.
- History exposes typed evidence references but not referenced snapshot bodies.
- Human verification covered the empty-history response; populated histories and every evidence
  type are covered by the PostgreSQL integration suite.
- Contextual human-escalation creation and status tracking remain unimplemented.
- Customer and account data are synthetic; real KDDI identity, APIs, compliance, and operations
  remain deferred.
- Docker, Kubernetes, and public deployment remain deferred.

### CP-010 — Contextual Mock Human Escalation

- Recorded: 2026-08-26 20:27 JST
- Classification: Human-verified development checkpoint; not a production release
- Branch: `main`
- Remote: `origin`
- Implementation commit: `5bea0e30160791c21ca22275d56c7b4cd21d87d9`
- Commit time: 2026-08-26 20:27:12 JST
- Remote status: Included in the `origin/main` checkpoint push associated with this record

Big-picture contribution: completes the focused MVP handoff boundary so customers can explicitly
request human support without repeating their conversation or losing truthful request status.

Feature breakdown:

- Authenticated customers explicitly create handoffs with a trimmed 1–1,000-character reason;
  recommendations never silently open a ticket.
- Creation freezes owned conversation metadata, ordered messages, assistant status/uncertainty,
  and typed evidence references into immutable PostgreSQL JSONB context without credentials or raw
  snapshot bodies.
- The service persists `requested` before crossing the mock boundary, then records `queued` on
  acceptance or `failed` with a safe retry step on rejection or provider unavailability.
- The deterministic runtime mock accepts valid handoffs. Injected test adapters exercise both
  explicit failure and provider exception behavior.
- Migration `20260826_05` adds constrained escalation persistence and a partial unique index that
  permits only one `requested`, `queued`, or `assigned` escalation per conversation.
- `GET /v1/escalations/{escalation_id}` returns the minimal customer-scoped status resource while
  keeping internal handoff context private. Missing and cross-customer IDs share one 404 response.
- The domain validates the approved requested, queued, assigned, resolved, and failed lifecycle;
  automatic assignment and resolution remain outside this slice.

Verification evidence:

- Codex verification: all 110 pytest tests passed with PostgreSQL integration enabled; Ruff and
  strict mypy passed across 72 source files.
- Migration verification: `20260826_05` reached head and `alembic check` reported no new upgrade
  operations.
- PostgreSQL integration verified immutable bill-plus-charge context, duplicate prevention,
  durable failed status, safe retry guidance, and a successful retry after failure.
- Existing current-plan regression gate: routine 10/10, safety 6/6, release gate pass offline.
- Human localhost verification: explicit creation and status retrieval for escalation
  `695fde8f-3d21-4de0-bf87-110438421782` returned the correct conversation and reason,
  `status: queued`, UTC timestamps, and `next_step: null` on 2026-08-26.
- Reproduction steps: see `README.md`, section **Manual API Verification**.

Known limitations:

- The handoff provider is deterministic and local; no request reaches an actual KDDI representative
  or external ticketing system.
- Runtime requests remain queued. Assignment, resolution, cancellation, reopening, notifications,
  and background processing are not implemented.
- Failure behavior is covered by injected automated tests and is not exposed through a public
  simulation switch.
- No dedicated escalation evaluation dataset or success metric exists yet.
- Customer, conversation, and account data are synthetic; production identity, consent,
  compliance, retention, and operations remain deferred.
- Docker, Kubernetes, and public deployment remain deferred.
