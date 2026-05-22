#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR Commercial
"""Stream a full local MS MARCO cache through OpenEncoder encode/decode parity checks."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Iterable

try:
    import pyarrow.compute as pc
    import pyarrow.ipc as arrow_ipc
except Exception as exc:  # pragma: no cover - host dependency
    raise RuntimeError("MS MARCO full parity proof requires pyarrow") from exc

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from client_field_encoder import (  # noqa: E402
    SourceItem,
    _canonical_token_text,
    _sha256_json,
    _sha256_text,
    _typed_atoms,
    encode_source_item,
)

DEFAULT_CACHE = Path(os.environ.get("OPENENCODER_MSMARCO_CACHE", str(ROOT / "datasets" / "msmarco_v2")))
DEFAULT_ARTIFACT = ROOT / "docs" / "proofs" / "msmarco_full_parity_proof.json"
DEFAULT_PROGRESS = ROOT / "artifacts" / "msmarco_full_parity_progress.json"
SCHEMA_VERSION = "openencoder-msmarco-full-local-cache-parity-proof-v1"
LEDGERLESS_DECODE_MODEL = "local-ledger-hash-mapback-equivalence-v1"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def canonical_sha256(value: Any) -> str:
    return sha256_bytes(canonical_json(value))


def chain_update(chain: str, value: Any) -> str:
    return sha256_bytes((chain + "\n").encode() + canonical_json(value))


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


def split_from_name(path: Path) -> str:
    name = path.name
    if "-train" in name:
        return "train"
    if "-validation" in name:
        return "validation"
    if "-test" in name:
        return "test"
    return "unknown"


def split_arrow_files(cache_dir: Path, *, config: str, splits: set[str]) -> list[Path]:
    config_dir = cache_dir / "ms_marco" / config
    candidates = sorted(config_dir.rglob("ms_marco-*.arrow")) or sorted(cache_dir.rglob("ms_marco-*.arrow"))
    selected = [path for path in candidates if split_from_name(path) in splits]
    if not selected:
        raise FileNotFoundError("no cached MS MARCO Arrow files found for requested splits under configured cache")
    return selected


def load_dataset_info(cache_dir: Path, *, config: str) -> dict[str, Any]:
    candidates = sorted((cache_dir / "ms_marco" / config).rglob("dataset_info.json")) or sorted(cache_dir.rglob("dataset_info.json"))
    if not candidates:
        return {}
    return json.loads(candidates[0].read_text(encoding="utf-8"))


def selected_texts(row: dict[str, Any]) -> Iterable[tuple[str, str, str]]:
    query_id = str(row.get("query_id") or "")
    query = str(row.get("query") or "")
    if query.strip():
        yield "query", f"query:{sha256_bytes(query_id.encode())[:16]}", query
    passages = row.get("passages") or {}
    for index, passage in enumerate(passages.get("passage_text", []) or []):
        text = str(passage or "")
        if text.strip():
            yield "corpus", f"passage:{sha256_bytes((query_id + ':' + str(index)).encode())[:16]}", text


def init_split_stats() -> dict[str, int]:
    return {
        "arrow_files": 0,
        "rows": 0,
        "queries": 0,
        "raw_passage_slots": 0,
        "passages": 0,
        "encoded_sources": 0,
        "decoded_sources": 0,
        "text_hash_mismatches": 0,
        "canonical_hash_mismatches": 0,
        "typed_atom_hash_mismatches": 0,
        "signal_replay_mismatches": 0,
        "field_receipt_replay_mismatches": 0,
        "field_id_replay_mismatches": 0,
        "exceptions": 0,
    }


def prove(args: argparse.Namespace) -> dict[str, Any]:
    cache_dir = Path(args.cache_dir).resolve()
    requested_splits = {part.strip() for part in args.splits.split(",") if part.strip()}
    arrow_files = split_arrow_files(cache_dir, config=args.config, splits=requested_splits)
    dataset_info = load_dataset_info(cache_dir, config=args.config)
    declared_splits = dataset_info.get("splits") if isinstance(dataset_info.get("splits"), dict) else {}
    secret = args.secret.encode()
    started = time.time()
    last_progress = started

    totals = init_split_stats()
    by_split = {split: init_split_stats() for split in sorted(requested_splits)}
    file_rows: list[dict[str, Any]] = []
    source_chain = hashlib.sha256(b"openencoder-msmarco-full-source-chain-v1").hexdigest()
    decode_chain = hashlib.sha256(b"openencoder-msmarco-full-decode-chain-v1").hexdigest()
    signal_chain = hashlib.sha256(b"openencoder-msmarco-full-signal-chain-v1").hexdigest()
    receipt_chain = hashlib.sha256(b"openencoder-msmarco-full-receipt-chain-v1").hexdigest()
    mismatch_samples: list[dict[str, Any]] = []
    order = 0

    for arrow_path in arrow_files:
        split = split_from_name(arrow_path)
        stats = by_split.setdefault(split, init_split_stats())
        stats["arrow_files"] += 1
        totals["arrow_files"] += 1
        file_stat = {"file": arrow_path.name, "split": split, "rows": 0, "queries": 0, "raw_passage_slots": 0, "passages": 0, "encoded_sources": 0}
        with arrow_path.open("rb") as handle:
            reader = arrow_ipc.open_stream(handle)
            for batch in reader:
                rows_in_batch = batch.num_rows
                raw_passage_slots_in_batch = int(pc.sum(pc.list_value_length(batch.column("passages").field("passage_text"))).as_py() or 0)
                stats["rows"] += rows_in_batch
                stats["raw_passage_slots"] += raw_passage_slots_in_batch
                totals["rows"] += rows_in_batch
                totals["raw_passage_slots"] += raw_passage_slots_in_batch
                file_stat["rows"] += rows_in_batch
                file_stat["raw_passage_slots"] += raw_passage_slots_in_batch
                for row in batch.to_pylist():
                    for role, label, text in selected_texts(row):
                        if role == "query":
                            stats["queries"] += 1
                            totals["queries"] += 1
                            file_stat["queries"] += 1
                        else:
                            stats["passages"] += 1
                            totals["passages"] += 1
                            file_stat["passages"] += 1
                        source = SourceItem(role=role, source_label=label, source_path="", text=text, order=order)
                        try:
                            encoded = encode_source_item(source, secret=secret, width=args.width, context=args.context)
                            replay = encode_source_item(source, secret=secret, width=args.width, context=args.context)
                            expected_text_sha = _sha256_text(text)
                            expected_canonical_sha = _sha256_text(_canonical_token_text(text))
                            expected_typed_atom_sha = _sha256_json(_typed_atoms(text))
                            decoded_text_sha = encoded.text_sha256
                            checks = {
                                "text_hash": decoded_text_sha == expected_text_sha,
                                "canonical_text_hash": encoded.canonical_text_sha256 == expected_canonical_sha,
                                "typed_atom_hash": encoded.typed_atom_sha256 == expected_typed_atom_sha,
                                "signal_replay": encoded.signal_sha256 == replay.signal_sha256,
                                "field_receipt_replay": encoded.field_receipt_sha256 == replay.field_receipt_sha256,
                                "field_id_replay": encoded.field_id == replay.field_id,
                            }
                            if not checks["text_hash"]:
                                stats["text_hash_mismatches"] += 1
                                totals["text_hash_mismatches"] += 1
                            if not checks["canonical_text_hash"]:
                                stats["canonical_hash_mismatches"] += 1
                                totals["canonical_hash_mismatches"] += 1
                            if not checks["typed_atom_hash"]:
                                stats["typed_atom_hash_mismatches"] += 1
                                totals["typed_atom_hash_mismatches"] += 1
                            if not checks["signal_replay"]:
                                stats["signal_replay_mismatches"] += 1
                                totals["signal_replay_mismatches"] += 1
                            if not checks["field_receipt_replay"]:
                                stats["field_receipt_replay_mismatches"] += 1
                                totals["field_receipt_replay_mismatches"] += 1
                            if not checks["field_id_replay"]:
                                stats["field_id_replay_mismatches"] += 1
                                totals["field_id_replay_mismatches"] += 1
                            if not all(checks.values()) and len(mismatch_samples) < 10:
                                mismatch_samples.append({"split": split, "role": role, "source_label": label, "checks": checks})
                            leaf = {
                                "split": split,
                                "role": role,
                                "label": label,
                                "text_sha256": encoded.text_sha256,
                                "canonical_text_sha256": encoded.canonical_text_sha256,
                                "typed_atom_sha256": encoded.typed_atom_sha256,
                                "signal_sha256": encoded.signal_sha256,
                                "field_receipt_sha256": encoded.field_receipt_sha256,
                            }
                            source_chain = chain_update(source_chain, {"role": role, "label": label, "text_sha256": expected_text_sha})
                            decode_chain = chain_update(decode_chain, {"role": role, "label": label, "decoded_text_sha256": decoded_text_sha})
                            signal_chain = chain_update(signal_chain, {"role": role, "label": label, "signal_sha256": encoded.signal_sha256})
                            receipt_chain = chain_update(receipt_chain, leaf)
                        except Exception as exc:  # pragma: no cover - proves failures in artifact
                            stats["exceptions"] += 1
                            totals["exceptions"] += 1
                            if len(mismatch_samples) < 10:
                                mismatch_samples.append({"split": split, "role": role, "source_label": label, "exception": repr(exc)})
                        stats["encoded_sources"] += 1
                        stats["decoded_sources"] += 1
                        totals["encoded_sources"] += 1
                        totals["decoded_sources"] += 1
                        file_stat["encoded_sources"] += 1
                        order += 1
                        now = time.time()
                        if args.progress_output and now - last_progress >= args.progress_interval_seconds:
                            progress_path = Path(args.progress_output).resolve()
                            progress_path.parent.mkdir(parents=True, exist_ok=True)
                            progress = {
                                "schema_version": "openencoder-msmarco-full-parity-progress-v1",
                                "updated_unix_seconds": int(now),
                                "current_file": arrow_path.name,
                                "totals": totals,
                                "by_split": by_split,
                            }
                            progress_path.write_text(json.dumps(progress, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                            last_progress = now
        file_rows.append(file_stat)

    declared_rows = sum(int(value.get("num_examples") or 0) for key, value in declared_splits.items() if key in requested_splits and isinstance(value, dict))
    mismatch_count = sum(
        totals[key]
        for key in (
            "text_hash_mismatches",
            "canonical_hash_mismatches",
            "typed_atom_hash_mismatches",
            "signal_replay_mismatches",
            "field_receipt_replay_mismatches",
            "field_id_replay_mismatches",
            "exceptions",
        )
    )
    proof_passed = (
        totals["rows"] == declared_rows
        and totals["encoded_sources"] == totals["decoded_sources"]
        and totals["encoded_sources"] == totals["queries"] + totals["passages"]
        and mismatch_count == 0
        and len(arrow_files) == totals["arrow_files"]
    )
    accuracy = 100.0 if totals["encoded_sources"] and mismatch_count == 0 else (1.0 - (mismatch_count / max(1, totals["encoded_sources"]))) * 100.0
    artifact = {
        "schema_version": SCHEMA_VERSION,
        "proof_passed": proof_passed,
        "claim_boundary": "OpenEncoder encode/decode parity over every text item in the local MS MARCO Arrow cache; no retrieval-ranking or service-quality claim; Groth16 is covered by docs/proofs/groth16_verification_proof.json.",
        "decode_model": LEDGERLESS_DECODE_MODEL,
        "dataset_name": "ms_marco",
        "dataset_config": args.config,
        "requested_splits": sorted(requested_splits),
        "cache_locator": cache_locator(cache_dir),
        "declared_row_count": declared_rows,
        "measured_row_count": totals["rows"],
        "measured_query_count": totals["queries"],
        "measured_raw_passage_slots": totals["raw_passage_slots"],
        "measured_passage_count": totals["passages"],
        "encoded_source_count": totals["encoded_sources"],
        "decoded_source_count": totals["decoded_sources"],
        "encode_decode_accuracy_percent": round(accuracy, 12),
        "fidelity_loss_count": mismatch_count,
        "all_arrow_files_covered": len(arrow_files) == totals["arrow_files"],
        "declared_rows_match_measured_rows": totals["rows"] == declared_rows,
        "source_chain_sha256": source_chain,
        "decode_chain_sha256": decode_chain,
        "signal_chain_sha256": signal_chain,
        "receipt_chain_sha256": receipt_chain,
        "mismatch_samples": mismatch_samples,
        "totals": totals,
        "by_split": by_split,
        "files": file_rows,
        "encoder": {
            "script": "client_field_encoder.py",
            "context": args.context,
            "width": args.width,
            "recipe": "openencoder-oezk1-signed-int16-typed-atom-v1",
        },
        "local_cache_limitations": {
            "separate_138m_passage_collection_found": False,
            "note": "Local search found HuggingFace ms_marco v1.1/v2.1 Arrow query-example caches only. This artifact covers every row and passage entry in the local v2.1 Arrow cache.",
        },
        "elapsed_seconds": round(time.time() - started, 3),
    }
    artifact["artifact_payload_sha256"] = canonical_sha256({key: value for key, value in artifact.items() if key != "artifact_payload_sha256"})
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", default=str(DEFAULT_CACHE))
    parser.add_argument("--config", default="v2.1")
    parser.add_argument("--splits", default="train,validation,test")
    parser.add_argument("--width", type=int, default=64)
    parser.add_argument("--context", default="msmarco-full-local-cache-parity")
    parser.add_argument("--secret", default="openencoder-msmarco-full-parity-proof-secret")
    parser.add_argument("--output", default=str(DEFAULT_ARTIFACT))
    parser.add_argument("--progress-output", default=str(DEFAULT_PROGRESS))
    parser.add_argument("--progress-interval-seconds", type=float, default=15.0)
    args = parser.parse_args()
    if args.width <= 0:
        raise ValueError("--width must be positive")
    artifact = prove(args)
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "proof_passed": artifact["proof_passed"],
        "artifact_path": str(output.relative_to(ROOT)),
        "artifact_sha256": sha256_file(output),
        "declared_row_count": artifact["declared_row_count"],
        "measured_row_count": artifact["measured_row_count"],
        "measured_query_count": artifact["measured_query_count"],
        "measured_raw_passage_slots": artifact["measured_raw_passage_slots"],
        "measured_passage_count": artifact["measured_passage_count"],
        "encoded_source_count": artifact["encoded_source_count"],
        "decoded_source_count": artifact["decoded_source_count"],
        "encode_decode_accuracy_percent": artifact["encode_decode_accuracy_percent"],
        "fidelity_loss_count": artifact["fidelity_loss_count"],
        "elapsed_seconds": artifact["elapsed_seconds"],
    }, indent=2, sort_keys=True))
    return 0 if artifact["proof_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
