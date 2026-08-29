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

## D-029 — Explicit consent for escalation creation

Date: 2026-08-26 · Status: Accepted

Create a durable escalation only when the authenticated customer explicitly requests one through
the escalation endpoint. The agent may recommend human support when evidence is unavailable or a
dispute requires judgment, but it must never infer consent or silently create a ticket. This keeps
handoff creation auditable and avoids unexpected escalations while automatic escalation remains
outside the focused MVP.

## D-030 — Bounded customer-authored escalation reason

Date: 2026-08-26 · Status: Accepted

Require `POST /v1/conversations/{conversation_id}/escalations` to contain a customer-authored
`reason`. Trim surrounding whitespace and accept 1–1,000 Unicode characters; invalid input returns
the stable `422 invalid_escalation_reason` envelope. Conversation history supplies the detailed
messages and evidence, while the reason records why the customer explicitly wants a human.

## D-031 — Durable and truthful mock-handoff outcome

Date: 2026-08-26 · Status: Accepted

Persist an escalation in `requested` before synchronously attempting the deterministic mock
handoff. Mock acceptance transitions it to `queued`; rejection or unavailability transitions it to
`failed`. Return `201 Created` for either outcome because the customer's request remains durable,
and expose ID, conversation ID, reason, status, creation/update timestamps, and nullable
`next_step`. A failed handoff provides a safe retry-later instruction. Never report `queued` before
the mock accepts or discard a failed request.

## D-032 — One active escalation per conversation

Date: 2026-08-26 · Status: Accepted

Allow at most one active escalation in `requested`, `queued`, or `assigned` for a conversation.
Reject another creation attempt with stable `409 escalation_already_active` and do not create a
duplicate. A `resolved` or `failed` escalation permits a later request. Enforce this invariant in
PostgreSQL in addition to service-level handling so concurrent requests cannot create duplicate
active handoffs.

## D-033 — Immutable typed handoff context

Date: 2026-08-26 · Status: Accepted

At escalation creation, freeze the owned conversation metadata, every message in deterministic
order, assistant status/uncertainty, and typed plan, bill, or charge evidence references into an
immutable typed context stored as PostgreSQL `JSONB`. Do not include credentials, raw customer
identity, or raw snapshot bodies. Later conversation messages must not mutate the submitted
handoff, preserving an auditable record of exactly what the mock representative received.

## D-034 — Minimal customer-scoped escalation resource

Date: 2026-08-26 · Status: Accepted

Return the same public escalation representation from creation and
`GET /v1/escalations/{escalation_id}`: ID, conversation ID, reason, status, creation/update
timestamps, and nullable `next_step`. Keep immutable handoff context internal rather than exposing
conversation content through the status route. Scope lookup by authenticated customer and return
the same stable `404 escalation_not_found` response for absent and cross-customer identifiers.

## D-035 — Accepted-by-default runtime mock

Date: 2026-08-26 · Status: Accepted

The runtime deterministic mock accepts every valid handoff and transitions the durable escalation
from `requested` to `queued`. Exercise provider rejection and unavailability through injected
deterministic test adapters, not magic customer text or a public failure switch. Validate the
remaining lifecycle transitions in the domain, but do not automatically progress `queued` records
to `assigned` or `resolved` in this focused slice.

## D-036 — Per-feature routine gates for the focused MVP

Date: 2026-08-26 · Status: Accepted

Evaluate latest-bill, unexpected-charge, conversation-history, and escalation routine quality as
four independent groups requiring at least 80% each. Combine mandatory safety cases into a separate
gate requiring exactly 100%. The overall cross-feature release gate fails if any feature routine
group misses its threshold or if any safety case fails, so strong behavior in one feature cannot
hide weakness or offset a safety violation elsewhere.

## D-037 — Balanced 36-case cross-feature baseline

Date: 2026-08-26 · Status: Accepted

Start the cross-feature MVP evaluation with 36 versioned deterministic cases. Allocate five routine
and four mandatory safety cases to each of latest bill, unexpected charge, conversation history,
and escalation, for 20 routine and 16 safety cases total. Five routine cases make the 80% threshold
concrete—one miss is allowed per feature—while the equal safety allocation prevents one feature's
corner cases from being underrepresented.

## D-038 — Approved cross-feature scenario catalog

Date: 2026-08-26 · Status: Accepted

