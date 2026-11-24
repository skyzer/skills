---
name: e2e-proof
description: Design and execute end-to-end acceptance tests for a candidate through its normal browser, API, or voice entrypoint. Use when asked to reproduce a bug, prove a workflow, capture evidence, or verify graceful failure across service boundaries.
---

# End-to-end proof

1. Record the candidate revision or artifact and the environment. Use the project's existing local or staging harness, with an isolated account and synthetic fixtures. Identify real components and any substituted external dependencies. If there is no harness, use a minimal isolated setup that exercises the real entrypoint. For a plan-only request, describe the setup and mark cases not run. Check that the candidate is actually running before testing.
2. Write the observable pass condition and allowed retries before running the scenario. Exercise the natural entrypoint and assert the visible result or state transition. Verify relevant persisted state through the product or API after a reload. Select paths by the behavior changed, including identity, permissions, channel, and configuration where they differ.
3. Exercise the failure mode the change promises to handle. Make the test fail on the prior bug or demonstrate that an injected failure really occurred. Assert the subsequent behavior in the same session or transaction if continuity is part of the claim.
4. Record a case table with revision, environment, fixture, expected behavior, observed behavior, and pass/fail/not run. Include a screenshot for visual behavior and a trace, sanitized logs, or recording for behavior the screenshot cannot prove. Report all failed attempts, including those followed by a pass. Record their timing and classify the cause only as far as the evidence supports.
5. Add a regression scenario at the seam most likely to catch the problem again. For provider-backed checks, identify which jobs only validate deterministic boot and plumbing and which scenarios actually exercised the provider. Require evidence from a provider-backed run before recording a provider path as passed. Mark blocked scenarios with the missing dependency or capability, such as browser automation, provider access, or network reachability. Use an authorized test environment and destination for any external call, message or other side effect.

Read [browser, API and voice examples](references/scenario-examples.md) for relevant checks and evidence.
