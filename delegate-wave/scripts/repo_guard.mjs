import { appendFileSync, existsSync, realpathSync } from "node:fs";
import { dirname, isAbsolute, relative, resolve, sep } from "node:path";

const FILE_TOOLS = new Set(["read", "write", "edit", "grep", "find", "ls"]);
const WRITE_TOOLS = new Set(["write", "edit"]);
const BLOCKED_SEGMENTS = new Set([
  ".aws",
  ".git",
  ".gnupg",
  ".ssh",
  "credentials",
  "secrets",
]);
const UNICODE_SPACES = /[\u00A0\u2000-\u200A\u202F\u205F\u3000]/g;

function isInside(root, candidate) {
  const path = relative(root, candidate);
  return path === "" || (path !== ".." && !path.startsWith(`..${sep}`) && !isAbsolute(path));
}

function nearestExisting(path) {
  let candidate = path;
  while (!existsSync(candidate)) {
    const parent = dirname(candidate);
    if (parent === candidate) {
      break;
    }
    candidate = parent;
  }
  return candidate;
}

function isSensitive(relativePath) {
  const segments = relativePath.split("/").filter(Boolean);
  if (segments.some((segment) => BLOCKED_SEGMENTS.has(segment))) {
    return true;
  }

  const basename = segments.at(-1) ?? "";
  const isEnvironmentFile =
    basename === ".env" ||
    (basename.startsWith(".env.") && !basename.endsWith(".example") && !basename.endsWith(".template"));
  const isCredentialFile = /^(?:credentials?|secrets?)(?:\.(?:json|ya?ml|toml|txt|key|pem))?$/i.test(basename);
  const isCredentialConfig = new Set([".envrc", ".git-credentials", ".netrc", ".npmrc", ".pypirc"])
    .has(basename);
  const isPrivateKey = /^(?:id_rsa|id_ed25519)$|\.(?:key|p12|pem|pfx|tfstate)$/i.test(basename);
  return isEnvironmentFile || isCredentialFile || isCredentialConfig || isPrivateKey;
}

function isAllowedWrite(relativePath, allowedPaths) {
  return allowedPaths.some(
    (prefix) => relativePath === prefix || relativePath.startsWith(`${prefix}/`),
  );
}

export function inspectToolPath(root, rawPath, { write = false, allowedPaths = [] } = {}) {
  try {
    let normalizedPath = String(rawPath || ".").replace(UNICODE_SPACES, " ");
    if (normalizedPath.startsWith("@")) {
      normalizedPath = normalizedPath.slice(1);
    }
    if (
      normalizedPath === "~" ||
      normalizedPath.startsWith("~/") ||
      normalizedPath.startsWith("~\\") ||
      /^file:\/\//i.test(normalizedPath)
    ) {
      return { allowed: false, reason: "home-directory and file-URL paths are blocked" };
    }

    const rootReal = realpathSync(root);
    const lexicalPath = resolve(rootReal, normalizedPath || ".");
    if (!isInside(rootReal, lexicalPath)) {
      return { allowed: false, reason: "path is outside the delegated repository" };
    }

    const existingAncestor = nearestExisting(lexicalPath);
    const ancestorReal = realpathSync(existingAncestor);
    if (!isInside(rootReal, ancestorReal)) {
      return { allowed: false, reason: "path resolves through a symlink outside the repository" };
    }

    const relativePath = relative(rootReal, lexicalPath).split(sep).join("/") || ".";
    if (isSensitive(relativePath)) {
      return { allowed: false, reason: "sensitive path is blocked", relativePath };
    }
    if (write && !isAllowedWrite(relativePath, allowedPaths)) {
      return { allowed: false, reason: "write path is outside the declared allowlist", relativePath };
    }
    return { allowed: true, relativePath };
  } catch (error) {
    return {
      allowed: false,
      reason: `path validation failed: ${error instanceof Error ? error.message : String(error)}`,
    };
  }
}

function parseAllowedPaths() {
  try {
    const value = JSON.parse(process.env.DELEGATE_WAVE_ALLOWED_PATHS_JSON ?? "[]");
    return Array.isArray(value) && value.every((item) => typeof item === "string") ? value : [];
  } catch {
    return [];
  }
}

function record(event) {
  const path = process.env.DELEGATE_WAVE_GUARD_LOG;
  if (!path) {
    return;
  }
  appendFileSync(path, `${JSON.stringify(event)}\n`, { encoding: "utf-8", mode: 0o600 });
}

export default function repoGuard(pi) {
  const allowedPaths = parseAllowedPaths();

  pi.on("tool_call", (event, context) => {
    if (!FILE_TOOLS.has(event.toolName)) {
      return undefined;
    }

    const rawPath = typeof event.input?.path === "string" ? event.input.path : ".";
    const write = WRITE_TOOLS.has(event.toolName);
    const decision = inspectToolPath(context.cwd, rawPath, { write, allowedPaths });

    if (!decision.allowed) {
      record({
        kind: "blocked",
        tool: event.toolName,
        path: rawPath,
        reason: decision.reason,
      });
      return { block: true, reason: decision.reason, terminate: true };
    }

    if (write) {
      record({ kind: "mutation", tool: event.toolName, path: decision.relativePath });
    }
    return undefined;
  });
}
