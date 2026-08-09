#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR Commercial
"""Standalone sample client field encoder/decoder.

The script has no project imports. It emits opaque signed-int16 field signals
from local typed atoms with a client-held key and keeps a local append-only map
ledger so returned field identifiers can be resolved back to client files.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "openencoder-oezk1-request-v1"
LEDGER_SCHEMA_VERSION = "client-field-map-ledger-v1"
FIELD_RECEIPT_SCHEMA_VERSION = "openencoder-oezk1-field-receipt-v1"
REQUEST_RECEIPT_SCHEMA_VERSION = "openencoder-oezk1-request-receipt-v1"
TYPED_ATOM_SCHEMA_VERSION = "openencoder-oezk1-typed-atom-v1"
REFERENCE_RECIPE_ID = "openencoder-oezk1-signed-int16-typed-atom-v1"
REFERENCE_DTYPE = "int16"
REFERENCE_SHAPE = "dense_fixed_width"
REFERENCE_AXIS_POLICY = "hmac-sha256-typed-atom-axis-v1"
REFERENCE_WEIGHT_POLICY = "hmac-sha256-signed-int16-weight-v1"
REFERENCE_COMBINE_POLICY = "saturating_add"
INT16_FIELD_MIN = -32767
INT16_FIELD_MAX = 32767
DECODE_SCHEMA_VERSION = "openencoder-oezk1-emission-decode-v1"
ANSWER_FOLDER_DECODE_SCHEMA_VERSION = "openencoder-oezk1-answer-folder-decode-v1"
CONFIG_SCHEMA_VERSION = "openencoder-client-field-kit-config-v1"
SUBMISSION_MANIFEST_SCHEMA_VERSION = "client-field-submission-manifest-v1"
CRITICAL_INFO_TABLE_SCHEMA_VERSION = "client-field-critical-info-table-v1"
LEDGER_TIME_ENV = "CLIENT_FIELD_LEDGER_WRITTEN_AT"
TOKEN_RE = re.compile(r"[a-z0-9_]+")
FIELD_REFERENCE_KEYS = {
    "corpus_hash",
    "field_id",
    "item_id",
    "query_payload_hash",
    "record_id",
    "request_id",
}
WIRE_ROLES = {"corpus": "a", "query": "b"}
COMPATIBILITY_METADATA_KEYS = {"recipe_id", "dtype", "shape", "schema_version", "typed_atom_schema_version"}
ANSWER_TEXT_MAX_CHARS = 200_000
ANSWER_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "before",
    "by",
    "do",
    "does",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "to",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
}
CLIENT_FIELD_PROTOCOL_REQUIREMENTS = """
OpenEncoder client field protocol requirements for third-party field services:

