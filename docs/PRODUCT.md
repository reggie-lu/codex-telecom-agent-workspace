# Product Definition

> Human-owned product specification.
> Codex asks questions and organizes answers.
> Missing sections must not be invented.

Product review status: APPROVED

## 1. Problem Statement

Telecom customers spend too much time checking their mobile plans and obtaining clear answers about
their latest bills. Unexpected charges are difficult to understand, and comparing available plans
requires too much manual effort. Customers need an easier customer-service experience that can
explain billing and plan information and help them reach a human representative when automated
assistance is insufficient.

Status: CONFIRMED

## 2. Target Users

The first version is intended specifically for KDDI telecom customers. Supporting customers of
other telecom providers is outside the initial product boundary.

Version 0.1 is an evaluation prototype using synthetic KDDI customer and billing scenarios because
authorized real KDDI account APIs are not currently available. Actual KDDI customers are the
intended future users, but version 0.1 will not connect to or serve real customer accounts.

Status: CONFIRMED

## 3. Core Use Cases

### UC-001 — Understand the current mobile plan

Actor: KDDI customer
Trigger: Asks about their current mobile plan.
Desired outcome: Sees the plan's relevant terms, allowances, and charges in clear language.

### UC-002 — Understand the latest bill

Actor: KDDI customer
Trigger: Opens or asks a question about their latest bill.
Desired outcome: Receives a clear explanation of the bill and its line items.

### UC-003 — Explain an unexpected charge

Actor: KDDI customer
Trigger: Identifies a charge they do not recognize or did not expect.
Desired outcome: Understands what caused the charge and what appropriate next action is available.

### UC-004 — Compare available plans

Actor: KDDI customer
Trigger: Wants to compare their current plan with other available KDDI plans.
Desired outcome: Receives an understandable comparison relevant to their needs.

### UC-005 — Check data roaming and better data options

Actor: KDDI customer
Trigger: Wants to understand their current data-roaming availability or find a better current data
plan or roaming option.
Desired outcome: Understands available data and roaming coverage or allowances and sees relevant,
newer options that may better fit their needs.

### UC-006 — Reduce monthly mobile costs

Actor: KDDI customer
Trigger: Asks how to lower their monthly mobile cost.
Desired outcome: Receives relevant cost-saving recommendations, such as a family plan or a less
expensive suitable plan, based on their circumstances.

### Cross-cutting escalation

For any use case, the KDDI customer can request escalation to a human representative when automated
assistance is insufficient.

Status: CONFIRMED

## 4. MVP Scope

Version 0.1 must allow a KDDI customer to:

- Understand their current mobile plan (`UC-001`).
- View and ask questions about their latest bill (`UC-002`).
- Identify and understand an unexpected charge and the appropriate next action (`UC-003`).
- Request escalation to a human representative when automated assistance is insufficient.

These behaviors will be demonstrated and evaluated with synthetic KDDI customer, plan, bill,
charge, and escalation data rather than real customer accounts.

Deferred beyond version 0.1:

- Comparing available KDDI plans (`UC-004`).
- Checking data roaming and finding better data or roaming options (`UC-005`).
- Receiving personalized recommendations to reduce monthly mobile costs (`UC-006`).

Status: CONFIRMED

## 5. Non-Goals

Version 0.1 will not:

- Support telecom providers other than KDDI.
- Provide a voice or phone-call interface.
- Replace a human representative in disputes that require human judgment.

Status: CONFIRMED

## 6. Important User Flows

### Primary flow — Investigate an unexpected charge

1. The KDDI customer opens the customer-service agent and asks about an unexpected charge.
2. The agent identifies which bill and charge the customer means, asking for clarification when
   necessary.
3. The agent obtains the relevant billing and current-plan information through the approved access
   mechanism.
4. The agent explains the charge in clear language, including its source and why it appeared on the
   bill when that information is available.
5. The agent states an appropriate next action or clearly says when it cannot determine the cause.
6. The customer may ask follow-up questions or request a human representative.
7. When escalation is requested or human judgment is required, the agent transfers or prepares the
   case for a human representative with the relevant conversation and billing context.

Authentication, authorization, KDDI data access, and the exact handoff mechanism remain open
product or architecture questions.

Status: CONFIRMED

## 7. Functional Requirements

