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

The next useful increment is measurement rather than another feature. A compact current-plan eval
set can establish a repeatable baseline for routine phrasings and release-blocking safety cases.
Deterministic graders should own facts, evidence, uncertainty, and prohibited claims; live
MiniMax-M3 execution remains an explicit opt-in layer rather than a dependency of normal tests.

The baseline immediately paid for itself. Natural punctuation broke the original intent matcher,
and a small normalization fix moved offline scoring to the approved 80% routine and 100% safety
gates. Two paraphrase misses remain visible. The first live run then found another case the manual
happy path did not: a recurring-charge response was safely rejected, leaving live routine quality at
70% while safety stayed perfect. The gate failed openly, providing the next concrete improvement
target without weakening the dataset.

The human-run live evaluation reproduced all three failures and the split aggregate scores. That
agreement between independent runs is the checkpoint: the measurement system works, while the
product remains correctly blocked from release until routine quality improves.

The remediation kept that measurement contract fixed. Two narrow intent patterns taught the
orchestrator to recognize natural questions about monthly data and the customer's mobile service.
The recurring-charge failure required a different kind of investigation: the model had answered
the question directly with only the price. That was factually correct but incomplete relative to
the evidence contract, so the guard was right to discard it.

Instead of making the guard more permissive, the prompt now tells MiniMax-M3 to state all four
canonical values exactly once even when only one is requested. With the dataset, numeric checks,
and gates unchanged, both offline and live runs reached 10/10 routine and 6/6 safety. The result is
a useful pattern for future billing work: diagnose which boundary failed, correct that boundary,
and prove the improvement against the same corner cases before expanding scope.

The independent human run produced the same perfect routine and safety scores. That closes the
remediation as a human-verified development checkpoint and gives the next feature a clean,
repeatable current-plan foundation.

The next logical capability is the latest bill. It is deliberately placed before unexpected-charge
investigation: the agent first needs a trustworthy bill period, total, and set of line items before
it can reason about which charge surprised the customer. Treating that retrieval and explanation as
its own vertical slice keeps the evidence model observable and gives missing billing data a safe,
testable behavior before diagnostic logic is introduced.

That latest-bill boundary is now approved. Implementation will continue through the existing
conversation endpoint and introduce no direct public bill resource. Before code can claim any
amount or billing period, the synthetic fixture itself needs explicit human approval; grounding
starts with deciding exactly which facts are allowed to be true.

The approved bill now travels through that boundary as typed evidence. Its four ordered line items
sum exactly to JPY 6,930 before the service is allowed to compose an answer. The snapshot, items,
messages, and evidence link are written in one PostgreSQL transaction; absent or inconsistent data
produces a limitation without leaking any remembered amount. MiniMax-M3 is intentionally absent
from this path, keeping the first billing milestone about factual integrity rather than phrasing.

The intent boundary also stays honest. “What is my latest bill?” receives the summary, while “Why
is my bill higher?” remains unsupported because answering it requires the next charge-investigation
slice. That distinction prevents a list of charges from masquerading as an explanation.

The human-run API verification returned the same period, total, four line items, grounded status,
and bill-snapshot evidence. The latest-bill foundation is therefore complete as a development
checkpoint; the roaming item is available for the next slice to investigate without yet claiming
why it appeared.
