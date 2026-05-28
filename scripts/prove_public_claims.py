#!/usr/bin/env python3
# Copyright 2026 Shri Narayan Justin Ram / Mushku Nobleworks. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0 OR Commercial
"""Build a fail-closed proof for public OpenEncoder claim wording."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "docs" / "proofs" / "public_claims_verification_proof.json"
SCHEMA_VERSION = "openencoder-public-claims-verification-proof-v1"

PUBLIC_CLAIM_FILES = [
    "README.md",
    "PUBLIC_CLAIMS.md",
    "RELEASE_ATTESTATION.md",
    "CHANGELOG.md",
    "docs/BENCHMARKS.md",
    "docs/MSMARCO_REPRODUCTION.md",
    "docs/RELEASE_CHECKLIST.md",
]

FORBIDDEN_CLAIM_FRAGMENTS = [
    "NOT " + "CLAIMED until exact " + "full" + "-gamut run",
    "pending exact " + "full" + "-gamut " + "artifact",
    "OpenEncoder+Gravitas " + "production",
    "OpenEncoder+Gravitas        | encode/decode parity only; retrieval " + "not " + "claimed",
    "OpenEncoder+Gravitas " + "retrieval",
    "retrieval " + "not " + "claimed",
    "receipt-backed Legal-MLEB " + "base" + "line exists",
    "| Surface | " + "Boundary |",
    "| OpenEncoder+Gravitas | MS MARCO " + "parity proof PASS; Gravitas " + "sub" + "mitted |",
    "semantic_retrieval_claim   | NOT " + "CLAIMED",
    "OPENENCODER STANDALONE RETRIEVAL CLAIM: NOT " + "CLAIMED",
    "OpenEncoder MS MARCO " + "full" + " gamut",
    "openencoder" + "_full_scale",
    "MS MARCO v2.1 " + "full" + " gamut",
    "full" + "-gamut",
    "full" + " gamut",
]

REQUIRED_CLAIM_FRAGMENTS = [
    "| Benchmark            | Lane                 | Status                 | Scale",
    "| Legal-MLEB           | OpenEncoder+Gravitas | PASS comparator        | 2,535 q; 7,635 corpus; 2,580 qrels",
    "| Legal-MLEB           | Ionizer+Gravitas     | PASS fullbar           | 2,535 q; 7,635 corpus; 2,580 qrels",
    "| MS MARCO v2 passage  | Ionizer+Gravitas     | PASS world fullbar     | 285,328 q; 138,364,198 records; 285,328,000 rank entries",
    "| MS MARCO stream      | OpenEncoder+Gravitas | PASS parity            | 285,328 q + 138,364,198 passages = 138,649,526 sources",
    "| MS MARCO local cache | OpenEncoder+Gravitas | PASS parity submission | 1,010,916 q + 10,087,677 corpus = 11,098,593 sources",
    "MSSQL fullbar_world_metric_receipts; commit 5bb633581468eb66",
    "mteb/msmarco-v2 stream parity| 138.6M srcs | PASS",
    "OpenEncoder+Gravitas MS MARCO  | parity proof PASS; Gravitas submission receipt",
    "OpenEncoder+Gravitas MS MARCO| PASS; stream parity proof + Gravitas receipt",
    "OpenEncoder+Gravitas MS MARCO stream parity | PASS",
    "MS MARCO semantic retrieval benchmark | out of scope; no ranking metric",
    "docs/proofs/msmarco_v2_real_proof.json",
    "d15c702867e001b7020e65e55b5d23b3844c03638203f45bc3237154b3ddd202",
]

REQUIRED_ARTIFACTS = {
    "docs/proofs/msmarco_v2_real_proof.json": {
        "file_sha256": "38782428a27e12e2ef3da5ccd137f90d8e270546e68bec1a87a520633dc24932",
        "proof_path": ["proof", "proof_passed"],
        "proof_value": True,
    },
    "docs/proofs/msmarco_v2_real_public_handoff.json": {
        "file_sha256": "a640232df9ae6400a54371be3aa41e9364c1365a2843a8f7c06722ea27cf9125",
        "proof_path": ["results", "proof_passed"],
        "proof_value": True,
    },
    "docs/proofs/msmarco_full_parity_gravitas_submission.json": {
        "file_sha256": "92e8a052b5bb0c7fc1246c26c947af52796731c9d65d4344c7e7a0f37cf951b7",
        "proof_path": ["fidelity", "proof_passed"],
        "proof_value": True,
    },
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def nested_get(value: dict[str, Any], path: list[str]) -> Any:
    current: Any = value
    for part in path:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def find_fragment(text: str, fragment: str) -> list[int]:
    return [line_no for line_no, line in enumerate(text.splitlines(), start=1) if fragment in line]


def prove() -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    scanned_files: list[dict[str, Any]] = []
    all_public_text = ""

    for rel in PUBLIC_CLAIM_FILES:
        path = ROOT / rel
        if not path.exists():
            blockers.append({"type": "public_claim_file_missing", "path": rel})
            continue
        text = path.read_text(encoding="utf-8")
        all_public_text += "\n" + text
        scanned_files.append({
            "path": rel,
            "sha256": sha256_file(path),
            "size_bytes": path.stat().st_size,
        })
        for fragment in FORBIDDEN_CLAIM_FRAGMENTS:
            lines = find_fragment(text, fragment)
            if lines:
                blockers.append({
                    "type": "forbidden_claim_fragment",
                    "path": rel,
                    "fragment": fragment,
                    "lines": lines,
                })

    for fragment in REQUIRED_CLAIM_FRAGMENTS:
        if fragment not in all_public_text:
            blockers.append({"type": "required_claim_fragment_missing", "fragment": fragment})

    artifact_checks: list[dict[str, Any]] = []
    for rel, expected in REQUIRED_ARTIFACTS.items():
        path = ROOT / rel
        if not path.exists():
            blockers.append({"type": "required_artifact_missing", "path": rel})
            continue
        file_sha256 = sha256_file(path)
        artifact = json.loads(path.read_text(encoding="utf-8"))
        proof_value = nested_get(artifact, expected["proof_path"])
        check = {
            "path": rel,
            "file_sha256": file_sha256,
            "expected_file_sha256": expected["file_sha256"],
            "file_sha256_matches": file_sha256 == expected["file_sha256"],
            "proof_path": ".".join(expected["proof_path"]),
            "proof_value": proof_value,
            "proof_value_matches": proof_value == expected["proof_value"],
        }
        artifact_checks.append(check)
        if not check["file_sha256_matches"]:
            blockers.append({"type": "artifact_sha256_mismatch", "path": rel, "expected": expected["file_sha256"], "actual": file_sha256})
        if not check["proof_value_matches"]:
            blockers.append({"type": "artifact_proof_value_mismatch", "path": rel, "expected": expected["proof_value"], "actual": proof_value})

    payload = {
        "schema_version": SCHEMA_VERSION,
        "proof_passed": not blockers,
        "claim_boundary": "OpenEncoder+Gravitas MS MARCO public wording must claim the checked stream encode/decode parity PASS and Gravitas submission receipt while keeping MSSQL/Gravitas authority separate from rendered files.",
        "public_claim_files": scanned_files,
        "forbidden_claim_fragment_sha256": [sha256_bytes(fragment.encode("utf-8")) for fragment in FORBIDDEN_CLAIM_FRAGMENTS],
        "required_claim_fragments": REQUIRED_CLAIM_FRAGMENTS,
        "artifact_checks": artifact_checks,
        "blocker_count": len(blockers),
        "blockers": blockers,
    }
    payload["artifact_payload_sha256"] = sha256_bytes(canonical_json({k: v for k, v in payload.items() if k != "artifact_payload_sha256"}))
    return payload


def main() -> int:
    output = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_OUTPUT
    artifact = prove()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "proof_passed": artifact["proof_passed"],
        "artifact_path": str(output.relative_to(ROOT)),
        "artifact_sha256": sha256_file(output),
        "blocker_count": artifact["blocker_count"],
        "blockers": artifact["blockers"],
    }, indent=2, sort_keys=True))
    return 0 if artifact["proof_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
