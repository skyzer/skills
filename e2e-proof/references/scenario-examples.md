# Scenario examples

## Browser workflow

For a setting with published and draft values, test both directions of the override. Open a preview with published off and draft on, then with published on and draft off. Assert that each preview uses the draft. Read the published value again after each run and verify it stayed the same. When testing a save, open the normal screen in a fresh session and check that it displays the persisted value.

## API or CLI workflow

For a protected action, run the allowed and denied cases from the same seeded state. Assert that the denied request is rejected and leaves the resource unchanged. Assert that the allowed request succeeds and persists the intended change. For a retried write, reuse the same idempotency key or equivalent request identity and count durable effects. Capture the response or exit status along with the resulting state.

## Background work and external integrations

Trigger an import through its normal entrypoint. For a successful run, verify that the job reaches its terminal success state and that the imported data can be read. For a promised recovery path, inject a failure at the external dependency, verify that the request actually failed, and follow the same job through retry or fallback to its observable outcome. Use a job or request ID to correlate sanitized logs with what the user or downstream consumer receives.

If you use a substitute for the external service, identify it in the evidence. An authorized sandbox run can verify the real integration path and demonstrate any external effect the scenario claims.
