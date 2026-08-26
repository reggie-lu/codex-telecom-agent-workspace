# Project Decisions

Only record decisions important enough that a future developer would reasonably ask, "Why did we
choose this?"

## Decision Record Template

```text
## D-XXX — <Decision title>

Date:
Status: Proposed | Accepted | Superseded

Context:
What problem or choice required a decision?

Decision:
What was selected?

Why:
Why was it selected?

Alternatives:
What meaningful alternatives were considered?

Consequences:
What tradeoffs does this introduce?
```

Do not create a decision record for trivial implementation choices.

## D-001 — API-first backend for version 0.1

Date: 2026-08-25
Status: Accepted

Context:
The approved product is conversational and may eventually support web, mobile, or KDDI-integrated
customer interfaces. Building a customer frontend now would expand the first implementation beyond
the desired scope.

Decision:
Build version 0.1 as an API-first backend. Defer the frontend.

Why:
This keeps the initial implementation focused on grounded telecom-support behavior, evaluation, and
integration boundaries while leaving a reusable interface for future clients.

Alternatives:
A Web chat application or a CLI prototype.

Consequences:
Version 0.1 will not be directly usable by ordinary customers without an API client. The API contract
will become an important public boundary and must be tested carefully.

## D-002 — Python as the initial backend language

Date: 2026-08-25
Status: Accepted

Context:
The MVP needs an API backend, LLM or agent integration, and strong behavioral evaluation of routine
and corner cases.

Decision:
Use Python for the version 0.1 backend.

Why:
Python has strong AI and evaluation tooling, supports concise API development, and aligns with the
project's test-driven workflow through pytest.

Alternatives:
TypeScript and Java.

Consequences:
The project gains fast access to AI tooling and straightforward testing but has fewer compile-time
guarantees than Java or TypeScript. A future frontend will likely use a different language.

## D-003 — FastAPI as the API framework

Date: 2026-08-25
Status: Accepted

Context:
The version 0.1 API is the product's initial public boundary and needs explicit, testable request and
response contracts.

Decision:
Use FastAPI for the Python backend.

Why:
FastAPI provides typed validation, OpenAPI generation, async support, and straightforward API testing
without requiring a larger application stack.

Alternatives:
Flask.

Consequences:
The code will follow FastAPI and Pydantic conventions. This adds framework structure but reduces
manual schema and documentation work.

## D-004 — Local PostgreSQL for version 0.1 persistence

Date: 2026-08-25
Status: Accepted

Context:
Conversation history, human-escalation requests and status, and retrieved customer plan and billing
data must survive application restarts. The data is structured, sensitive, and may be updated by
concurrent support workflows.

Decision:
Use PostgreSQL running locally for version 0.1 development and verification.

Why:
PostgreSQL supports transactional escalation updates, concurrent access, and structured queries while
providing a realistic persistence boundary for the intended backend.

Alternatives:
SQLite.

Consequences:
Local development requires a PostgreSQL service and database configuration. Schema migrations,
retention, encryption, and access controls must be designed before sensitive data is used. Production
database hosting remains undecided.

## D-005 — Synthetic KDDI data behind a replaceable integration boundary

Date: 2026-08-25
Status: Accepted

Context:
The intended product serves actual KDDI customers, but this project does not currently have
authorized access to KDDI customer, billing, authentication, or escalation APIs. Public website data
cannot provide private account-specific information.

Decision:
Treat version 0.1 as an evaluation prototype. Use deterministic synthetic KDDI customer, plan, bill,
charge, and escalation data behind a replaceable provider adapter. Include missing, incomplete,
conflicting, outdated, and unavailable data scenarios. Do not implement dynamic KDDI website
retrieval without a separate approved decision.

Why:
Synthetic data allows safe, reproducible development and corner-case evaluation without implying
unauthorized access to real customer accounts.

Alternatives:
Dynamic retrieval from public KDDI pages or waiting for official API access before building.

