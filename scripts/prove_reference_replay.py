#!/usr/bin/env python3
# Copyright 2026 Shri Narayan Justin Ram / Mushku Nobleworks. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0 OR Commercial
"""Prove deterministic OpenEncoder replay and whitespace-change parity receipts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ENCODER = ROOT / "client_field_encoder.py"
LEDGER_TIME = "2026-05-20T00:00:00+00:00"
DEFAULT_WORK_DIR = ROOT / "artifacts" / "reference_replay_proof"
DEFAULT_ARTIFACT = ROOT / "docs" / "proofs" / "reference_replay_proof.json"
SECRET = "openencoder-reference-replay-secret"
CONTEXT = "openencoder-reference-replay"
WIDTH = 32
LIMIT = 3

BASE_CORPUS = "Contract renewal requires legal approval before Friday.\n"
CHANGED_CORPUS = "Contract   renewal   requires   legal approval before   Friday.\n"
QUERY = "What approval is needed for renewal?\n"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode())


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_sha256(value: Any) -> str:
    return sha256_bytes(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode())


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def write_fixture(fixture_dir: Path, *, corpus_text: str) -> None:
    if fixture_dir.exists():
        shutil.rmtree(fixture_dir)
    (fixture_dir / "corpus").mkdir(parents=True)
    (fixture_dir / "query").mkdir(parents=True)
    (fixture_dir / "corpus" / "contract.txt").write_text(corpus_text, encoding="utf-8")
    (fixture_dir / "query" / "approval.txt").write_text(QUERY, encoding="utf-8")


def run_encoder(args: list[str], *, env: dict[str, str]) -> None:
    subprocess.run([sys.executable, str(ENCODER), *args], cwd=ROOT, env=env, check=True)


def query_fields(request: dict[str, Any]) -> list[dict[str, Any]]:
    fields = request.get("query_fields") or [request.get("query_field")]
    return [field for field in fields if isinstance(field, dict)]



def run_once(*, fixture_dir: Path, run_dir: Path) -> dict[str, Any]:
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True)
    request_path = run_dir / "01_field_request.json"
    ledger_path = run_dir / "02_client_field_ledger.jsonl"
    emission_path = run_dir / "03_service_emission.json"
    decoded_path = run_dir / "04_decoded_answers.json"
    env = os.environ.copy()
    env["CLIENT_FIELD_LEDGER_WRITTEN_AT"] = LEDGER_TIME
    run_encoder(
        [
            "encode",
            "--corpus-path",
            str(fixture_dir / "corpus"),
            "--query-path",
            str(fixture_dir / "query"),
            "--secret",
            SECRET,
            "--context",
            CONTEXT,
            "--width",
            str(WIDTH),
            "--limit",
            str(LIMIT),
            "--ledger",
            str(ledger_path),
            "--output",
            str(request_path),
        ],
        env=env,
    )
    request = json.loads(request_path.read_text(encoding="utf-8"))
    run_encoder(
        [
            "emit",
            "--request",
            str(request_path),
            "--output",
            str(emission_path),
        ],
        env=env,
    )
    run_encoder(
        [
            "decode",
            "--ledger",
            str(ledger_path),
            "--emission",
            str(emission_path),
            "--include-text",
            "--max-members",
            "0",
            "--output",
            str(decoded_path),
        ],
        env=env,
    )
    decoded = json.loads(decoded_path.read_text(encoding="utf-8"))
    query_field = query_fields(request)[0]
    answer_rows = decoded.get("local_answer_report", {}).get("rows") or []
    answer_text = str(answer_rows[0].get("answer_text") or "") if answer_rows else ""
    return {
        "request_sha256": sha256_file(request_path),
        "ledger_sha256": sha256_file(ledger_path),
        "emission_sha256": sha256_file(emission_path),
        "decoded_sha256": sha256_file(decoded_path),
        "request_payload_sha256": canonical_sha256(request),
        "decoded_payload_sha256": canonical_sha256(decoded),
        "client_request_id": request["client_request_id"],
        "schema_version": request["schema_version"],
        "recipe_id": request["field_encoding"]["recipe_id"],
        "dtype": request["field_encoding"]["dtype"],
        "corpus_hash": request["corpus_field"]["corpus_hash"],
        "corpus_signal_sha256": request["corpus_field"]["signal_sha256"],
        "corpus_typed_atom_sha256": request["corpus_field"]["typed_atom_sha256"],
        "query_payload_hash": query_field["query_payload_hash"],
        "query_signal_sha256": query_field["signal_sha256"],
        "ledger_hash_chain_valid": decoded["ledger"]["hash_chain_valid"],
        "compatibility_passed": decoded["compatibility"]["passed"],
        "resolved_reference_count": decoded["resolved_reference_count"],
        "unresolved_field_like_reference_count": decoded["unresolved_field_like_reference_count"],
        "envelope_proof_passed": decoded["envelope_proof"]["passed"],
        "envelope_proof_count": decoded["envelope_proof"]["proof_count"],
        "all_questions_answered": decoded["local_answer_report"]["all_questions_answered"],
        "answer_coverage_percent": decoded["local_answer_report"]["answer_coverage_percent"],
        "replay_coverage_percent": decoded["local_answer_report"]["replay_coverage_percent"],
        "source_hash_coverage_percent": decoded["local_answer_report"]["source_hash_coverage_percent"],
        "answer_text_normalized": " ".join(answer_text.split()),
        "files": {
            "request": rel(request_path),
            "ledger": rel(ledger_path),
            "emission": rel(emission_path),
            "decoded": rel(decoded_path),
        },
    }


def proof(work_dir: Path) -> dict[str, Any]:
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True)
    base_fixture = work_dir / "base_fixture"
    changed_fixture = work_dir / "changed_fixture"
    write_fixture(base_fixture, corpus_text=BASE_CORPUS)
    write_fixture(changed_fixture, corpus_text=CHANGED_CORPUS)
    base_run_dir = work_dir / "base_run"
    base_a_snapshot = work_dir / "base_run_a_snapshot"
    base_b_snapshot = work_dir / "base_run_b_snapshot"
    base_a = run_once(fixture_dir=base_fixture, run_dir=base_run_dir)
    shutil.copytree(base_run_dir, base_a_snapshot)
    base_b = run_once(fixture_dir=base_fixture, run_dir=base_run_dir)
    shutil.copytree(base_run_dir, base_b_snapshot)
    changed = run_once(fixture_dir=changed_fixture, run_dir=work_dir / "changed_run")
    exact_replay_checks = {
        key: base_a[key] == base_b[key]
        for key in (
            "request_sha256",
            "ledger_sha256",
            "emission_sha256",
            "decoded_sha256",
            "request_payload_sha256",
            "decoded_payload_sha256",
            "client_request_id",
            "corpus_hash",
            "corpus_signal_sha256",
            "corpus_typed_atom_sha256",
            "query_payload_hash",
            "query_signal_sha256",
            "answer_text_normalized",
        )
    }
    easy_change_checks = {
        "raw_source_changed": sha256_text(BASE_CORPUS) != sha256_text(CHANGED_CORPUS),
        "corpus_hash_parity": base_a["corpus_hash"] == changed["corpus_hash"],
        "corpus_signal_parity": base_a["corpus_signal_sha256"] == changed["corpus_signal_sha256"],
        "typed_atom_parity": base_a["corpus_typed_atom_sha256"] == changed["corpus_typed_atom_sha256"],
        "answer_fidelity_parity": base_a["answer_text_normalized"] == changed["answer_text_normalized"],
        "changed_decode_passed": changed["ledger_hash_chain_valid"] and changed["compatibility_passed"] and changed["envelope_proof_passed"] and changed["all_questions_answered"],
    }
    health_checks = {
        "base_decode_passed": base_a["ledger_hash_chain_valid"] and base_a["compatibility_passed"] and base_a["envelope_proof_passed"] and base_a["all_questions_answered"],
        "base_replay_decode_passed": base_b["ledger_hash_chain_valid"] and base_b["compatibility_passed"] and base_b["envelope_proof_passed"] and base_b["all_questions_answered"],
        "signed_int16_recipe": base_a["recipe_id"] == "openencoder-oezk1-signed-int16-typed-atom-v1" and base_a["dtype"] == "int16",
        "no_unresolved_refs": base_a["unresolved_field_like_reference_count"] == 0 and changed["unresolved_field_like_reference_count"] == 0,
    }
    proof_passed = all(exact_replay_checks.values()) and all(easy_change_checks.values()) and all(health_checks.values())
    return {
        "schema_version": "openencoder-deterministic-replay-receipt-v1",
        "proof_passed": proof_passed,
        "claim_boundary": "OpenEncoder client encode/decode replay, signed-int16 typed-atom parity, and local answer fidelity receipt only. Legacy BN254 pairing fixture is covered by docs/proofs/groth16_verification_proof.json; the pinned real Groth16 reference circuit proof is covered by docs/proofs/openencoder_real_groth16_circuit_manifest.json.",
        "encoder": {
            "script": "client_field_encoder.py",
            "schema_version": base_a["schema_version"],
            "recipe_id": base_a["recipe_id"],
            "dtype": base_a["dtype"],
            "width": WIDTH,
            "limit": LIMIT,
            "context": CONTEXT,
            "ledger_time": LEDGER_TIME,
        },
        "fixture_change": {
            "change_type": "whitespace-only corpus edit",
            "base_source_sha256": sha256_text(BASE_CORPUS),
            "changed_source_sha256": sha256_text(CHANGED_CORPUS),
            "query_sha256": sha256_text(QUERY),
        },
        "exact_replay_checks": exact_replay_checks,
        "easy_change_checks": easy_change_checks,
        "health_checks": health_checks,
        "base_run": base_a,
        "base_replay_run": base_b,
        "changed_run": changed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", default=str(DEFAULT_WORK_DIR))
    parser.add_argument("--artifact", default=str(DEFAULT_ARTIFACT))
    args = parser.parse_args()
    artifact = proof(Path(args.work_dir).resolve())
    artifact_path = Path(args.artifact).resolve()
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {
        "receipt_passed": artifact["proof_passed"],
        "artifact_path": rel(artifact_path),
        "artifact_sha256": sha256_file(artifact_path),
        "exact_replay_passed": all(artifact["exact_replay_checks"].values()),
        "easy_change_passed": all(artifact["easy_change_checks"].values()),
        "base_answer": artifact["base_run"]["answer_text_normalized"],
        "changed_answer": artifact["changed_run"]["answer_text_normalized"],
        "recipe_id": artifact["encoder"]["recipe_id"],
        "dtype": artifact["encoder"]["dtype"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if artifact["proof_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
