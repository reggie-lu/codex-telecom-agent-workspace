# Grounded Current-Plan Message

## Goal

An authenticated synthetic customer can send a message in an owned conversation and receive a
persisted English explanation of the customer's current synthetic KDDI plan, with explicit evidence
and safe behavior when plan data is unavailable.

## Requirement References

- `UC-001` and `FR-001` — explain the authenticated customer's current plan from retrieved evidence
- `FR-004` — preserve conversation context
- Privacy, accuracy, and missing-data gates in `docs/PRODUCT.md`
- D-007 — synthetic bearer authentication and ownership
- D-011 — ports and adapters
- D-012 — explicit persistent types and evidence
- D-013 — conversation-centric API
- D-017 — release-blocking missing/conflicting-data safety

## Non-Goals

- Latest-bill or unexpected-charge explanations.
- Plan comparison, roaming guidance, or savings recommendations.
- Human escalation.
- Real KDDI APIs, website scraping, or real customer data.
- Multi-turn reference resolution beyond persisting this first exchange.
- Changing plans or performing account actions.

## Current State

Customers can authenticate and create persisted conversations. Messages, plan snapshots, synthetic
KDDI retrieval, grounding evidence, and message submission are not implemented. SambaNova is
approved architecturally but has no adapter, prompt contract, timeout, or evaluation harness yet.

## Proposed Design

- Add framework-independent plan snapshot, message, evidence, and availability types.
- Add narrow owned-conversation, plan-data, and message-persistence ports.
- Add a deterministic synthetic KDDI adapter for Synthetic Alice's current plan plus unavailable
  fixtures required by the safety gate.
- Add a service that verifies ownership, persists the user message, obtains plan evidence, produces
  a grounded answer or explicit unavailable answer, and persists the assistant message and evidence.
- Add PostgreSQL plan-snapshot and message tables through a second Alembic migration.
- Add `POST /v1/conversations/{conversation_id}/messages` with a bounded content field and stable
  ownership-safe errors.
- Prefer a deterministic explanation formatter for this first slice, establishing the grounding and
  missing-data contract before introducing probabilistic model output. Add the SambaNova adapter as
  the following separately evaluated slice.

## Files Expected to Change

- New plan/message domain, service, and port modules
- Synthetic KDDI and PostgreSQL adapters
- FastAPI schemas, route, composition, and error translation
- Second Alembic migration and seed fixtures
- Unit, API, integration, safety, and contract tests
- README run/verification steps, architecture flow, decisions, and feature history status

## Test Strategy

- Unit: available plan produces only evidence-supported plan name, allowance, recurring charge, and
  effective date.
- Unit safety: unavailable or incomplete plan data never produces invented account facts and clearly
  states the limitation and next step.
- Unit privacy: a conversation owned by another customer is indistinguishable from a missing one.
- API: approved request/response, validation, authentication, ownership, and error contracts.
- Integration: user and assistant messages, plan snapshot, evidence reference, ownership, decimal
  JPY amount, and UTC timestamps persist correctly.
- Migration: upgrade from revision `20260826_01` creates only the approved new tables and constraints.
- Full: pytest, Ruff, strict mypy, documented local curl verification.

Tests will be written and observed failing before implementation.

## Implementation Steps

- [x] Confirm deterministic-first versus immediate SambaNova generation.
- [x] Confirm the exact message API, ownership, and unsupported-question contracts.
- [x] Add failing domain/service grounding and safety tests.
- [x] Implement the minimum domain, ports, synthetic KDDI adapter, and service.
- [x] Add failing API tests and implement the route and stable errors.
- [x] Add failing PostgreSQL/migration tests and implement persistence.
- [x] Run targeted and full verification.
- [x] Update the runbook, decision record, and living architecture flow.
- [x] Await human verification before CP-003, commit, and push.

## Open Questions

None.

## Decisions

- The endpoint remains conversation-centric and requires bearer authentication plus ownership.
- Raw model generation, if selected, cannot bypass typed plan evidence or the missing-data safety
  gate.
- This slice uses deterministic evidence-templated answers. SambaNova generation is deferred to the
  next separately evaluated slice behind the same grounding boundary.
- `POST /v1/conversations/{conversation_id}/messages` accepts trimmed Unicode `content` of 1–2,000
  characters and returns the persisted user and assistant messages with `201`.
- Assistant answers use `grounded`, `unavailable`, or `unsupported`, an explicit uncertainty flag,
  and typed plan-snapshot evidence references. Unavailable and unsupported answers are successful
  persisted exchanges rather than transport errors.
- Missing and cross-customer conversations share `404 conversation_not_found`; invalid content uses
  stable `422 invalid_message`.

## Discoveries

- The initial schema has only customers and conversations, so this slice requires a forward-only
  second migration.
- No KDDI or SambaNova adapter behavior currently exists beyond approved package boundaries.
- SQLAlchemy mapper ordering without relationships did not reliably insert evidence after its parent
  messages; the repository now explicitly flushes snapshots and messages before evidence rows.
- Local development upgraded forward from `20260826_01` to `20260826_02` without resetting existing
  conversations.

## Progress

Implementation, automated verification, Codex manual verification, and the required human
run-through are complete. CP-003 is recorded and this plan is ready for archival.

## Verification

Completed commands:

```bash
uv sync --frozen
TEST_DATABASE_URL=postgresql+psycopg://bowenl@127.0.0.1:55432/telecom_agent_test uv run pytest
uv run ruff check .
uv run mypy src tests
```

## Result

Implemented deterministic grounded current-plan messages with customer ownership, typed synthetic
KDDI plan data, explicit unavailable/unsupported answers, atomic PostgreSQL message/snapshot/evidence
persistence, stable API errors, and a forward-only second migration.

Verification on 2026-08-26:

- Full pytest with isolated PostgreSQL: 37 passed.
- Ruff: passed.
- Strict mypy: passed across 45 source files.
- Codex manual verification: migration upgraded the existing development database; grounded and
  unsupported message requests returned the approved `201` contracts; graceful shutdown passed.
- Human verification: passed on 2026-08-26. The human reproduced both responses and confirmed their
  deterministic mock-data origin before approving the checkpoint.
