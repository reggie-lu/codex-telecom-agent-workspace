# SambaNova-Grounded Current-Plan Generation

## Goal

Use the approved SambaNova OpenAI-compatible endpoint and `MiniMax-M3` to word supported
current-plan answers, while preserving the existing typed evidence boundary, safe missing-data
behavior, atomic persistence, and deterministic ordinary tests.

## Requirement References

- D-006, D-010, D-015, D-016, D-017, D-019, and D-022
- The current-plan safety and accuracy gates in `docs/PRODUCT.md`
- The SambaNova model boundary in `docs/ARCHITECTURE.md`

## Non-Goals

- Billing, charge, roaming, savings, plan comparison, or escalation behavior.
- Conversation-history prompting or retrieval-augmented generation.
- Streaming, tools, JSON mode, or provider/model fallback.
- Real KDDI data, production authentication, containers, or deployment.
- Claiming that `MiniMax-M3` is publicly listed by SambaNova before a live endpoint check proves it.

## Current State

Current-plan facts come from the typed synthetic KDDI adapter and are persisted as a snapshot.
The service currently formats the grounded answer deterministically. The OpenAI SDK and SambaNova
environment placeholders exist, but no model port, adapter, runtime validation, retry behavior, or
live smoke procedure exists.

## Proposed Design

- Add a narrow synchronous current-plan answer-generator port.
- Pass the model only the user's question and the four approved display facts from the newly
  created plan snapshot; do not send customer, conversation, message, or evidence identifiers.
- Use the OpenAI SDK chat-completions surface with the configured SambaNova base URL, exact model
  name, a 30-second timeout, SDK retries disabled, temperature zero, and one adapter-owned retry for
  timeout, rate-limit, and server failures.
- Do not retry authentication, permission, not-found, conflict, validation, or other client errors.
- Require generated text to contain each canonical display value and reject extra numeric claims,
  blank output, or overlong output before persistence.
- On terminal provider or validation failure, atomically persist the user's message and a safe
  `unavailable` assistant response without persisting rejected model text.
- Keep unsupported and missing-plan behavior deterministic and model-free.
- Use a deterministic fake generator in ordinary tests. Provide an explicit opt-in live smoke
  command rather than making network calls in pytest.

## Files Expected to Change

- `src/telecom_agent/ports/messages.py`
- `src/telecom_agent/services/send_current_plan_message.py`
- `src/telecom_agent/adapters/sambanova/`
- API composition and CLI runtime configuration
- Focused unit, adapter, API, integration, and CLI tests
- `README.md`, `docs/ARCHITECTURE.md`, and `docs/DECISIONS.md`
- `learning.md` and `blog.md`

## Test Strategy

- Service: available typed data calls the generator once and persists accepted grounded text.
- Service safety: terminal provider failure or rejected output persists a safe unavailable exchange;
  unsupported and missing-plan requests never call the generator.
- Adapter: exact client configuration and prompt payload; one retry only for approved transient
  failures; no retry for client/auth failures; empty responses become terminal failures.
- API: preserve the existing response schema and grounding evidence contract with a fake generator.
- CLI: require all three SambaNova settings for `serve` without printing their values.
- Integration: production composition can use a deterministic injected generator so PostgreSQL
  coverage remains offline.
- Full: PostgreSQL-backed pytest, Ruff, strict mypy, and an opt-in live smoke request.

## Implementation Steps

- [x] Confirm official OpenAI and SambaNova chat-completions compatibility guidance.
- [x] Record the agreed architecture boundary and execution plan.
- [x] Add failing service and adapter tests.
- [x] Implement the model port, grounding guard, and SambaNova adapter.
- [x] Wire validated runtime configuration through CLI and composition.
- [x] Add the opt-in live smoke command and human runbook.
- [x] Run targeted and full automated verification.
- [x] Update durable decisions, learning notes, blog notes, and architecture flow.
- [x] Await human verification before checkpoint commit and push.

## Open Questions

None. The exact `MiniMax-M3` availability will be tested against the configured endpoint; failure
will be reported without substituting a different model.

## Decisions

- Use 30 seconds per attempt and at most two total attempts for approved transient failures.
- Preserve the current public message schema for this slice; provider details remain runtime
  configuration rather than customer-facing response fields.
- Model output is untrusted until the service-level grounding guard accepts it.
- A rejected or unavailable generation is a safe unavailable answer, not a deterministic grounded
  fallback, so the application never hides a failed model call behind mock wording.

## Discoveries

- OpenAI Python SDK 3.3.1 is installed and supports custom `base_url`, timeout, and `max_retries`.
- SambaNova documents OpenAI-client chat completions with `base_url`, `api_key`, `model`, and
  `messages`.
- SambaNova's public model documentation inspected on 2026-08-26 does not clearly list
  `MiniMax-M3`; runtime availability remains unverified.
- The configured SambaNova endpoint accepted `MiniMax-M3` during the live smoke test and returned a
  response that passed the grounding guard.

## Progress

Implementation, Codex verification, and the required human run-through are complete. The plan is
archived for the CP-004 development checkpoint.

## Verification

Completed on 2026-08-26:

```bash
.venv/bin/pytest tests/unit tests/api tests/contract
TEST_DATABASE_URL=postgresql+psycopg://bowenl@127.0.0.1:55432/telecom_agent_test .venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy src tests
```

- 45 offline unit/API/contract tests passed.
- 53 full tests passed with isolated PostgreSQL.
- Ruff passed.
- Strict mypy passed across 48 source files.
- Live localhost smoke passed: health `200`, conversation `201`, and the configured `MiniMax-M3`
  current-plan request returned `201 grounded`, `uncertain: false`, all four canonical values, and
  one plan-snapshot evidence reference. Graceful shutdown passed.

## Result

Implemented the guarded SambaNova current-plan generation boundary, exact runtime configuration,
bounded retry and timeout, safe terminal failure, offline fake, documentation, and live smoke
procedure. Human verification passed on 2026-08-26 with a grounded `MiniMax-M3` answer containing
all four canonical values and one typed plan-snapshot evidence reference.
