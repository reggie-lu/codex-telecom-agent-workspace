# Project Decisions

Only durable decisions whose rationale matters are recorded here.

## D-001 — API-first backend

Date: 2026-08-25 · Status: Accepted

Build version 0.1 as a backend API and defer the frontend. This focuses work on agent behavior,
evaluation, and reusable contracts; ordinary customers cannot use it without a client.

## D-002 — Python backend

Date: 2026-08-25 · Status: Accepted

Use Python for its AI/evaluation ecosystem and pytest workflow. A future frontend will likely use a
different language, and Python provides fewer compile-time guarantees than Java or TypeScript.

## D-003 — FastAPI

Date: 2026-08-25 · Status: Accepted

Use FastAPI for typed validation, OpenAPI, and API testing. This introduces FastAPI/Pydantic
conventions but avoids manual schema and documentation plumbing.

## D-004 — Local PostgreSQL

Date: 2026-08-25 · Status: Accepted

Persist conversations, retrieved snapshots, and escalation state in local PostgreSQL. Production
hosting, retention, encryption, and operations remain deferred.

## D-005 — Synthetic KDDI adapter

Date: 2026-08-25 · Status: Accepted

Use deterministic synthetic customer, plan, bill, charge, and escalation data behind a replaceable
adapter because authorized KDDI APIs are unavailable. No dynamic website retrieval is approved.

## D-006 — SambaNova behind a model port

Date: 2026-08-25 · Status: Accepted

Use SambaNova for real evaluation behind a narrow model interface and a deterministic fake for
ordinary tests. This boundary exists for testability and isolation, not speculative multi-provider
support.

## D-007 — Synthetic bearer authentication

Date: 2026-08-25 · Status: Accepted

Map mock bearer tokens to synthetic customer identities and enforce ownership everywhere. This must
never be represented or reused as production KDDI authentication.

## D-008 — Explicit development reset

Date: 2026-08-25 · Status: Accepted

Retain synthetic records across restarts until an explicit reset restores approved seed state. Do
not invent production retention rules or reset data at startup.

## D-009 — Localhost-only runtime

Date: 2026-08-25 · Status: Accepted

Bind the API to localhost and use local PostgreSQL. Public hosting, cloud resources, containers, and
CI/CD require future approval.

## D-010 — Separate tests from live evaluations

Date: 2026-08-25 · Status: Accepted

Use deterministic pytest verification normally and a separate opt-in SambaNova evaluation suite.
A passing deterministic suite alone does not prove live model quality.

## D-011 — Ports and adapters

Date: 2026-08-25 · Status: Accepted

Separate domain, services, ports, adapters, API, and evaluation concerns. Each module corresponds to
an approved boundary; do not add generic repositories or extra layers.

## D-012 — Explicit persistent types

Date: 2026-08-25 · Status: Accepted

Persist approved entities with UUIDs, decimal/`NUMERIC` money, currency constraints, dates,
timezone-aware UTC timestamps, constrained statuses, Unicode text, and typed evidence. Never store
raw bearer tokens.

## D-013 — Conversation-centric API

Date: 2026-08-25 · Status: Accepted

Expose conversation creation, messaging, history, escalation creation, and escalation status only.
Direct plan, bill, and charge resources are outside version 0.1.

## D-014 — Five-state escalation lifecycle

Date: 2026-08-25 · Status: Accepted

Use `requested`, `queued`, `assigned`, `resolved`, and `failed`. Validate transitions and provide a
safe next step after failure; cancellation and reopening are deferred.

## D-015 — MiniMax-M3 on SambaNova

Date: 2026-08-25 · Status: Accepted

Use SambaNova's OpenAI-compatible chat-completions endpoint and `MiniMax-M3`, configured at runtime.
Model changes require evaluation before becoming the default.

## D-016 — Bounded model retry

Date: 2026-08-25 · Status: Accepted

Use a finite timeout and at most one retry for transient failures. Never retry bad requests or auth
failures, never use an unapproved fallback, and return a safe terminal failure.

## D-017 — Release-blocking safety gates

Date: 2026-08-26 · Status: Accepted

Require 100% safe behavior for missing/unavailable and conflicting/outdated data. Any invented fact
or unflagged stale conflict blocks release regardless of the routine 80% score.

## D-018 — SQLAlchemy, Alembic, and Psycopg

Date: 2026-08-26 · Status: Accepted

Use synchronous SQLAlchemy 2, Alembic, and Psycopg. This adds dependencies but avoids unnecessary
async database complexity and provides explicit transactions and migrations.

## D-019 — OpenAI SDK for SambaNova

Date: 2026-08-26 · Status: Accepted

Use the OpenAI Python SDK with the SambaNova base URL and `max_retries=0`; the adapter owns the
single approved retry. Use only the narrow chat-completions surface.

## D-020 — Conversation-creation HTTP contract

Date: 2026-08-26 · Status: Accepted

