#!/usr/bin/env python3
# Copyright 2026 Shri Narayan Justin Ram / Mushku Nobleworks. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0 OR Commercial
"""Fail-closed OpenEncoder release gate checks."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BINARY = ROOT / "bin" / "OpenEncoder.com"
HASH_RE = re.compile(r"\b[0-9a-f]{64}\b")
sys.path.insert(0, str(ROOT))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tracked_text_files() -> list[Path]:
    return [
        path
        for path in ROOT.rglob("*")
        if path.is_file()
        and ".git" not in path.parts
        and path.suffix in {".md", ".py", ".yml", ".yaml", ".json", ".toml"}
        and "__pycache__" not in path.parts
    ]


def main() -> int:
    blockers: list[str] = []
    binary_hash = sha256_file(BINARY) if BINARY.exists() else ""
    if not binary_hash:
        blockers.append("binary_missing:bin/OpenEncoder.com")
    stale_binary_hashes = {
        "97802ae390bac1fc493b6b5ee2c2799"
        + "f95b04f5354a8c09fc3ac93aa04a3e8a2",
    }
    for path in tracked_text_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = path.relative_to(ROOT).as_posix()
        for digest in HASH_RE.findall(text):
            if digest in stale_binary_hashes:
                blockers.append(f"stale_binary_hash:{rel}:{digest}")
    client_source = (ROOT / "client_field_encoder.py").read_text(encoding="utf-8")
    if "def _calc_label(*, width: int, context: str)" not in client_source:
        blockers.append("calc_hash_not_unkeyed_recipe_function")
    if "hmac.new(secret, _canonical_json_bytes(_recipe_descriptor" in client_source:
        blockers.append("calc_hash_still_secret_derived")
    if '"pseudonym_enabled": False' not in client_source:
        blockers.append("metering_pseudonym_not_disabled_by_default")
    if "def _request_binding_report" not in client_source:
        blockers.append("service_response_binding_missing")
    groth_source = (ROOT / "openencoder_groth16.py").read_text(encoding="utf-8")
    if "def real_circuit_gate_status" not in groth_source:
        blockers.append("real_groth16_circuit_gate_missing")
    try:
        from openencoder_groth16 import real_circuit_gate_status

        circuit_gate = real_circuit_gate_status(ROOT / "docs" / "proofs" / "openencoder_real_groth16_circuit_manifest.json")
    except Exception as exc:  # pragma: no cover - defensive release gate
        circuit_gate = {"passed": False, "blockers": [f"real_circuit_gate_exception:{type(exc).__name__}"]}
    release_allowed = not blockers and circuit_gate.get("passed") is True
    payload = {
        "schema_version": "openencoder-release-gates-v1",
        "binary_sha256": binary_hash,
        "release_allowed": release_allowed,
        "real_groth16_circuit_gate": circuit_gate,
        "blocker_count": len(blockers) + (0 if circuit_gate.get("passed") is True else 1),
        "blockers": blockers + ([] if circuit_gate.get("passed") is True else ["real_groth16_circuit_gate_not_passing"]),
    }
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0 if release_allowed else 1


if __name__ == "__main__":
    raise SystemExit(main())
