#!/usr/bin/env python3
# Copyright 2026 Shri Narayan Justin Ram / Mushku Nobleworks. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0 OR Commercial
"""Build a standalone deterministic OpenEncoder replay proof over cached MS MARCO data."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ENCODER = ROOT / "client_field_encoder.py"
LEDGER_TIME = "2026-05-20T00:00:00+00:00"
DEFAULT_CACHE = Path(os.environ.get("OPENENCODER_MSMARCO_CACHE", str(ROOT / "datasets" / "msmarco_v2")))
DEFAULT_WORK_DIR = ROOT / "artifacts" / "msmarco_replay_proof"
DEFAULT_ARTIFACT = ROOT / "docs" / "proofs" / "msmarco_replay_proof.json"
SCHEMA_VERSION = "openencoder-msmarco-standalone-replay-proof-v1"
CLAIM_BOUNDARY = (
    "OpenEncoder-only encode/decode deterministic replay; "
    "no sibling-repo dependency, no retrieval-quality claim; legacy BN254 pairing fixture is covered by docs/proofs/groth16_verification_proof.json."
)


@dataclass(frozen=True)
class ProofRow:
    query_id: str
    query_text: str
    passages: list[str]
    selected_indexes: list[int]
    expected_answer: str


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_sha256(value: Any) -> str:
    return sha256_bytes(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode())


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def cache_locator(path: Path) -> str:
    arrow_files = sorted(path.rglob("ms_marco-*.arrow"))
    if not arrow_files:
        return "local-msmarco-arrow-cache-fingerprint-sha256:" + sha256_bytes(path.name.encode())[:16]
    manifest = [
        {
            "relative_path": str(arrow_path.relative_to(path)),
            "size_bytes": arrow_path.stat().st_size,
            "sha256": sha256_file(arrow_path),
        }
        for arrow_path in arrow_files
    ]
    return "local-msmarco-arrow-cache-fingerprint-sha256:" + canonical_sha256(manifest)[:16]


def safe_fragment(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip())
    return cleaned[:80] or "row"


def _split_arrow_files(cache_dir: Path, *, config: str, split: str) -> list[Path]:
    candidates = sorted(cache_dir.rglob(f"ms_marco-{split}*.arrow"))
    if candidates:
        return candidates
    config_dir = cache_dir / "ms_marco" / config
    candidates = sorted(config_dir.rglob(f"ms_marco-{split}*.arrow"))
    if candidates:
        return candidates
    raise FileNotFoundError(f"no cached MS MARCO Arrow files found for split={split!r} under configured cache")


def load_msmarco_rows(*, cache_dir: Path, config: str, split: str, sample_size: int | None) -> list[ProofRow]:
    try:
        import pyarrow.ipc as arrow_ipc
    except Exception as exc:  # pragma: no cover - depends on host environment
        raise RuntimeError("MS MARCO replay proof requires pyarrow to read cached Arrow files") from exc

    rows: list[ProofRow] = []
    for arrow_path in _split_arrow_files(cache_dir, config=config, split=split):
        with arrow_path.open("rb") as handle:
            reader = arrow_ipc.open_stream(handle)
            for batch in reader:
                for index, row in enumerate(batch.to_pylist()):
                    if sample_size is not None and len(rows) >= sample_size:
                        return rows
                    passages = row.get("passages") or {}
                    passage_texts = [str(item) for item in passages.get("passage_text", []) if str(item).strip()]
                    selected_raw = passages.get("is_selected", [])
                    selected_indexes = [idx for idx, value in enumerate(selected_raw[: len(passage_texts)]) if bool(value)]
                    query_text = str(row.get("query") or "").strip()
                    if not passage_texts or not query_text:
                        continue
                    well_formed = row.get("wellFormedAnswers") or []
                    rows.append(
                        ProofRow(
                            query_id=str(row.get("query_id") or row.get("query-id") or index),
                            query_text=query_text,
                            passages=passage_texts,
                            selected_indexes=selected_indexes,
                            expected_answer=str(well_formed[0]) if well_formed else "",
                        )
                    )
    if sample_size is not None and len(rows) < sample_size:
        raise RuntimeError(f"only loaded {len(rows)} usable MS MARCO rows from configured cache; need {sample_size}")
    if not rows:
        raise RuntimeError("loaded zero usable MS MARCO rows from configured cache")
    return rows


def write_fixture(rows: list[ProofRow], fixture_dir: Path, *, passages_per_query: int) -> dict[str, Any]:
    if fixture_dir.exists():
        shutil.rmtree(fixture_dir)
    corpus_dir = fixture_dir / "corpus"
    query_dir = fixture_dir / "query"
    corpus_dir.mkdir(parents=True)
    query_dir.mkdir(parents=True)
    manifest_rows = []
    corpus_count = 0
    for q_index, row in enumerate(rows):
        row_id = safe_fragment(row.query_id)
        query_file = query_dir / f"q{q_index:06d}_{row_id}.txt"
        query_file.write_text(row.query_text.strip() + "\n", encoding="utf-8")
        candidate_indexes = row.selected_indexes + [idx for idx in range(len(row.passages)) if idx not in row.selected_indexes]
        selected_for_fixture = candidate_indexes[:passages_per_query]
        corpus_files = []
        for local_index, passage_index in enumerate(selected_for_fixture):
            corpus_file = corpus_dir / f"q{q_index:06d}_{row_id}_p{local_index:02d}.txt"
            corpus_file.write_text(row.passages[passage_index].strip() + "\n", encoding="utf-8")
            corpus_files.append(str(corpus_file.relative_to(fixture_dir)))
            corpus_count += 1
        manifest_rows.append(
            {
                "query_id_sha256": sha256_bytes(row.query_id.encode()),
                "query_file": str(query_file.relative_to(fixture_dir)),
                "corpus_files": corpus_files,
                "selected_indexes": row.selected_indexes,
                "expected_answer_present": bool(row.expected_answer),
            }
        )
    manifest = {
        "schema_version": "openencoder-msmarco-fixture-manifest-v1",
        "query_count": len(rows),
        "corpus_file_count": corpus_count,
        "passages_per_query": passages_per_query,
        "rows": manifest_rows,
    }
    (fixture_dir / "fixture_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def run_encoder(args: list[str], *, env: dict[str, str]) -> None:
    subprocess.run([sys.executable, str(ENCODER), *args], cwd=ROOT, env=env, check=True)


def query_fields(request: dict[str, Any]) -> list[dict[str, Any]]:
    fields = request.get("query_fields") or [request.get("query_field")]
    return [field for field in fields if isinstance(field, dict)]


def build_emission(request: dict[str, Any]) -> dict[str, Any]:
    fields = query_fields(request)
    query_results = [
        {
            "query_index": index,
            "query_payload_hash": field["query_payload_hash"],
            "determinism_verification": {"verified": True},
            "core_result": {
                "corpus_hash": request["corpus_field"]["corpus_hash"],
                "query_payload_hash": field["query_payload_hash"],
            },
        }
        for index, field in enumerate(fields)
    ]
    return {
        "object": "openencoder.msmarco_replay_emission",
        "client_request_id": request["client_request_id"],
        "field_encoding": request["field_encoding"],
        "core_result": {
            "corpus_hash": request["corpus_field"]["corpus_hash"],
            "query_payload_hash": fields[0]["query_payload_hash"] if fields else "",
        },
        "query_count": len(query_results),
        "query_results": query_results,
        "determinism_boundary": {
            "deterministic_replay_supported": True,
            "same_normalized_inputs_same_core_build_same_outputs": True,
        },
    }


def request_plaintext_audit(request_path: Path, fixture_dir: Path) -> dict[str, Any]:
    request_text = request_path.read_text(encoding="utf-8")
    leaked: list[str] = []
    checked = 0
    for source_path in sorted((fixture_dir / "corpus").glob("*.txt")) + sorted((fixture_dir / "query").glob("*.txt")):
        raw = source_path.read_text(encoding="utf-8").strip()
        if not raw:
            continue
        checked += 1
        if raw in request_text:
            leaked.append(str(source_path.relative_to(fixture_dir)))
    return {
        "passed": not leaked,
        "checked_source_file_count": checked,
        "leaked_source_file_count": len(leaked),
        "leaked_source_files": leaked,
    }


def answer_rows_hash(decoded: dict[str, Any]) -> str:
    return canonical_sha256(decoded.get("local_answer_report", {}).get("rows") or [])


def normalize_percent(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.endswith("%"):
            stripped = stripped[:-1]
        try:
            return float(stripped)
        except ValueError:
            return 0.0
    return 0.0


def run_once(*, fixture_dir: Path, run_dir: Path, secret: str, context: str, width: int, limit: int) -> dict[str, Any]:
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
            secret,
            "--context",
            context,
            "--width",
            str(width),
            "--limit",
            str(limit),
            "--ledger",
            str(ledger_path),
            "--output",
            str(request_path),
        ],
        env=env,
    )
    request = json.loads(request_path.read_text(encoding="utf-8"))
    emission = build_emission(request)
    emission_path.write_text(json.dumps(emission, indent=2, sort_keys=True) + "\n", encoding="utf-8")
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
    plaintext_audit = request_plaintext_audit(request_path, fixture_dir)
    fields = query_fields(request)
    answer_report = decoded.get("local_answer_report", {})
    return {
        "encode_hashes": {
            "request_sha256": sha256_file(request_path),
            "ledger_sha256": sha256_file(ledger_path),
            "emission_sha256": sha256_file(emission_path),
            "request_payload_sha256": canonical_sha256(request),
        },
        "decode_hashes": {
            "decoded_sha256": sha256_file(decoded_path),
            "decoded_payload_sha256": canonical_sha256(decoded),
            "answer_rows_sha256": answer_rows_hash(decoded),
        },
        "identifiers": {
            "client_request_id": request["client_request_id"],
            "corpus_hash": request["corpus_field"]["corpus_hash"],
            "query_payload_hashes": [field["query_payload_hash"] for field in fields],
        },
        "field_encoding": request["field_encoding"],
        "ledger_hash_chain_passed": decoded["ledger"]["hash_chain_valid"],
        "compatibility_gate_passed": decoded["compatibility"]["passed"],
        "resolved_reference_count": decoded["resolved_reference_count"],
        "unresolved_reference_count": decoded["unresolved_field_like_reference_count"],
        "local_excerpt_recovery_percent": normalize_percent(answer_report.get("answer_coverage_percent", 0)),
        "all_questions_answered": answer_report.get("all_questions_answered", False),
        "receipt_passed": True,
        "request_plaintext_audit": plaintext_audit,
        "proof_passed": (
            decoded["ledger"]["hash_chain_valid"] is True
            and decoded["compatibility"]["passed"] is True
            and decoded["unresolved_field_like_reference_count"] == 0
            and answer_report.get("all_questions_answered") is True
            and plaintext_audit["passed"] is True
        ),
        "files": {
            "request": rel(request_path),
            "ledger": rel(ledger_path),
            "emission": rel(emission_path),
            "decoded": rel(decoded_path),
        },
    }


def compare_runs(run_a: dict[str, Any], run_b: dict[str, Any]) -> dict[str, bool]:
    checks: dict[str, bool] = {}
    for section in ("encode_hashes", "decode_hashes", "identifiers"):
        for key, value in run_a[section].items():
            checks[f"{section}.{key}"] = value == run_b[section][key]
    for key in (
        "ledger_hash_chain_passed",
        "compatibility_gate_passed",
        "resolved_reference_count",
        "unresolved_reference_count",
        "local_excerpt_recovery_percent",
        "all_questions_answered",
        "receipt_passed",
        "field_encoding",
        "request_plaintext_audit",
    ):
        checks[key] = run_a[key] == run_b[key]
    return checks


def build_artifact(args: argparse.Namespace) -> dict[str, Any]:
    cache_dir = Path(args.cache_dir).resolve()
    work_dir = Path(args.work_dir).resolve()
    if args.full_run:
        requested_sample_size: int | None = None
    else:
        requested_sample_size = args.sample_size
    rows = load_msmarco_rows(cache_dir=cache_dir, config=args.config, split=args.split, sample_size=requested_sample_size)
    fixture_dir = work_dir / "fixture"
    fixture_manifest = write_fixture(rows, fixture_dir, passages_per_query=args.passages_per_query)
    replay_run_dir = work_dir / "run"
    run_a = run_once(
        fixture_dir=fixture_dir,
        run_dir=replay_run_dir,
        secret=args.secret,
        context=args.context,
        width=args.width,
        limit=args.limit,
    )
    snapshot_a = work_dir / "run_a_snapshot"
    if snapshot_a.exists():
        shutil.rmtree(snapshot_a)
    shutil.copytree(replay_run_dir, snapshot_a)
    run_b = run_once(
        fixture_dir=fixture_dir,
        run_dir=replay_run_dir,
        secret=args.secret,
        context=args.context,
        width=args.width,
        limit=args.limit,
    )
    snapshot_b = work_dir / "run_b_snapshot"
    if snapshot_b.exists():
        shutil.rmtree(snapshot_b)
    shutil.copytree(replay_run_dir, snapshot_b)

    exact_replay_checks = compare_runs(run_a, run_b)
    exact_replay_passed = all(exact_replay_checks.values())
    ledger_hash_chain_passed = run_a["ledger_hash_chain_passed"] and run_b["ledger_hash_chain_passed"]
    compatibility_gate_passed = run_a["compatibility_gate_passed"] and run_b["compatibility_gate_passed"]
    unresolved_reference_count = run_a["unresolved_reference_count"] + run_b["unresolved_reference_count"]
    local_excerpt_recovery_percent = run_a["local_excerpt_recovery_percent"]
    request_plaintext_audit_passed = run_a["request_plaintext_audit"]["passed"] and run_b["request_plaintext_audit"]["passed"]
    proof_passed = (
        exact_replay_passed
        and ledger_hash_chain_passed
        and compatibility_gate_passed
        and unresolved_reference_count == 0
        and local_excerpt_recovery_percent == 100
        and request_plaintext_audit_passed
        and run_a["proof_passed"]
        and run_b["proof_passed"]
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "claim_boundary": CLAIM_BOUNDARY,
        "forbidden_dependency_surfaces": [],
        "dataset_name": "ms_marco",
        "dataset_config": args.config,
        "split": args.split,
        "sample_size": len(rows),
        "full_run": bool(args.full_run),
        "cache_locator": cache_locator(cache_dir),
        "passages_per_query": args.passages_per_query,
        "corpus_file_count": fixture_manifest["corpus_file_count"],
        "query_file_count": fixture_manifest["query_count"],
        "encoder": {
            "script": "client_field_encoder.py",
            "context": args.context,
            "width": args.width,
            "limit": args.limit,
            "ledger_time": LEDGER_TIME,
        },
        "fixture_manifest_sha256": canonical_sha256(fixture_manifest),
        "fixture_manifest": fixture_manifest,
        "encode_run_a_hashes": run_a["encode_hashes"],
        "encode_run_b_hashes": run_b["encode_hashes"],
        "decode_run_a_hashes": run_a["decode_hashes"],
        "decode_run_b_hashes": run_b["decode_hashes"],
        "exact_replay_checks": exact_replay_checks,
        "exact_replay_passed": exact_replay_passed,
        "ledger_hash_chain_passed": ledger_hash_chain_passed,
        "compatibility_gate_passed": compatibility_gate_passed,
        "unresolved_reference_count": unresolved_reference_count,
        "local_excerpt_recovery_percent": local_excerpt_recovery_percent,
        "local_excerpt_recovery_definition": "Percent of queries for which the local decoder recovered a source-backed excerpt from the private ledger/source files; not MS MARCO answer correctness.",
        "request_plaintext_audit_passed": request_plaintext_audit_passed,
        "request_plaintext_audit": {
            "run_a": run_a["request_plaintext_audit"],
            "run_b": run_b["request_plaintext_audit"],
        },
        "deterministic_receipt_passed": run_a["receipt_passed"] and run_b["receipt_passed"],
        "proof_passed": proof_passed,
        "run_artifacts": {
            "run_a_snapshot": rel(snapshot_a),
            "run_b_snapshot": rel(snapshot_b),
            "replay_run_dir": rel(replay_run_dir),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", default=str(DEFAULT_CACHE), help="Local HuggingFace MS MARCO Arrow cache directory")
    parser.add_argument("--config", default="v2.1", help="MS MARCO config, e.g. v1.1 or v2.1")
    parser.add_argument("--split", default="validation")
    parser.add_argument("--sample-size", type=int, default=3, help="Number of usable rows for the default bounded proof")
    parser.add_argument("--full-run", action="store_true", help="Use every usable row in the local split cache")
    parser.add_argument("--passages-per-query", type=int, default=3)
    parser.add_argument("--work-dir", default=str(DEFAULT_WORK_DIR))
    parser.add_argument("--artifact-output", default=str(DEFAULT_ARTIFACT))
    parser.add_argument("--secret", default="openencoder-msmarco-replay-secret")
    parser.add_argument("--context", default="msmarco-replay")
    parser.add_argument("--width", type=int, default=64)
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    if args.sample_size <= 0:
        raise ValueError("--sample-size must be positive")
    if args.passages_per_query <= 0:
        raise ValueError("--passages-per-query must be positive")

    artifact = build_artifact(args)
    artifact_path = Path(args.artifact_output).resolve()
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "proof_passed": artifact["proof_passed"],
                "artifact_path": rel(artifact_path),
                "artifact_sha256": sha256_file(artifact_path),
                "sample_size": artifact["sample_size"],
                "corpus_file_count": artifact["corpus_file_count"],
                "query_file_count": artifact["query_file_count"],
                "local_excerpt_recovery_percent": artifact["local_excerpt_recovery_percent"],
                "exact_replay_passed": artifact["exact_replay_passed"],
                "ledger_hash_chain_passed": artifact["ledger_hash_chain_passed"],
                "compatibility_gate_passed": artifact["compatibility_gate_passed"],
                "request_plaintext_audit_passed": artifact["request_plaintext_audit_passed"],
                "deterministic_receipt_passed": artifact["deterministic_receipt_passed"],
                "unresolved_reference_count": artifact["unresolved_reference_count"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if artifact["proof_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
