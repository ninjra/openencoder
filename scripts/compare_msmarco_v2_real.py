#!/usr/bin/env python3
"""Compare two MSMARCO v2 real parity artifacts for deterministic parity evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

FIELDS_TO_COMPARE = [
    "schema_version",
    "benchmark_kind",
    "not_a_semantic_retrieval_benchmark",
    "dataset.dataset_id",
    "dataset.query_count",
    "dataset.passage_count",
    "dataset.encoded_decoded_source_count",
    "openencoder.recipe_id",
    "proof.proof_passed",
    "proof.artifact_sha256",
    "metrics.text_hash_mismatches",
    "metrics.canonical_hash_mismatches",
    "metrics.typed_atom_hash_mismatches",
    "metrics.signal_replay_mismatches",
    "metrics.field_receipt_replay_mismatches",
    "metrics.field_id_replay_mismatches",
    "metrics.exceptions",
]


def get_nested(value: dict[str, Any], path: str) -> Any:
    current: Any = value
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def canonicalize_artifact(path: str) -> dict[str, Any]:
    artifact_path = Path(path)
    return json.loads(artifact_path.read_text(encoding="utf-8"))


def compare_fields(left: dict[str, Any], right: dict[str, Any]) -> list[dict[str, Any]]:
    diffs = []
    for field in FIELDS_TO_COMPARE:
        left_value = get_nested(left, field)
        right_value = get_nested(right, field)
        equal = left_value is not None and right_value is not None and left_value == right_value
        diffs.append({"field": field, "left": left_value, "right": right_value, "equal": equal})
    return diffs


def resolve_paths(args: argparse.Namespace) -> tuple[str, str]:
    left = args.left or args.artifact_a
    right = args.right or args.artifact_b
    if not left or not right:
        raise SystemExit("Provide two artifact paths, either positionally or with --left/--right.")
    return left, right


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact_a", nargs="?", help="Path to reference artifact JSON")
    parser.add_argument("artifact_b", nargs="?", help="Path to candidate artifact JSON")
    parser.add_argument("--left", help="Path to reference artifact JSON")
    parser.add_argument("--right", help="Path to candidate artifact JSON")
    parser.add_argument("--json", action="store_true", help="Emit JSON summary")
    args = parser.parse_args()

    left_path, right_path = resolve_paths(args)
    left = canonicalize_artifact(left_path)
    right = canonicalize_artifact(right_path)
    diffs = compare_fields(left, right)
    unequal = [diff for diff in diffs if not diff["equal"]]

    if args.json:
        print(json.dumps({
            "field_count": len(FIELDS_TO_COMPARE),
            "mismatch_count": len(unequal),
            "all_equal": not unequal,
            "differences": diffs,
        }, indent=2, sort_keys=True))
    elif unequal:
        print("Artifacts differ:")
        for diff in unequal:
            print(f"  {diff['field']}: {diff['left']} != {diff['right']}")
    else:
        print("Artifacts match on all comparison fields.")

    return 1 if unequal else 0


if __name__ == "__main__":
    raise SystemExit(main())
