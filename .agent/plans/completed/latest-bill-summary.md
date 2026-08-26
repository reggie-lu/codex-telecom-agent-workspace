# Latest-bill summary

## Goal

Implement `UC-002` as a focused vertical slice: an authenticated synthetic KDDI customer can ask
for the latest bill and receive its billing period, total, and line items backed by typed persisted
bill evidence, with safe behavior when billing data is missing or unavailable.

## Requirement References

- `docs/PRODUCT.md`: `UC-002`, `FR-002`, privacy, grounding, and missing-data safety.
- `docs/ARCHITECTURE.md`: conversation-centric API, typed bill/charge snapshots, synthetic KDDI
  adapter, PostgreSQL persistence, and customer ownership.
- `docs/DECISIONS.md`: API-first backend, synthetic data, ports and adapters, explicit persistent
  types, and deterministic safety boundaries.
- Human approval on 2026-08-26 to implement latest-bill summary separately from unexpected-charge
  investigation.

## Non-Goals

- Explaining why a charge occurred or deciding whether it is unexpected.
- Comparing plans, roaming options, savings recommendations, refunds, or adjustments.
- Conversation-history retrieval or human escalation.
- Real KDDI account data or website scraping.
- A billing evaluation dataset or live MiniMax-M3 wording; those require separately approved slices.

## Current State

The message endpoint supports only current-plan questions. Billing questions return `unsupported`.
PostgreSQL stores plan snapshots and plan evidence but has no bill, charge, or bill-evidence tables.

## Proposed Design

Add typed bill and charge snapshot domain records, a narrow latest-bill provider port, a synthetic
KDDI implementation, and forward-only PostgreSQL tables. Extend message orchestration to classify
latest-bill intent, format a deterministic evidence-backed English summary, persist the exchange
atomically, and attach one `bill_snapshot` evidence reference. Missing or unavailable bill data
returns a safe `unavailable` exchange without amounts, dates, line items, or evidence.

## Files Expected to Change

- Domain, message ports/service, synthetic KDDI and PostgreSQL adapters
- FastAPI composition and response types
- A forward-only Alembic migration
- Unit, contract, API, and PostgreSQL integration tests
- README and durable project documentation
- `learning.md` and `blog.md`

## Test Strategy

Use TDD at each boundary: domain/service behavior first, then synthetic adapter contract, API
contract, PostgreSQL schema and atomic persistence, migration upgrade/downgrade, and the full suite.
Verify customer ownership, exact bill facts, decimal money, evidence typing, and absence of invented
facts when data is unavailable.

## Implementation Steps

1. Obtain approval for the exact synthetic latest-bill fixture.
2. Define failing domain/service and adapter contract tests.
3. Add typed bill models, provider/repository contracts, and deterministic orchestration.
4. Extend the existing message API composition without adding a direct bill endpoint.
5. Add forward-only bill, charge, and evidence persistence with integration tests.
6. Update run/verification documentation and the architecture flow.
7. Run automated verification and request independent human API verification.

## Open Questions

None.

## Decisions

- Keep latest-bill summary separate from unexpected-charge diagnosis.
- Use the existing conversation message endpoint and preserve customer ownership semantics.
- Start with deterministic grounded wording; live model wording and billing evaluation remain later
  slices so retrieval and evidence correctness are established first.
- Use the human-approved July 1–31, 2026 bill totaling JPY 6,930 with monthly service JPY 4,500,
  domestic calls JPY 600, international roaming data JPY 1,200, and taxes/fees JPY 630.

## Discoveries

- The existing `MessageExchange` and PostgreSQL repository are plan-specific and must be extended
  without allowing plan and bill evidence to become ambiguous.
- SQLAlchemy required an explicit flush after the bill snapshot insert and before independent line
  item records; the flush remains inside the same transaction and does not weaken atomicity.

## Progress

- [x] Confirmed the next approved MVP use case and focused scope.
- [x] Recorded the agreed architecture boundary.
- [x] Approved the synthetic bill fixture.
- [x] Added failing behavioral tests.
- [x] Implemented the vertical slice.
- [x] Updated runbooks and durable documentation.
- [x] Completed automated and Codex localhost verification.
- [x] Received independent human verification.

## Verification

Service, contract, API, migration, and PostgreSQL integration tests pass. The full suite passes 73
tests with integration coverage; Ruff and strict mypy pass across 55 source files. The existing
current-plan evaluation remains at 10/10 routine and 6/6 safety. Local migration `20260826_03`
reached head, and a localhost smoke request returned the exact grounded bill with typed evidence.
`alembic check` reports no model/migration drift. The human independently reproduced `201 grounded`,
`uncertain: false`, the exact approved bill and line items, and one typed `bill_snapshot` evidence
reference.

## Result

The focused latest-bill vertical slice is complete. It retrieves, reconciles, formats, and
atomically persists the approved synthetic bill with typed evidence while failing safely for
missing or inconsistent data. It does not diagnose charges or call MiniMax-M3. Automated,
localhost, and independent human verification all pass; the slice is ready for a development
checkpoint.
