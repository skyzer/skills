from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "delegate_wave.py"
SPEC = importlib.util.spec_from_file_location("delegate_wave", SCRIPT)
assert SPEC and SPEC.loader
delegate_wave = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(delegate_wave)


def run(*args: str, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def make_repo(root: Path) -> Path:
    repo = root / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Delegate Test"], cwd=repo, check=True)
    (repo / "README.md").write_text("fixture\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=repo, check=True)
    return repo


class DelegateWaveUnitTests(unittest.TestCase):
    def test_allowed_paths_are_normalized_and_boundary_checked(self) -> None:
        allowed = delegate_wave.normalize_allowed(["src/file.ts", "src"])
        self.assertEqual(allowed, ["src", "src/file.ts"])
        self.assertTrue(delegate_wave.path_is_allowed("src/file.ts", allowed))
        self.assertFalse(delegate_wave.path_is_allowed("src-old/file.ts", allowed))
        for unsafe in ("/tmp/file", "../file", ".", ""):
            with self.assertRaises(delegate_wave.DelegateError):
                delegate_wave.normalize_allowed([unsafe])

    def test_git_metadata_and_symlink_escapes_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "repo"
            repo.mkdir()
            outside = Path(temporary) / "outside"
            outside.mkdir()
            (repo / "escape").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(delegate_wave.DelegateError):
                delegate_wave.validate_allowed_paths(repo, [".git/config"])
            with self.assertRaises(delegate_wave.DelegateError):
                delegate_wave.validate_allowed_paths(repo, ["escape/file.ts"])

    def test_sensitive_file_preflight_allows_templates_and_rejects_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = make_repo(Path(temporary))
            (repo / ".gitignore").write_text(".env.local\n", encoding="utf-8")
            subprocess.run(["git", "add", ".gitignore"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "ignore fixture secret"], cwd=repo, check=True)
            (repo / ".env.example").write_text("SAFE=placeholder\n", encoding="utf-8")
            self.assertEqual(delegate_wave.find_sensitive_files(repo), [])
            (repo / ".env.local").write_text("SECRET=value\n", encoding="utf-8")
            (repo / "terraform.tfstate").write_text("{}\n", encoding="utf-8")
            self.assertEqual(
                delegate_wave.find_sensitive_files(repo),
                [".env.local", "terraform.tfstate"],
            )

    def test_trace_parser_sums_billable_turns_and_keeps_final_text(self) -> None:
        lines = [
            {
                "type": "message_end",
                "message": {
                    "role": "assistant",
                    "usage": {
                        "input": 10,
                        "output": 3,
                        "cacheRead": 20,
                        "reasoning": 2,
                        "totalTokens": 35,
                        "cost": {"total": 0.001},
                    },
                },
            },
            {
                "type": "turn_end",
                "message": {"content": [{"type": "text", "text": "final report"}]},
            },
        ]
        usage, report = delegate_wave.parse_trace("\n".join(json.dumps(item) for item in lines))
        self.assertEqual(usage["turns"], 1)
        self.assertEqual(usage["totalTokens"], 35)
        self.assertEqual(usage["costUSD"], 0.001)
        self.assertEqual(report, "final report")

    def test_pi_version_parser_requires_a_semantic_version(self) -> None:
        self.assertEqual(delegate_wave.parse_pi_version("pi 0.84.1"), (0, 84, 1))
        self.assertEqual(delegate_wave.parse_pi_version("0.90.0-beta"), (0, 90, 0))
        with self.assertRaises(delegate_wave.DelegateError):
            delegate_wave.parse_pi_version("unknown")

    def test_worker_environment_drops_unrelated_credentials(self) -> None:
        original = os.environ.copy()
        try:
            os.environ["DEEPSEEK_API_KEY"] = "deepseek-test"
            os.environ["UNRELATED_API_TOKEN"] = "must-not-reach-worker"
            worker_env = delegate_wave.build_worker_env()
            self.assertEqual(worker_env["DEEPSEEK_API_KEY"], "deepseek-test")
            self.assertNotIn("UNRELATED_API_TOKEN", worker_env)
        finally:
            os.environ.clear()
            os.environ.update(original)

    def test_dry_run_needs_no_api_key_or_pi_binary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = make_repo(Path(temporary))
            env = os.environ.copy()
            env.pop("DEEPSEEK_API_KEY", None)
            env["PATH"] = "/usr/bin:/bin"
            result = run(
                "--repo", str(repo),
                "--mode", "inspect",
                "--task", "Inspect the fixture.",
                "--dry-run",
                cwd=repo,
                env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["mode"], "inspect")
            self.assertEqual(payload["model"], "deepseek-v4-flash")

    def test_edit_mode_refuses_a_dirty_worktree_before_calling_pi(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = make_repo(Path(temporary))
            (repo / "README.md").write_text("dirty\n", encoding="utf-8")
            env = os.environ.copy()
            env.pop("DEEPSEEK_API_KEY", None)
            result = run(
                "--repo", str(repo),
                "--mode", "edit",
                "--allow", "README.md",
                "--task", "Change the fixture.",
                cwd=repo,
                env=env,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("clean isolated worktree", result.stderr)

    def test_out_of_scope_worker_change_is_rejected_and_secret_is_redacted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = make_repo(root)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            fake_pi = fake_bin / "pi"
            fake_pi.write_text(
                """#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys

if len(sys.argv) > 1 and sys.argv[1] == "auth":
    if sys.argv[2] == "check":
        print(json.dumps({"status": "ready"}))
    elif sys.argv[2] == "print-api-key":
        print(os.environ["DEEPSEEK_API_KEY"])
    raise SystemExit(0)
if len(sys.argv) > 1 and sys.argv[1] == "--version":
    print("0.84.1")
    raise SystemExit(0)
if len(sys.argv) > 1 and sys.argv[1] == "--list-models":
    print("deepseek  deepseek-v4-flash")
    raise SystemExit(0)

Path("outside.txt").write_text("out of scope\\n", encoding="utf-8")
usage = {
    "type": "message_end",
    "message": {
        "role": "assistant",
        "usage": {"totalTokens": 10, "cost": {"total": 0.001}},
    },
}
report = {
    "type": "turn_end",
    "message": {
        "content": [
            {"type": "text", "text": "worker leaked " + os.environ["DEEPSEEK_API_KEY"]}
        ]
    },
}
print(json.dumps(usage))
print(json.dumps(report))
""",
                encoding="utf-8",
            )
            fake_pi.chmod(0o755)

            secret = "test-secret-never-print"
            env = os.environ.copy()
            env["PATH"] = f"{fake_bin}:{env['PATH']}"
            env["DEEPSEEK_API_KEY"] = secret
            env["DELEGATE_WAVE_RUN_DIR"] = str(root / "runs")
            result = run(
                "--repo", str(repo),
                "--mode", "edit",
                "--allow", "README.md",
                "--task", "Change only README.md.",
                cwd=repo,
                env=env,
            )

            self.assertEqual(result.returncode, 4, result.stderr)
            self.assertIn("changed paths outside allowlist: outside.txt", result.stdout)
            self.assertIn("[REDACTED]", result.stdout)
            self.assertNotIn(secret, result.stdout)

if __name__ == "__main__":
    unittest.main()
