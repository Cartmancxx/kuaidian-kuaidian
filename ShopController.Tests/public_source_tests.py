"""High-confidence public-source hygiene checks. Findings print locations, never values.

This is a local heuristic check, not a guarantee that every possible secret is detectable.
It does not contact a remote service or inspect directories outside this repository.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {".git", "dist", ".tools", "bin", "obj", "__pycache__", "node_modules", "verification"}
PRIVATE_NAMES = {"Cookies", "Login Data", "History", "config.json", "config.json.bak", "host-identity.json", ".env"}
PRIVATE_SUFFIXES = {".pfx", ".p12", ".pem", ".key", ".kdbx", ".pdb"}
PATTERNS = {
    "private-key-material": re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----"),
    "github-token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b"),
    "api-token": re.compile(r"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{28,}\b"),
    "cloud-access-key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "chat-service-token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    "personal-home-path": re.compile(r'''(?i)(?:[A-Z]:[\\/]+Users[\\/]+(?!example|test|fixture|Default|Public)[^\\/\s"']+|/User''' + r'''s/(?!example|test|fixture)[^/\s"']+)'''),
    "secret-literal-assignment": re.compile(r'''(?im)\b(?:api[_-]?key|access[_-]?token|client[_-]?secret|password|passwd)\b\s*[=:]\s*["'][^"'\r\n]{10,}["']'''),
}
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def main():
    tracked = []
    if (ROOT / ".git").exists():
        result = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True)
        tracked = [name for name in result.stdout.decode("utf-8").split("\0") if name]
    files = [ROOT / name for name in tracked] if tracked else [
        file for file in ROOT.rglob("*") if file.is_file() and not EXCLUDED.intersection(file.relative_to(ROOT).parts)]
    public_email = json.loads((ROOT / "ShopController/release-config.json").read_text(encoding="utf-8-sig")).get("supportEmail")
    findings = []
    text_count = 0
    for path in files:
        relative = path.relative_to(ROOT)
        if EXCLUDED.intersection(relative.parts):
            findings.append((relative.as_posix(), 0, "tracked-generated-or-local-data"))
            continue
        if path.is_symlink() or path.resolve() != path.absolute():
            findings.append((relative.as_posix(), 0, "redirected-source-path"))
            continue
        if path.name in PRIVATE_NAMES or path.name.startswith(".env.") or path.suffix.lower() in PRIVATE_SUFFIXES:
            findings.append((relative.as_posix(), 0, "private-filename"))
        if path.suffix.lower() in {".exe", ".dll", ".zip"} or path.name == "ShopController.Host":
            findings.append((relative.as_posix(), 0, "compiled-payload-in-source"))
        try:
            contents = path.read_text(encoding="utf-8-sig")
        except UnicodeError:
            continue
        text_count += 1
        for label, pattern in PATTERNS.items():
            for match in pattern.finditer(contents):
                findings.append((relative.as_posix(), contents.count("\n", 0, match.start()) + 1, label))
        for match in EMAIL.finditer(contents):
            domain = match.group().rsplit("@", 1)[1].lower()
            if match.group() != public_email and domain not in {"example.com", "example.org", "example.invalid"}:
                findings.append((relative.as_posix(), contents.count("\n", 0, match.start()) + 1, "unclassified-email"))
    for file, line, label in findings:
        print(f"REVIEW {file}:{line} [{label}] — value redacted")
    if findings:
        raise SystemExit(f"Public-source scan requires review at {len(findings)} location(s). No matched values were printed.")
    print(f"PASS public-source scan: {len(files)} source files / {text_count} UTF-8 files; no high-confidence secret, personal-home path, unclassified email or tracked local artifact detected.")
    print("Configured public support email and reserved example-domain fixtures are allowed. Manual review remains necessary.")


if __name__ == "__main__":
    main()