`POST /v1/conversations` requires a synthetic bearer token and no body. It returns `201` with a UUID,
`open` status, and UTC creation timestamp while omitting customer identity. Missing or invalid tokens
return a stable `401` error envelope and bearer challenge. Idempotency is deferred, so each successful
request creates a distinct empty conversation.

## D-021 — Minimal internal health endpoint

Date: 2026-08-26 · Status: Accepted

Expose unauthenticated `GET /health` because infrastructure probes must work independently of
customer authentication. On healthy PostgreSQL it returns only
`200 {"status":"ok","database":"ok"}`; on database failure it returns only
`503 {"status":"unavailable","database":"unavailable"}`. It is localhost-only in the current
runtime and must remain internal rather than publicly routed in future deployments. Never expose
credentials, addresses, exception text, or customer data.

## D-022 — Deterministic grounding before model generation

Date: 2026-08-26 · Status: Accepted

Implement the first current-plan message answer with deterministic intent matching and an
evidence-templated explanation. Persist both messages, a typed plan snapshot, explicit uncertainty,
and the evidence link atomically. Missing plan data and unsupported questions return safe persisted
answers; missing and cross-customer conversations share a privacy-preserving `404`. SambaNova
generation is deferred to a separately evaluated slice behind this grounding boundary.

## D-023 — Guarded SambaNova wording

Date: 2026-08-26 · Status: Accepted

For supported current-plan questions with available typed data, call `MiniMax-M3` through the
SambaNova OpenAI-compatible chat-completions endpoint. Send only the customer question and four
canonical display facts; never send internal identifiers. Use a 30-second timeout per attempt,
disable SDK retries, and allow one adapter-controlled retry only for timeouts, rate limits, and
server errors. Accept output only when every canonical value is present, no extra numeric claim is
introduced, and the text is non-empty and bounded. A terminal or rejected generation produces a
persisted safe unavailable answer rather than a model or deterministic fallback. Unsupported and
missing-data answers remain deterministic and do not call the model.

## D-024 — Split deterministic evaluation gates

Date: 2026-08-26 · Status: Accepted

Start evaluation with a versioned 16-case current-plan dataset: 10 routine cases requiring at least
80% and 6 safety/adversarial cases requiring 100%. Grade explicit application contracts
deterministically—status, uncertainty, evidence, required facts, and prohibited claims—rather than
introducing an LLM judge. Keep routine and safety scores separate and block the release gate on any
safety failure. Ordinary mode is offline; live mode uses the configured `MiniMax-M3` only for
eligible generation cases and may never weaken deterministic missing-data or output-guard checks.

## D-025 — Remediate quality without weakening safety

Date: 2026-08-26 · Status: Accepted

Keep the versioned 16-case dataset, 80% routine threshold, 100% safety threshold, and deterministic
grounding guard unchanged. Recognize the two approved current-plan paraphrases, `how much data` and
`mobile service`, in the deterministic intent matcher. Require MiniMax-M3 to include all four
canonical values exactly once even when a question asks about a single fact. Validate remediation
by rerunning the same offline and opt-in live evaluations so the new score remains comparable to
the first baseline.

## D-026 — Latest bill before charge diagnosis

Date: 2026-08-26 · Status: Accepted

Implement latest-bill summary as a separate deterministic vertical slice before unexpected-charge
investigation. Use the existing authenticated conversation message endpoint. Retrieve the approved
Synthetic Alice bill for July 1–31, 2026 with total JPY 6,930 and four ordered line items totaling
that amount. Persist typed bill and line-item snapshots and attach one `bill_snapshot` evidence
reference. Reject absent, structurally invalid, negative, or non-reconciling billing data with a
safe unavailable answer containing no billing claims. Do not call MiniMax-M3 or infer why a charge
occurred in this slice.

## D-027 — Two-source unexpected-charge grounding

Date: 2026-08-26 · Status: Accepted

Investigate only the approved JPY 1,200 international-roaming item in the first charge slice. A
grounded causal explanation requires both a reconciled latest bill and confirmed synthetic usage
evidence matching its code, description, amount, currency, and billing period. The approved event
is mobile data use in the United States on July 18, 2026, which automatically activated the
Synthetic KDDI Overseas Data Day Pass. Persist both evidence snapshots and links. Missing evidence
must state that the cause is unknown; stale or conflicting evidence must flag that condition and
omit the causal claim. Recommend human support for unrecognized usage without deciding a dispute,
issuing a refund, or implementing escalation in this slice.

## D-028 — Complete customer-scoped conversation history

Date: 2026-08-26 · Status: Accepted

Expose authenticated `GET /v1/conversations/{conversation_id}` as the read boundary required by
later contextual escalation. Return conversation metadata and the complete message history for the
focused synthetic MVP, ordered by UTC creation time with UUID as a deterministic tiebreaker. User
messages expose base fields; assistant messages additionally expose status, uncertainty, and typed
plan, bill, or charge evidence references. Do not embed snapshot bodies and defer pagination.
Resolve ownership in the repository query and use the same `404 conversation_not_found` response
for absent and cross-customer conversations.
