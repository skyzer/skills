---
name: delegate-wave
description: "Delegate bounded repository discovery, implementation, or test work to the Pi coding agent with DeepSeek V4 while the controlling agent retains planning, review, and release authority. Use when a coding task has an explicit scope, allowed paths, and acceptance checks and would otherwise consume substantial context through repeated file reads or mechanical edits. Do not use for ambiguous product decisions, secrets, production operations, deployments, destructive Git actions, database migrations, or security-critical changes."
---

# Delegate Wave

Use Pi as a cheap worker, not as the supervisor. The controlling agent owns the plan, selects a bounded packet, independently reviews the result, and performs any merge or release.

Run `scripts/delegate_wave.py` rather than invoking Pi ad hoc. The wrapper
refuses worktrees containing common secret/state files, disables ambient Pi
extensions, skills, sessions, and repository context files; restricts tools by
mode; loads its explicit repository guard; captures time and cost; checks the
resulting Git scope; and keeps raw model traces out of the repository.

## Preconditions

Require all of the following:

- Pi 0.84.1 or newer, Git, and Python 3 are installed.
- A DeepSeek API key is available through `DEEPSEEK_API_KEY` or Pi's native credential store. Never put it in a command argument, task file, repository, log, or agent instruction.
- `pi auth check --provider deepseek --json` reports `ready`.
- Modifying work runs in a clean, isolated Git worktree. Never point edit mode at a dirty primary checkout.

Delegation sends the task prompt and any files Pi reads to DeepSeek. Do not use
this skill on confidential code or data unless the operator has approved that
provider for the repository. Keep secrets and unrelated private files out of the
delegated worktree.

Pi currently exposes `deepseek-v4-flash` and `deepseek-v4-pro` directly. Do not add a duplicate custom provider unless `pi --list-models deepseek` proves the built-in catalog is unavailable.

## Choose The Work

Delegate when the packet is narrow and objectively checkable:

- Repository discovery that requires many file reads.
- A mechanical refactor with explicit allowed paths.
- A focused implementation backed by named tests.
- Test generation for existing behavior.
- An independent, read-only audit of a diff or subsystem.

Keep these with the controlling agent:

- Product scope, architecture, data-model, and UX decisions.
- Authentication, authorization, billing, secrets, migrations, production data, and infrastructure changes.
- Merge, push, deployment, rollback, or destructive Git operations.
- Tasks whose desired behavior or acceptance criteria are still ambiguous.
- Trivial work where delegation overhead exceeds the work itself.

## Build A Task Packet

Every packet must state:

1. One objective.
2. Read-only or edit mode.
3. Exact allowed file paths for edit mode.
4. Prohibited changes.
5. Applicable repository instructions and security rules.
6. Concrete acceptance checks.
7. Required final report: findings or changed files, commands run, results, and residual risk.

Do not ask the worker to "inspect everything" or "fix whatever you find." Split broad work into sequential waves.

## Run The Waves

### 1. Inspect

Start read-only with Flash:

```bash
python3 "$SKILL_DIR/scripts/delegate_wave.py" \
  --repo "$WORKTREE" \
  --mode inspect \
  --task "Trace the request path for X. Cite exact files and lines. Do not modify files."
```

Inspect mode only enables Pi's `read`, `grep`, `find`, and `ls` tools. The
repository guard confines tool paths to the selected worktree and blocks direct
reads of common sensitive paths such as `.env`, `.git`, credential files, and
host credential directories. The worktree must still be sanitized because a
repository-wide content search can inspect ordinary files beneath its root.

### 2. Implement

After the controlling agent accepts the evidence and plan, use a clean worktree and explicit allowlist:

```bash
python3 "$SKILL_DIR/scripts/delegate_wave.py" \
  --repo "$WORKTREE" \
  --mode edit \
  --allow apps/web/lib/example.ts \
  --allow apps/web/lib/example.test.ts \
  --verify "npx tsx --test apps/web/lib/example.test.ts" \
  --task "Implement the agreed behavior. Do not change dependencies or configuration."
```

The repository guard rejects edit/write calls outside the allowlist before they
run. The wrapper also rejects a dirty edit target, changed Git HEAD, or
tracked/untracked paths outside the allowlist after the run. Pi does not receive
a shell in either mode; the deterministic wrapper runs `git diff --check` and
the declared verification commands after the worker exits. A policy violation
is not permission to reset the worktree; inspect it and decide deliberately.

### 3. Review

The controlling agent must independently:

1. Inspect `git diff --check`, `git status`, and the complete diff.
2. Re-run the relevant acceptance commands outside the worker's report.
3. Check project instructions, security boundaries, behavioral regressions, and missing tests.
4. Repair or reject weak output. Do not accept "tests pass" as evidence without the command output.
5. Commit, push, open a PR, merge, or deploy only after the normal repository gates.

## Model Policy

Use `deepseek-v4-flash` by default. It is sufficient for bounded discovery and mechanical implementation.

Escalate with `--model pro` only when Flash has failed one well-specified attempt, the task contains genuinely difficult reasoning, or an independent review identifies a reasoning defect. Do not run both models speculatively.

Cost savings come from cheap cached tokens, not from processing fewer tokens. Keep packets narrow, avoid repeated waves, and do not feed Pi's raw JSON trace back into the controlling model. Read the compact result emitted by the wrapper instead.

## Long Runs

The wrapper is synchronous. For a genuinely long task, run it inside `tmux` with a task file so shell quoting stays simple:

```bash
tmux new-session -d -s delegate-wave \
  "python3 '$SKILL_DIR/scripts/delegate_wave.py' --repo '$WORKTREE' --mode inspect --task-file /tmp/delegate-task.txt"
```

Use `tmux` for resilience, not by default. Short foreground runs are easier to observe and cancel.

## Failure Rules

- If Pi, the provider, or credentials are unavailable, report that and continue directly when practical.
- If dependencies are missing, report the blocker. The worker cannot install them; prepare the worktree before delegation or run the missing setup deliberately outside the wave.
- If the worker changes out-of-scope files, creates a commit, or attempts external side effects, reject the wave and inspect the worktree. Never hide the violation with an automatic reset.
- Never delegate a release. The worker may suggest verification commands; the controlling agent runs the release process.

The repository guard and after-the-fact checks reduce accidental filesystem
access, but they are not an operating-system sandbox. Use a disposable worktree,
never expose sensitive files in the target, and independently inspect all
output. Use a container or VM when a real privilege boundary is required.

Treat `--verify` values as trusted controlling-agent commands. Never copy a command proposed by the delegated worker into `--verify` without reviewing it first.