Consequences:
Version 0.1 cannot validate real KDDI authentication or account integration and cannot be offered to
actual customers. The mock adapter must not leak into domain behavior so an official integration can
replace it later. General public plan information may be considered separately with freshness,
attribution, and terms-of-use controls.

## D-006 — SambaNova behind a small model interface

Date: 2026-08-25
Status: Accepted

Context:
The agent needs real model behavior for meaningful evaluation, but automated tests must remain
deterministic and business behavior should not be coupled directly to a provider SDK.

Decision:
Use a SambaNova endpoint as the version 0.1 hosted LLM provider behind a small internal model
interface. Use a deterministic fake implementation in automated tests.

Why:
This enables realistic agent responses while preserving reproducible tests and a clear external
boundary. The abstraction exists to support evaluation and isolation, not speculative multi-provider
features.

Alternatives:
Direct SambaNova coupling or deterministic scripted responses without a real hosted model.

Consequences:
The project must define a narrow model request/response contract and test both the fake and SambaNova
adapter boundary. Model identifiers and endpoint settings remain runtime configuration. Credentials
must never be committed or written into project documentation.

## D-007 — Synthetic bearer-token authentication

Date: 2026-08-25
Status: Accepted

Context:
The evaluation prototype needs to test customer isolation even though official KDDI authentication
is unavailable.

Decision:
Use synthetic bearer tokens mapped to mock customer identities. Enforce customer scoping for all
conversation, plan, billing, charge, and escalation access.

Why:
This provides a realistic authorization boundary for privacy tests without pretending to implement
real KDDI identity or authentication.

Alternatives:
No authentication on localhost or one shared development API key.

Consequences:
Test identities and credentials must be clearly labeled synthetic. This mechanism cannot be reused
as production KDDI authentication and must be replaced when an authorized identity integration is
available.

## D-008 — Retain synthetic data until explicit development reset

Date: 2026-08-25
Status: Accepted

Context:
Prototype conversations, billing snapshots, and escalation state must survive restarts, but no real
customer-data retention policy is available and version 0.1 stores synthetic data only.

Decision:
Retain version 0.1 synthetic records until an explicit development reset. Ordinary startup must not
silently erase persisted state.

Why:
This keeps demos and evaluations reproducible without inventing production compliance rules or
adding an unnecessary cleanup scheduler.

Alternatives:
Fixed-period deletion or lifecycle rules based on conversation and escalation status.

Consequences:
The project needs a deliberate reset mechanism and documented synthetic seed state. Real KDDI data
must not use this retention policy; production retention and deletion require separate approval.

## D-009 — Localhost-only runtime for version 0.1

Date: 2026-08-25
Status: Accepted

Context:
Version 0.1 uses mock authentication, synthetic KDDI data, local PostgreSQL, and is intended for
development and evaluation rather than real customer traffic.

Decision:
Run the FastAPI service locally and bind it to localhost only. Do not create public hosting, cloud
infrastructure, containers, or CI/CD as part of the approved bootstrap architecture.

Why:
Localhost access minimizes exposure while the project validates agent behavior and security
boundaries without production authentication or operations.

Alternatives:
Local-network access or public deployment.

Consequences:
Remote clients and ordinary customers cannot access version 0.1. Any broader deployment requires a
new security, authentication, infrastructure, and operational decision.

## D-010 — Separate deterministic tests from live model evaluations

Date: 2026-08-25
Status: Accepted

Context:
The MVP requires reproducible behavioral checks and meaningful evaluation of a real SambaNova-backed
agent. Live model responses are nondeterministic, slower, and may incur cost.

Decision:
Use pytest with a deterministic fake model for ordinary unit, API, integration, and contract tests.
Run live SambaNova evaluations as a separate opt-in suite with aggregate and corner-case metrics.

Why:
This keeps routine verification stable and fast while still measuring the behavior users will
actually experience from the hosted model.

Alternatives:
Use the live model in every test or evaluate only scripted responses.

Consequences:
The project needs both deterministic fixtures and a maintained evaluation dataset. A passing normal
test suite does not by itself prove the live agent meets the approved quality target.

