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
