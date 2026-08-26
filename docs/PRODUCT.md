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
- `UC-004`: Compare available KDDI plans. Deferred beyond version 0.1.
- `UC-005`: Explain data roaming and better data or roaming options. Deferred beyond version 0.1.
- `UC-006`: Recommend ways to lower monthly cost, including suitable family plans. Deferred beyond
  version 0.1.
- Cross-cutting: Allow contextual human escalation for any support conversation.

Status: CONFIRMED

## 4. MVP Scope

Version 0.1 uses synthetic data to explain a current plan, answer latest-bill questions, investigate
unexpected charges, preserve conversational follow-ups, and request contextual human escalation.
Plan comparison, roaming guidance, and cost-saving recommendations are deferred.

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

Status: CONFIRMED

## 10. Open Product Questions

- Evaluation datasets and rubrics for billing, unexpected-charge, history, and escalation behavior;
  the current-plan baseline is approved.
- Escalation-success metric.
- Whether future versions perform plan changes, refunds, or billing adjustments.
- Future authorized KDDI APIs, authentication, consent, and customer-data access.
