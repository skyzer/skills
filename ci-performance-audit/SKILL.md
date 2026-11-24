---
name: ci-performance-audit
description: Diagnose slow or expensive CI with workflow configuration and actual run history. Use for CI wait time, runner consumption, caching, test selection, sharding, or batching. Produce a baseline, ranked changes, and a way to verify coverage and measure improvement.
---

# CI performance audit

Start with a checkout and workflow configuration. Timing needs run records. Use existing repository tooling or authenticated `gh` or `glab` for the correct host. An exported run bundle also works.

## Measure the existing pipeline

1. Find the repository's CI entrypoints, branch protection, runner types, and merge policy. Trace generated jobs, dependencies, and separately triggered workflows. Inspect reusable workflows, matrix jobs, and GitLab child pipelines where applicable. Record the checks that block a merge and the checks that run later for release.
2. Read a bounded recent sample. Prefer a repository metrics command when available. Otherwise use authenticated read-only API calls. For GitHub Actions, start with workflow run and job records through `gh`. For GitLab, collect pipeline jobs and follow bridges to child pipelines through `glab`. Include observable retries, failures, and cancellations. On GitHub, fetch jobs for each run attempt through the per-attempt jobs endpoint when the run was retried. Say if pagination, access, or history retention limited the sample. With only local configuration, label timing conclusions as hypotheses.
3. Report elapsed time from pipeline creation to completion, time to first actionable failure, and summed runner-minutes. Break out queue, setup, and execution where timestamps allow. Exclude trigger jobs that merely mirror child execution from the runner sum. Treat running jobs and jobs without a runner or terminal timing according to what their timestamps actually establish.
4. Report billing only from a matched billing export. When pricing runner time instead, report an estimate with dated rates, actual machine shapes and known exclusions. Distinguish download bytes, billed network bytes, and elapsed time.
5. Identify the job or prerequisite that finishes last on typical slow runs. Rank changes by the metric they affect. An improvement to a parallel job may free capacity while leaving feedback time unchanged.

## Propose and verify changes

Use [optimization cases and benchmark design](references/optimization-cases.md) for candidates involving setup, sharding, test selection, batching, or cost.

For each proposal, name the observed bottleneck, affected jobs, expected savings and assumptions, coverage risk, and a test of the claim. Prefer removing redundant work and waits in the existing CI system. Inspect the change selector against required checks, including shared code, build inputs, configuration, and unmapped paths. Keep a full-suite fallback where impact is uncertain.

If asked to implement, establish the baseline first. Compare required checks and test identities, then benchmark equivalent base and candidate workloads across multiple comparable runs where practical. Show incomplete, failed, and canceled work in the results. A changed candidate earns fresh merge evidence under the repository's rules. Obtain authorization for any branch push or pipeline trigger outside the requested scope. A plan-only audit uses existing history and describes the proposed benchmark without starting it.
