# Learning Notes

## 2026-08-26 — Guarding model output with typed evidence

- Account facts still originate from the synthetic KDDI adapter, not from MiniMax-M3.
- The model receives only the user's question and canonical plan display values; internal customer,
  conversation, message, snapshot, and evidence identifiers stay outside the prompt.
- A prompt is not a safety boundary by itself. Generated text is checked before persistence for all
  required values, length, and unexpected numeric claims.
- Unsupported questions and missing plan data should stop before the model call. This makes the
  missing-data safety behavior deterministic and avoids unnecessary provider usage.
- OpenAI SDK retries are disabled so the application owns a visible upper bound: one initial call
  and one retry for a timeout, rate limit, or server error.
- A successful offline test proves orchestration, not live model availability or answer quality.
  The live API request and later evaluation suite remain separate evidence.
- SambaNova's public documentation confirms OpenAI-compatible chat completions, but the inspected
  public model list did not clearly confirm `MiniMax-M3`. The configured endpoint is the authority;
  the application must fail safely rather than substitute a model.
- The 2026-08-26 live smoke request confirmed that the configured endpoint accepts `MiniMax-M3`;
  the returned wording passed the canonical-value and numeric-claim guard.

## 2026-08-26 — Confirmed MiniMax-M3 responsibility

- MiniMax-M3 is the natural-language response layer for supported, already-grounded customer-service
  use cases.
- It does not retrieve or create customer facts, determine conversation ownership, or replace the
  typed KDDI adapter and application safety rules.
- The current implementation uses it only to word an explanation of an available current plan.
  Billing, charge analysis, roaming, savings, comparison, and escalation remain future slices.

## 2026-08-26 — Manual MiniMax-M3 verification

- Load the untracked `.env`, start `telecom-agent serve`, create a fresh synthetic conversation,
  and submit a current-plan question.
- A successful live call returns `grounded`, `uncertain: false`, all four canonical plan values,
  and one `plan_snapshot` evidence reference.
- An unavailable response means the provider call or output guard failed safely; it must not be
  mistaken for a successful live-model verification.
- Human verification passed with `grounded`, `uncertain: false`, all four expected plan values, and
  one `plan_snapshot` evidence reference.

## 2026-08-26 — Recommended next slice

- Establish a current-plan evaluation baseline before adding billing behavior.
- Keep ordinary scoring deterministic: required facts, evidence, answer status, uncertainty, and
  prohibited claims can be checked without introducing a second judge model.
- Keep real MiniMax-M3 runs opt-in and report routine quality separately from release-blocking
  safety groups.
- Proposed initial dataset: 10 routine phrasings and 6 safety/adversarial cases covering missing
  data, unsupported intent, prompt injection, and extra-claim rejection.

## 2026-08-26 — First evaluation baseline

- The first offline run exposed a punctuation bug: `plan.` and `plan!` were not recognized. Keeping
  the natural cases and normalizing punctuation raised routine quality from 60% to the required 80%
  and safety from 66.7% to 100%.
- Two routine paraphrases remain intentionally failing because the keyword matcher does not
  recognize natural requests for monthly data or mobile service. They are now explicit regression
  targets rather than hidden limitations.
- The first live MiniMax-M3 run scored 70% routine and 100% safety. One additional recurring-charge
  answer was safely rejected by the output guard, so the live release gate failed as designed.
- Prompt-injection safety accepts either correct grounded content or a safe unavailable response;
  requiring a grounded response would incorrectly classify safe refusal as unsafe.
- Human verification reproduced the same live results: 7/10 routine, 6/6 safety, and a failed
  release gate. Reproducibility confirms the evaluator is suitable for the next remediation slice.

## 2026-08-26 — Focused current-plan quality remediation

- Preserve failing evaluation cases as regression tests; do not rewrite the dataset to make a
  score improve. Adding the exact `how much data` and `mobile service` intent patterns moved the
  unchanged offline routine score from 8/10 to 10/10.
- Inspect the rejected generation before changing a guard. For the recurring-charge case,
  MiniMax-M3 returned only `JPY 4,500`; it did not invent a claim. The guard correctly rejected the
  answer because the evidence contract requires all four canonical values.
- The smallest safe correction was prompt-level: explicitly require all four values exactly once
  even when the customer asks about only one. The numeric guard and adversarial cases did not need
  to be relaxed.
- The unchanged live evaluation then passed 10/10 routine and 6/6 safety. This is automated
  development evidence until the human independently reproduces it.
- Independent human verification reproduced 10/10 routine, 6/6 safety, and a passing release gate;
  the remediation can now be recorded as a development checkpoint.

## 2026-08-26 — Selecting the next MVP slice

- Latest-bill explanation (`UC-002`) is the next dependency in the approved MVP: unexpected-charge
  investigation needs a bill and its line items before it can identify or explain a specific charge.
- Keep latest-bill retrieval separate from unexpected-charge reasoning so typed billing evidence,
  persistence, ownership, and missing-data behavior can be verified before adding diagnosis.
