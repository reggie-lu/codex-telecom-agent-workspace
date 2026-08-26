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
