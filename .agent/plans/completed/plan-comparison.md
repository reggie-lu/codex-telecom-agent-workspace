# Factual synthetic KDDI plan comparison

## Goal

Add a read-only, conversation-based comparison between the authenticated customer's current
synthetic KDDI plan and three catalog-listed synthetic offers. Ground every fact in typed provider
data, persist one immutable comparison snapshot, disclose unverified eligibility, and extend the
singular MVP release gate without weakening existing cases.

## Requirement References

- `docs/PRODUCT.md`: UC-004 and the approved post-0.1 factual comparison scope.
- D-043 through D-057 in `docs/DECISIONS.md`.
- Human approvals from 2026-08-27 through 2026-08-29 covering scope, data, API, safety,
  persistence, wording, evaluation, and schema.

## Non-Goals

- Personalized best-plan, savings, family-plan, or roaming recommendations.
- Customer-specific eligibility claims.
- Changing a customer's plan or any account mutation.
- Real KDDI website/API retrieval or providers other than KDDI.
- MiniMax-M3 wording for comparison responses.
- A separate public comparison endpoint.

## Approved Behavior

- Route natural comparison requests through
  `POST /v1/conversations/{conversation_id}/messages`.
- Compare the current 20 GB, JPY 4,500 recurring-charge plan with all three catalog offers in
  provider order:
  - Synthetic KDDI Lite 5GB: 5 GB, JPY 2,800/month.
  - Synthetic KDDI Plus 30GB: 30 GB, JPY 5,200/month.
  - Synthetic KDDI Max 100GB: 100 GB, JPY 7,500/month.
- Show signed recurring-charge and domestic-data deltas without ranking or projected savings.
- State that offers are catalog listed and customer-specific eligibility is unverified.
- Use catalog version `synthetic-kddi-catalog-2026-08-28`, dated 2026-08-28, with age <=30 days
  considered current through an injected clock.
- Return a deterministic grounded answer with exactly one `plan_comparison_snapshot` evidence
  reference.
- Fail closed with an uncertain evidence-free unavailable answer and human-support next step for
  missing, incomplete, stale, conflicting, or ineffective inputs.

## Proposed Design

Add typed comparison/catalog domain values, a catalog provider port, and a deterministic synthetic
adapter. Extend the existing support-message orchestrator with a higher-specificity comparison
intent before the generic current-plan route. The comparison path validates the complete current
plan and catalog, freshness, currencies, dates, identities, uniqueness, and deltas before formatting
a canonical answer. Inject UTC time through application composition for deterministic boundary
tests while production uses the real clock.

Add one forward-only migration after `20260826_05`:

- `plan_comparison_snapshots`: snapshot/customer IDs, current-plan name/data/charge/currency/effective
  date, catalog source version/as-of, retrieval timestamp, and `eligibility_verified = false`.
- `plan_comparison_offers`: offer ID, snapshot ID, catalog ID/name, data, charge, currency, effective
  date, signed charge/data deltas, and unique nonnegative position.
- `message_plan_comparison_evidence`: assistant-message/snapshot link.

Extend the PostgreSQL exchange repository and history read model to persist/reconstruct the new
typed evidence atomically. Keep unavailable exchanges message-only.

## Files Expected to Change

- Domain types and evidence enum/exchange contracts.
- Catalog provider port and synthetic KDDI adapter.
- Comparison orchestration, intent routing, canonical formatting, and composition.
- PostgreSQL models/repositories and one Alembic migration.
- API/history schemas only where the existing generic evidence enum requires extension.
- Unit, API, contract, integration, migration, history, and evaluation tests.
- `evals/cases/mvp.jsonl`, evaluator group reporting, runbooks, architecture, decisions, learning,
  blog, and this plan.

## Test Strategy

Follow TDD and observe focused failures before implementation:

- Domain/contract: valid catalog and boundary validation, exact approved facts, source order.
- Service: three or more natural intents; canonical four-plan facts and deltas; disclosure; no
  ranking/savings language; current at age 30 and stale at age 31.
- Safety: missing/incomplete current plan, empty/incomplete/duplicate/conflicting offers, mixed
  currency, ineffective or stale catalog, and unavailable provider all fail closed without evidence.
- API/privacy: authentication, ownership, stable response schema, and unsupported intent regression.
- PostgreSQL: migration constraints, atomic snapshot/offers/link persistence, reconstruction in
  history, and message-only unavailable persistence.
- Evaluation: preserve 36 cases, add five comparison routine and four safety cases, require 5/5
  expected locally and combined 20/20 safety, with the same singular no-argument command.
- Regression: full PostgreSQL pytest suite, Ruff, strict mypy, current-plan gate, and 45-case MVP
  gate.

## Implementation Steps

1. Add focused red domain, service, adapter, and API tests.
2. Implement typed catalog and comparison orchestration with deterministic output.
3. Add migration and PostgreSQL persistence/history reconstruction under integration tests.
4. Extend the versioned evaluator from 36 to 45 cases without modifying existing cases.
5. Update run/verify documentation and architecture status.
6. Run all automated gates and request independent migration/API/evaluation verification.
7. After human verification, create implementation and checkpoint commits and push `main`.

## Open Questions

None after final implementation authorization.

## Progress

- [x] Approved feature scope and factual-only boundary.
- [x] Approved synthetic catalog, freshness, and eligibility contracts.
- [x] Approved conversation API, deterministic response, evidence, and persistence contracts.
- [x] Approved evaluation and normalized schema contracts.
- [x] Authorized implementation.
- [x] Added focused failing tests.
- [x] Implemented domain, service, adapter, persistence, API, and evaluation changes.
- [x] Updated runbooks and completed automated verification.
- [x] Completed independent human verification.

## Verification

- Focused catalog/comparison tests: 10 passed.
- Focused API plus comparison tests: 27 passed.
- Migration/persistence/history tests: passed against local PostgreSQL.
- Full PostgreSQL suite: 130 passed.
- Ruff and strict mypy over 78 source files: passed.
- Migration `20260829_06` applied locally; `alembic check`: no new operations.
- Current-plan gate: routine 10/10, safety 6/6, release PASS.
- Expanded MVP gate: all five routine groups 5/5, safety 20/20, release PASS.
- Independent human verification on 2026-08-29: the migrated localhost API returned the complete
  grounded comparison with one typed evidence reference, and the 45-case gate reproduced five
  routine groups at 5/5, safety 20/20, and release PASS.

## Result

The feature is implemented and human-verified for the approved synthetic API and evaluation
scenarios. PostgreSQL history reconstruction is verified by integration tests.