- The next human decision is whether to approve that narrow latest-bill summary as its own vertical
  slice or combine it with unexpected-charge investigation.

## 2026-08-26 — Latest-bill slice approved

- The human approved latest-bill summary as a focused vertical slice before unexpected-charge
  diagnosis.
- Exact synthetic billing facts must be approved before tests or implementation encode them;
  examples are not requirements.
- Deterministic bill wording is the recommended first boundary, matching the earlier plan-first
  approach: establish typed retrieval, evidence, persistence, and safe absence before adding model
  variability or diagnostic reasoning.

## 2026-08-26 — Latest-bill implementation

- Reconcile the bill before creating snapshot identifiers or wording: a nonempty item set, valid
  period, nonnegative amounts, and exact decimal sum are deterministic safety prerequisites.
- A bill summary and an unexpected-charge explanation are different intents. Direct bill requests
  are supported; diagnostic language such as `why`, `higher`, or `unexpected` remains unsupported.
- SQLAlchemy did not order independent bill-snapshot and line-item mapper inserts from foreign-key
  columns alone. An explicit parent flush inside the same transaction preserves atomicity and makes
  the dependency unambiguous.
- Renaming the orchestration class to `SendSupportMessageService` keeps its responsibility accurate
  now that one conversation endpoint supports both plan and bill intents.
- The localhost smoke test returned `201 grounded`, `uncertain: false`, the exact reconciled bill,
  and one `bill_snapshot` reference after migration `20260826_03` reached head.
- Independent human verification reproduced the exact July bill, grounded status, false uncertainty,
  and typed bill evidence, completing the latest-bill development checkpoint.

## 2026-08-26 — Unexpected-charge investigation started

- A billed line item proves description and amount, not causation. Explaining `why` requires a
  separate supporting event with human-approved date, location, trigger, and service identity.
- Start with the known roaming item rather than pretending a deterministic matcher can diagnose
  every charge category.
- Missing or conflicting causal evidence must result in an uncertain limitation and next step;
  presence of the JPY 1,200 item alone is insufficient for a grounded explanation.

## 2026-08-26 — Two-source charge grounding implemented

- A causal explanation is grounded only after bill and event evidence agree on stable item code,
  description, decimal amount, currency, and event date within the billing period.
- Missing usage evidence can still safely identify the line item using bill evidence, but the
  response remains `unavailable` and uncertain about the cause.
- Stale or mismatched event records are worth persisting as evidence of the conflict; the answer
  cites both snapshots, flags the condition, and omits the activation explanation.
- Generic “this charge” language cannot identify a line item without conversation-reference
  resolution, so the deterministic service asks for a description or amount instead of guessing.
- The current-plan unsupported safety case moved from a now-supported high-bill question to a
  refund request; its counts, thresholds, and safety purpose remain unchanged.
- A localhost listener from the prior human test was still using port 8000. Do not terminate an
  unowned process automatically; document an explicit stop, migrate, and restart step so the human
  loads the new charge implementation safely.
- After restarting, the human independently reproduced the grounded explanation with both typed
  evidence references and the explicit boundary against deciding a dispute.

## 2026-08-26 — Selecting conversation history next

- Contextual escalation depends on a trustworthy conversation read model, so history retrieval
  should precede creation of escalation records.
- Persisting messages is not enough: the read adapter must restore chronological order and merge
  plan, bill, and charge evidence links while enforcing the same customer ownership boundary.
- For the small synthetic MVP, complete history is simpler and more testable than inventing page
  sizes without a volume requirement; pagination remains the one contract decision for approval.

## 2026-08-26 — Conversation-history retrieval implemented

- Ownership belongs in the history query itself. Returning no row for both absent and differently
  owned conversations avoids a separate existence check that could leak customer boundaries.
- Reconstruct message order independently from evidence loading. Bulk-loading the three evidence
  link tables avoids one query per message while preserving a deterministic message sequence.
- Evidence references are sufficient for the first handoff boundary; embedding full snapshots
  would enlarge the API contract before escalation has defined which facts it actually needs.
- Complete history is appropriate for this bounded synthetic MVP, but the deliberate lack of
  pagination is now documented rather than accidental.
- Human verification with a newly created conversation returned `200 OK` and `messages: []`. An
  empty list is positive evidence that the read route distinguishes a real empty conversation from
  the privacy-preserving not-found case.

## 2026-08-26 — Contextual escalation planning started

- Conversation history now supplies the exact context boundary that escalation needed; handoff
  should consume that read model instead of independently reconstructing messages and evidence.
- Reliability means persisting both successful and failed mock handoff attempts. A provider failure
  must never be reported as a queued request or disappear without a safe next step.
- Whether escalation is explicit or automatic affects customer consent, duplicates, and the API
  contract, so it must be approved before behavioral tests encode it.
- The approved boundary requires explicit authenticated customer action. Existing assistant wording
  remains a recommendation and cannot be mistaken for a submitted handoff.
- Requiring a bounded reason captures the customer's intent without asking them to reproduce the
  entire issue; the handoff context remains responsible for messages and evidence.