## D-011 — Ports and adapters around the support domain

Date: 2026-08-25
Status: Accepted

Context:
The backend has several approved external boundaries—FastAPI, PostgreSQL, synthetic KDDI data, and
SambaNova—and must replace them with deterministic implementations during testing.

Decision:
Separate the code into domain, services, ports, adapters, and API modules. Keep the evaluation suite
outside production request handling. Dependencies flow from API to services to domain, while
adapters implement service-owned ports.

Why:
Each boundary corresponds to a current requirement: domain clarity, provider isolation, persistence,
API contracts, or reproducible evaluation.

Alternatives:
A single FastAPI module with direct database and model calls.

Consequences:
The project has several explicit modules from the start, but each has an approved responsibility.
Avoid adding generic repositories or extra abstraction layers beyond the required ports.

## D-012 — PostgreSQL-backed domain entities with explicit core types

Date: 2026-08-25
Status: Accepted

Context:
The prototype must persist conversations, escalation state, and retrieved plan and billing snapshots.
Billing explanations and evidence require types that avoid ambiguity and monetary precision errors.

Decision:
Persist synthetic customers, plan snapshots, bills, charges, conversations, messages, and escalations
in PostgreSQL. Use UUID identifiers, fixed-precision decimal and PostgreSQL `NUMERIC` for money,
three-letter currency codes, dates for calendar values, timezone-aware UTC timestamps for events,
constrained statuses and roles, Unicode text, and typed evidence references.

Why:
Explicit types make the API, persistence, authorization, and evaluation contracts testable. Decimal
money prevents binary floating-point errors, while typed evidence supports grounded explanations.

Alternatives:
Loosely typed dictionaries, string identifiers, floating-point money, or unstructured evidence text.

Consequences:
Database migrations and API schemas must preserve these invariants. Exact tables, constraints,
indexes, and enum representation will be specified before implementation. Raw bearer tokens are not
stored.

## D-013 — Conversation-centric public API

Date: 2026-08-25
Status: Accepted

Context:
Version 0.1 must support persistent support conversations, contextual follow-ups, and human
escalation. The API is the initial public product boundary, while a frontend is deferred.

Decision:
Expose endpoints to create a conversation, send a message, retrieve conversation history, request an
escalation, and retrieve escalation status. Require synthetic bearer authentication and customer
ownership on every endpoint. Do not expose direct public plan, bill, or charge resources in version
0.1.

Why:
This is the smallest API surface that supports the approved conversational flow and escalation
lifecycle without adding resource endpoints not required by the MVP.

Alternatives:
A resource-plus-conversation API or one support-query endpoint.

Consequences:
Future clients must interact through conversations. Exact schemas, HTTP status codes, error format,
idempotency behavior, and escalation states still require definition before implementation.

## D-014 — Five-state escalation lifecycle

Date: 2026-08-25
Status: Accepted

Context:
Escalation requests and their status must persist and be visible through the API. The synthetic
prototype needs enough lifecycle detail to test successful and failed handoffs.

Decision:
Use `requested`, `queued`, `assigned`, `resolved`, and `failed` escalation statuses. Allow the
forward flow from requested to queued to assigned to resolved, with failure after acceptance when a
handoff cannot continue. Defer cancellation and reopening.

Why:
These states cover initiation, acceptance, human assignment, completion, and failure without adding
unapproved case-management behavior.

Alternatives:
A binary open/closed status or a larger customer-service case lifecycle.

Consequences:
State transitions must be validated and tested. Failed escalations require a safe customer-facing
next step. Cancellation and reopening require future product approval.

## D-015 — MiniMax-M3 through SambaNova's OpenAI-compatible endpoint

Date: 2026-08-25
Status: Accepted

Context:
The approved model boundary needs one concrete hosted implementation for live agent evaluation.

Decision:
Use the SambaNova OpenAI-compatible chat-completions endpoint with `MiniMax-M3` as the initial model.
Configure the base URL, model name, and API key at runtime. Never commit the API key.