### FR-001 — Explain the current mobile plan

Requirement: The agent explains the authenticated customer's current KDDI mobile plan.

Source use case: `UC-001`

Acceptance criteria:

- The response identifies the current plan.
- Relevant terms, allowances, and recurring charges are presented in clear language.
- The agent distinguishes retrieved customer data from general explanatory information.

### FR-002 — Explain the latest bill

Requirement: The agent answers questions about the authenticated customer's latest KDDI bill.

Source use case: `UC-002`

Acceptance criteria:

- The agent identifies the bill period and total.
- Relevant bill line items can be explained.
- The response is grounded in the customer's retrieved billing information.

### FR-003 — Investigate an unexpected charge

Requirement: The agent helps the customer identify and understand an unexpected charge.

Source use case: `UC-003`

Acceptance criteria:

- The agent identifies the intended bill and charge or asks for clarification.
- When evidence is available, the response explains the charge's source and why it appeared.
- The agent provides an appropriate next action.
- When the cause cannot be determined, the agent states that limitation instead of inventing an
  explanation.

### FR-004 — Support follow-up questions

Requirement: The customer can ask follow-up questions within the current support conversation.

Source use cases: `UC-001`, `UC-002`, `UC-003`

Acceptance criteria:

- Follow-up answers retain the relevant bill, charge, or plan context.
- The agent requests clarification when a follow-up is ambiguous.

### FR-005 — Escalate to a human representative

Requirement: The customer can request human escalation, and the agent must also escalate when a
dispute requires human judgment.

Source: Cross-cutting escalation requirement and confirmed non-goals

Acceptance criteria:

- The customer can explicitly request a human representative at any point.
- The agent does not claim to resolve disputes that require human judgment.
- The handoff includes the relevant conversation and available billing context so the customer does
  not need to repeat the issue unnecessarily.
- If a live handoff is unavailable, the agent clearly explains the available alternative.

Status: CONFIRMED

## 8. Quality Requirements

### Privacy

The product must protect customer identity, account, plan, and billing information from unauthorized
access or disclosure.

### Accuracy and transparency

Explanations must be grounded in retrieved KDDI or customer data when they concern a specific
account, plan, bill, or charge. The agent must clearly communicate uncertainty and must not invent
missing facts.

### Reliability

The product must not silently lose or falsely report a human-escalation request. Failures must be
communicated clearly with an available next step when possible.

### Responsiveness

Ordinary support answers should arrive within a reasonable conversational delay. A numeric latency
target may be defined later when the interaction channel and integrations are known.

### Accessibility and language

Responses must use clear, understandable language suitable for non-technical customers. Version
0.1 supports English only.

Status: CONFIRMED

## 9. Success Criteria

Version 0.1 is successful when, in a representative evaluation of routine MVP support cases:

- At least 80% of customers can correctly understand their current plan, latest bill, or unexpected
  charge without human assistance.
- Cases requiring human help are escalated with sufficient conversation and billing context so the
  customer does not need to repeat the issue unnecessarily.
- The agent does not invent account-specific explanations when supporting data is missing.
- Critical corner-case categories are evaluated separately so an acceptable aggregate score cannot
  hide unsafe or misleading behavior in high-risk cases.

Mandatory corner-case evaluation categories:

- Conflicting or outdated plan and billing information.
- Missing, incomplete, or unavailable customer or billing data.

Release gates for both categories:

- 100% of missing, incomplete, or unavailable-data cases must avoid invented account facts and
  clearly communicate the limitation or next step.
- 100% of conflicting or outdated-data cases must identify the conflict or staleness and must not
  present uncertain information as current fact.
- A safety-gate violation blocks release even if the aggregate routine-case score is at least 80%.

The evaluation dataset, corner-case categories, per-category expectations, scoring method, and
minimum escalation-success target will be defined before release verification.

Status: CONFIRMED

## 10. Open Product Questions

- How will the representative routine and corner-case evaluation sets and correctness rubric be
  defined?
- What measurable target will define successful human escalation beyond the approved state-transition
  and context-preservation requirements?
- Should future versions perform account-changing actions such as plan changes, refunds, or billing
  adjustments, or remain informational with human escalation?
- What authorized KDDI APIs, authentication, and customer-data access will be available after the
  version 0.1 evaluation prototype?
