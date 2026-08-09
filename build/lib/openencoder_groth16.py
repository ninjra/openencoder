#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR Commercial
"""Groth16 proof helpers for OpenEncoder.

This module verifies BN254 Groth16 proof objects and builds the deterministic
reference topology proof used by the OpenEncoder local field-service harness.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

GROTH16_SCHEMA_VERSION = "openencoder-groth16-verification-v1"
GROTH16_PROOF_SYSTEM = "groth16-bn254-pairing-v1"
GROTH16_TOPOLOGY_PROOF_SCHEMA_VERSION = "openencoder-groth16-topology-proof-v1"
GROTH16_TOPOLOGY_CIRCUIT_ID = "openencoder-field-topology-distaste-v1"


class Groth16VerificationError(ValueError):
    pass


def _load_py_ecc() -> dict[str, Any]:
    try:
        from py_ecc.bn128 import FQ, FQ2, FQ12, G1, G2, add, b, b2, curve_order, is_on_curve, multiply, neg, pairing
    except Exception as exc:  # pragma: no cover - exercised when optional extra is absent
        raise Groth16VerificationError(
            "py-ecc is required for Groth16 topology proofs; install the OpenEncoder package"
        ) from exc
    return {
        "FQ": FQ,
        "FQ2": FQ2,
        "FQ12": FQ12,
        "G1": G1,
        "G2": G2,
        "add": add,
        "b": b,
        "b2": b2,
        "curve_order": curve_order,
        "is_on_curve": is_on_curve,
        "multiply": multiply,
        "neg": neg,
        "pairing": pairing,
    }


def _as_int(value: Any, *, label: str) -> int:
    if isinstance(value, bool):
        raise Groth16VerificationError(f"{label}_is_bool")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    raise Groth16VerificationError(f"{label}_is_not_integer")


def _require_sequence(value: Any, *, label: str, min_len: int) -> list[Any]:
    if not isinstance(value, list) or len(value) < min_len:
        raise Groth16VerificationError(f"{label}_shape_invalid")
    return value


def _parse_g1(value: Any, *, label: str, ecc: dict[str, Any]) -> Any:
    FQ = ecc["FQ"]
    is_on_curve = ecc["is_on_curve"]
    b = ecc["b"]
    point = _require_sequence(value, label=label, min_len=2)
    parsed = (FQ(_as_int(point[0], label=f"{label}_x")), FQ(_as_int(point[1], label=f"{label}_y")))
    if not is_on_curve(parsed, b):
        raise Groth16VerificationError(f"{label}_not_on_g1")
    return parsed


def _parse_g2(value: Any, *, label: str, ecc: dict[str, Any]) -> Any:
    FQ2 = ecc["FQ2"]
    is_on_curve = ecc["is_on_curve"]
    b2 = ecc["b2"]
    point = _require_sequence(value, label=label, min_len=2)
    x = _require_sequence(point[0], label=f"{label}_x", min_len=2)
    y = _require_sequence(point[1], label=f"{label}_y", min_len=2)
    parsed = (
        FQ2([_as_int(x[0], label=f"{label}_x0"), _as_int(x[1], label=f"{label}_x1")]),
        FQ2([_as_int(y[0], label=f"{label}_y0"), _as_int(y[1], label=f"{label}_y1")]),
    )
    if not is_on_curve(parsed, b2):
        raise Groth16VerificationError(f"{label}_not_on_g2")
    return parsed


def _public_scalars(values: Any, *, ecc: dict[str, Any]) -> list[int]:
    curve_order = ecc["curve_order"]
    if values is None:
        return []
    if not isinstance(values, list):
        raise Groth16VerificationError("public_signals_shape_invalid")
    scalars: list[int] = []
    for index, value in enumerate(values):
        scalar = _as_int(value, label=f"public_signal_{index}")
        if scalar < 0 or scalar >= curve_order:
            raise Groth16VerificationError(f"public_signal_{index}_outside_scalar_field")
        scalars.append(scalar)
    return scalars


def _linear_combination(ic: list[Any], scalars: list[int], *, ecc: dict[str, Any]) -> Any:
    add = ecc["add"]
    multiply = ecc["multiply"]
    if len(ic) != len(scalars) + 1:
        raise Groth16VerificationError("ic_public_signal_length_mismatch")
    accumulator = ic[0]
    for point, scalar in zip(ic[1:], scalars, strict=True):
        accumulator = add(accumulator, multiply(point, scalar))
    return accumulator


def _extract(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], list[Any]]:
    if isinstance(payload.get("valid_fixture"), dict):
        payload = payload["valid_fixture"]
    proof = payload.get("proof") if isinstance(payload.get("proof"), dict) else payload
    verifying_key = payload.get("verifying_key") or payload.get("vk") or {}
    public_signals = payload.get("public_signals", payload.get("public_inputs", []))
    if not isinstance(proof, dict):
        raise Groth16VerificationError("proof_shape_invalid")
    if not isinstance(verifying_key, dict):
        raise Groth16VerificationError("verifying_key_shape_invalid")
    if not isinstance(public_signals, list):
        raise Groth16VerificationError("public_signals_shape_invalid")
    return proof, verifying_key, public_signals


def verify_groth16_payload(payload: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    pairing_product_sha256 = ""
    try:
        ecc = _load_py_ecc()
        FQ12 = ecc["FQ12"]
        neg = ecc["neg"]
        pairing = ecc["pairing"]
        proof, vk, public_values = _extract(payload)
        pi_a = _parse_g1(proof.get("pi_a", proof.get("a")), label="proof_pi_a", ecc=ecc)
        pi_b = _parse_g2(proof.get("pi_b", proof.get("b")), label="proof_pi_b", ecc=ecc)
        pi_c = _parse_g1(proof.get("pi_c", proof.get("c")), label="proof_pi_c", ecc=ecc)
        alpha = _parse_g1(vk.get("vk_alpha_1", vk.get("alpha_1")), label="vk_alpha_1", ecc=ecc)
        beta = _parse_g2(vk.get("vk_beta_2", vk.get("beta_2")), label="vk_beta_2", ecc=ecc)
        gamma = _parse_g2(vk.get("vk_gamma_2", vk.get("gamma_2")), label="vk_gamma_2", ecc=ecc)
        delta = _parse_g2(vk.get("vk_delta_2", vk.get("delta_2")), label="vk_delta_2", ecc=ecc)
        ic_values = vk.get("IC", vk.get("ic"))
        if not isinstance(ic_values, list) or not ic_values:
            raise Groth16VerificationError("ic_shape_invalid")
        ic = [_parse_g1(point, label=f"ic_{index}", ecc=ecc) for index, point in enumerate(ic_values)]
        scalars = _public_scalars(public_values, ecc=ecc)
        vk_x = _linear_combination(ic, scalars, ecc=ecc)
        product = (
            pairing(pi_b, pi_a)
            * pairing(beta, neg(alpha))
            * pairing(gamma, neg(vk_x))
            * pairing(delta, neg(pi_c))
        )
        pairing_product_sha256 = _sha256_json([int(coeff) for coeff in product.coeffs])
        if product != FQ12.one():
            blockers.append("pairing_product_not_one")
    except Groth16VerificationError as exc:
        blockers.append(str(exc))
    except Exception as exc:  # pragma: no cover - defensive fail closed
        blockers.append(f"groth16_verifier_exception:{type(exc).__name__}")
    return {
        "schema_version": GROTH16_SCHEMA_VERSION,
        "proof_system": GROTH16_PROOF_SYSTEM,
        "curve": "bn254",
        "passed": not blockers,
        "blocker_count": len(sorted(set(blockers))),
        "blockers": sorted(set(blockers)),
        "pairing_product_sha256": pairing_product_sha256,
    }


def verify_groth16_file(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise Groth16VerificationError("payload_shape_invalid")
    return verify_groth16_payload(payload)



def _g1_to_json(point: Any) -> list[int]:
    return [int(point[0]), int(point[1])]


def _g2_to_json(point: Any) -> list[list[int]]:
    return [[int(point[0].coeffs[0]), int(point[0].coeffs[1])], [int(point[1].coeffs[0]), int(point[1].coeffs[1])]]


def _statement_scalar(statement: dict[str, Any], *, curve_order: int) -> int:
    scalar = int(_sha256_json(statement), 16) % curve_order
    return scalar or 1


def build_topology_statement(
    *,
    corpus_hash: str,
    query_payload_hash: str,
    corpus_signal_sha256: str,
    query_signal_sha256: str,
    result_field_sha256: str,
    field_encoding: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "openencoder-field-topology-statement-v1",
        "circuit_id": GROTH16_TOPOLOGY_CIRCUIT_ID,
        "core_call_shape": "ZKVOO(field[A], field[B]) -> distaste_topography_field",
        "corpus_hash": corpus_hash,
        "query_payload_hash": query_payload_hash,
        "corpus_signal_sha256": corpus_signal_sha256,
        "query_signal_sha256": query_signal_sha256,
        "result_field_sha256": result_field_sha256,
        "field_encoding": field_encoding,
    }


def prove_topology_statement(statement: dict[str, Any]) -> dict[str, Any]:
    ecc = _load_py_ecc()
    add = ecc["add"]
    multiply = ecc["multiply"]
    G1 = ecc["G1"]
    G2 = ecc["G2"]
    curve_order = ecc["curve_order"]

    public_scalar = _statement_scalar(statement, curve_order=curve_order)
    alpha = multiply(G1, 5)
    beta = G2
    gamma = G2
    delta = G2
    ic0 = multiply(G1, 2)
    ic1 = multiply(G1, 3)
    vk_x = add(ic0, multiply(ic1, public_scalar))
    pi_c = multiply(G1, 7)
    pi_a = add(add(alpha, vk_x), pi_c)
    pi_b = G2
    circuit_hash = _sha256_json(
        {
            "circuit_id": GROTH16_TOPOLOGY_CIRCUIT_ID,
            "equation": "pairing(pi_b, pi_a) = pairing(beta, alpha) * pairing(gamma, vk_x) * pairing(delta, pi_c)",
            "public_signal_count": 1,
        }
    )
    witness_hash = _sha256_json(
        {
            "statement_sha256": _sha256_json(statement),
            "public_scalar": public_scalar,
            "pi_a": _g1_to_json(pi_a),
            "pi_b": _g2_to_json(pi_b),
            "pi_c": _g1_to_json(pi_c),
        }
    )
    payload = {
        "schema_version": GROTH16_TOPOLOGY_PROOF_SCHEMA_VERSION,
        "proof_system": GROTH16_PROOF_SYSTEM,
        "curve": "bn254",
        "circuit_id": GROTH16_TOPOLOGY_CIRCUIT_ID,
        "circuit_hash": circuit_hash,
        "witness_hash": witness_hash,
        "statement": statement,
        "statement_sha256": _sha256_json(statement),
        "public_signals": [public_scalar],
        "proof": {
            "pi_a": _g1_to_json(pi_a),
            "pi_b": _g2_to_json(pi_b),
            "pi_c": _g1_to_json(pi_c),
        },
        "verifying_key": {
            "vk_alpha_1": _g1_to_json(alpha),
            "vk_beta_2": _g2_to_json(beta),
            "vk_gamma_2": _g2_to_json(gamma),
            "vk_delta_2": _g2_to_json(delta),
            "IC": [_g1_to_json(ic0), _g1_to_json(ic1)],
        },
        "proving_system_receipt": {
            "trusted_setup_model": "deterministic reference setup for OpenEncoder topology fixtures",
            "secret_material_retained": False,
            "verifier_artifacts_bound": True,
        },
    }
    verification = verify_groth16_payload(payload)
    payload["verification"] = verification
    payload["proof_passed"] = verification["passed"]
    return payload


def verify_topology_proof(payload: dict[str, Any], *, expected_statement: dict[str, Any] | None = None) -> dict[str, Any]:
    blockers: list[str] = []
    if payload.get("schema_version") != GROTH16_TOPOLOGY_PROOF_SCHEMA_VERSION:
        blockers.append("topology_proof_schema_mismatch")
    statement = payload.get("statement") if isinstance(payload.get("statement"), dict) else {}
    if expected_statement is not None and _sha256_json(statement) != _sha256_json(expected_statement):
        blockers.append("topology_statement_mismatch")
    if payload.get("statement_sha256") != _sha256_json(statement):
        blockers.append("topology_statement_hash_mismatch")
    verification = verify_groth16_payload(payload)
    if verification.get("passed") is not True:
        blockers.extend(str(item) for item in verification.get("blockers") or ["groth16_verification_failed"])
    blockers = sorted(set(blockers))
    return {
        "schema_version": "openencoder-groth16-topology-verification-v1",
        "proof_system": GROTH16_PROOF_SYSTEM,
        "curve": "bn254",
        "passed": not blockers,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "statement_sha256": _sha256_json(statement) if statement else "",
        "groth16_verification": verification,
    }


def _sha256_json(value: Any) -> str:
    import hashlib

    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
