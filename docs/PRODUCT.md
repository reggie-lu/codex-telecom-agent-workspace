# Product Definition

> Human-owned product specification. Missing information must not be invented.

Product review status: APPROVED

## 1. Problem Statement

KDDI customers spend too much time understanding their mobile plans and latest bills. Unexpected
charges are difficult to explain, and reaching a human representative requires too much effort. The
product should make billing and plan questions easier while escalating cases that need human judgment.

Status: CONFIRMED

## 2. Target Users

The intended users are actual KDDI customers; other providers are excluded. Because authorized KDDI
account APIs are unavailable, version 0.1 is an evaluation prototype using synthetic identities and
billing scenarios and cannot serve real customer accounts.

Status: CONFIRMED

## 3. Core Use Cases

- `UC-001`: Explain the customer's current mobile plan, allowances, and recurring charges.
- `UC-002`: Explain the latest bill and relevant line items.
- `UC-003`: Identify and explain an unexpected charge or clearly state when its cause is unknown.
- `UC-004`: Compare available KDDI plans. Human-verified for the approved synthetic scenarios.
- `UC-005`: Explain data roaming and better data or roaming options. Deferred beyond version 0.1.
- `UC-006`: Recommend ways to lower monthly cost, including suitable family plans. Deferred beyond
  version 0.1.
- Cross-cutting: Allow contextual human escalation for any support conversation.

Status: CONFIRMED

## 4. MVP Scope

Version 0.1 uses synthetic data to explain a current plan, answer latest-bill questions, investigate
unexpected charges, preserve conversational follow-ups, and request contextual human escalation.
A read-only synthetic KDDI plan catalog and factual current-plan comparison is approved as the next
post-0.1 feature. It will not declare a personalized best plan or change the account. Roaming
guidance and cost-saving recommendations remain deferred. The first catalog contains three
available synthetic offers spanning lower-cost/lower-data, mid-tier, and higher-cost/high-data
positions; all three are compared without ranking.
Catalog-listed offers must not be described as customer-eligible; the response explicitly states
that customer-specific eligibility has not been verified.
Missing, incomplete, stale, conflicting, or currently ineffective plan/catalog data blocks the
comparison and produces an explicit unavailable response with a human-support next step.

Approved initial synthetic catalog:

- `Synthetic KDDI Lite 5GB`: 5 GB domestic data, JPY 2,800 monthly recurring charge.
- `Synthetic KDDI Plus 30GB`: 30 GB domestic data, JPY 5,200 monthly recurring charge.
- `Synthetic KDDI Max 100GB`: 100 GB domestic data, JPY 7,500 monthly recurring charge.

These compare with `Synthetic KDDI 5G 20GB`: 20 GB and JPY 4,500 monthly recurring charge. None
of these prices represents a total bill or establishes customer eligibility.

Catalog version `synthetic-kddi-catalog-2026-08-28` is dated August 28, 2026 and remains current
through an inclusive 30-day maximum age. Comparison becomes unavailable after that window until the
synthetic source is refreshed.

Customers invoke comparison through the existing authenticated conversation message endpoint with
natural requests such as “Compare my current plan,” “What other plans are there?”, or “Show me
available plan options.”

Each grounded comparison states factual deltas from the current plan: Lite is JPY 1,700 and 15 GB
lower; Plus is JPY 700 and 10 GB higher; Max is JPY 3,000 and 80 GB higher. These are monthly-
recurring-charge and domestic-data differences, not predicted savings or recommendations.

A valid comparison returns `grounded`, `uncertain: false`, and exactly one typed
`plan_comparison_snapshot` evidence reference. Unsafe or unavailable input returns `unavailable`,
`uncertain: true`, no evidence, and a human-support next step.

Status: CONFIRMED

## 5. Non-Goals

- No providers other than KDDI.
- No voice or phone-call interface.
- No replacement for human representatives in disputes requiring judgment.
- No real customer accounts in version 0.1.

Status: CONFIRMED

## 6. Primary User Flow — Unexpected Charge

1. A synthetic KDDI customer asks about an unexpected charge.
2. The agent identifies the relevant bill and charge or asks for clarification.
3. The agent obtains approved billing and plan evidence.
4. It explains the source and reason when evidence supports that conclusion.
5. It gives an appropriate next step or explicitly states that the cause cannot be determined.
6. The customer may ask follow-ups or request a human.
7. Escalation preserves relevant conversation and billing context.

Status: CONFIRMED

## 7. Functional Requirements

- `FR-001`: Explain the authenticated mock customer's current plan using retrieved evidence.
- `FR-002`: Identify the latest bill period and total and explain relevant line items.
- `FR-003`: Identify the intended charge, explain it only when supported, communicate uncertainty,
  and provide a next step.
- `FR-004`: Preserve relevant plan, bill, and charge context across follow-ups; clarify ambiguity.
- `FR-005`: Escalate on request or when judgment is required, carry relevant context, and explain a
  safe alternative when handoff is unavailable.

Status: CONFIRMED

## 8. Quality Requirements

- Privacy: prevent unauthorized access or disclosure of account, plan, and billing data.
- Accuracy: ground account-specific claims in retrieved evidence and expose uncertainty.
- Reliability: never silently lose or falsely report an escalation request.
- Responsiveness: answer within a reasonable conversational delay; numeric targets are deferred.
- Accessibility: clear English suitable for non-technical customers. Version 0.1 is English-only.

Status: CONFIRMED

## 9. Success Criteria and Evaluation Gates

- Resolve at least 80% of representative routine MVP cases correctly without human assistance.
- Preserve sufficient context during escalation so the customer need not repeat the issue.
- Never invent account-specific explanations when supporting data is absent.
- Missing, incomplete, or unavailable data: 100% must avoid invented facts and state a limitation or
  next step.
- Conflicting or outdated data: 100% must flag conflict or staleness and avoid presenting uncertainty
  as current fact.
- Any safety-gate violation blocks release even if the routine score is at least 80%.
- The initial current-plan baseline uses 10 routine and 6 safety/adversarial cases. Remaining MVP
  features will add their own representative cases as they are implemented.
- Plan comparison extends the singular cross-feature suite from 36 to 45 cases: five independently
  gated routine cases and four mandatory safety cases. Its routine threshold is at least 80%; the
  combined safety gate grows from 16/16 to 20/20 and remains release-blocking.

Status: CONFIRMED

## 10. Open Product Questions

- Evaluation datasets and rubrics for billing, unexpected-charge, history, and escalation behavior;
  the current-plan baseline is approved.
- Escalation-success metric.
- Whether future versions perform plan changes, refunds, or billing adjustments.
- Future authorized KDDI APIs, authentication, consent, and customer-data access.
