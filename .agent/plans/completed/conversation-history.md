# Conversation-history retrieval

## Goal

Implement authenticated `GET /v1/conversations/{conversation_id}` so Synthetic Alice can retrieve
the complete ordered support conversation, including assistant status, uncertainty, and typed
evidence references, establishing the context source required by later human escalation.

## Requirement References

- `docs/PRODUCT.md`: MVP conversation follow-ups, `FR-004`, privacy, and contextual escalation.
- `docs/ARCHITECTURE.md`: approved conversation-history route, customer ownership, persisted
  messages and evidence, and dependency direction.
- `docs/DECISIONS.md`: conversation-centric API, synthetic authentication, PostgreSQL persistence,
  and explicit types.
- Human request on 2026-08-26 to proceed to the next MVP step after unexpected-charge verification.

## Non-Goals

- Creating or updating escalation records.
- Sending history to MiniMax-M3 or implementing model-aware follow-up resolution.
- Returning raw plan, bill, or charge snapshot bodies; messages retain typed evidence references.
- Pagination, filtering, search, deletion, retention changes, or a frontend.
- Real KDDI accounts or production authorization.

## Current State

The authenticated API reconstructs customer-owned conversations from PostgreSQL with ordered
messages and typed evidence references. The next approved dependency, contextual human escalation,
remains unimplemented.

## Proposed Design

Add a read-only conversation-history domain view and repository port. The PostgreSQL adapter loads
the customer-owned conversation, all messages ordered by `created_at` with a deterministic ID
tiebreaker, and each assistant message's plan, bill, and charge evidence references. The service
uses the existing privacy-preserving not-found behavior. FastAPI returns conversation `id`, `status`,
`created_at`, and the ordered message list. For the focused synthetic MVP, return the complete
history in one response and defer pagination.

## Files Expected to Change

- Conversation/message domain views and repository ports
- PostgreSQL read adapter and FastAPI composition
- API schemas and route
- Unit, API, and PostgreSQL integration tests
- README and durable project documentation
- `learning.md` and `blog.md`

## Test Strategy

Use TDD for empty history, chronological mixed-message history, all evidence types, authentication,
cross-customer privacy, stable not-found behavior, and read-only persistence. Preserve all message,
migration, and evaluation regressions.

## Implementation Steps

1. Approve the complete-history response contract and pagination deferral.
2. Add failing service and API contract tests.
3. Implement the read model, port, service, and PostgreSQL adapter.
4. Compose and expose the authenticated GET route.
5. Update runbooks, decisions, architecture flow, learning notes, and blog.
6. Run automated and localhost verification, then request independent human verification.

## Open Questions

None.

## Decisions

- Reuse `404 conversation_not_found` for both missing and cross-customer conversations.
- Preserve existing message and evidence shapes rather than embedding snapshot bodies.
- Sort by UTC creation time and UUID as a deterministic tiebreaker.
- Return complete history without pagination for version 0.1.

## Discoveries

- All three evidence link types are already persisted separately, so the read adapter must merge
  them without losing message order or exposing another customer's records.

## Progress

- [x] Identified conversation history as the next escalation dependency.
- [x] Recorded the proposed architecture boundary.
- [x] Approved the response and pagination contract.
- [x] Added failing behavioral tests.
- [x] Implemented history retrieval.
- [x] Updated runbooks and durable documentation.
- [x] Completed automated verification.
- [x] Completed human verification.

## Verification

The full suite passes 92/92 with
`TEST_DATABASE_URL=postgresql+psycopg://bowenl@127.0.0.1:55432/telecom_agent_test uv run pytest`.
`uv run mypy src tests` and `uv run ruff check .` pass. The unchanged offline evaluation passes
10/10 routine cases, 6/6 safety cases, and the release gate. An existing process on port 8000 was
confirmed healthy but had loaded the prior checkpoint: the new path returned framework-level 404.
It was not terminated because it is human-owned. After restarting, the human independently
retrieved conversation `f384cd7f-9707-4f88-ba3f-2dbe75bb15cb`: the API returned `200 OK`, the
correct `open` metadata, and an empty `messages` list for that newly created empty conversation.

## Result

Completed and independently human-verified on 2026-08-26. The history read boundary is ready to
supply context to the later escalation slice.