Why:
The user has access to this endpoint and selected the model. The OpenAI-compatible protocol permits
a narrow adapter without coupling the domain to a provider SDK.

Alternatives:
Another hosted provider, model, or a scripted-only prototype.

Consequences:
Live evaluation results are specific to `MiniMax-M3` and the active endpoint configuration. Model
changes require evaluation before becoming the default. Endpoint timeout, retry, and failure behavior
still require approval.

## D-016 — Bounded model retry with safe terminal failure

Date: 2026-08-25
Status: Accepted

Context:
The hosted model endpoint may time out, rate-limit requests, reject credentials, or become
unavailable. The product must not fabricate an account-specific answer when generation fails.

Decision:
Use a finite timeout and at most one retry for clearly transient timeouts, rate limits, or server
errors. Do not retry invalid requests or authentication failures and do not use an unapproved fallback
model. On terminal failure, return a safe service-unavailable response, preserve the customer's
message, and allow retry or mock human escalation.

Why:
This provides limited resilience without creating retry storms, hiding configuration errors, or
silently changing model behavior.

Alternatives:
No retry, unlimited retries, or automatic fallback to another model.

Consequences:
The API needs typed upstream-failure responses and idempotent message handling. The exact timeout is
an implementation-plan decision and must be covered by adapter tests.

## D-017 — Release-blocking corner-case safety gates

Date: 2026-08-26
Status: Accepted

Context:
An aggregate 80% routine-case score could hide unsafe behavior when account data is missing,
unavailable, conflicting, or outdated.

Decision:
Require 100% of missing or unavailable-data evaluation cases to avoid invented account facts and
clearly state the limitation or next step. Require 100% of conflicting or outdated-data cases to
identify the conflict or staleness and avoid presenting uncertainty as current fact. Any violation
blocks release regardless of aggregate score.

Why:
These thresholds measure safety behavior rather than perfect issue resolution and protect the most
important trust boundary in billing support.

Alternatives:
Include corner cases only in the aggregate 80% score or use lower category thresholds.

Consequences:
The evaluation dataset and scorer must distinguish factual resolution from safe refusal or
escalation. A single unsafe result in either mandatory category prevents release.

## D-018 — Synchronous SQLAlchemy, Alembic, and Psycopg

Date: 2026-08-26
Status: Accepted

Context:
The approved PostgreSQL model contains related customers, snapshots, bills, charges, conversations,
messages, and escalation state and requires repeatable schema evolution.

Decision:
Use synchronous SQLAlchemy 2 for relational persistence, Alembic for migrations, and Psycopg as the
PostgreSQL driver.

Why:
This provides explicit transactions, testable relational mapping, and standard migrations without
the additional lifecycle complexity of async database access in a localhost prototype.

Alternatives:
Async SQLAlchemy with asyncpg or direct Psycopg with hand-written mapping and migration plumbing.

Consequences:
The project gains three persistence dependencies and must keep domain entities separate from ORM
models. Database operations are synchronous; async database scaling can be reconsidered only if a
measured deployment requirement appears.

## D-019 — OpenAI Python SDK for the SambaNova adapter

Date: 2026-08-26
Status: Accepted

Context:
SambaNova exposes the selected `MiniMax-M3` model through an OpenAI-compatible chat-completions
endpoint. The model adapter needs typed protocol support while retaining the project's approved
timeout and retry behavior.

Decision:
Use the OpenAI Python SDK with a configurable SambaNova base URL. Set SDK `max_retries=0`; implement
the approved single transient retry in the adapter.

Why:
The SDK provides maintained protocol types and request handling without requiring a custom HTTP
schema implementation. Disabling SDK retries prevents hidden retry multiplication.

Alternatives:
Use HTTPX directly and maintain request and response schemas locally.

Consequences:
The project adds the OpenAI SDK dependency but must use only the narrow chat-completions surface.
SambaNova-specific behavior remains inside its adapter, and live calls remain opt-in during tests.