Use the human-approved 36-case catalog. Latest-bill routine cases cover summary, recent invoice,
period, total, and line items; safety covers missing bill, empty items, non-reconciliation, and
negative amounts. Unexpected-charge routine covers higher bill, unexpected item, roaming charge,
JPY 1,200, and unrecognized usage; safety covers missing, stale, conflicting, and ambiguous causal
evidence. History routine covers empty, plan, bill, charge, and mixed ordered histories; safety
covers authentication, missing and cross-customer privacy, and response disclosure. Escalation
routine covers queued creation, reason trimming, status retrieval, populated context, and empty
conversation handoff; safety covers invalid reasons, active duplicates, cross-customer status, and
durable provider failure with retry guidance.

## D-039 — Singular offline MVP evaluation command

Date: 2026-08-26 · Status: Accepted

Expose `uv run python -m telecom_agent.evaluation.mvp` as the only initial cross-feature evaluation
command. It always runs all 36 deterministic offline cases, prints each PASS/FAIL, four independent
routine scores, one combined safety score, and the overall release gate, and exits nonzero if any
gate fails. Do not add feature filters or live mode, preventing a partial run from being mistaken
for the complete release gate.

## D-040 — Preserve the first cross-feature baseline failures

Date: 2026-08-26 · Status: Accepted

Record the first 36-case baseline without weakening or rewriting its approved scenarios. Latest
bill scored 3/5 because `recent invoice` and `billing period` were not recognized; unexpected
charge scored 3/5 because direct `roaming charge` and unrecognized-roaming-usage language were not
recognized. History and escalation each scored 5/5 and all 16 safety cases passed. The overall gate
correctly failed. Any remediation must retain the same dataset, per-feature thresholds, and perfect
safety requirement.

## D-041 — Narrow cross-feature intent remediation

Date: 2026-08-26 · Status: Accepted

Remediate only the four CP-011 routine gaps: `recent invoice`, `billing period` or latest-statement
language, direct `roaming charge`, and unrecognized roaming usage. Extend the existing deterministic
intent predicates without changing the 36-case dataset, graders, feature thresholds, or 100%
safety gate. Preserve ambiguous-charge clarification and all grounding/evidence requirements.

## D-042 — Keep intent remediation deterministic and evidence-neutral

Date: 2026-08-26 · Status: Accepted

Implement the four approved language additions inside the existing normalized intent predicates.
Do not alter bill or charge retrieval, canonical answer formatting, evidence construction, or
persistence. Keep ambiguous `this charge` routing ahead of charge investigation. This makes the
unchanged 36-case gate green without weakening its graders or introducing model-dependent routing.

## D-043 — Build plan comparison on a typed offer catalog

Date: 2026-08-27 · Status: Accepted

Make read-only synthetic KDDI plan comparison the next post-0.1 feature. Introduce one typed, dated
offer catalog shared by future comparison, roaming, and savings capabilities, rather than encoding
offer facts independently in each answer path. Compare catalog offers with the authenticated
customer's current plan; changing the customer's plan remains outside this feature.

## D-044 — Separate factual comparison from recommendation

Date: 2026-08-27 · Status: Accepted

The first plan-comparison slice presents evidence-backed price, domestic-data, effective-date, and
key-difference facts side by side. It does not label an offer “best,” infer customer preferences or
eligibility, calculate personalized savings, or change the account. Recommendation remains a later
feature with its own inputs and evaluation contract.

## D-045 — Start with three contrasting catalog offers

Date: 2026-08-27 · Status: Accepted

Use three available synthetic KDDI offers in the first catalog: a lower-cost/lower-data option, a
mid-tier option near the customer's current 20 GB plan, and a higher-cost/high-data option. Compare
all three with the current plan and preserve their source order; do not rank, score, or hide offers.

## D-046 — Keep catalog reference data behind a provider port

Date: 2026-08-28 · Status: Accepted

Expose the typed plan catalog through a KDDI provider port with a deterministic synthetic adapter,
not PostgreSQL. Include explicit source-version and freshness metadata. This catalog is external
reference data rather than customer-owned state; a future real KDDI adapter can replace the mock
without changing comparison orchestration or persistence boundaries.

## D-047 — Do not equate catalog visibility with customer eligibility

Date: 2026-08-28 · Status: Accepted

Describe offers as catalog-listed KDDI options, not as plans available to the authenticated
customer. Every comparison must state that customer-specific eligibility is unverified. Do not
infer eligibility from current-plan ownership, catalog presence, price, or data allowance.

## D-048 — Persist immutable plan-comparison evidence

Date: 2026-08-28 · Status: Accepted

Atomically persist each grounded comparison exchange with a typed comparison evidence reference
and immutable PostgreSQL snapshot. Capture the current-plan facts, all three catalog offers,
catalog source version, and freshness metadata shown to the customer. Conversation history must
continue to display the exact evidence reference even after a later catalog changes.

