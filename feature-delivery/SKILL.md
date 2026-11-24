---
name: feature-delivery
description: Turn a feature brief into a scoped implementation and reviewable change using a user-flow prototype when needed, acceptance criteria, implementation, independent review, and test evidence. Use when asked to carry a feature from brief through a review-ready handoff.
---

# Feature delivery

1. Translate the brief into the user outcome, entrypoints, acceptance criteria, and the failure that must be prevented. Reproduce a reported defect when feasible. Identify existing code and behavior that constrain the change.
2. For a UI or interaction change, show the real sequence using the closest available prototype. Include states that affect decisions, such as empty, loading, permission denied, and recoverable failure. Walk it with the requester when a meaningful product choice is open. For an API or internal change, use a request/response or behavior example when it conveys the contract more clearly.
3. Write a shareable implementation plan for substantial work. Save it as a draft or in the user’s tracker when requested. Identify affected components, data and API changes, acceptance checks, and any migration. For changes spanning components or changing a user workflow, seek a fresh reviewer as the default where available and in scope. Give them the proposed behavior and the context needed to challenge assumptions, interactions and missing tests.
4. Implement within scope. Run the most specific checks that can catch each change. Self-review the candidate’s diff. Give an independent reviewer the actual revision, surrounding context, test evidence, and open questions when appropriate. Prefer a different model when practical and record the review coverage. If bounded work needs delegation and `delegate-wave` is installed, use it within the authorized scope. Fix substantiated serious findings. Review the affected changes again. Surface unresolved design choices or repeated serious findings before expanding scope.
5. Exercise the real workflow on the candidate. Record expected and observed results, including a meaningful failure path, along with the revision, environment and relevant artifacts. Use `e2e-proof` if installed or follow the repository's own E2E harness.
6. Prepare the requested handoff with the evidence and any remaining constraints. If asked to open a PR or MR, include the issue, user-visible changes, exact revision tested and test results. Report merge, deployment and production verification only when each occurred.

A handoff can be as short as a link to the brief, the behavior implemented, the candidate revision, each review verdict, executed checks with their evidence, and unresolved items.
