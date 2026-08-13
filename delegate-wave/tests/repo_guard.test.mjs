import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import repoGuard, { inspectToolPath } from "../scripts/repo_guard.mjs";

function fixture() {
  const parent = mkdtempSync(join(tmpdir(), "delegate-wave-guard-"));
  const root = join(parent, "repo");
  const outside = join(parent, "outside");
  mkdirSync(join(root, "src"), { recursive: true });
  mkdirSync(outside);
  writeFileSync(join(root, "README.md"), "fixture\n");
  writeFileSync(join(root, ".env"), "SECRET=value\n");
  symlinkSync(outside, join(root, "escape"), "dir");
  return { parent, root };
}

test("allows repository reads and declared writes", () => {
  const { parent, root } = fixture();
  try {
    assert.deepEqual(inspectToolPath(root, "README.md"), {
      allowed: true,
      relativePath: "README.md",
    });
    assert.deepEqual(
      inspectToolPath(root, "src/new.ts", { write: true, allowedPaths: ["src"] }),
      { allowed: true, relativePath: "src/new.ts" },
    );
  } finally {
    rmSync(parent, { recursive: true, force: true });
  }
});

test("blocks outside, sensitive, symlinked, and out-of-scope paths", () => {
  const { parent, root } = fixture();
  try {
    assert.equal(inspectToolPath(root, "../outside").allowed, false);
    assert.equal(inspectToolPath(root, "@../outside").allowed, false);
    assert.equal(inspectToolPath(root, "~/.ssh/config").allowed, false);
    assert.equal(inspectToolPath(root, "file:///etc/hosts").allowed, false);
    assert.equal(inspectToolPath(root, ".env").allowed, false);
    assert.equal(inspectToolPath(root, ".npmrc").allowed, false);
    assert.equal(inspectToolPath(root, "infra/terraform.tfstate").allowed, false);
    assert.equal(inspectToolPath(root, "escape/file.txt").allowed, false);
    assert.equal(
      inspectToolPath(root, "README.md", { write: true, allowedPaths: ["src"] }).allowed,
      false,
    );
  } finally {
    rmSync(parent, { recursive: true, force: true });
  }
});

test("extension blocks disallowed tool calls before execution", () => {
  const { parent, root } = fixture();
  const originalAllowed = process.env.DELEGATE_WAVE_ALLOWED_PATHS_JSON;
  const originalLog = process.env.DELEGATE_WAVE_GUARD_LOG;
  try {
    process.env.DELEGATE_WAVE_ALLOWED_PATHS_JSON = JSON.stringify(["src"]);
    process.env.DELEGATE_WAVE_GUARD_LOG = join(parent, "guard.jsonl");
    let handler;
    const pi = {
      on(eventName, callback) {
        assert.equal(eventName, "tool_call");
        handler = callback;
      },
    };

    repoGuard(pi);
    assert.equal(typeof handler, "function");
    assert.equal(
      handler({ toolName: "read", input: { path: "../outside" } }, { cwd: root }).block,
      true,
    );
    assert.equal(
      handler({ toolName: "write", input: { path: "README.md" } }, { cwd: root }).block,
      true,
    );
    assert.equal(
      handler({ toolName: "write", input: { path: "src/new.ts" } }, { cwd: root }),
      undefined,
    );
  } finally {
    if (originalAllowed === undefined) delete process.env.DELEGATE_WAVE_ALLOWED_PATHS_JSON;
    else process.env.DELEGATE_WAVE_ALLOWED_PATHS_JSON = originalAllowed;
    if (originalLog === undefined) delete process.env.DELEGATE_WAVE_GUARD_LOG;
    else process.env.DELEGATE_WAVE_GUARD_LOG = originalLog;
    rmSync(parent, { recursive: true, force: true });
  }
});