## D-049 — Format initial comparisons deterministically

Date: 2026-08-28 · Status: Accepted

Use a canonical deterministic formatter for the first comparison response. It must include the
current plan, all three catalog offers, comparable numeric/date facts, catalog freshness, and the
eligibility disclosure. Do not call MiniMax-M3 in this slice. Model wording requires a later
comparison-specific output guard and evaluation gate before adoption.

## D-050 — Fail closed on unsafe comparison inputs

Date: 2026-08-28 · Status: Accepted

Do not compare when the current plan or offer catalog is missing, incomplete, stale, internally
conflicting, or outside its effective window. Return a typed `unavailable` answer that explains the
limitation and recommends explicit human support. Persist no grounded comparison snapshot or
evidence when the input contract fails; never silently drop suspect offers and compare the rest.

## D-051 — Fix the first synthetic comparison facts

Date: 2026-08-28 · Status: Accepted

Populate the initial catalog with `Synthetic KDDI Lite 5GB` at JPY 2,800/month, `Synthetic KDDI
Plus 30GB` at JPY 5,200/month, and `Synthetic KDDI Max 100GB` at JPY 7,500/month. Compare them with
the existing 20 GB, JPY 4,500/month current-plan fixture. Label every amount as a monthly recurring
charge rather than a total bill, and keep all names explicitly synthetic.

## D-052 — Enforce a 30-day catalog freshness window

Date: 2026-08-28 · Status: Accepted

Set the initial source version to `synthetic-kddi-catalog-2026-08-28` with an `as_of` date of
2026-08-28. Treat age of 30 days or less as current and age greater than 30 days as stale, using an
injected UTC clock for deterministic boundary tests. A stale catalog blocks comparison until the
synthetic source version and date are explicitly refreshed.

## D-053 — Reuse the conversation message API for comparison

Date: 2026-08-28 · Status: Accepted

Route natural comparison requests through the existing authenticated
`POST /v1/conversations/{conversation_id}/messages` endpoint. Extend deterministic intent matching
for current-plan comparison, other-plan, and available-plan-option language. Do not add a separate
comparison endpoint; preserve customer ownership, persisted exchanges, response status, and typed
evidence conventions.

## D-054 — Show factual deltas without projecting savings

Date: 2026-08-28 · Status: Accepted

Calculate each catalog offer's signed monthly-recurring-charge and domestic-data difference from
the current plan. For the initial fixture: Lite is JPY 1,700/15 GB lower, Plus is JPY 700/10 GB
higher, and Max is JPY 3,000/80 GB higher. Do not translate a lower recurring charge into promised
bill savings, because usage, fees, discounts, taxes, and eligibility are outside this evidence.

## D-055 — Use one typed comparison evidence reference

Date: 2026-08-28 · Status: Accepted

Return valid comparisons as `grounded`, `uncertain: false`, with exactly one
`plan_comparison_snapshot` evidence reference covering the current plan, all three offers, source
metadata, and computed deltas. Return invalid or unavailable comparisons as `unavailable`,
`uncertain: true`, with no evidence and a human-support next step. Persist the user and safe
assistant messages in both paths.

## D-056 — Add plan comparison to the singular MVP gate

Date: 2026-08-28 · Status: Accepted

Extend `uv run python -m telecom_agent.evaluation.mvp` from 36 to 45 deterministic cases by adding
five plan-comparison routine cases and four safety cases. Require at least 80% comparison routine
success. Add missing current plan, stale catalog, conflicting catalog, and unverified-eligibility
disclosure cases to the mandatory combined safety gate, which grows from 16/16 to 20/20. Preserve
all existing cases and block release on any feature gate or safety failure.

## D-057 — Normalize persisted comparison snapshots and offers

Date: 2026-08-29 · Status: Accepted

Add one forward-only Alembic migration with `plan_comparison_snapshots`, ordered
`plan_comparison_offers`, and `message_plan_comparison_evidence`. Store customer ownership,
current-plan facts, catalog source/freshness, retrieval time, and the unverified-eligibility state on
the snapshot. Store each offer's facts, position, and signed charge/data deltas in child rows. Link
the grounded assistant message to exactly one snapshot, following existing bill evidence patterns.

## D-058 — Inject comparison time through application composition

Date: 2026-08-29 · Status: Accepted

Pass the UTC clock through FastAPI and PostgreSQL composition into support-message orchestration.
Production defaults to real UTC time; API, integration, and evaluation tests inject deterministic
time. Test clocks advance by deterministic microseconds when message order is under test, preserving
the repository's timestamp-plus-UUID ordering contract.