- Persisting `requested` before the mock call makes failure observable. Returning `201 failed` is
  truthful because the request record exists even though the handoff provider did not accept it.
- Treat duplicate prevention as a database invariant, not only a preflight query. A partial unique
  constraint on active states protects concurrent requests while terminal states permit retry.
- Snapshot handoff context at creation rather than reading it dynamically later. Even though
  messages are immutable, new follow-ups would otherwise change what a past escalation appears to
  have contained.
- A status endpoint needs only operational state and guidance. Keeping handoff context internal
  reduces repeated disclosure of conversation and billing content through another public route.
- Failure simulation belongs at the adapter boundary. Special reason strings would mix test
  controls with customer data and risk turning legitimate text into unexpected behavior.

## 2026-08-26 — Contextual escalation implemented

- The reliability sequence is intentionally two transactions: persist `requested`, call the mock,
  then persist `queued` or `failed`. A crash cannot erase the fact that the customer asked.
- Provider rejection and provider exceptions converge on the same durable failed state and safe
  next step; neither can bubble out after leaving an unexplained requested record.
- A partial unique PostgreSQL index enforces one active escalation while allowing a failed request
  to be retried successfully.
- JSONB preserves the immutable nested handoff payload, while domain reconstruction keeps status
  retrieval typed and customer-scoped.
- Human verification confirmed the full create-and-status loop: the accepted mock request remained
  queued with the same reason and conversation ID, and correctly omitted a retry next step.

## 2026-08-26 — Selecting post-MVP evaluation next

- The focused MVP now has implemented paths for plan, bill, charge investigation, history, and
  escalation, but only current-plan behavior has a versioned release-blocking evaluation dataset.
- Expanding features before measuring the other completed paths would leave the most important
  corner cases—missing data, conflicting evidence, privacy, duplicate handoffs, and failed
  handoffs—covered only by implementation tests rather than product-level gates.
- The recommended next slice is a deterministic cross-feature MVP evaluation baseline, preserving
  the existing split between routine quality and 100% mandatory safety behavior.
- The human approved this evaluation slice before deferred plan comparison, roaming, or savings
  work. The first contract choice is whether an aggregate routine score may hide a weak feature.
- Per-feature 80% routine gates were approved. This makes the result diagnostically useful and
  prevents easy billing cases from masking weak history or escalation behavior.
- Five routine cases per feature make the percentage actionable: four passes meet the gate and
  three do not. Equal four-case safety allocations keep each feature visible in the mandatory set.
- The approved catalog evaluates observable customer outcomes rather than copying test names. It
  includes both empty valid states and unsafe absent/conflicting states so absence is not treated as
  one generic condition.
- The user tried the proposed singular command before implementation and correctly received
  `No module named telecom_agent.evaluation.mvp`. Treating that attempt as contract approval keeps
  the distinction clear: documentation must not present a proposed command as already available.
- The first implemented baseline found four routine intent gaps while every safety case passed:
  `recent invoice`, `billing period`, direct `roaming charge`, and unrecognized roaming usage. The
  gate correctly fails rather than averaging those weaknesses into history and escalation success.
- A fixture initially modeled two charge evidence references as two exchanges. Correcting it before
  recording the baseline kept evaluation data aligned with the real one-answer/two-evidence shape.
- Independent human execution reproduced all four failures, both 60% routine scores, both perfect
  routine scores, and 16/16 safety. That repeatability confirms the evaluator rather than the
  product behavior is ready for checkpointing.

## 2026-08-26 — Cross-feature remediation approved

- All four misses happen at deterministic intent selection, before bill or charge retrieval. The
  factual grounding paths and safety cases do not need to change.
- The approved fix is deliberately lexical and narrow: invoice/period language for bill summaries,
  and direct or unrecognized roaming language for charge investigation.
- Ambiguous `this charge` must retain higher routing precedence so expanded charge recognition does
  not convert a clarification case into a guessed explanation.

## 2026-08-26 — Cross-feature remediation implemented locally

- Four public-API regression tests failed as `unsupported` before the matcher change and passed
  afterward, confirming the failure and fix remained at intent selection.
- Adding only invoice/statement and roaming-recognition vocabulary raised bill and charge routine
  scores from 3/5 to 5/5 while history, escalation, and all 16 safety cases stayed perfect.
- The complete 118-test PostgreSQL suite, Ruff, strict mypy, and the 16-case current-plan gate also
  pass. The next evidence required is an independent human run of the unchanged MVP command.

## 2026-08-27 — Cross-feature remediation human-verified

- The independent command reproduced 20/20 routine passes across four separately gated features
  and 16/16 safety passes, confirming the local result without special flags or hidden setup.
- The comparison is valid because the 36 cases, thresholds, evidence expectations, and graders are
  unchanged from the human-verified red baseline.
- This closes the focused quality gap, but it remains a development checkpoint: real KDDI data,
  production identity, real representative delivery, and deployment remain outside the evidence.
