#!/usr/bin/env python3
# Copyright 2026 Shri Narayan Justin Ram / Mushku Nobleworks. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0 OR Commercial
"""Stream mteb/msmarco-v2 through OpenEncoder encode/decode parity checks."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import socket
import sys
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any

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


DEFAULT_ARTIFACT = ROOT / "docs" / "proofs" / "msmarco_v2_real_proof.json"
SCHEMA_VERSION = "openencoder-msmarco-v2-real-parity-proof-v1"
DATASET_ID = "mteb/msmarco-v2"
RECIPE_ID = "openencoder-oezk1-signed-int16-typed-atom-v1"


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


def _first_text(row: dict[str, Any], keys: Iterable[str]) -> str:
    for key in keys:
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value
    raise KeyError(f"row has no text field among {tuple(keys)!r}")


def _first_id(row: dict[str, Any], keys: Iterable[str], fallback: str) -> str:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value):
            return str(value)
    return fallback


def load_stream(dataset_id: str, config: str, split: str) -> Iterable[dict[str, Any]]:
    try:
        from datasets import load_dataset
    except Exception as exc:  # pragma: no cover - host dependency
        raise RuntimeError("mteb/msmarco-v2 parity proof requires the datasets package") from exc
    return load_dataset(dataset_id, config, split=split, streaming=True)


def iter_sources(args: argparse.Namespace) -> Iterable[SourceItem]:
    order = 0
    query_stream = load_stream(args.dataset_id, args.query_config, args.query_split)
    for row in query_stream:
        if order >= args.query_limit:
            break
        text = _first_text(row, ("text", "query", "query_text", "contents"))
        source_id = _first_id(row, ("_id", "id", "query_id", "qid"), f"query:{order}")
        yield SourceItem(role="query", source_label=f"query:{source_id}", source_path="", text=text, order=order)
        order += 1

    passage_order = 0
    passage_stream = load_stream(args.dataset_id, args.passage_config, args.passage_split)
    for row in passage_stream:
        if passage_order >= args.passage_limit:
            break
        text = _first_text(row, ("text", "passage", "passage_text", "contents"))
        source_id = _first_id(row, ("_id", "id", "docid", "doc_id", "pid"), f"passage:{passage_order}")
        yield SourceItem(role="corpus", source_label=f"passage:{source_id}", source_path="", text=text, order=order)
        order += 1
        passage_order += 1


def machine_report() -> dict[str, Any]:
    return {
        "cpu": platform.processor() or platform.machine(),
        "hostname_redacted": bool(socket.gethostname()),
        "kernel": platform.release(),
        "logical_threads": os.cpu_count(),
        "os": platform.platform(),
        "ram_gib": None,
    }


def prove(args: argparse.Namespace) -> dict[str, Any]:
    secret = args.secret.encode()
    started = time.time()
    source_chain = hashlib.sha256(b"openencoder-msmarco-v2-source-chain-v1").hexdigest()
    decode_chain = hashlib.sha256(b"openencoder-msmarco-v2-decode-chain-v1").hexdigest()
    signal_chain = hashlib.sha256(b"openencoder-msmarco-v2-signal-chain-v1").hexdigest()
    receipt_chain = hashlib.sha256(b"openencoder-msmarco-v2-receipt-chain-v1").hexdigest()
    typed_atom_chain = hashlib.sha256(b"openencoder-msmarco-v2-typed-atom-chain-v1").hexdigest()
    field_id_chain = hashlib.sha256(b"openencoder-msmarco-v2-field-id-chain-v1").hexdigest()
    metrics = {
        "canonical_hash_mismatches": 0,
        "exceptions": 0,
        "field_id_replay_mismatches": 0,
        "field_receipt_replay_mismatches": 0,
        "signal_replay_mismatches": 0,
        "text_hash_mismatches": 0,
        "typed_atom_hash_mismatches": 0,
    }
    processed = 0

    for source in iter_sources(args):
        try:
            encoded = encode_source_item(source, secret=secret, width=args.width, context=args.context)
            replay = encode_source_item(source, secret=secret, width=args.width, context=args.context)
            expected_text_sha = _sha256_text(source.text)
            expected_canonical_sha = _sha256_text(_canonical_token_text(source.text))
            expected_typed_atom_sha = _sha256_json(_typed_atoms(source.text))
            if encoded.text_sha256 != expected_text_sha:
                metrics["text_hash_mismatches"] += 1
            if encoded.canonical_text_sha256 != expected_canonical_sha:
                metrics["canonical_hash_mismatches"] += 1
            if encoded.typed_atom_sha256 != expected_typed_atom_sha:
                metrics["typed_atom_hash_mismatches"] += 1
            if encoded.signal_sha256 != replay.signal_sha256:
                metrics["signal_replay_mismatches"] += 1
            if encoded.field_receipt_sha256 != replay.field_receipt_sha256:
                metrics["field_receipt_replay_mismatches"] += 1
            if encoded.field_id != replay.field_id:
                metrics["field_id_replay_mismatches"] += 1
            leaf = {
                "role": source.role,
                "label": source.source_label,
                "text_sha256": expected_text_sha,
                "canonical_text_sha256": expected_canonical_sha,
                "typed_atom_sha256": expected_typed_atom_sha,
                "signal_sha256": encoded.signal_sha256,
                "field_receipt_sha256": encoded.field_receipt_sha256,
                "field_id": encoded.field_id,
            }
            source_chain = chain_update(source_chain, {"role": source.role, "label": source.source_label, "text_sha256": expected_text_sha})
            decode_chain = chain_update(decode_chain, {"role": source.role, "label": source.source_label, "decoded_text_sha256": encoded.text_sha256})
            signal_chain = chain_update(signal_chain, {"role": source.role, "label": source.source_label, "signal_sha256": encoded.signal_sha256})
            receipt_chain = chain_update(receipt_chain, leaf)
            typed_atom_chain = chain_update(typed_atom_chain, {"role": source.role, "label": source.source_label, "typed_atom_sha256": encoded.typed_atom_sha256})
            field_id_chain = chain_update(field_id_chain, {"role": source.role, "label": source.source_label, "field_id": encoded.field_id})
        except Exception:
            metrics["exceptions"] += 1
        processed += 1

    elapsed = round(time.time() - started, 3)
    mismatch_count = sum(metrics.values())
    proof_passed = (
        processed == args.query_limit + args.passage_limit
        and mismatch_count == 0
    )
    metrics["elapsed_seconds"] = elapsed
    metrics["encode_decode_accuracy_percent"] = 100.0 if proof_passed else round((1.0 - mismatch_count / max(1, processed)) * 100.0, 12)
    metrics["throughput_sources_per_second"] = round(processed / elapsed, 2) if elapsed else 0.0
    artifact = {
        "schema_version": SCHEMA_VERSION,
        "benchmark_kind": "encode_decode_parity_only",
        "not_a_semantic_retrieval_benchmark": True,
        "dataset": {
            "dataset_id": args.dataset_id,
            "query_count": args.query_limit,
            "passage_count": args.passage_limit,
            "encoded_decoded_source_count": processed,
            "revision": args.revision,
            "selection_rule": (
                f"deterministic first {args.query_limit} queries and first {args.passage_limit} passages "
                f"in streaming mode (requested_query_limit={args.query_limit}, requested_passage_limit={args.passage_limit})"
            ),
            "source": "huggingface",
            "streaming": True,
        },
        "machine": machine_report(),
        "metrics": metrics,
        "chains": {
            "decode_chain_sha256": decode_chain,
            "field_id_chain_sha256": field_id_chain,
            "receipt_chain_sha256": receipt_chain,
            "signal_chain_sha256": signal_chain,
            "source_chain_sha256": source_chain,
            "typed_atom_chain_sha256": typed_atom_chain,
        },
        "openencoder": {
            "binary_sha256": sha256_file(ROOT / "bin" / "OpenEncoder.com") if (ROOT / "bin" / "OpenEncoder.com").exists() else None,
            "calc_hash": None,
            "git_commit": args.git_commit,
            "python_version": platform.python_version(),
            "recipe_id": RECIPE_ID,
        },
        "proof": {
            "artifact_path": str(Path(args.output).relative_to(ROOT)) if Path(args.output).is_absolute() else args.output,
            "artifact_sha256": None,
            "proof_passed": proof_passed,
        },
    }
    artifact["proof"]["artifact_sha256"] = canonical_sha256(
        {key: value for key, value in artifact.items() if key != "proof"}
        | {"proof": {**artifact["proof"], "artifact_sha256": None}}
    )
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-id", default=DATASET_ID)
    parser.add_argument("--query-config", default="queries")
    parser.add_argument("--query-split", default="queries")
    parser.add_argument("--passage-config", default="corpus")
    parser.add_argument("--passage-split", default="corpus")
    parser.add_argument("--query-limit", type=int)
    parser.add_argument("--passage-limit", type=int)
    parser.add_argument("--limit", type=int, help="Compatibility fallback for setting both query and passage limits")
    parser.add_argument("--revision")
    parser.add_argument("--width", type=int, default=64)
    parser.add_argument("--context", default="msmarco-v2-real-parity")
    parser.add_argument("--secret", default="openencoder-msmarco-v2-real-parity-proof-secret")
    parser.add_argument("--git-commit")
    parser.add_argument("--output", default=str(DEFAULT_ARTIFACT))
    args = parser.parse_args()
    if args.limit is not None:
        args.query_limit = args.query_limit or args.limit
        args.passage_limit = args.passage_limit or args.limit
    if args.query_limit is None or args.passage_limit is None:
        raise ValueError("provide --query-limit and --passage-limit, or provide --limit")
    if args.query_limit <= 0 or args.passage_limit <= 0:
        raise ValueError("query and passage limits must be positive")
    artifact = prove(args)
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "artifact_path": str(output.relative_to(ROOT)),
        "artifact_sha256": sha256_file(output),
        "canonical_artifact_sha256": artifact["proof"]["artifact_sha256"],
        "proof_passed": artifact["proof"]["proof_passed"],
        "query_count": artifact["dataset"]["query_count"],
        "passage_count": artifact["dataset"]["passage_count"],
        "encoded_decoded_source_count": artifact["dataset"]["encoded_decoded_source_count"],
        "elapsed_seconds": artifact["metrics"]["elapsed_seconds"],
        "throughput_sources_per_second": artifact["metrics"]["throughput_sources_per_second"],
    }, indent=2, sort_keys=True))
    return 0 if artifact["proof"]["proof_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
