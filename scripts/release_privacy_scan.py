#!/usr/bin/env python3
# Copyright 2026 Shri Narayan Justin Ram / Mushku Nobleworks. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0 OR Commercial
"""Fail closed on private paths, contacts, and internal-only terms in release files.

This scanner uses regex patterns for common private-data patterns. It does not
replace high-entropy secret scanners like trufflehog or gitleaks. Run both before
release.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".json", ".md", ".py", ".zig", ".toml", ".yml", ".yaml", ".txt", ".cfg", ".ini"}
TEXT_NAMES = {"LICENSE", "CHANGELOG", "CONTRIBUTING", "SECURITY"}
BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
BINARY_PATHS = {"bin/OpenEncoder.com"}
LOCAL_DENYLIST = ROOT / ".release-privacy-denylist.local"
PUBLIC_TERM_PATTERNS = [
    re.compile(r"/home/[A-Za-z0-9._-]+"),
    re.compile(r"Users\\[A-Za-z0-9._-]+", re.IGNORECASE),
    re.compile(r"\\\\wsl\.localhost\\[^\\\s]+", re.IGNORECASE),
    re.compile(r"\bPCT\s+Request\b", re.IGNORECASE),
    re.compile(r"\bsigned[_-]asfiled\b", re.IGNORECASE),
    re.compile(r"\bpatent[-_]attorney[-_]", re.IGNORECASE),
]
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
ALLOWED_BINARY_EMAILS = {"millert" + "@openbsd.org", "H@t" + ".IIEA"}


def local_terms() -> list[str]:
    if not LOCAL_DENYLIST.is_file():
        return []
    return [
        line.strip()
        for line in LOCAL_DENYLIST.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def git_files() -> list[Path]:
    completed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [ROOT / line for line in completed.stdout.splitlines() if line.strip()]


def is_binary_release_artifact(path: Path) -> bool:
    try:
        rel = path.relative_to(ROOT).as_posix()
    except ValueError:
        return False
    return rel in BINARY_PATHS or path.suffix.lower() in BINARY_SUFFIXES


def should_scan(path: Path) -> bool:
    if ".git" in path.parts:
        return False
    if path.suffix in TEXT_SUFFIXES or path.name in TEXT_NAMES:
        return True
    return is_binary_release_artifact(path)


def scan_text(path: Path, text: str) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    patterns = PUBLIC_TERM_PATTERNS
    for pattern in patterns:
        if pattern.search(text):
            findings.append({"path": str(path.relative_to(ROOT)), "pattern": pattern.pattern})
    for term in local_terms():
        if term in text:
            findings.append({"path": str(path.relative_to(ROOT)), "pattern": "local_denylist_term"})
    emails = set(EMAIL_RE.findall(text))
    if is_binary_release_artifact(path):
        emails = emails - ALLOWED_BINARY_EMAILS
    if emails:
        findings.append({"path": str(path.relative_to(ROOT)), "pattern": "email_address"})
    return findings


def main() -> int:
    findings: list[dict[str, str]] = []
    scanned = 0
    for path in git_files():
        if not path.is_file() or not should_scan(path):
            continue
        scanned += 1
        raw = path.read_bytes()
        text = raw.decode("utf-8", errors="ignore")
        findings.extend(scan_text(path, text))
    payload = {
        "schema_version": "openencoder-release-privacy-scan-v1",
        "scanned_file_count": scanned,
        "finding_count": len(findings),
        "findings": findings,
        "passed": not findings,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