1. The API receives only field objects, not private source text. The API emits field results plus emission_quality.
2. The local decoder owns answer recovery because it has the private ledger and source files.
3. Every corpus source and every query source MUST be written to the local append-only ledger before sending a request.
4. Every ledger field_map event MUST include role, item_id, field_id, source_label, source_path, text_sha256, signal_sha256, width, context, and calc_hash.
5. Every request_map event MUST bind the client_request_id to the sent request hash and all query field ids.
6. Every field_group_map event MUST bind the corpus_hash to all member corpus item ids and member field ids.
7. The field tensor MUST be a fixed-width list of signed int16-compatible integers. This reference kit uses width=64 by default.
8. The reference client emits signed int16 typed-atom tensors in [-32767, 32767].
9. Services MUST preserve recipe_id, dtype, shape, calc_hash, and returned references needed by the local decoder.
10. calc_hash identifies the field encoding recipe. If a third-party field service changes tokenization, typed atoms, weighting, width, modality handling, or normalization, it MUST change calc_hash.
11. corpus_hash and query_payload_hash MUST be opaque, content-bound ids that the local ledger can resolve.
12. The API response is correct only for field math. Natural-language answers MUST be decoded locally from the ledger/source files.
13. To answer image/audio/video queries, the third-party field service MUST store local answerable text such as captions, OCR, transcript, or operator-approved descriptions in the ledger. Raw binary bytes alone are not enough for a human answer.
14. The decoder MUST show the original query, the final answer in the query language/dialect, supporting source labels/excerpts, replay status, and emission quality.
15. The decoder MUST fail closed when the ledger hash chain is invalid, source files do not match recorded hashes, field ids do not resolve, encoding compatibility fails, or a query cannot be answered from local source text.
""".strip()


@dataclass(frozen=True)
class SourceItem:
    role: str
    source_label: str
    source_path: str
    text: str
    order: int


@dataclass(frozen=True)
class EncodedItem:
    source: SourceItem
    item_id: str
    field_id: str
    signal: list[int]
    text_sha256: str
    canonical_text_sha256: str
    signal_sha256: str
    typed_atom_count: int
    typed_atom_sha256: str
    field_encoding: dict[str, Any]
    field_receipt: dict[str, Any]
    field_receipt_sha256: str


def _mac(secret: bytes, *parts: object) -> bytes:
    message = "\0".join(str(part) for part in parts).encode()
    return hmac.new(secret, message, hashlib.sha256).digest()


def _tokens(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower()) or [""]


def _canonical_token_text(text: str) -> str:
    return " ".join(token for token in _tokens(text) if token)


def _typed_atoms(text: str) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    ordered_tokens = [token for token in _tokens(text) if token]
    for token in ordered_tokens:
        counts[token] = counts.get(token, 0) + 1
    atoms = [
        {"kind": "token", "value_sha256": _sha256_text(token), "count": count}
        for token, count in sorted(counts.items())
    ]
    canonical = " ".join(ordered_tokens)
    atoms.append({"kind": "canonical_text", "value_sha256": _sha256_text(canonical), "count": 1})
    atoms.append({"kind": "token_count", "value_sha256": _sha256_text(str(len(ordered_tokens))), "count": 1})
    return atoms


def _recipe_descriptor(*, width: int, context: str) -> dict[str, Any]:
    return {
        "schema_version": "openencoder-oezk1-recipe-v1",
        "recipe_id": REFERENCE_RECIPE_ID,
        "dtype": REFERENCE_DTYPE,
        "shape": REFERENCE_SHAPE,
        "width": int(width),
        "context": context,
        "typed_atom_schema_version": TYPED_ATOM_SCHEMA_VERSION,
        "axis_policy": REFERENCE_AXIS_POLICY,
        "weight_policy": REFERENCE_WEIGHT_POLICY,
        "combine_policy": REFERENCE_COMBINE_POLICY,
        "range": [INT16_FIELD_MIN, INT16_FIELD_MAX],
    }


def _field_encoding(*, width: int, context: str) -> dict[str, Any]:
    descriptor = _recipe_descriptor(width=width, context=context)
    return {
        "recipe_id": REFERENCE_RECIPE_ID,
        "dtype": REFERENCE_DTYPE,
        "shape": REFERENCE_SHAPE,
        "width": int(width),
        "typed_atom_schema_version": TYPED_ATOM_SCHEMA_VERSION,
        "axis_policy": REFERENCE_AXIS_POLICY,
        "weight_policy": REFERENCE_WEIGHT_POLICY,
        "combine_policy": REFERENCE_COMBINE_POLICY,
        "recipe_sha256": _sha256_json(descriptor),
    }


def _saturating_add(current: int, delta: int) -> int:
    return max(INT16_FIELD_MIN, min(INT16_FIELD_MAX, current + delta))


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _iter_text_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if path.is_dir():
        files = sorted(candidate for candidate in path.rglob("*") if candidate.is_file())
        if files:
            return files
        raise ValueError(f"path contains no files: {path}")
    raise ValueError(f"path does not exist: {path}")


def _source_items_from_paths(raw_paths: list[str], *, role: str, start_order: int = 0) -> list[SourceItem]:
    items: list[SourceItem] = []
    order = start_order
    for raw_path in raw_paths:
        root = Path(raw_path)
        for file_path in _iter_text_files(root):
            source_label = str(file_path if root.is_file() else file_path.relative_to(root))
            items.append(
                SourceItem(
                    role=role,
                    source_label=source_label,
                    source_path=str(file_path.resolve()),
                    text=_read_text(file_path),
                    order=order,
                )
            )
            order += 1
    return items


def _source_items_from_literals(values: list[str], *, role: str, start_order: int = 0) -> list[SourceItem]:
    return [
        SourceItem(role=role, source_label=f"{role}:literal:{start_order + idx}", source_path="", text=value, order=start_order + idx)
        for idx, value in enumerate(values)
    ]


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def requirements_command(_args: argparse.Namespace | None = None) -> dict[str, Any]:
    return {
        "schema_version": "openencoder-client-field-protocol-requirements-v1",
        "purpose": "requirements for third-party field services that want OpenEncoder field API responses to decode locally into human answers",
        "api_decoder_split": {
            "api_role": "accept field objects and emit deterministic field results plus emission_quality",
            "decoder_role": "use the private local ledger and source files to emit human-readable answers",
            "api_must_not": "synthesize private natural-language answers from opaque fields",
        },
        "human_readable_requirements": CLIENT_FIELD_PROTOCOL_REQUIREMENTS,
        "machine_readable_requirements": [
            "append_only_local_ledger_required",
            "field_map_events_bind_every_source",
            "field_group_map_binds_corpus_hash_to_members",
            "request_map_binds_client_request_id_to_payload_hash",
            "fixed_width_signed_int16_field_tensor_required",
            "typed_atom_recipe_metadata_required",
            "compatibility_gated_decode_required",
            "calc_hash_changes_when_encoding_recipe_changes",
            "local_decoder_generates_natural_language_answer",
            "non_text_modalities_require_local_answerable_text",
            "decoder_fails_closed_on_unresolved_or_hash_mismatch",
            "decoded_output_contains_monospace_table_and_txt_report",
        ],
    }


def _dig(value: Any, *keys: str) -> Any:
    current = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _display_value(value: Any, *, max_len: int = 96) -> str:
    if value is True:
        text = "true"
    elif value is False:
        text = "false"
    elif value is None:
        text = ""
    elif isinstance(value, list):
        text = ", ".join(_display_value(item, max_len=max_len) for item in value)
    elif isinstance(value, dict):
        text = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    else:
        text = str(value)
    text = " ".join(text.split())
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text


def _short_hash(value: Any) -> str:
    text = str(value or "")
    if text.startswith("sha256:"):
        digest = text.split(":", 1)[1]
        return "sha256:" + digest[:12]
    if len(text) == 64 and all(char in "0123456789abcdefABCDEF" for char in text):
        return text[:12]
    if len(text) > 28:
        return text[:25] + "..."
    return text


def _render_table(title: str, headers: list[str], rows: list[list[Any]]) -> str:
    rendered_rows = [[_display_value(cell, max_len=96) for cell in row] for row in rows]
    widths = [len(header) for header in headers]
    for row in rendered_rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(cell))
    border = "+" + "+".join("-" * (width + 2) for width in widths) + "+"

    def render_row(values: list[str]) -> str:
        return "| " + " | ".join(value.ljust(widths[idx]) for idx, value in enumerate(values)) + " |"

    lines = [title, border, render_row(headers), border]
    lines.extend(render_row(row) for row in rendered_rows)
    lines.append(border)
    return "\n".join(lines)


def _source_labels_from_decoded(decoded: dict[str, Any], *, role: str, max_labels: int = 8) -> str:
    labels: list[str] = []
    seen: set[str] = set()
    for ref in decoded.get("resolved_references") or []:
        if not isinstance(ref, dict):
            continue
        for match in ref.get("matches") or []:
            if not isinstance(match, dict):
                continue
            if match.get("role") == role and match.get("source_label"):
                label = str(match["source_label"])
                if label not in seen:
                    seen.add(label)
                    labels.append(label)
            for member in match.get("members") or []:
                if isinstance(member, dict) and member.get("role") == role and member.get("source_label"):
                    label = str(member["source_label"])
                    if label not in seen:
                        seen.add(label)
                        labels.append(label)
    if not labels:
        return "not resolved"
    suffix = f", +{len(labels) - max_labels} more" if len(labels) > max_labels else ""
    return ", ".join(labels[:max_labels]) + suffix


def _query_source_for_result(decoded: dict[str, Any], result: dict[str, Any]) -> str:
    query_payload_hash = result.get("query_payload_hash") or _dig(result, "core_result", "query_payload_hash")
    if not query_payload_hash:
        return "not resolved"
    for ref in decoded.get("resolved_references") or []:
        if not isinstance(ref, dict) or ref.get("value") != query_payload_hash:
            continue
        for match in ref.get("matches") or []:
            if isinstance(match, dict) and match.get("role") == "query" and match.get("source_label"):
                return str(match["source_label"])
    return "not resolved"


def _critical_status(value: Any) -> str:
    return "yes" if value is True else "no" if value is False else "unknown"


def _percent(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "0.0%"
    return f"{(float(numerator) / float(denominator)) * 100.0:.1f}%"


def _pass_fail(value: bool) -> str:
    return "PASS" if value else "FAIL"


def _resolved_entries(decoded: dict[str, Any], *, role: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for ref in decoded.get("resolved_references") or []:
        if not isinstance(ref, dict):
            continue
        for match in ref.get("matches") or []:
            if not isinstance(match, dict):
                continue
            candidates = list(match.get("members") or []) if match.get("event_type") == "field_group_map" else [match]
            for candidate in candidates:
                if not isinstance(candidate, dict) or candidate.get("role") != role:
                    continue
                identity = str(candidate.get("item_id") or candidate.get("field_id") or candidate.get("source_path") or "")
                if identity and identity in seen:
                    continue
                if identity:
                    seen.add(identity)
                entries.append(candidate)
    return entries


def _query_entry_for_hash(decoded: dict[str, Any], query_hash: str) -> dict[str, Any] | None:
    for ref in decoded.get("resolved_references") or []:
        if not isinstance(ref, dict) or ref.get("value") != query_hash:
            continue
        for match in ref.get("matches") or []:
            if isinstance(match, dict) and match.get("role") == "query":
                return match
    return None


def _read_entry_text(entry: dict[str, Any]) -> tuple[str, bool]:
    if isinstance(entry.get("text"), str):
        return str(entry["text"]), True
    source_path = entry.get("source_path")
    if not isinstance(source_path, str) or not source_path:
        return "", False
    path = Path(source_path)
    if not path.exists():
        return "", False
    try:
        text = path.read_text(encoding="utf-8", errors="replace")[:ANSWER_TEXT_MAX_CHARS]
    except OSError:
        return "", False
    expected = str(entry.get("text_sha256") or "")
    return text, bool(expected and _sha256_text(text if len(text) < ANSWER_TEXT_MAX_CHARS else path.read_text(encoding="utf-8", errors="replace")) == expected)


def _answer_tokens(text: str) -> set[str]:
    return {token for token in _tokens(text) if token and token not in ANSWER_STOPWORDS and len(token) > 1}


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [" ".join(part.split()) for part in parts if part.strip()]


def _best_local_answer(query_text: str, corpus_entries: list[dict[str, Any]]) -> dict[str, Any]:
    query_tokens = _answer_tokens(query_text)
    if not query_tokens:
        return {"answer_text": "", "status": "query_text_unavailable", "score": 0}
    best: dict[str, Any] = {"answer_text": "", "status": "no_supporting_source_text", "score": 0}
    for entry in corpus_entries:
        source_text, source_ok = _read_entry_text(entry)
        if not source_ok or not source_text.strip():
            continue
        for sentence in _sentences(source_text)[:200]:
            sentence_tokens = _answer_tokens(sentence)
            overlap = query_tokens & sentence_tokens
            score = (len(overlap) * 100) + min(len(sentence_tokens), 25)
            if score > int(best.get("score") or 0):
                best = {
                    "answer_text": sentence,
                    "answer_source_label": entry.get("source_label") or "",
                    "answer_source_path": entry.get("source_path") or "",
                    "matched_query_terms": sorted(overlap),
                    "status": "answered_from_local_source",
                    "score": score,
                }
    return best


def _local_answer_report(decoded: dict[str, Any]) -> dict[str, Any]:
    emission = dict(decoded.get("emission") or {}) if isinstance(decoded.get("emission"), dict) else {}
    query_results = emission.get("query_results")
    if not isinstance(query_results, list) or not query_results:
        query_results = [{"query_index": 0, "core_result": emission.get("core_result") or {}}]
    corpus_entries = _resolved_entries(decoded, role="corpus")
    rows = []
    for idx, result in enumerate(query_results):
        if not isinstance(result, dict):
            continue
        result_core = dict(result.get("core_result") or {}) if isinstance(result.get("core_result"), dict) else {}
        query_hash = str(result.get("query_payload_hash") or result_core.get("query_payload_hash") or "")
        query_entry = _query_entry_for_hash(decoded, query_hash) if query_hash else None
        query_text, query_ok = _read_entry_text(query_entry or {}) if query_entry else ("", False)
        answer = _best_local_answer(query_text, corpus_entries) if query_ok else {"answer_text": "", "status": "query_source_text_unavailable", "score": 0}
        replay_verified = _dig(result, "determinism_verification", "verified")
        if replay_verified is None and len(query_results) == 1:
            replay_verified = _dig(emission, "determinism_boundary", "deterministic_replay_supported")
        answered = bool(answer.get("answer_text")) and answer.get("status") == "answered_from_local_source"
        rows.append(
            {
                "query_index": result.get("query_index", idx),
                "query_source_label": (query_entry or {}).get("source_label") or "not resolved",
                "query_payload_hash": query_hash,
                "query_text": " ".join(query_text.split()) if query_ok else "",
                "answer_text": answer.get("answer_text") or "",
                "answer_source_label": answer.get("answer_source_label") or "",
                "matched_query_terms": answer.get("matched_query_terms") or [],
                "status": "answered" if answered else str(answer.get("status") or "not_answered"),
                "replay_verified": replay_verified is True,
                "source_hash_verified": query_ok,
            }
        )
    compatibility = dict(decoded.get("compatibility") or {}) if isinstance(decoded.get("compatibility"), dict) else {}
    compatibility_passed = compatibility.get("passed") is True
    all_answered = bool(rows) and compatibility_passed and all(row["status"] == "answered" and row["replay_verified"] for row in rows)
    question_count = len(rows)
    answered_count = sum(1 for row in rows if row["status"] == "answered")
    replay_verified_count = sum(1 for row in rows if row["replay_verified"])
    source_hash_verified_count = sum(1 for row in rows if row["source_hash_verified"])
    query_resolved_count = sum(1 for row in rows if row["query_source_label"] != "not resolved")
    ledger_valid = _dig(decoded, "ledger", "hash_chain_valid") is True
    unresolved_count = int(decoded.get("unresolved_field_like_reference_count") or 0)
    human_success_score = 100.0 if all_answered and ledger_valid else min(
        99.0,
        (
            (answered_count / question_count if question_count else 0.0)
            + (replay_verified_count / question_count if question_count else 0.0)
            + (source_hash_verified_count / question_count if question_count else 0.0)
            + (1.0 if ledger_valid else 0.0)
        )
        * 25.0,
    )
    return {
        "schema_version": "client-field-local-answer-report-v1",
        "answer_language_policy": "answer_text is quoted from the client's local source text, preserving the source language/dialect; third-party field services must store answerable text for non-text sources",
        "all_questions_answered": all_answered,
        "answered_count": answered_count,
        "question_count": question_count,
        "replay_verified_count": replay_verified_count,
        "source_hash_verified_count": source_hash_verified_count,
        "query_resolved_count": query_resolved_count,
        "ledger_hash_chain_valid": ledger_valid,
        "unresolved_field_like_reference_count": unresolved_count,
        "compatibility_passed": compatibility_passed,
        "compatibility_blocker_count": int(compatibility.get("blocker_count") or 0),
        "compatibility_blockers": compatibility.get("blockers") or [],
        "answer_coverage_percent": _percent(answered_count, question_count),
        "replay_coverage_percent": _percent(replay_verified_count, question_count),
        "source_hash_coverage_percent": _percent(source_hash_verified_count, question_count),
        "query_resolution_percent": _percent(query_resolved_count, question_count),
        "human_success_score_percent": round(human_success_score, 1),
        "human_verdict": "PASS: every question has a verified local answer and replay proof" if all_answered and ledger_valid else "FAIL: not every question has a verified local answer, replay proof, and compatible encoding",
        "accuracy_claim": "100_percent_local_answered" if all_answered else "not_all_questions_answered_from_local_sources",
        "rows": rows,
    }


def _emission_performance_breakdown(emission: dict[str, Any]) -> dict[str, Any]:
    performance = emission.get("performance") if isinstance(emission.get("performance"), dict) else {}
    quality_performance = _dig(emission, "emission_quality", "performance")
    quality_performance = dict(quality_performance) if isinstance(quality_performance, dict) else {}
    core_total = performance.get("core_calc_elapsed_ms_total")
    if core_total is None:
        query_results = [row for row in emission.get("query_results") or [] if isinstance(row, dict)]
        core_values = []
        for row in query_results:
            value = _dig(row, "core_result", "elapsed_ms")
            if isinstance(value, int | float):
                core_values.append(float(value))
        core_total = round(sum(core_values), 4) if core_values else None
    api_elapsed = performance.get("api_elapsed_ms", quality_performance.get("api_elapsed_ms"))
    overhead = performance.get("api_overhead_elapsed_ms")
    if overhead is None and isinstance(api_elapsed, int | float) and isinstance(core_total, int | float):
        overhead = round(max(0.0, float(api_elapsed) - float(core_total)), 4)
    return {
        "api_elapsed_ms": api_elapsed,
        "core_calc_elapsed_ms_total": core_total,
        "api_overhead_elapsed_ms": overhead,
        "ultra_minimal_time_passed": performance.get("ultra_minimal_time_passed", quality_performance.get("ultra_minimal_time_passed")),
    }


def _customer_success_scoreboard(decoded: dict[str, Any]) -> str:
    emission = dict(decoded.get("emission") or {}) if isinstance(decoded.get("emission"), dict) else {}
    report = dict(decoded.get("local_answer_report") or {}) if isinstance(decoded.get("local_answer_report"), dict) else {}
    question_count = int(report.get("question_count") or 0)
    answered_count = int(report.get("answered_count") or 0)
    replay_count = int(report.get("replay_verified_count") or 0)
    source_count = int(report.get("source_hash_verified_count") or 0)
    query_count = int(report.get("query_resolved_count") or 0)
    perf = _emission_performance_breakdown(emission)
    quality = emission.get("emission_quality") if isinstance(emission.get("emission_quality"), dict) else {}
    accuracy = quality.get("accuracy") if isinstance(quality.get("accuracy"), dict) else {}
    validity = quality.get("validity") if isinstance(quality.get("validity"), dict) else {}
    mandatory_bar = quality.get("mandatory_emission_bar") if isinstance(quality.get("mandatory_emission_bar"), dict) else emission.get("mandatory_emission_bar")
    mandatory_bar = dict(mandatory_bar) if isinstance(mandatory_bar, dict) else {}
    system_full_bar = emission.get("system_full_bar_proof") if isinstance(emission.get("system_full_bar_proof"), dict) else {}
    accuracy_metrics = accuracy.get("metrics") if isinstance(accuracy.get("metrics"), dict) else {}
    benchmark_metric_present = any(str(key).split("@", 1)[0] in {"p", "fp", "recall", "hit_rate", "mrr", "ndcg", "gndcg"} for key in accuracy_metrics)
    rows = [
        ["Field emission", "withheld by failure gate" if emission.get("field_emission_withheld") is True else "emitted", _pass_fail(emission.get("field_emission_withheld") is not True)],
        ["Overall verdict", report.get("human_verdict") or "FAIL: no local answer report", _pass_fail(bool(report.get("all_questions_answered")) and bool(report.get("ledger_hash_chain_valid")))],
        ["Questions answered", f"{answered_count}/{question_count} ({report.get('answer_coverage_percent') or '0.0%'})", _pass_fail(question_count > 0 and answered_count == question_count)],
        ["Query files verified", f"{query_count}/{question_count} ({report.get('query_resolution_percent') or '0.0%'})", _pass_fail(question_count > 0 and query_count == question_count)],
        ["Source hashes verified", f"{source_count}/{question_count} ({report.get('source_hash_coverage_percent') or '0.0%'})", _pass_fail(question_count > 0 and source_count == question_count)],
        ["API replay verified", f"{replay_count}/{question_count} ({report.get('replay_coverage_percent') or '0.0%'})", _pass_fail(question_count > 0 and replay_count == question_count)],
        ["Ledger integrity", f"hash_chain_valid={_critical_status(report.get('ledger_hash_chain_valid'))}", _pass_fail(bool(report.get("ledger_hash_chain_valid")))],
        ["Mandatory API bar", f"passed={_critical_status(mandatory_bar.get('passed'))}; blockers={', '.join(mandatory_bar.get('blockers') or []) or 'none'}", _pass_fail(mandatory_bar.get("passed") is True)],
        ["API field accuracy", f"score_floor={accuracy.get('score_floor', 'not reported')}; evidence={accuracy.get('evidence_type') or 'not reported'}", _pass_fail(accuracy.get("proven_100_percent") is True)],
        ["API validity", f"validity_score={validity.get('validity_score', 'not reported')}", _pass_fail(validity.get("deterministically_valid") is True)],
        ["System full bar", f"proof_passed={_critical_status(system_full_bar.get('proof_passed'))}; independent={_critical_status(system_full_bar.get('independently_verified'))}", _pass_fail(system_full_bar.get("proof_passed") is True)],
        ["API quality fields", f"all_three_reported={_critical_status(quality.get('all_three_reported'))}", _pass_fail(quality.get("all_three_reported") is True)],
        ["API time", f"{perf.get('api_elapsed_ms', 'not reported')} ms total", _pass_fail(perf.get("ultra_minimal_time_passed") is True)],
        ["Core field math time", f"{perf.get('core_calc_elapsed_ms_total', 'not reported')} ms", "INFO"],
        ["API overhead", f"{perf.get('api_overhead_elapsed_ms', 'not reported')} ms", "INFO"],
        ["Benchmark relevance", f"P@K/gNDCG present={_critical_status(benchmark_metric_present)}; reason={accuracy.get('unavailable_reason') or 'reported'}", "INFO"],
        ["Independent verification", "not independently verified; explicitly flagged", "INFO"],
        ["Cryptographic full OO", f"separate external claim passed={_critical_status(quality.get('full_oblivious_oracle_claim_passed'))}", "INFO"],
        ["Human success score", f"{report.get('human_success_score_percent', 0.0)}%", _pass_fail(float(report.get("human_success_score_percent") or 0.0) >= 100.0)],
    ]
    return _render_table("Customer Proof Scoreboard", ["Check", "Result", "Status"], rows)


def _answer_critical_info_table(decoded: dict[str, Any], *, answer_path: str = "") -> str:
    emission = dict(decoded.get("emission") or {}) if isinstance(decoded.get("emission"), dict) else {}
    core_result = dict(emission.get("core_result") or {}) if isinstance(emission.get("core_result"), dict) else {}
    determinism = dict(emission.get("determinism_boundary") or {}) if isinstance(emission.get("determinism_boundary"), dict) else {}
    corporate_proof = (
        dict(emission.get("corporate_field_groth16_proof") or {})
        if isinstance(emission.get("corporate_field_groth16_proof"), dict)
        else {}
    )
    openencoder_status_value = _dig(emission, "openencoder_answer_field", "status")
    openencoder_status = dict(openencoder_status_value) if isinstance(openencoder_status_value, dict) else {}
    claim_boundary_value = emission.get("claim_boundary") or _dig(emission, "openencoder_answer_field", "claim_boundary")
    claim_boundary = dict(claim_boundary_value) if isinstance(claim_boundary_value, dict) else {}
    replay_verified = determinism.get("same_normalized_inputs_same_core_build_same_outputs")
    if replay_verified is None:
        replay_rows = [row for row in determinism.get("replay_verifications") or [] if isinstance(row, dict)]
        replay_verified = all(row.get("verified") is True for row in replay_rows) if replay_rows else None
    summary_rows = [
        ["Answer path", answer_path or "direct emission"],
        ["Object", emission.get("object") or "unknown"],
        ["Channel", emission.get("channel") or core_result.get("channel") or "unknown"],
        ["Query mode/count", f"{emission.get('query_mode') or 'single'} / {emission.get('query_count') or core_result.get('process_query_count') or 'unknown'}"],
        ["Ledger", f"hash_chain_valid={_critical_status(_dig(decoded, 'ledger', 'hash_chain_valid'))}; events={_dig(decoded, 'ledger', 'event_count') or 0}"],
        ["Resolved refs", f"{decoded.get('resolved_reference_count') or 0} resolved; {decoded.get('unresolved_field_like_reference_count') or 0} unresolved"],
        ["Corpus sources", _source_labels_from_decoded(decoded, role="corpus")],
        ["Query sources", _source_labels_from_decoded(decoded, role="query")],
        ["Deterministic replay", _critical_status(replay_verified)],
        ["Full ZK proof claim", _critical_status(emission.get("full_zk_proof_claim"))],
        ["OpenEncoder ready", _critical_status(openencoder_status.get("openencoder_ready"))],
        ["Groth16 proof", f"requested={_critical_status(corporate_proof.get('proof_requested'))}; ready={_critical_status(corporate_proof.get('proof_ready'))}"],
        ["Alignment score", core_result.get("alignment_score")],
        ["Positive/negative", f"{core_result.get('positive_alignment_score')} / {core_result.get('negative_alignment_score')}"],
        ["Corpus hash", _short_hash(core_result.get("corpus_hash"))],
        ["Result hash", _short_hash(core_result.get("result_field_sha256"))],
        ["Emission hash", _short_hash(decoded.get("emission_sha256"))],
        ["Claim boundary", claim_boundary.get("honest_label") or claim_boundary.get("claim_supported") or "not declared"],
    ]
    query_rows = []
    answer_rows = []
    answer_report = dict(decoded.get("local_answer_report") or {}) if isinstance(decoded.get("local_answer_report"), dict) else {}
    for row in answer_report.get("rows") or []:
        if not isinstance(row, dict):
            continue
        answer_rows.append(
            [
                row.get("query_index"),
                row.get("query_source_label"),
                row.get("answer_text") or row.get("status"),
                row.get("answer_source_label"),
                _critical_status(row.get("replay_verified")),
            ]
        )
    query_results = emission.get("query_results") or []
    if isinstance(query_results, list):
        for idx, result in enumerate(query_results[:10]):
            if not isinstance(result, dict):
                continue
            result_core = dict(result.get("core_result") or {}) if isinstance(result.get("core_result"), dict) else {}
            query_rows.append(
                [
                    result.get("query_index", idx),
                    _query_source_for_result(decoded, result),
                    result_core.get("alignment_score", ""),
                    _critical_status(_dig(result, "determinism_verification", "verified")),
                    _short_hash(result_core.get("result_field_sha256")),
                ]
            )
    tables = [
        _customer_success_scoreboard(decoded),
        _render_table("Critical Info", ["Field", "Value"], summary_rows),
    ]
    if answer_rows:
        tables.append(_render_table("Decoded Natural-Language Answers", ["Query", "Question file", "Answer", "Source", "Replay"], answer_rows))
    if query_rows:
        tables.append(_render_table("Query Results", ["Query", "Source", "Alignment", "Replay", "Result hash"], query_rows))
    return "\n\n".join(tables)


def _folder_critical_info_table(decoded_answers: list[dict[str, Any]]) -> str:
    rows = []
    for idx, item in enumerate(decoded_answers):
        decoded = dict(item.get("decoded") or {}) if isinstance(item.get("decoded"), dict) else {}
        emission = dict(decoded.get("emission") or {}) if isinstance(decoded.get("emission"), dict) else {}
        corporate_proof = dict(emission.get("corporate_field_groth16_proof") or {}) if isinstance(emission.get("corporate_field_groth16_proof"), dict) else {}
        openencoder_ready = _dig(emission, "openencoder_answer_field", "status", "openencoder_ready")
        deterministic = _dig(emission, "determinism_boundary", "same_normalized_inputs_same_core_build_same_outputs")
        rows.append(
            [
                idx,
                Path(str(item.get("answer_path") or "")).name or "direct emission",
                emission.get("object") or "unknown",
                emission.get("query_count") or _dig(emission, "core_result", "process_query_count") or "unknown",
                decoded.get("resolved_reference_count") or 0,
                _critical_status(deterministic),
                _critical_status(openencoder_ready),
                _critical_status(corporate_proof.get("proof_ready")),
            ]
        )
    return _render_table(
        "Decoded Answers Summary",
        ["#", "Answer", "Object", "Queries", "Refs", "Replay", "OE", "Proof"],
        rows,
    )


def _decode_text_report(payload: dict[str, Any]) -> str:
    parts = []
    if payload.get("critical_info_table"):
        parts.append(str(payload["critical_info_table"]))
    if isinstance(payload.get("decoded_answers"), list):
        for item in payload["decoded_answers"]:
            if isinstance(item, dict) and isinstance(item.get("decoded"), dict) and item["decoded"].get("critical_info_table"):
                parts.append(str(item["decoded"]["critical_info_table"]))
    return "\n\n".join(parts)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _config_path(raw_path: str, *, base: Path) -> str:
    path = Path(raw_path)
    return str(path if path.is_absolute() else base / path)


def _default_frozen_config() -> str | None:
    if not getattr(sys, "frozen", False):
        return None
    config_path = Path(sys.executable).resolve().parent / "config.json"
    return str(config_path) if config_path.exists() else None


def _config_path_list(config: dict[str, Any], key: str, *, base: Path) -> list[str]:
    values = config.get(key)
    if values is None:
        return []
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, list):
        raise ValueError(f"{key} must be a path string or list of path strings")
    return [_config_path(str(value), base=base) for value in values]


def _apply_config(args: argparse.Namespace, *, command: str) -> argparse.Namespace:
    args.config_base = ""
    if not args.config:
        if args.ledger is None:
            args.ledger = "client_field_ledger.jsonl"
        return args
    config_path = Path(args.config).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") not in (None, CONFIG_SCHEMA_VERSION):
        raise ValueError(f"unsupported config schema: {config.get('schema_version')}")
    base = config_path.parent
    args.config_base = str(base)
    if not args.corpus_path:
        args.corpus_path = _config_path_list(config, "corpus_paths", base=base)
    if not args.query_path:
        args.query_path = _config_path_list(config, "query_paths", base=base)
    if not args.answers_path and config.get("answers_path"):
        args.answers_path = _config_path(str(config["answers_path"]), base=base)
    if not args.secret and config.get("client_secret"):
        args.secret = str(config["client_secret"])
    if args.secret_env == "CLIENT_SIGNAL_SECRET" and config.get("secret_env"):
        args.secret_env = str(config["secret_env"])
    if args.context == "default" and config.get("context"):
        args.context = str(config["context"])
    if args.width == 64 and config.get("width") is not None:
        args.width = int(config["width"])
    if args.limit == 10 and config.get("limit") is not None:
        args.limit = int(config["limit"])
    if args.ledger is None:
        args.ledger = _config_path(str(config.get("ledger") or "client_field_ledger.jsonl"), base=base)
    if not args.submission_manifest_output and config.get("submission_manifest_output"):
        args.submission_manifest_output = _config_path(str(config["submission_manifest_output"]), base=base)
    if not args.request_output and config.get("request_output"):
        args.request_output = _config_path(str(config["request_output"]), base=base)
    if not args.decode_output and config.get("decode_output"):
        args.decode_output = _config_path(str(config["decode_output"]), base=base)
    if not args.output:
        args.output = args.decode_output if command == "decode" else args.request_output
    return args


def _client_display_path(raw_path: str, args: argparse.Namespace) -> str:
    base_text = str(getattr(args, "config_base", "") or "")
    base = Path(base_text) if base_text else None
    path = Path(raw_path)
    if base is not None and path.is_absolute():
        try:
            return str(path.resolve().relative_to(base.resolve()))
        except ValueError:
            return str(path)
    return str(path)


def _sendable_filename(raw_path: str) -> str:
    if not raw_path or raw_path == "stdout":
        return "stdout"
    return Path(raw_path).name


def _public_source_refs(items: list[EncodedItem]) -> list[dict[str, Any]]:
    return [
        {
            "role": item.source.role,
            "source_ref": item.item_id,
            "field_id": item.field_id,
            "source_order": item.source.order,
        }
        for item in items
    ]


def encode_texts(texts: list[str], *, secret: bytes, width: int, role: str, context: str) -> list[int]:
    if width <= 0:
        raise ValueError("width must be positive")
    accumulator = [0] * width
    for doc_index, text in enumerate(texts):
        for atom in _typed_atoms(text):
            atom_hash = atom["value_sha256"]
            count = int(atom["count"])
            axis_digest = _mac(secret, REFERENCE_RECIPE_ID, context, role, doc_index, atom["kind"], atom_hash, "axis")
            weight_digest = _mac(secret, REFERENCE_RECIPE_ID, context, role, doc_index, atom["kind"], atom_hash, "weight")
            axis = int.from_bytes(axis_digest[:8], "big", signed=False) % width
            magnitude = 1 + (int.from_bytes(weight_digest[:2], "big", signed=False) % 1024)
            sign = 1 if weight_digest[2] & 1 else -1
            accumulator[axis] = _saturating_add(accumulator[axis], sign * magnitude * max(1, count))
    return accumulator


def _item_id(secret: bytes, *, source: SourceItem, context: str) -> str:
    digest = hmac.new(
        secret,
        _canonical_json_bytes(
            {
                "context": context,
                "role": source.role,
                "source_label": source.source_label,
                "source_path": source.source_path,
                "text_sha256": _sha256_text(source.text),
            }
        ),
        hashlib.sha256,
    ).hexdigest()
    return f"client-item:{digest[:40]}"


def _opaque_id(secret: bytes, *, context: str, role: str, texts: list[str], signal: list[int]) -> str:
    payload = json.dumps(
        {
            "recipe_id": REFERENCE_RECIPE_ID,
            "context": context,
            "role": role,
            "canonical_text_sha256s": [_sha256_text(_canonical_token_text(text)) for text in texts],
            "typed_atom_sha256s": [_sha256_json(_typed_atoms(text)) for text in texts],
            "signal": signal,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return "sha256:" + hmac.new(secret, payload, hashlib.sha256).hexdigest()


def _field_receipt(
    *,
    source: SourceItem,
    item_id: str,
    field_id: str,
    width: int,
    context: str,
    calc_hash: str,
    signal: list[int],
) -> dict[str, Any]:
    atoms = _typed_atoms(source.text)
    return {
        "schema_version": FIELD_RECEIPT_SCHEMA_VERSION,
        "recipe_id": REFERENCE_RECIPE_ID,
        "dtype": REFERENCE_DTYPE,
        "shape": REFERENCE_SHAPE,
        "role": source.role,
        "item_id": item_id,
        "field_id": field_id,
        "text_sha256": _sha256_text(source.text),
        "canonical_text_sha256": _sha256_text(_canonical_token_text(source.text)),
        "typed_atom_sha256": _sha256_json(atoms),
        "typed_atom_count": len(atoms),
        "signal_sha256": _sha256_json(signal),
        "width": int(width),
        "context": context,
        "calc_hash": calc_hash,
    }


def encode_source_item(source: SourceItem, *, secret: bytes, width: int, context: str) -> EncodedItem:
    wire_role = WIRE_ROLES.get(source.role, source.role)
    signal = encode_texts([source.text], secret=secret, width=width, role=wire_role, context=context)
    calc_hash = _calc_label(secret, width=width, context=context)
    field_id = _opaque_id(secret, context=context, role=wire_role, texts=[source.text], signal=signal)
    receipt = _field_receipt(
        source=source,
        item_id=_item_id(secret, source=source, context=context),
        field_id=field_id,
        width=width,
        context=context,
        calc_hash=calc_hash,
        signal=signal,
    )
    return EncodedItem(
        source=source,
        item_id=str(receipt["item_id"]),
        field_id=field_id,
        signal=signal,
        text_sha256=str(receipt["text_sha256"]),
        canonical_text_sha256=str(receipt["canonical_text_sha256"]),
        signal_sha256=str(receipt["signal_sha256"]),
        typed_atom_count=int(receipt["typed_atom_count"]),
        typed_atom_sha256=str(receipt["typed_atom_sha256"]),
        field_encoding=_field_encoding(width=width, context=context),
        field_receipt=receipt,
        field_receipt_sha256=_sha256_json(receipt),
    )


def _calc_label(secret: bytes, *, width: int, context: str) -> str:
    digest = hmac.new(secret, _canonical_json_bytes(_recipe_descriptor(width=width, context=context)), hashlib.sha256).hexdigest()
    return f"{REFERENCE_RECIPE_ID}:{digest[:32]}"


def build_request(
    *,
    corpus_texts: list[str],
    query_texts: list[str],
    secret: bytes,
    width: int,
    limit: int,
    context: str,
) -> dict[str, object]:
    calc_hash = _calc_label(secret, width=width, context=context)
    corpus_signal = encode_texts(corpus_texts, secret=secret, width=width, role="a", context=context)
    corpus_atoms = [atom for text in corpus_texts for atom in _typed_atoms(text)]
    request: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "field_encoding": _field_encoding(width=width, context=context),
        "corpus_field": {
            "corpus_hash": _opaque_id(secret, context=context, role="a", texts=corpus_texts, signal=corpus_signal),
            "calc_hash": calc_hash,
            "field_tensor": corpus_signal,
            "field_encoding": _field_encoding(width=width, context=context),
            "typed_atom_count": len(corpus_atoms),
            "typed_atom_sha256": _sha256_json(corpus_atoms),
            "signal_sha256": _sha256_json(corpus_signal),
        },
        "limit": int(limit),
    }
    query_fields = []
    for query_text in query_texts:
        query_signal = encode_texts([query_text], secret=secret, width=width, role="b", context=context)
        query_atoms = _typed_atoms(query_text)
        query_fields.append(
            {
                "query_payload_hash": _opaque_id(secret, context=context, role="b", texts=[query_text], signal=query_signal),
                "calc_hash": calc_hash,
                "field_tensor": query_signal,
                "field_encoding": _field_encoding(width=width, context=context),
                "typed_atom_count": len(query_atoms),
                "typed_atom_sha256": _sha256_json(query_atoms),
                "signal_sha256": _sha256_json(query_signal),
            }
        )
    if len(query_fields) == 1:
        request["query_field"] = query_fields[0]
    else:
        request["query_fields"] = query_fields
    return request


def _last_ledger_state(path: Path) -> tuple[int, str]:
    if not path.exists():
        return 0, ""
    sequence = 0
    last_hash = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        sequence += 1
        event = json.loads(line)
        last_hash = str(event.get("event_hash") or "")
    return sequence, last_hash


def _ledger_event_hash(event: dict[str, Any]) -> str:
    payload = {key: value for key, value in event.items() if key != "event_hash"}
    return _sha256_json(payload)


def append_ledger_event(path: Path, event: dict[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    sequence, previous_hash = _last_ledger_state(path)
    written_at = os.environ.get(LEDGER_TIME_ENV) or datetime.now(UTC).isoformat()
    entry = {
        "schema_version": LEDGER_SCHEMA_VERSION,
        "sequence": sequence + 1,
        "previous_event_hash": previous_hash,
        "written_at": written_at,
        **event,
    }
    entry["event_hash"] = _ledger_event_hash(entry)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
    return entry


def load_ledger_events(path: Path) -> tuple[list[dict[str, Any]], bool]:
    if not path.exists():
        raise ValueError(f"ledger does not exist: {path}")
    events: list[dict[str, Any]] = []
    previous_hash = ""
    hash_chain_valid = True
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        event = json.loads(line)
        if event.get("sequence") != len(events) + 1:
            hash_chain_valid = False
        if event.get("previous_event_hash") != previous_hash:
            hash_chain_valid = False
        if event.get("event_hash") != _ledger_event_hash(event):
            hash_chain_valid = False
        if event.get("schema_version") != LEDGER_SCHEMA_VERSION:
            raise ValueError(f"unsupported ledger schema on line {line_number}: {event.get('schema_version')}")
        previous_hash = str(event.get("event_hash") or "")
        events.append(event)
    return events, hash_chain_valid


def _event_aliases(event: dict[str, Any]) -> list[str]:
    aliases = []
    event_type = event.get("event_type")
    keys = ("request_id", "request_sha256") if event_type == "request_map" else ("field_id", "item_id")
    for key in keys:
        value = event.get(key)
        if isinstance(value, str) and value:
            aliases.append(value)
    return aliases


def ledger_alias_index(events: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        for alias in _event_aliases(event):
            index.setdefault(alias, []).append(event)
    return index


def _ledger_item_event(encoded: EncodedItem, *, request_id: str, width: int, context: str, calc_hash: str) -> dict[str, Any]:
    return {
        "event_type": "field_map",
        "request_id": request_id,
        "role": encoded.source.role,
        "item_id": encoded.item_id,
        "field_id": encoded.field_id,
        "source_label": encoded.source.source_label,
        "source_path": encoded.source.source_path,
        "source_order": encoded.source.order,
        "text_sha256": encoded.text_sha256,
        "byte_count": len(encoded.source.text.encode()),
        "token_count": len(_tokens(encoded.source.text)),
        "signal_sha256": encoded.signal_sha256,
        "canonical_text_sha256": encoded.canonical_text_sha256,
        "typed_atom_schema_version": TYPED_ATOM_SCHEMA_VERSION,
        "typed_atom_count": encoded.typed_atom_count,
        "typed_atom_sha256": encoded.typed_atom_sha256,
        "recipe_id": REFERENCE_RECIPE_ID,
        "dtype": REFERENCE_DTYPE,
        "shape": REFERENCE_SHAPE,
        "field_encoding": encoded.field_encoding,
        "field_receipt": encoded.field_receipt,
        "field_receipt_sha256": encoded.field_receipt_sha256,
        "width": int(width),
        "context": context,
        "calc_hash": calc_hash,
    }


def write_encode_ledger(
    *,
    ledger_path: Path,
    request: dict[str, Any],
    request_id: str,
    request_output_path: str,
    corpus_items: list[EncodedItem],
    query_items: list[EncodedItem],
    width: int,
    context: str,
) -> None:
    calc_hash = str(request["corpus_field"]["calc_hash"])
    for encoded in corpus_items + query_items:
        append_ledger_event(ledger_path, _ledger_item_event(encoded, request_id=request_id, width=width, context=context, calc_hash=calc_hash))
    append_ledger_event(
        ledger_path,
        {
            "event_type": "field_group_map",
            "request_id": request_id,
            "role": "corpus",
            "field_id": str(request["corpus_field"]["corpus_hash"]),
            "member_item_ids": [item.item_id for item in corpus_items],
            "member_field_ids": [item.field_id for item in corpus_items],
            "member_count": len(corpus_items),
            "signal_sha256": _sha256_json(request["corpus_field"]["field_tensor"]),
            "recipe_id": REFERENCE_RECIPE_ID,
            "dtype": REFERENCE_DTYPE,
            "shape": REFERENCE_SHAPE,
            "field_encoding": _field_encoding(width=width, context=context),
            "width": int(width),
            "context": context,
            "calc_hash": calc_hash,
        },
    )
    query_field_payloads = request.get("query_fields") or [request.get("query_field")]
    query_field_ids = [str(item["query_payload_hash"]) for item in query_field_payloads if isinstance(item, dict)]
    append_ledger_event(
        ledger_path,
        {
            "event_type": "request_map",
            "request_id": request_id,
            "request_sha256": _sha256_json(request),
            "request_output_path": request_output_path,
            "corpus_field_id": str(request["corpus_field"]["corpus_hash"]),
            "query_field_ids": query_field_ids,
            "corpus_item_count": len(corpus_items),
            "query_item_count": len(query_items),
            "recipe_id": REFERENCE_RECIPE_ID,
            "dtype": REFERENCE_DTYPE,
            "shape": REFERENCE_SHAPE,
            "field_encoding": _field_encoding(width=width, context=context),
            "request_receipt": request.get("request_receipt"),
            "request_receipt_sha256": _sha256_json(request.get("request_receipt")),
            "width": int(width),
            "context": context,
            "calc_hash": calc_hash,
        },
    )


def build_submission_manifest(
    *,
    request: dict[str, Any],
    request_output_path: str,
    submission_manifest_output_path: str,
    ledger_path: str,
    corpus_items: list[EncodedItem],
    query_items: list[EncodedItem],
    answers_path: str,
    decode_output_path: str,
) -> dict[str, Any]:
    del ledger_path, answers_path, decode_output_path
    return {
        "schema_version": SUBMISSION_MANIFEST_SCHEMA_VERSION,
        "sendable_files": [_sendable_filename(request_output_path), _sendable_filename(submission_manifest_output_path)],
        "primary_payload_file": _sendable_filename(request_output_path),
        "api_endpoint": "/v1/openencoder/field-request",
        "client_request_id": request.get("client_request_id"),
        "request_sha256": _sha256_json(request),
        "client_metering": {
            "pseudonym_id": _dig(request, "client_metering", "pseudonym_id"),
            "pseudonym_source": _dig(request, "client_metering", "pseudonym_source"),
            "raw_fields_must_not_be_persisted_for_billing": _dig(request, "client_metering", "raw_fields_must_not_be_persisted_for_billing"),
        },
        "corpus_item_count": len(corpus_items),
        "query_item_count": len(query_items),
        "corpus_source_refs": _public_source_refs(corpus_items),
        "query_source_refs": _public_source_refs(query_items),
        "source_labels_redacted": True,
        "paths_redacted": True,
        "client_local_only": {
            "ledger_required": True,
            "ledger_must_not_be_uploaded": True,
            "source_files_must_not_be_uploaded": True,
            "secret_must_not_be_uploaded": True,
            "exact_paths_stored_only_in_local_ledger": True,
        },
        "decode_after_service_response": {
            "place_service_json_files_under_local_answers_directory": True,
            "command": "python3 client_field_encoder.py decode --config config.json --answers-path answers",
        },
        "third_party_field_service_requirements": {
            "command": "python3 client_field_encoder.py requirements",
            "summary": "The API emits fields; the local decoder emits human answers from the private ledger/source files.",
            "non_text_sources_require_answerable_text": True,
            "calc_hash_must_change_when_encoding_recipe_changes": True,
        },
    }


def write_submission_manifest(path: str, manifest: dict[str, Any]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _gather_sources(args: argparse.Namespace, *, role: str, defaults: list[str]) -> list[SourceItem]:
    literal_values = list(getattr(args, role))
    path_values = [str(path) for path in getattr(args, f"{role}_path")]
    items = _source_items_from_literals(literal_values, role=role)
    items.extend(_source_items_from_paths(path_values, role=role, start_order=len(items)))
    if items:
        return items
    return _source_items_from_literals(defaults, role=role)



def _secret_from_args(args: argparse.Namespace) -> bytes:
    raw = str(args.secret or os.environ.get(str(args.secret_env), ""))
    if not raw:
        raise ValueError(f"provide --secret or set {args.secret_env}")
    return raw.encode()

def encode_command(args: argparse.Namespace) -> dict[str, Any]:
    secret = _secret_from_args(args)
    corpus_sources = _gather_sources(
        args,
        role="corpus",
        defaults=[
            "Contract renewal requires approval before Friday.",
            "Operational notes mention finance review and legal signoff.",
        ],
    )
    query_sources = _gather_sources(args, role="query", defaults=["What approval is needed for renewal?"])
    corpus_items = [encode_source_item(source, secret=secret, width=int(args.width), context=str(args.context)) for source in corpus_sources]
    query_items = [encode_source_item(source, secret=secret, width=int(args.width), context=str(args.context)) for source in query_sources]
    request = build_request(
        corpus_texts=[item.source.text for item in corpus_items],
        query_texts=[item.source.text for item in query_items],
        secret=secret,
        width=int(args.width),
        limit=int(args.limit),
        context=str(args.context),
    )
    request_id = "client-request:" + _sha256_json(request)[:40]
    request["client_request_id"] = request_id
    request["request_receipt"] = {
        "schema_version": REQUEST_RECEIPT_SCHEMA_VERSION,
        "recipe_id": REFERENCE_RECIPE_ID,
        "dtype": REFERENCE_DTYPE,
        "shape": REFERENCE_SHAPE,
        "width": int(args.width),
        "context": str(args.context),
        "calc_hash": str(request["corpus_field"]["calc_hash"]),
        "client_request_id": request_id,
        "corpus_hash": str(request["corpus_field"]["corpus_hash"]),
        "query_payload_hashes": [
            str(item["query_payload_hash"])
            for item in (request.get("query_fields") or [request.get("query_field")])
            if isinstance(item, dict)
        ],
        "payload_without_receipt_sha256": _sha256_json(request),
    }
    request["request_receipt_sha256"] = _sha256_json(request["request_receipt"])
    request["client_decode_hint"] = {
        "schema_version": "client-field-decode-hint-v1",
        "local_ledger_required": True,
        "ledger_path_redacted": True,
        "decode_command": f"python3 {Path(__file__).name} decode --config config.json --answers-path answers",
    }
    request["client_metering"] = {
        "schema_version": "client-field-metering-v1",
        "pseudonym_id": "local-client:" + hmac.new(secret, f"{args.context}\0metering-pseudonym".encode(), hashlib.sha256).hexdigest()[:40],
        "pseudonym_source": "local_free_encoder_no_oauth",
        "free_baseline_dimension_count": 4096,
        "background_noise_dimension_count": 256,
        "raw_fields_must_not_be_persisted_for_billing": True,
    }
    write_encode_ledger(
        ledger_path=Path(args.ledger),
        request=request,
        request_id=request_id,
        request_output_path=str(args.output or "stdout"),
        corpus_items=corpus_items,
        query_items=query_items,
        width=int(args.width),
        context=str(args.context),
    )
    if args.submission_manifest_output:
        submission_manifest = build_submission_manifest(
            request=request,
            request_output_path=_client_display_path(str(args.output or "stdout"), args),
            submission_manifest_output_path=_client_display_path(str(args.submission_manifest_output), args),
            ledger_path=_client_display_path(str(args.ledger), args),
            corpus_items=corpus_items,
            query_items=query_items,
            answers_path=_client_display_path(str(args.answers_path or "answers"), args),
            decode_output_path=_client_display_path(str(args.decode_output or "decoded/decoded_answers.json"), args),
        )
        write_submission_manifest(str(args.submission_manifest_output), submission_manifest)
    return request


def _json_pointer(parent: str, key: str) -> str:
    escaped = key.replace("~", "~0").replace("/", "~1")
    return f"{parent}/{escaped}" if parent else f"/{escaped}"


def _walk_strings(value: Any, *, pointer: str = "") -> list[tuple[str, str, str]]:
    if isinstance(value, dict):
        refs: list[tuple[str, str, str]] = []
        for key, nested in value.items():
            refs.extend(_walk_strings(nested, pointer=_json_pointer(pointer, str(key))))
        return refs
    if isinstance(value, list):
        refs = []
        for idx, nested in enumerate(value):
            refs.extend(_walk_strings(nested, pointer=_json_pointer(pointer, str(idx))))
        return refs
    if isinstance(value, str):
        key = pointer.rsplit("/", 1)[-1].replace("~1", "/").replace("~0", "~") if pointer else ""
        return [(pointer or "/", key, value)]
    return []


def _resolve_item_event(event: dict[str, Any], *, include_text: bool) -> dict[str, Any]:
    resolved = {
        "event_type": event.get("event_type"),
        "role": event.get("role"),
        "item_id": event.get("item_id"),
        "field_id": event.get("field_id"),
        "source_label": event.get("source_label"),
        "source_path": event.get("source_path"),
        "text_sha256": event.get("text_sha256"),
        "byte_count": event.get("byte_count"),
        "token_count": event.get("token_count"),
        "signal_sha256": event.get("signal_sha256"),
        "canonical_text_sha256": event.get("canonical_text_sha256"),
        "typed_atom_schema_version": event.get("typed_atom_schema_version"),
        "typed_atom_count": event.get("typed_atom_count"),
        "typed_atom_sha256": event.get("typed_atom_sha256"),
        "recipe_id": event.get("recipe_id"),
        "dtype": event.get("dtype"),
        "shape": event.get("shape"),
        "width": event.get("width"),
        "calc_hash": event.get("calc_hash"),
        "field_encoding": event.get("field_encoding"),
        "field_receipt_sha256": event.get("field_receipt_sha256"),
        "event_hash": event.get("event_hash"),
    }
    source_path = event.get("source_path")
    if isinstance(source_path, str) and source_path:
        path = Path(source_path)
        exists = path.exists()
        resolved["source_exists"] = exists
        if exists:
            current_text = _read_text(path)
            current_hash = _sha256_text(current_text)
            resolved["current_text_sha256"] = current_hash
            resolved["current_file_matches_ledger"] = current_hash == event.get("text_sha256")
            if include_text and resolved["current_file_matches_ledger"]:
                resolved["text"] = current_text
    return resolved


def _resolve_group_event(event: dict[str, Any], *, index: dict[str, list[dict[str, Any]]], include_text: bool, max_members: int) -> dict[str, Any]:
    member_ids = [str(item) for item in event.get("member_item_ids", []) if isinstance(item, str)]
    limit = len(member_ids) if max_members == 0 else max(0, min(max_members, len(member_ids)))
    members = []
    for item_id in member_ids[:limit]:
        item_events = [candidate for candidate in index.get(item_id, []) if candidate.get("event_type") == "field_map"]
        if item_events:
            members.append(_resolve_item_event(item_events[-1], include_text=include_text))
    return {
        "event_type": event.get("event_type"),
        "role": event.get("role"),
        "field_id": event.get("field_id"),
        "member_count": event.get("member_count"),
        "members_returned": len(members),
        "members_truncated": len(member_ids) - len(members),
        "members": members,
        "signal_sha256": event.get("signal_sha256"),
        "recipe_id": event.get("recipe_id"),
        "dtype": event.get("dtype"),
        "shape": event.get("shape"),
        "width": event.get("width"),
        "calc_hash": event.get("calc_hash"),
        "field_encoding": event.get("field_encoding"),
        "event_hash": event.get("event_hash"),
    }


def _resolve_event(event: dict[str, Any], *, index: dict[str, list[dict[str, Any]]], include_text: bool, max_members: int) -> dict[str, Any]:
    if event.get("event_type") == "field_group_map":
        return _resolve_group_event(event, index=index, include_text=include_text, max_members=max_members)
    if event.get("event_type") == "field_map":
        return _resolve_item_event(event, include_text=include_text)
    return {
        key: event.get(key)
        for key in (
            "event_type",
            "request_id",
            "request_sha256",
            "recipe_id",
            "dtype",
            "shape",
            "width",
            "calc_hash",
            "field_encoding",
            "request_receipt_sha256",
            "event_hash",
        )
        if key in event
    }


def _iter_resolved_match_objects(resolved_refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []
    for ref in resolved_refs:
        for match in ref.get("matches") or []:
            if not isinstance(match, dict):
                continue
            objects.append(match)
            for member in match.get("members") or []:
                if isinstance(member, dict):
                    objects.append(member)
    return objects


def _emission_declared_encodings(value: Any) -> list[dict[str, Any]]:
    declarations: list[dict[str, Any]] = []
    if isinstance(value, dict):
        if isinstance(value.get("field_encoding"), dict):
            declarations.append(value["field_encoding"])
        if any(key in value for key in ("recipe_id", "dtype", "shape")):
            declarations.append(value)
        for nested in value.values():
            declarations.extend(_emission_declared_encodings(nested))
    elif isinstance(value, list):
        for nested in value:
            declarations.extend(_emission_declared_encodings(nested))
    return declarations


def _compatibility_report(*, emission: dict[str, Any], resolved_refs: list[dict[str, Any]]) -> dict[str, Any]:
    required = {
        "recipe_id": REFERENCE_RECIPE_ID,
        "dtype": REFERENCE_DTYPE,
        "shape": REFERENCE_SHAPE,
    }
    blockers: list[str] = []
    checked_objects = 0
    for obj in _iter_resolved_match_objects(resolved_refs):
        if obj.get("event_type") not in {"field_map", "field_group_map", "request_map"}:
            continue
        checked_objects += 1
        label = str(obj.get("field_id") or obj.get("request_id") or obj.get("item_id") or "resolved_object")
        for key, expected in required.items():
            if obj.get(key) != expected:
                blockers.append(f"ledger_{key}_mismatch:{label}")
        if not isinstance(obj.get("width"), int) or int(obj.get("width") or 0) <= 0:
            blockers.append(f"ledger_width_missing:{label}")
        field_encoding = obj.get("field_encoding")
        if not isinstance(field_encoding, dict):
            blockers.append(f"ledger_field_encoding_missing:{label}")
        else:
            for key, expected in required.items():
                if field_encoding.get(key) != expected:
                    blockers.append(f"ledger_field_encoding_{key}_mismatch:{label}")
    for declaration in _emission_declared_encodings(emission):
        for key, expected in required.items():
            if key in declaration and declaration.get(key) != expected:
                blockers.append(f"emission_{key}_mismatch:{declaration.get(key)}")
    blockers = sorted(set(blockers))
    return {
        "schema_version": "openencoder-compatibility-report-v1",
        "passed": checked_objects > 0 and not blockers,
        "checked_resolved_object_count": checked_objects,
        "required": required,
        "blocker_count": len(blockers),
        "blockers": blockers,
    }


def decode_emission(*, emission: dict[str, Any], ledger_path: Path, include_text: bool, max_members: int) -> dict[str, Any]:
    events, hash_chain_valid = load_ledger_events(ledger_path)
    index = ledger_alias_index(events)
    resolved_refs = []
    unresolved_field_like_refs = []
    seen: set[tuple[str, str]] = set()
    for pointer, key, value in _walk_strings(emission):
        if "/groth16_topology_proof" in pointer:
            continue
        matched_events = index.get(value, [])
        if matched_events:
            dedupe_key = (pointer, value)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            resolved_refs.append(
                {
                    "json_pointer": pointer,
                    "key": key,
                    "value": value,
                    "matches": [
                        _resolve_event(event, index=index, include_text=include_text, max_members=max_members)
                        for event in matched_events
                    ],
                }
            )
        elif key in COMPATIBILITY_METADATA_KEYS:
            continue
        elif key in FIELD_REFERENCE_KEYS or key.endswith("_hash") or key.endswith("_id"):
            unresolved_field_like_refs.append({"json_pointer": pointer, "key": key, "value": value})
    topology_proof = _topology_proof_report(emission)
    compatibility = _compatibility_report(emission=emission, resolved_refs=resolved_refs)
    if topology_proof.get("passed") is not True:
        blockers = list(compatibility.get("blockers") or [])
        blockers.extend(f"topology_proof:{item}" for item in topology_proof.get("blockers") or ["missing"])
        blockers = sorted(set(blockers))
        compatibility["passed"] = False
        compatibility["blockers"] = blockers
        compatibility["blocker_count"] = len(blockers)
    decoded = {
        "schema_version": DECODE_SCHEMA_VERSION,
        "critical_info_table_schema_version": CRITICAL_INFO_TABLE_SCHEMA_VERSION,
        "emission_sha256": _sha256_json(emission),
        "ledger": {
            "path": str(ledger_path),
            "event_count": len(events),
            "hash_chain_valid": hash_chain_valid,
        },
        "resolved_reference_count": len(resolved_refs),
        "resolved_references": resolved_refs,
        "unresolved_field_like_reference_count": len(unresolved_field_like_refs),
        "unresolved_field_like_references": unresolved_field_like_refs,
        "topology_proof": topology_proof,
        "compatibility": compatibility,
        "emission": emission,
    }
    decoded["local_answer_report"] = _local_answer_report(decoded)
    decoded["critical_info_table"] = _answer_critical_info_table(decoded)
    return decoded


def _answer_json_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if path.is_dir():
        return sorted(candidate for candidate in path.rglob("*.json") if candidate.is_file())
    raise ValueError(f"answers path does not exist: {path}")



def decode_command(args: argparse.Namespace) -> dict[str, Any]:
    emission_paths = [Path(path) for path in (args.emission or [])]
    from_answers_path = bool(args.answers_path)
    if args.answers_path:
        emission_paths.extend(_answer_json_files(Path(args.answers_path)))
    if not emission_paths:
        raise ValueError("provide --emission or --answers-path for decode mode")
    decoded_answers = []
    for emission_path in emission_paths:
        emission = json.loads(emission_path.read_text(encoding="utf-8"))
        decoded = decode_emission(
            emission=emission,
            ledger_path=Path(args.ledger),
            include_text=bool(args.include_text),
            max_members=int(args.max_members),
        )
        decoded["critical_info_table"] = _answer_critical_info_table(decoded, answer_path=str(emission_path))
        decoded_answers.append(
            {
                "answer_path": str(emission_path),
                "decoded": decoded,
            }
        )
    if len(decoded_answers) == 1 and not from_answers_path:
        return decoded_answers[0]["decoded"]
    return {
        "schema_version": ANSWER_FOLDER_DECODE_SCHEMA_VERSION,
        "critical_info_table_schema_version": CRITICAL_INFO_TABLE_SCHEMA_VERSION,
        "critical_info_table": _folder_critical_info_table(decoded_answers),
        "answers_path": str(args.answers_path or ""),
        "answer_count": len(decoded_answers),
        "total_resolved_reference_count": sum(int(item["decoded"].get("resolved_reference_count") or 0) for item in decoded_answers),
        "decoded_answers": decoded_answers,
    }


def _namespace_copy(args: argparse.Namespace, **updates: Any) -> argparse.Namespace:
    values = vars(args).copy()
    values.update(updates)
    return argparse.Namespace(**values)


def _request_query_fields(request: dict[str, Any]) -> list[dict[str, Any]]:
    fields = request.get("query_fields") or [request.get("query_field")]
    return [field for field in fields if isinstance(field, dict)]


def _distaste_topography_field(corpus_signal: list[Any], query_signal: list[Any]) -> list[int]:
    width = min(len(corpus_signal), len(query_signal))
    return [_saturating_add(int(corpus_signal[index]), -int(query_signal[index])) for index in range(width)]


def _build_topology_statement_from_result(*, field_encoding: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    from openencoder_groth16 import build_topology_statement

    return build_topology_statement(
        corpus_hash=str(result.get("corpus_hash") or ""),
        query_payload_hash=str(result.get("query_payload_hash") or ""),
        corpus_signal_sha256=str(result.get("corpus_signal_sha256") or ""),
        query_signal_sha256=str(result.get("query_signal_sha256") or ""),
        result_field_sha256=str(result.get("result_field_sha256") or ""),
        field_encoding=field_encoding,
    )


def build_reference_emission(request: dict[str, Any]) -> dict[str, Any]:
    from openencoder_groth16 import prove_topology_statement

    field_encoding = dict(request.get("field_encoding") or {})
    corpus_field = dict(request.get("corpus_field") or {})
    corpus_signal = list(corpus_field.get("field_tensor") or [])
    query_results = []
    for index, query_field in enumerate(_request_query_fields(request)):
        query_signal = list(query_field.get("field_tensor") or [])
        result_field = _distaste_topography_field(corpus_signal, query_signal)
        core_result = {
            "schema_version": "openencoder-field-topology-distaste-result-v1",
            "core_call_shape": "ZKVOO(field[A], field[B]) -> distaste_topography_field",
            "corpus_hash": corpus_field.get("corpus_hash"),
            "query_payload_hash": query_field.get("query_payload_hash"),
            "corpus_signal_sha256": corpus_field.get("signal_sha256"),
            "query_signal_sha256": query_field.get("signal_sha256"),
            "result_field_sha256": _sha256_json(result_field),
            "distaste_topography_field": result_field,
        }
        statement = _build_topology_statement_from_result(field_encoding=field_encoding, result=core_result)
        proof = prove_topology_statement(statement)
        query_results.append(
            {
                "query_index": index,
                "query_payload_hash": query_field.get("query_payload_hash"),
                "determinism_verification": {"verified": True},
                "core_result": core_result,
                "groth16_topology_proof": proof,
            }
        )
    emission = {
        "object": "openencoder.reference_field_emission",
        "schema_version": "openencoder-reference-field-emission-v1",
        "client_request_id": request.get("client_request_id"),
        "field_encoding": field_encoding,
        "query_count": len(query_results),
        "query_results": query_results,
        "determinism_boundary": {
            "deterministic_replay_supported": True,
            "same_normalized_inputs_same_core_build_same_outputs": True,
        },
        "claim_boundary": {
            "honest_label": "Groth16-backed deterministic reference field emission; not encryption and not semantic retrieval quality proof",
        },
    }
    if query_results:
        emission["core_result"] = query_results[0]["core_result"]
        emission["groth16_topology_proof"] = query_results[0]["groth16_topology_proof"]
    return emission


def emit_command(args: argparse.Namespace) -> dict[str, Any]:
    if not args.request:
        raise ValueError("provide --request for emit mode")
    request = json.loads(Path(args.request).read_text(encoding="utf-8"))
    if not isinstance(request, dict):
        raise ValueError("request JSON must be an object")
    return build_reference_emission(request)


def _topology_proof_report(emission: dict[str, Any]) -> dict[str, Any]:
    from openencoder_groth16 import verify_topology_proof

    rows = []
    blockers: list[str] = []
    field_encoding = dict(emission.get("field_encoding") or {}) if isinstance(emission.get("field_encoding"), dict) else {}
    query_results = emission.get("query_results") if isinstance(emission.get("query_results"), list) else []
    if not query_results and isinstance(emission.get("core_result"), dict):
        query_results = [{"query_index": 0, "core_result": emission.get("core_result"), "groth16_topology_proof": emission.get("groth16_topology_proof")}]
    for index, result in enumerate(query_results):
        if not isinstance(result, dict):
            continue
        core_result = dict(result.get("core_result") or {}) if isinstance(result.get("core_result"), dict) else {}
        proof = result.get("groth16_topology_proof") if isinstance(result.get("groth16_topology_proof"), dict) else None
        if proof is None and index == 0 and isinstance(emission.get("groth16_topology_proof"), dict):
            proof = emission["groth16_topology_proof"]
        if proof is None:
            blockers.append(f"groth16_topology_proof_missing:{index}")
            rows.append({"query_index": result.get("query_index", index), "passed": False, "blockers": ["groth16_topology_proof_missing"]})
            continue
        expected = _build_topology_statement_from_result(field_encoding=field_encoding, result=core_result)
        verification = verify_topology_proof(proof, expected_statement=expected)
        if verification.get("passed") is not True:
            blockers.extend(f"{item}:{index}" for item in verification.get("blockers") or ["groth16_topology_proof_failed"])
        rows.append({"query_index": result.get("query_index", index), **verification})
    if not rows:
        blockers.append("groth16_topology_proof_missing")
    blockers = sorted(set(blockers))
    return {
        "schema_version": "openencoder-topology-proof-report-v1",
        "required": True,
        "passed": not blockers,
        "proof_count": len(rows),
        "blocker_count": len(blockers),
        "blockers": blockers,
        "rows": rows,
    }


def verify_groth16_command(args: argparse.Namespace) -> dict[str, Any]:
    if not args.proof:
        raise ValueError("provide --proof for verify mode")
    from openencoder_groth16 import verify_groth16_file

    verification = verify_groth16_file(Path(args.proof))
    return {
        "schema_version": "openencoder-groth16-verify-result-v1",
        "verification": verification,
    }



def launch_gui(args: argparse.Namespace) -> int:
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk
    except Exception as exc:
        sys.stderr.write(f"Tk GUI is unavailable on this host: {exc}\n")
        return 2

    repo_root = Path(__file__).resolve().parent
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        sys.stderr.write(f"Tk GUI failed to start: {exc}\n")
        return 2
    root.title("OpenEncoder")
    root.geometry("980x640")
    root.configure(bg="#111318")

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure("TFrame", background="#111318")
    style.configure("TLabel", background="#111318", foreground="#e7eaf0")
    style.configure("TButton", padding=6)
    style.configure("TEntry", fieldbackground="#1b1f27", foreground="#111318")

    state = {
        "corpus": tk.StringVar(value=str(repo_root / "examples" / "corpus")),
        "query": tk.StringVar(value=str(repo_root / "examples" / "query")),
        "ledger": tk.StringVar(value=str(repo_root / "ledger" / "client_field_ledger.jsonl")),
        "request": tk.StringVar(value=str(repo_root / "outbox" / "01_field_request.json")),
        "manifest": tk.StringVar(value=str(repo_root / "outbox" / "02_submission_manifest.json")),
        "answers": tk.StringVar(value=str(repo_root / "answers")),
        "decoded": tk.StringVar(value=str(repo_root / "decoded" / "decoded_answers.json")),
        "context": tk.StringVar(value=str(args.context or "gui")),
        "width": tk.StringVar(value=str(args.width or 64)),
        "limit": tk.StringVar(value=str(args.limit or 10)),
    }

    output = tk.Text(root, bg="#0c0e12", fg="#e7eaf0", insertbackground="#e7eaf0", wrap="word", height=18)

    def log(message: str) -> None:
        output.insert("end", message.rstrip() + "\n")
        output.see("end")
        root.update_idletasks()

    def choose_dir(key: str) -> None:
        selected = filedialog.askdirectory(initialdir=str(repo_root))
        if selected:
            state[key].set(selected)

    def choose_file(key: str) -> None:
        selected = filedialog.asksaveasfilename(initialdir=str(repo_root))
        if selected:
            state[key].set(selected)

    def run_command(command: list[str]) -> None:
        try:
            completed = subprocess.run(command, cwd=repo_root, capture_output=True, text=True, check=False)
        except Exception as exc:
            messagebox.showerror("OpenEncoder", str(exc))
            return
        if completed.stdout:
            log(completed.stdout)
        if completed.stderr:
            log(completed.stderr)
        log(f"exit_code={completed.returncode}")

    def run_encode() -> None:
        run_command([
            sys.executable,
            str(Path(__file__).resolve()),
            "encode",
            "--corpus-path",
            state["corpus"].get(),
            "--query-path",
            state["query"].get(),
            "--context",
            state["context"].get(),
            "--width",
            state["width"].get(),
            "--limit",
            state["limit"].get(),
            "--ledger",
            state["ledger"].get(),
            "--output",
            state["request"].get(),
            "--submission-manifest-output",
            state["manifest"].get(),
        ])

    def run_decode() -> None:
        run_command([
            sys.executable,
            str(Path(__file__).resolve()),
            "decode",
            "--ledger",
            state["ledger"].get(),
            "--answers-path",
            state["answers"].get(),
            "--include-text",
            "--output",
            state["decoded"].get(),
        ])

    def run_requirements() -> None:
        run_command([sys.executable, str(Path(__file__).resolve()), "requirements"])

    panel = ttk.Frame(root, padding=14)
    panel.pack(fill="both", expand=True)
    ttk.Label(panel, text="OpenEncoder private-field client kit", font=("Segoe UI", 15, "bold")).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 12))

    rows = [
        ("Corpus", "corpus", choose_dir),
        ("Query", "query", choose_dir),
        ("Ledger", "ledger", choose_file),
        ("Request", "request", choose_file),
        ("Manifest", "manifest", choose_file),
        ("Answers", "answers", choose_dir),
        ("Decoded", "decoded", choose_file),
        ("Context", "context", None),
        ("Width", "width", None),
        ("Limit", "limit", None),
    ]
    for row_index, (label, key, chooser) in enumerate(rows, start=1):
        ttk.Label(panel, text=label).grid(row=row_index, column=0, sticky="w", pady=2)
        ttk.Entry(panel, textvariable=state[key], width=92).grid(row=row_index, column=1, sticky="ew", pady=2)
        if chooser:
            ttk.Button(panel, text="Browse", command=lambda k=key, c=chooser: c(k)).grid(row=row_index, column=2, padx=(8, 0), pady=2)

    buttons = ttk.Frame(panel)
    buttons.grid(row=len(rows) + 1, column=0, columnspan=3, sticky="w", pady=12)
    ttk.Button(buttons, text="Encode", command=run_encode).pack(side="left", padx=(0, 8))
    ttk.Button(buttons, text="Decode", command=run_decode).pack(side="left", padx=(0, 8))
    ttk.Button(buttons, text="Requirements", command=run_requirements).pack(side="left")

    output.grid(in_=panel, row=len(rows) + 2, column=0, columnspan=3, sticky="nsew")
    panel.columnconfigure(1, weight=1)
    panel.rowconfigure(len(rows) + 2, weight=1)
    log("Set CLIENT_SIGNAL_SECRET before encoding real data. Send only the request JSON and non-secret submission manifest.")
    try:
        root.mainloop()
    except tk.TclError as exc:
        sys.stderr.write(f"Tk GUI failed: {exc}\n")
        return 2
    return 0

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        nargs="?",
        choices=("encode", "emit", "decode", "verify", "gui", "requirements"),
        help="Default is GUI mode. Use encode/decode for deterministic command-line operation.",
    )
    parser.add_argument("--config", help="Optional kit config JSON. Relative paths are resolved from the config file directory.")
    parser.add_argument("--corpus", action="append", default=[], help="Client text. Repeat for multiple inputs.")
    parser.add_argument("--corpus-path", action="append", default=[], help="Client file or directory. Repeat for multiple inputs.")
    parser.add_argument("--query", action="append", default=[], help="Client query. Repeat for multiple queries.")
    parser.add_argument("--query-path", action="append", default=[], help="Client query file or directory. Repeat for multiple inputs.")
    parser.add_argument("--request", help="OpenEncoder request JSON for emit mode.")
    parser.add_argument("--emission", action="append", default=[], help="Service response JSON to decode through the local append-only ledger. Repeat for multiple responses.")
    parser.add_argument("--answers-path", help="Directory containing service response JSON files to decode.")
    parser.add_argument("--ledger", help="Append-only local field-id map ledger.")
    parser.add_argument("--secret", default="", help="Client-held secret. Prefer the environment variable for real use.")
    parser.add_argument("--secret-env", default="CLIENT_SIGNAL_SECRET", help="Environment variable that carries the client-held secret.")
    parser.add_argument("--context", default="default", help="Domain-separation label chosen by the client.")
    parser.add_argument("--width", type=int, default=64, help="Output signal width.")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--include-text", action="store_true", help="During decode, include current source file text when hashes still match.")
    parser.add_argument("--max-members", type=int, default=100, help="During decode, max expanded corpus group members. Use 0 for all.")
    parser.add_argument("--request-output", help="Encode output path for the service payload JSON.")
    parser.add_argument("--decode-output", help="Decode output path for the decoded answer JSON.")
    parser.add_argument("--submission-manifest-output", help="Second sendable JSON with non-secret submission metadata.")
    parser.add_argument("--proof", help="Groth16 payload path for verify mode")
    parser.add_argument("--output", help="Optional path for JSON output")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.config:
        args.config = _default_frozen_config()
    command = args.command or ("decode" if args.emission or args.answers_path else "gui")
    args = _apply_config(args, command=command)
    if command == "gui":
        return launch_gui(args)
    if command == "requirements":
        payload = requirements_command(args)
    elif command == "emit":
        payload = emit_command(args)
    elif command == "decode":
        payload = decode_command(args)
    elif command == "verify":
        payload = verify_groth16_command(args)
    else:
        payload = encode_command(args)
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
        if command == "decode":
            text_report = _decode_text_report(payload)
            if text_report:
                output_path.with_suffix(".txt").write_text(text_report + "\n", encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    if command == "verify" and _dig(payload, "verification", "passed") is not True:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
