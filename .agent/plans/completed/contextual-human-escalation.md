# Contextual human escalation

## Goal

Implement the approved mock human-escalation workflow so an authenticated Synthetic Alice can
request a handoff for an owned conversation and later retrieve its durable status without repeating
the conversation, billing issue, or supporting evidence.

## Requirement References

- `docs/PRODUCT.md`: cross-cutting escalation, unexpected-charge steps 6–7, `FR-005`, privacy, and
  reliability requirements.
- `docs/ARCHITECTURE.md`: approved creation/status routes, five-state lifecycle, PostgreSQL entity,
  mock adapter, and conversation-history dependency.
- `docs/DECISIONS.md`: conversation-centric API, explicit persistent types, five-state lifecycle,
  and customer isolation.
- Human approval on 2026-08-26 to proceed after conversation-history checkpoint CP-009.

## Non-Goals

- A real KDDI representative, ticketing platform, phone call, or production notification.
- Refund, adjustment, plan-change, or dispute decisions.
- Automatic state progression driven by background workers.
- Production authentication, deployment, containers, or frontend work.
- Plan comparison, roaming-option, or cost-saving features.

## Current State

The API records explicit customer-authored handoff requests, freezes owned conversation context,
queues accepted mock handoffs, preserves failures, and exposes customer-scoped status retrieval.
Real KDDI representative integration and automatic lifecycle progression remain unimplemented.

## Proposed Design

Add an authenticated escalation creation service that loads an owned complete conversation, builds
a typed immutable handoff context, calls a deterministic mock handoff boundary, and atomically
persists the result. Add a customer-scoped status read service. Store the approved five-state
lifecycle with validated transitions, explicit timestamps, a bounded reason, and context sufficient
to avoid making the customer repeat the issue. Preserve a failed request rather than silently
dropping it and return a safe next step.

## Files Expected to Change

- Escalation domain, ports, services, and mock adapter
- PostgreSQL models, repository, and a new Alembic migration
- FastAPI schemas, composition, routes, and error translation
- Unit, API, contract, and PostgreSQL integration tests
- README, architecture, decisions, feature journals, and this ExecPlan

## Test Strategy

Use TDD for explicit request behavior, owned-context capture, evidence preservation, duplicate
handling, mock success/failure, lifecycle validation, status retrieval, authentication, and
cross-customer privacy. Run migration checks, the full PostgreSQL suite, strict typing/linting, and
the existing current-plan evaluation gate.

## Implementation Steps

1. Approve trigger, creation, duplicate, and mock-state contracts one decision at a time.
2. Define failing domain, service, and API behavioral tests.
3. Add the escalation schema and migration with explicit constraints.
4. Implement the mock handoff and PostgreSQL adapters.
5. Compose the creation/status routes and stable errors.
6. Update runbooks, architecture, decisions, learning notes, and blog.
7. Complete automated checks and request independent human verification.

## Open Questions

None.

## Decisions

- Use the already approved `requested`, `queued`, `assigned`, `resolved`, and `failed` lifecycle.
- The escalation includes conversation messages and typed evidence references, not duplicated raw
  snapshot bodies.
- Create escalation records only through an explicit authenticated customer request. The agent may
  recommend escalation at a judgment boundary but never creates one automatically.
- Creation requires a customer-authored `reason`, trimmed to 1–1,000 Unicode characters. Invalid
  input returns `422 invalid_escalation_reason`.
- Persist creation as `requested` before attempting the synchronous deterministic mock handoff.
  Acceptance transitions to `queued`; rejection/unavailability transitions to `failed`.
- Return `201 Created` for either durable outcome with ID, conversation ID, reason, status,
  timestamps, and nullable `next_step`. Failed handoff includes a safe retry-later next step.
- Permit at most one active escalation (`requested`, `queued`, or `assigned`) per conversation.
  Duplicate creation returns `409 escalation_already_active`; `resolved` and `failed` allow a new
  request. Enforce the invariant in PostgreSQL as well as the service contract.
- Store an immutable typed handoff-context snapshot as PostgreSQL `JSONB`: conversation metadata,
  every ordered message, assistant status/uncertainty, and typed evidence references. Exclude raw
  snapshot bodies and credentials; later messages do not mutate submitted context.
- `GET /v1/escalations/{escalation_id}` returns the same public fields as creation and does not
  expose handoff context. Missing and cross-customer IDs share `404 escalation_not_found`.
- The runtime deterministic mock accepts valid requests and transitions them to `queued`. Tests
  inject a failing mock to exercise durable `failed` behavior; no magic customer text or public
  failure switch is exposed. `assigned` and `resolved` are domain-validated but do not auto-progress.

## Discoveries

- The existing customer-scoped history read model is the natural input to a handoff context.
- There is an empty `adapters/escalation_mock` package but no escalation domain or persistence yet.

## Progress

- [x] Selected contextual human escalation after CP-009.
- [x] Recorded the agreed architecture boundary and active plan.
- [x] Approved the remaining behavioral contracts.
- [x] Added failing tests.
- [x] Implemented persistence, mock handoff, and routes.
- [x] Updated run/verification documentation.
- [x] Completed automated and human verification.

## Verification

The final PostgreSQL-enabled suite passes 110/110. Ruff and strict mypy pass; migration
`20260826_05` reaches head with no schema drift; the unchanged offline evaluation passes 10/10
routine, 6/6 safety, and the release gate.
The human independently applied migration `20260826_05`, created escalation
`695fde8f-3d21-4de0-bf87-110438421782`, and retrieved it through the documented status route. The
response returned `200 OK`, the correct conversation and reason, `status: queued`, UTC timestamps,
and `next_step: null` on 2026-08-26.

## Result

Completed and independently human-verified on 2026-08-26. The focused MVP now has a durable mock
handoff boundary; real representative integration and lifecycle progression remain deferred.
