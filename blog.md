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

That investigation now begins with a deliberate distinction: a bill is evidence that an amount was
charged, not evidence of the event that caused it. The next slice needs a second typed record before
it can connect the JPY 1,200 roaming line item to a date, place, and activation trigger. Until those
facts are explicitly approved and available, the honest answer is uncertainty rather than a
plausible story.

The implementation now joins those two evidence streams without hiding disagreement. A confirmed
event must match the bill's stable item code, description, amount, currency, and period before the
agent may say that United States mobile-data use activated the synthetic day pass. If the event is
missing, it identifies the billed item but says the cause is unknown. If records are stale or
different, it preserves both snapshots and names the conflict instead of choosing the convenient
version.

This is still not dispute automation. A customer who does not recognize the usage is directed to
human support, and the agent states that it cannot decide the dispute. Refunds and adjustments
remain unsupported, keeping factual investigation separate from judgment and account action.

The independent human run confirmed that boundary in the actual API response: the cause was stated
only alongside bill and charge snapshots, uncertainty was false for the matching records, and the
answer ended with human support rather than a verdict. That completes the focused investigation as
a development checkpoint.

The next step is less glamorous but structurally important: reading the conversation back. Human
escalation cannot be contextual if the system cannot reconstruct what was asked, what was answered,
and which plan, bill, or charge evidence supported each response. A customer-owned chronological
history therefore comes before the handoff workflow, turning stored rows into a reliable context
boundary rather than an implementation detail.

That read boundary is now implemented. One authenticated request reconstructs the conversation in
a stable order and restores the evidence references attached to each assistant answer. The database
query is customer-scoped from the start, so an unknown identifier and another customer's identifier
look identical at the API boundary.

For this focused prototype, the response is intentionally complete rather than paginated. It keeps
the upcoming escalation context easy to inspect while the dataset is small, without prematurely
locking in cursor behavior. Snapshot bodies remain behind their typed references; the history tells
us what supported an answer without turning one endpoint into a duplicate account-data API.

The first independent read used a newly created conversation and returned an empty message list.
That modest result exercises an important distinction: an owned conversation with no activity is a
successful resource, while a missing or differently owned identifier remains hidden behind the
same not-found response. Histories containing every evidence type are covered by the PostgreSQL
integration test; future manual sessions can populate the conversation before retrieving it.

With history in place, the project can finally cross from self-service explanation into an actual
handoff workflow. The next slice will package the customer's conversation and its evidence into a
durable mock escalation, then let the customer check what happened to that request.

The difficult part is not drawing a ticket-shaped table. It is preserving truthful state across
the boundary: a request that fails must still be visible as failed, while a request accepted by the
mock must not lose the context that justified it. The first decision is therefore when the system
is allowed to create that durable request—only after explicit customer action, or automatically
when the agent reaches a judgment boundary.

The answer is explicit action. Reaching a limit in automated support can justify recommending a
human, but it does not establish permission to open a case. Keeping those events separate makes the
handoff auditable and prevents the system from surprising customers with tickets they did not ask
for.

Explicit consent now has a concrete payload: a short reason written by the customer. It records the
purpose of the handoff without forcing them to paste their history again, because the context model
already carries the messages and evidence that led to the request.

The workflow also separates durable receipt from provider acceptance. It writes `requested` first,
then lets the mock move the record to `queued` or `failed`. Both outcomes are real created
resources; the status and retry guidance tell the customer what actually happened instead of
turning a provider failure into either a false success or a vanished request.

The workflow will also refuse a second active ticket for the same conversation. That policy belongs
in PostgreSQL as well as application code: two nearly simultaneous clicks should not bypass a
friendly preflight check. Once a request is failed or resolved, the customer is free to try again.

The submitted context will be a snapshot, not a live view. That choice matters as soon as the
customer continues chatting: a later message should not retroactively appear in a ticket that was
already handed off. The JSONB payload remains typed in the domain and contains only conversation
content and evidence references—never credentials or duplicated account snapshots.

