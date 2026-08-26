# Building a Grounded Telecom Agent

## 2026-08-26 — Letting an LLM speak without letting it invent the account

The first current-plan feature deliberately used a fixed sentence template. That was useful: it
proved authentication, conversation ownership, typed KDDI mock data, PostgreSQL snapshots, and
evidence links before probabilistic text entered the system.

The next slice puts SambaNova's `MiniMax-M3` behind that established boundary. The model does not
retrieve the customer or decide which account facts are true. The application first authenticates
the synthetic customer, verifies conversation ownership, classifies the supported intent, and
retrieves a typed plan. It then gives the model only four canonical display values and the question.

Generated wording is treated as untrusted. Every canonical value must survive exactly, output must
be bounded, and no new numeric claim may appear. If the provider fails or the answer violates that
contract, the raw generation is discarded and the conversation records a clear unavailable answer.
There is no hidden fallback that could make a failed model call look successful.

This division of responsibility is the central architectural lesson: deterministic code decides
what is known and safe to disclose; the language model helps express it. Offline tests cover the
boundary with a fake, while an explicit live smoke test checks the real endpoint. The upcoming
evaluation harness will measure answer quality and adversarial corner cases rather than confusing
network availability with correctness.

The first live smoke test completed that loop: the configured endpoint accepted `MiniMax-M3`, and
the resulting answer passed the guard with the correct plan name, allowance, charge, effective
date, and evidence reference. That is a development proof of wiring—not yet a broad quality score.

The intended role of MiniMax-M3 is deliberately narrow: it is the conversational language layer,
not the account database or policy engine. Today it words a current-plan explanation only after the
backend has established which facts are permitted. Later features can reuse the same pattern, but
each one must first define its own typed data, deterministic safety rules, and evaluation cases.

Manual verification follows the real production composition rather than the offline fake: load the
local environment, start the API, create a synthetic conversation, and ask for the current plan. A
grounded response with all canonical values and snapshot evidence confirms the complete live path.
The human-run verification produced exactly that result, completing this development slice.