Customers checking the handoff will see a deliberately small resource: what they requested, its
current state, timestamps, and any next step. The larger context is for the mock representative,
not a second API surface for replaying account conversations. Ownership checks make an unknown ID
and another customer's ID indistinguishable.

The local runtime will follow the happy handoff path consistently, accepting valid requests into
the queue. Failure remains fully testable by replacing the mock adapter in the automated suite;
there is no secret phrase a customer can type to change infrastructure behavior. That keeps test
control where it belongs and leaves customer language as data.

The resulting implementation makes the reliability promise visible in storage. It writes the
request before crossing the mock boundary, records acceptance as queued, and converts both explicit
rejection and provider unavailability into a failed resource with a retry instruction. A database
index prevents two active tickets even under concurrent creation attempts.

The handoff itself contains a frozen copy of the ordered conversation and evidence references. The
customer-facing resource stays small, but the mock representative receives enough context to avoid
asking the customer to begin again. Migration, API, lifecycle, failure, privacy, duplicate, and
context-persistence behavior are now exercised together in the PostgreSQL suite.

The independent localhost run completed the loop. The customer-created handoff was retrieved by its
new ID with the original conversation, reason, queued status, and UTC timestamps intact. Because
the mock accepted it, the next step was correctly null rather than displaying misleading retry
guidance. Contextual human escalation is now a human-verified development capability, while actual
KDDI representative delivery remains deliberately outside the prototype.

The focused MVP has reached an important transition: every promised path now exists, but the
measurement story is uneven. Current-plan support has a versioned release gate; billing,
investigation, history, and handoff still rely on ordinary tests. Those tests prove implementation
contracts, but they do not yet summarize whether the customer journey survives representative and
adversarial cases as a product.

The next recommended increment is therefore evaluation rather than another feature. A deterministic
cross-feature baseline can make missing data, conflicting evidence, customer isolation, duplicate
tickets, and failed handoffs visible as release-blocking outcomes before the project expands into
deferred plan comparison, roaming options, or savings advice.

That measurement slice is now approved. It will reuse the real public boundaries with deterministic
fixtures, keeping model variability out of paths whose wording and state changes are already
rule-based. Before choosing case counts, the project must decide whether routine success is one
pooled number or a promise each completed feature must meet independently.

The answer is independent promises. Bill explanation, charge investigation, history, and
escalation must each clear 80%; safety across them must remain perfect. The overall result fails as
soon as one feature or one safety case fails, making a green gate evidence of balanced MVP quality
rather than a favorable average.

The first baseline will use 36 cases, balanced evenly across the four features. Each gets five
routine opportunities and four safety challenges. The symmetry is intentional: it makes the 80%
line easy to interpret and prevents the newer history and escalation paths from receiving token
coverage beside the more familiar billing flows.

The scenario catalog is now fixed. It mixes natural billing and charge requests with stateful
history and handoff checks, then gives each feature four ways to fail safely. Empty-but-valid
resources, missing data, contradictory evidence, privacy boundaries, duplicate tickets, and failed
providers are distinct situations in the dataset rather than variations hidden inside one test.

The command contract is equally strict: one offline invocation will always mean the full 36-case
gate. The user's first attempt naturally failed because the module had not yet been written—a useful
reminder that an approved interface and an implemented interface are different milestones. That
exact command is now the TDD target.

The first run immediately justified the work. History and escalation were perfect, and all sixteen
safety cases passed, but billing and charge investigation each recognized only three of five natural
requests. “Recent invoice,” “billing period,” direct roaming-charge language, and unrecognized usage
now exist as durable regression targets. Because features are gated independently, the stronger
paths cannot make the overall result look healthy; the release gate fails openly at 60% for both
affected features.

The independent run matched the development baseline case for case. That is the checkpoint's real
success: not a green release, but a trustworthy red one. Four specific language gaps are now
visible, safety remains perfect, and the next remediation can be judged against an unchanged
36-case contract rather than intuition.
