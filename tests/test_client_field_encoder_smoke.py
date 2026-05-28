# Copyright 2026 Shri Narayan Justin Ram / Mushku Nobleworks. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0 OR Commercial

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "client_field_encoder.py"


def _run_encoder(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def test_client_field_encoder_round_trips_local_answer(tmp_path: Path) -> None:
    corpus_dir = tmp_path / "corpus"
    query_dir = tmp_path / "query"
    corpus_dir.mkdir()
    query_dir.mkdir()
    (corpus_dir / "contract.md").write_text(
        "Contract renewal requires legal approval before Friday.",
        encoding="utf-8",
    )
    (query_dir / "approval.md").write_text(
        "What approval is needed for renewal?",
        encoding="utf-8",
    )

    request_path = tmp_path / "field_request.json"
    ledger_path = tmp_path / "client_field_ledger.jsonl"
    _run_encoder(
        "encode",
        "--corpus-path",
        str(corpus_dir),
        "--query-path",
        str(query_dir),
        "--secret",
        "test-client-secret",
        "--context",
        "round-trip-test",
        "--width",
        "16",
        "--limit",
        "2",
        "--ledger",
        str(ledger_path),
        "--output",
        str(request_path),
    )

    request = json.loads(request_path.read_text(encoding="utf-8"))
    ledger_events = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines()]
    assert [event["event_type"] for event in ledger_events] == [
        "field_map",
        "field_map",
        "field_group_map",
        "request_map",
    ]

    emission_path = tmp_path / "service_emission.json"
    _run_encoder("emit", "--request", str(request_path), "--output", str(emission_path))

    decoded_path = tmp_path / "decoded_emission.json"
    _run_encoder(
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
    )
    decoded = json.loads(decoded_path.read_text(encoding="utf-8"))

    assert decoded["ledger"]["hash_chain_valid"] is True
    assert decoded["envelope_proof"]["passed"] is True
    assert decoded["local_answer_report"]["all_questions_answered"] is True
    assert "legal approval before Friday" in decoded["local_answer_report"]["rows"][0]["answer_text"]


def _make_roundtrip_fixture(tmp_path: Path) -> tuple[Path, Path, dict]:
    corpus_dir = tmp_path / "corpus"
    query_dir = tmp_path / "query"
    corpus_dir.mkdir()
    query_dir.mkdir()
    (corpus_dir / "contract.md").write_text(
        "Contract renewal requires legal approval before Friday.",
        encoding="utf-8",
    )
    (query_dir / "approval.md").write_text(
        "What approval is needed for renewal?",
        encoding="utf-8",
    )
    request_path = tmp_path / "field_request.json"
    ledger_path = tmp_path / "client_field_ledger.jsonl"
    _run_encoder(
        "encode",
        "--corpus-path",
        str(corpus_dir),
        "--query-path",
        str(query_dir),
        "--secret",
        "test-client-secret",
        "--context",
        "release-hardening-test",
        "--width",
        "16",
        "--limit",
        "2",
        "--ledger",
        str(ledger_path),
        "--output",
        str(request_path),
    )
    return request_path, ledger_path, json.loads(request_path.read_text(encoding="utf-8"))


def _write_emission(tmp_path: Path, request: dict, *, unresolved: bool = False) -> Path:
    from client_field_encoder import build_reference_emission

    emission_path = tmp_path / "service_emission.json"
    emission = build_reference_emission(request)
    if unresolved:
        bad_hash = "sha256:" + "0" * 64
        emission["core_result"]["corpus_hash"] = bad_hash
        emission["query_results"][0]["core_result"]["corpus_hash"] = bad_hash
    emission_path.write_text(json.dumps(emission, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return emission_path


def test_requirements_command_emits_valid_contract_json() -> None:
    completed = _run_encoder("requirements")
    payload = json.loads(completed.stdout)

    assert payload["schema_version"] == "openencoder-client-field-protocol-requirements-v1"
    assert "decoder_fails_closed_on_unresolved_or_hash_mismatch" in payload["machine_readable_requirements"]
    assert payload["api_decoder_split"]["api_must_not"] == "synthesize private natural-language answers from opaque fields"


def test_encode_request_omits_raw_corpus_and_query_text(tmp_path: Path) -> None:
    request_path, _ledger_path, request = _make_roundtrip_fixture(tmp_path)
    request_text = request_path.read_text(encoding="utf-8")

    assert "Contract renewal requires" not in request_text
    assert "What approval is needed" not in request_text
    assert request["corpus_field"]["field_tensor"]
    assert request["query_field"]["field_tensor"]


def test_sendable_request_and_manifest_redact_paths_and_source_labels(tmp_path: Path) -> None:
    corpus_dir = tmp_path / "case_alpha_corpus"
    query_dir = tmp_path / "case_alpha_query"
    corpus_dir.mkdir()
    query_dir.mkdir()
    (corpus_dir / "client-secret-contract.md").write_text("Private renewal text stays local.", encoding="utf-8")
    (query_dir / "client-secret-question.md").write_text("What stays local?", encoding="utf-8")
    request_path = tmp_path / "outbox" / "field_request.json"
    manifest_path = tmp_path / "outbox" / "submission_manifest.json"
    ledger_path = tmp_path / "ledger" / "client_field_ledger.jsonl"

    _run_encoder(
        "encode",
        "--corpus-path",
        str(corpus_dir),
        "--query-path",
        str(query_dir),
        "--secret",
        "test-client-secret",
        "--context",
        "sendable-redaction-test",
        "--ledger",
        str(ledger_path),
        "--output",
        str(request_path),
        "--submission-manifest-output",
        str(manifest_path),
    )

    request = json.loads(request_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sendable_text = request_path.read_text(encoding="utf-8") + manifest_path.read_text(encoding="utf-8")
    ledger_text = ledger_path.read_text(encoding="utf-8")

    assert str(tmp_path) not in sendable_text
    assert "case_alpha" not in sendable_text
    assert "client-secret" not in sendable_text
    assert "ledger_path" not in request["client_decode_hint"]
    assert request["client_decode_hint"]["ledger_path_redacted"] is True
    assert manifest["api_endpoint"] == "/v1/openencoder/field-request"
    assert manifest["sendable_files"] == [request_path.name, manifest_path.name]
    assert manifest["source_labels_redacted"] is True
    assert manifest["paths_redacted"] is True
    assert "corpus_source_labels" not in manifest
    assert "query_source_labels" not in manifest
    assert str(tmp_path) in ledger_text
    assert "client-secret-contract.md" in ledger_text


def test_encode_request_emits_oezk1_reference_fields(tmp_path: Path) -> None:
    _request_path, ledger_path, request = _make_roundtrip_fixture(tmp_path)
    corpus_tensor = request["corpus_field"]["field_tensor"]
    query_tensor = request["query_field"]["field_tensor"]
    ledger_events = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines()]

    assert request["schema_version"] == "openencoder-oezk1-request-v1"
    assert request["field_encoding"]["recipe_id"] == "openencoder-oezk1-signed-int16-typed-atom-v1"
    assert request["field_encoding"]["dtype"] == "int16"
    assert request["field_encoding"]["tokenization_policy"] == "unicode-word-token-v2"
    assert request["corpus_field"]["calc_hash"] == request["field_encoding"]["recipe_id"] + ":" + request["field_encoding"]["recipe_sha256"][:32]
    assert all(isinstance(value, int) and -32767 <= value <= 32767 for value in corpus_tensor)
    assert all(isinstance(value, int) and -32767 <= value <= 32767 for value in query_tensor)
    assert all(event.get("recipe_id") == "openencoder-oezk1-signed-int16-typed-atom-v1" for event in ledger_events)
    assert all(event.get("dtype") == "int16" for event in ledger_events)
    assert all("field_receipt_sha256" in event for event in ledger_events if event["event_type"] == "field_map")


def test_calc_hash_is_unkeyed_recipe_hash_across_client_secrets(tmp_path: Path) -> None:
    corpus_dir = tmp_path / "corpus"
    query_dir = tmp_path / "query"
    corpus_dir.mkdir()
    query_dir.mkdir()
    (corpus_dir / "doc.txt").write_text("Same recipe across secrets.", encoding="utf-8")
    (query_dir / "q.txt").write_text("What is stable?", encoding="utf-8")
    requests = []
    for idx, secret in enumerate(("long-secret-alpha-1", "long-secret-beta-22")):
        request_path = tmp_path / f"request_{idx}.json"
        ledger_path = tmp_path / f"ledger_{idx}.jsonl"
        _run_encoder(
            "encode", "--corpus-path", str(corpus_dir), "--query-path", str(query_dir),
            "--secret", secret, "--context", "same-recipe", "--width", "16",
            "--ledger", str(ledger_path), "--output", str(request_path),
        )
        requests.append(json.loads(request_path.read_text(encoding="utf-8")))

    assert requests[0]["corpus_field"]["calc_hash"] == requests[1]["corpus_field"]["calc_hash"]
    assert requests[0]["corpus_field"]["corpus_hash"] != requests[1]["corpus_field"]["corpus_hash"]


def test_demo_secret_is_rejected(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable, str(SCRIPT), "encode",
            "--corpus", "demo corpus",
            "--query", "demo query",
            "--secret", "example-not-secret",
            "--ledger", str(tmp_path / "ledger.jsonl"),
            "--output", str(tmp_path / "request.json"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "refusing known demo secret" in result.stderr


def test_decode_fails_closed_on_incompatible_encoding_declaration(tmp_path: Path) -> None:
    _request_path, ledger_path, request = _make_roundtrip_fixture(tmp_path)
    query_payload = request.get("query_field") or request["query_fields"][0]
    emission_path = tmp_path / "service_emission_incompatible.json"
    emission_path = _write_emission(tmp_path, request)
    emission = json.loads(emission_path.read_text(encoding="utf-8"))
    emission["field_encoding"]["recipe_id"] = "wrong-recipe"
    emission["field_encoding"]["dtype"] = "float32"
    emission_path.write_text(json.dumps(emission, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    decoded_path = tmp_path / "decoded_incompatible.json"

    _run_encoder(
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
    )
    decoded = json.loads(decoded_path.read_text(encoding="utf-8"))

    assert decoded["compatibility"]["passed"] is False
    assert decoded["compatibility"]["blocker_count"] >= 1
    assert decoded["local_answer_report"]["all_questions_answered"] is False
    assert decoded["local_answer_report"]["compatibility_passed"] is False


def test_decode_reports_unresolved_references_without_answering(tmp_path: Path) -> None:
    _request_path, ledger_path, request = _make_roundtrip_fixture(tmp_path)
    emission_path = _write_emission(tmp_path, request, unresolved=True)
    decoded_path = tmp_path / "decoded.json"

    _run_encoder(
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
    )
    decoded = json.loads(decoded_path.read_text(encoding="utf-8"))

    assert decoded["unresolved_field_like_reference_count"] >= 1
    assert decoded["local_answer_report"]["all_questions_answered"] is False
    assert decoded["local_answer_report"]["human_verdict"].startswith("FAIL:")


def test_decode_fails_closed_on_service_request_hash_mismatch(tmp_path: Path) -> None:
    _request_path, ledger_path, request = _make_roundtrip_fixture(tmp_path)
    emission_path = _write_emission(tmp_path, request)
    emission = json.loads(emission_path.read_text(encoding="utf-8"))
    emission["request_sha256"] = "0" * 64
    emission_path.write_text(json.dumps(emission, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    decoded_path = tmp_path / "decoded_binding_mismatch.json"

    _run_encoder(
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
    )
    decoded = json.loads(decoded_path.read_text(encoding="utf-8"))

    assert decoded["request_binding"]["passed"] is False
    assert "request_binding:request_sha256_mismatch" in decoded["compatibility"]["blockers"]
    assert decoded["local_answer_report"]["all_questions_answered"] is False


def test_decode_fails_closed_when_ledger_hash_chain_is_tampered(tmp_path: Path) -> None:
    _request_path, ledger_path, request = _make_roundtrip_fixture(tmp_path)
    lines = ledger_path.read_text(encoding="utf-8").splitlines()
    tampered = json.loads(lines[0])
    tampered["text_sha256"] = "0" * 64
    lines[0] = json.dumps(tampered, sort_keys=True, separators=(",", ":"))
    ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    emission_path = _write_emission(tmp_path, request)
    decoded_path = tmp_path / "decoded_tampered.json"

    _run_encoder(
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
    )
    decoded = json.loads(decoded_path.read_text(encoding="utf-8"))

    assert decoded["ledger"]["hash_chain_valid"] is False
    assert decoded["local_answer_report"]["all_questions_answered"] is False
    assert decoded["local_answer_report"]["human_verdict"].startswith("FAIL:")


def test_decode_fails_closed_when_source_hash_changes(tmp_path: Path) -> None:
    _request_path, ledger_path, request = _make_roundtrip_fixture(tmp_path)
    corpus_path = tmp_path / "corpus" / "contract.md"
    corpus_path.write_text("This local source was changed after encoding.", encoding="utf-8")
    emission_path = _write_emission(tmp_path, request)
    decoded_path = tmp_path / "decoded_changed_source.json"

    _run_encoder(
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
    )
    decoded = json.loads(decoded_path.read_text(encoding="utf-8"))

    assert decoded["ledger"]["hash_chain_valid"] is True
    assert decoded["local_answer_report"]["all_questions_answered"] is False
    assert decoded["local_answer_report"]["rows"][0]["status"] != "answered"


def test_gui_command_has_launch_function() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "def launch_gui" in source
    assert "return launch_gui(args)" in source


def test_release_privacy_scan_passes() -> None:
    root = SCRIPT.parent
    completed = subprocess.run(
        [sys.executable, str(root / "scripts" / "release_privacy_scan.py")],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["passed"] is True
    assert payload["finding_count"] == 0
    assert payload["scanned_file_count"] >= 1


def test_ci_runs_on_push_pull_request_and_snark() -> None:
    root = SCRIPT.parent
    workflow = (root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "push:" in workflow
    assert "pull_request:" in workflow
    assert "scripts/release_privacy_scan.py" in workflow
    assert "scripts/package_portable_launcher_ape.py" in workflow
    assert "scripts/check_release_gates.py" in (root / ".github" / "workflows" / "release-attestation.yml").read_text(encoding="utf-8")
    assert "python3 -m pip install . pytest" in workflow
    assert "docs/proofs/groth16_verification_proof.json" in workflow
    assert "./bin/OpenEncoder.com --synthetic-e2e" in workflow


def test_repository_public_files_do_not_contain_private_paths_or_contacts() -> None:
    root = SCRIPT.parent
    tracked = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    checked_paths = [
        root / raw
        for raw in tracked
        if (root / raw).exists()
        and (root / raw).suffix in {".md", ".py", ".zig", ".toml", ".yml", ".yaml", ""}
    ]
    joined = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in checked_paths)

    private_home = "/home/" + "private-user"
    private_windows_user = "Users\\" + "private-user"
    assert private_home not in joined
    assert private_windows_user not in joined
    assert re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", joined) is None


def test_msmarco_replay_proof_script_is_present_and_safe() -> None:
    root = SCRIPT.parent
    proof_script = root / "scripts" / "prove_msmarco_replay.py"
    text = proof_script.read_text(encoding="utf-8")

    assert "client_field_encoder.py" in text
    assert "pyarrow.ipc" in text
    assert "DEFAULT_ARTIFACT = ROOT / \"docs\" / \"proofs\" / \"msmarco_replay_proof.json\"" in text
    assert "OpenEncoder-only encode/decode deterministic replay" in text
    assert "download_mode" not in text
    assert ("ioni" + "zer") not in text.lower()
    assert ("gravi" + "tas") not in text.lower()
    assert ("zk" + "voo") not in text.lower()
    private_home = "/home/" + "private-user"
    assert private_home not in text


def test_msmarco_replay_proof_artifact_has_required_release_fields() -> None:
    root = SCRIPT.parent
    artifact_path = root / "docs" / "proofs" / "msmarco_replay_proof.json"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    required_fields = {
        "dataset_name",
        "dataset_config",
        "split",
        "sample_size",
        "corpus_file_count",
        "query_file_count",
        "encode_run_a_hashes",
        "encode_run_b_hashes",
        "decode_run_a_hashes",
        "decode_run_b_hashes",
        "exact_replay_passed",
        "ledger_hash_chain_passed",
        "compatibility_gate_passed",
        "unresolved_reference_count",
        "local_excerpt_recovery_percent",
        "local_excerpt_recovery_definition",
        "request_plaintext_audit_passed",
        "deterministic_receipt_passed",
    }

    assert required_fields <= set(artifact)
    assert artifact["schema_version"] == "openencoder-msmarco-standalone-replay-proof-v1"
    assert artifact["dataset_name"] == "ms_marco"
    assert artifact["dataset_config"] == "v2.1"
    assert artifact["split"] == "validation"
    assert artifact["sample_size"] == 3
    assert artifact["corpus_file_count"] == 9
    assert artifact["query_file_count"] == 3
    assert artifact["exact_replay_passed"] is True
    assert artifact["ledger_hash_chain_passed"] is True
    assert artifact["compatibility_gate_passed"] is True
    assert artifact["unresolved_reference_count"] == 0
    assert artifact["local_excerpt_recovery_percent"] == 100.0
    assert "not MS MARCO answer correctness" in artifact["local_excerpt_recovery_definition"]
    assert artifact["request_plaintext_audit_passed"] is True
    assert artifact["deterministic_receipt_passed"] is True
    assert artifact["forbidden_dependency_surfaces"] == []
    assert artifact["cache_locator"].startswith("local-msmarco-arrow-cache-fingerprint-sha256:")
    assert all(artifact["exact_replay_checks"].values())
    assert artifact["encode_run_a_hashes"] == artifact["encode_run_b_hashes"]
    assert artifact["decode_run_a_hashes"] == artifact["decode_run_b_hashes"]


def test_msmarco_full_parity_proof_artifact_has_required_release_fields() -> None:
    root = SCRIPT.parent
    proof_script = root / "scripts" / "prove_msmarco_full_parity.py"
    script_text = proof_script.read_text(encoding="utf-8")
    artifact_path = root / "docs" / "proofs" / "msmarco_full_parity_proof.json"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    readme = (root / "README.md").read_text(encoding="utf-8")
    artifact_sha256 = hashlib.sha256(artifact_path.read_bytes()).hexdigest()

    assert "encode_source_item" in script_text
    assert "local-ledger-hash-mapback-equivalence-v1" in script_text
    assert "download_mode" not in script_text
    private_home = "/home/" + "private-user"
    assert private_home not in script_text

    assert artifact["schema_version"] == "openencoder-msmarco-full-local-cache-parity-proof-v1"
    assert artifact["proof_passed"] is True
    assert artifact["dataset_name"] == "ms_marco"
    assert artifact["dataset_config"] == "v2.1"
    assert artifact["requested_splits"] == ["test", "train", "validation"]
    assert artifact["declared_row_count"] == 1010916
    assert artifact["measured_row_count"] == 1010916
    assert artifact["measured_query_count"] == 1010916
    assert artifact["measured_passage_count"] == 10087677
    assert artifact["encoded_source_count"] == 11098593
    assert artifact["decoded_source_count"] == 11098593
    assert artifact["encode_decode_parity_percent"] == 100.0
    assert artifact["fidelity_loss_count"] == 0
    assert artifact["all_arrow_files_covered"] is True
    assert artifact["declared_rows_match_measured_rows"] is True
    assert artifact["mismatch_samples"] == []
    assert artifact["totals"]["text_hash_mismatches"] == 0
    assert artifact["totals"]["canonical_hash_mismatches"] == 0
    assert artifact["totals"]["typed_atom_hash_mismatches"] == 0
    assert artifact["totals"]["signal_replay_mismatches"] == 0
    assert artifact["totals"]["field_receipt_replay_mismatches"] == 0
    assert artifact["totals"]["field_id_replay_mismatches"] == 0
    assert artifact["totals"]["exceptions"] == 0
    assert artifact["local_cache_limitations"]["separate_138m_passage_collection_found"] is False
    assert artifact_sha256 in readme
    assert artifact["source_chain_sha256"] in readme
    assert artifact["decode_chain_sha256"] in readme
    assert artifact["signal_chain_sha256"] in readme
    assert artifact["receipt_chain_sha256"] in readme


def test_msmarco_v2_real_parity_handoff_has_required_release_fields() -> None:
    root = SCRIPT.parent
    proof_script = root / "scripts" / "prove_msmarco_v2_real_parity.py"
    compare_script = root / "scripts" / "compare_msmarco_v2_real.py"
    script_text = proof_script.read_text(encoding="utf-8")
    artifact_path = root / "docs" / "proofs" / "msmarco_v2_real_proof.json"
    handoff_path = root / "docs" / "proofs" / "msmarco_v2_real_public_handoff.json"
    gravitas_path = root / "docs" / "proofs" / "msmarco_full_parity_gravitas_submission.json"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    gravitas = json.loads(gravitas_path.read_text(encoding="utf-8"))
    readme = (root / "README.md").read_text(encoding="utf-8")
    artifact_file_sha256 = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    handoff_file_sha256 = hashlib.sha256(handoff_path.read_bytes()).hexdigest()

    assert "load_dataset" in script_text
    assert "streaming=True" in script_text
    assert "encode_source_item" in script_text
    assert proof_script.exists()
    assert compare_script.exists()

    assert artifact["schema_version"] == "openencoder-msmarco-v2-real-parity-proof-v1"
    assert artifact["benchmark_kind"] == "encode_decode_parity_only"
    assert artifact["not_a_semantic_retrieval_benchmark"] is True
    assert artifact["dataset"]["dataset_id"] == "mteb/msmarco-v2"
    assert artifact["dataset"]["query_count"] == 285328
    assert artifact["dataset"]["passage_count"] == 138364198
    assert artifact["dataset"]["encoded_decoded_source_count"] == 138649526
    assert artifact["metrics"]["encode_decode_accuracy_percent"] == 100.0
    assert artifact["metrics"]["text_hash_mismatches"] == 0
    assert artifact["metrics"]["canonical_hash_mismatches"] == 0
    assert artifact["metrics"]["typed_atom_hash_mismatches"] == 0
    assert artifact["metrics"]["signal_replay_mismatches"] == 0
    assert artifact["metrics"]["field_receipt_replay_mismatches"] == 0
    assert artifact["metrics"]["field_id_replay_mismatches"] == 0
    assert artifact["metrics"]["exceptions"] == 0
    assert artifact["proof"]["proof_passed"] is True
    assert artifact["proof"]["artifact_sha256"] == "d15c702867e001b7020e65e55b5d23b3844c03638203f45bc3237154b3ddd202"

    assert handoff["schema_version"] == "openencoder-msmarco-v2-repro-handoff-v1"
    assert handoff["artifact_set"]["proof"]["file_sha256"] == artifact_file_sha256
    assert handoff["results"]["proof_passed"] is True
    assert gravitas["schema_version"] == "openencoder-msmarco-full-parity-gravitas-v1"
    assert gravitas["submitted_to"] == "gravitas"
    assert gravitas["not_a_semantic_retrieval_benchmark"] is True
    assert gravitas["fidelity"]["encoded_source_count"] == 11098593
    assert artifact["proof"]["artifact_sha256"] in readme
    assert artifact_file_sha256 in readme
    assert handoff_file_sha256 in readme


def test_public_claims_verification_proof_blocks_stale_msmarco_wording() -> None:
    root = SCRIPT.parent
    proof_script = root / "scripts" / "prove_public_claims.py"
    proof_artifact = root / "docs" / "proofs" / "public_claims_verification_proof.json"
    script_text = proof_script.read_text(encoding="utf-8")
    artifact = json.loads(proof_artifact.read_text(encoding="utf-8"))

    assert proof_script.exists()
    assert "FORBIDDEN_CLAIM_FRAGMENTS" in script_text
    assert artifact["schema_version"] == "openencoder-public-claims-verification-proof-v1"
    assert artifact["proof_passed"] is True
    assert artifact["blocker_count"] == 0
    assert artifact["blockers"] == []
    forbidden_hashes = set(artifact["forbidden_claim_fragment_sha256"])
    assert hashlib.sha256(("NOT CLAIMED until exact " + "full" + "-gamut run").encode("utf-8")).hexdigest() in forbidden_hashes
    assert hashlib.sha256(("OpenEncoder+Gravitas " + "production").encode("utf-8")).hexdigest() in forbidden_hashes
    scanned_paths = {entry["path"] for entry in artifact["public_claim_files"]}
    assert "README.md" in scanned_paths
    assert "docs/BENCHMARKS.md" in scanned_paths


def test_msmarco_reproduction_docs_reference_public_dataset_and_artifact() -> None:
    root = SCRIPT.parent
    readme = (root / "README.md").read_text(encoding="utf-8")
    reproduction = (root / "docs" / "MSMARCO_REPRODUCTION.md").read_text(encoding="utf-8")
    docs = readme + "\n" + reproduction

    assert "https://microsoft.github.io/msmarco/" in docs
    assert "https://huggingface.co/datasets/microsoft/ms_marco" in docs
    assert "https://arxiv.org/abs/1611.09268" in docs
    assert "scripts/prove_msmarco_full_parity.py" in reproduction
    assert "docs/proofs/msmarco_full_parity_proof.json" in reproduction
    assert "scripts/prove_msmarco_v2_real_parity.py" in reproduction
    assert "docs/proofs/msmarco_v2_real_proof.json" in reproduction
    assert "docs/proofs/msmarco_full_parity_gravitas_submission.json" in reproduction
    assert "/home/" + "private-user" not in docs


def test_reference_replay_proof_script_is_present_and_safe() -> None:
    root = SCRIPT.parent
    proof_script = root / "scripts" / "prove_reference_replay.py"
    text = proof_script.read_text(encoding="utf-8")

    assert "openencoder-oezk1-signed-int16-typed-atom-v1" in text
    assert "whitespace-only corpus edit" in text
    assert "download_mode" not in text
    private_home = "/home/" + "private-user"
    assert private_home not in text



def test_groth16_verification_artifact_positive_and_tampered() -> None:
    pytest = __import__("pytest")
    pytest.importorskip("py_ecc")
    from openencoder_groth16 import verify_groth16_payload

    root = SCRIPT.parent
    artifact_path = root / "docs" / "proofs" / "groth16_verification_proof.json"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

    valid = verify_groth16_payload(artifact["valid_fixture"])
    wrapped = verify_groth16_payload(artifact)
    tampered = artifact["tampered_verification"]

    assert artifact["schema_version"] == "openencoder-groth16-verification-proof-v1"
    assert artifact["proof_passed"] is True
    assert valid["passed"] is True
    assert wrapped["passed"] is True
    assert tampered["passed"] is False
    assert "pairing_product_not_one" in tampered["blockers"]
    assert valid["proof_system"] == "groth16-bn254-pairing-v1"


def test_groth16_required_dependency_and_cli_are_documented() -> None:
    root = SCRIPT.parent
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    source = SCRIPT.read_text(encoding="utf-8")

    assert 'dependencies = ["py-ecc>=8.0.0,<9"]' in pyproject
    assert "verify_groth16_command" in source
    assert "emit_command" in source
    assert "_envelope_proof_report" in source
    assert "verify-groth16" not in source
    assert "verify-groth16" not in readme
    assert "docs/proofs/groth16_verification_proof.json" in readme


def test_real_groth16_circuit_gate_passes_with_pinned_manifest_and_artifacts() -> None:
    from openencoder_groth16 import real_circuit_gate_status

    root = SCRIPT.parent
    gate = real_circuit_gate_status(root / "docs" / "proofs" / "openencoder_real_groth16_circuit_manifest.json")
    assert gate["passed"] is True
    assert gate["blockers"] == []
    assert (root / "circuits" / "openencoder_field_envelope.circom").exists()
    assert (root / "docs" / "proofs" / "real_groth16" / "proof.json").exists()
    assert (root / "docs" / "proofs" / "real_groth16" / "verification_key.json").exists()


def test_required_unresolved_reference_fails_closed(tmp_path: Path) -> None:
    corpus_dir = tmp_path / "corpus"
    query_dir = tmp_path / "query"
    corpus_dir.mkdir()
    query_dir.mkdir()
    (corpus_dir / "doc.txt").write_text("Some corpus text here.", encoding="utf-8")
    (query_dir / "q.txt").write_text("Some query text.", encoding="utf-8")

    request_path = tmp_path / "request.json"
    ledger_path = tmp_path / "ledger.jsonl"
    _run_encoder(
        "encode",
        "--corpus-path", str(corpus_dir),
        "--query-path", str(query_dir),
        "--secret", "test-unresolved-secret",
        "--context", "unresolved-test",
        "--width", "16",
        "--limit", "2",
        "--ledger", str(ledger_path),
        "--output", str(request_path),
    )

    request = json.loads(request_path.read_text(encoding="utf-8"))

    corpus_field = dict(request.get("corpus_field") or {})
    corpus_field["corpus_hash"] = "sha256:bogus_unresolvable_hash_not_in_ledger"

    emission = {
        "object": "openencoder.reference_field_emission",
        "schema_version": "openencoder-reference-field-emission-v1",
        "client_request_id": request.get("client_request_id"),
        "field_encoding": request.get("field_encoding", {}),
        "query_count": 0,
        "query_results": [],
        "determinism_boundary": {"deterministic_replay_supported": True},
        "core_result": {
            "schema_version": "openencoder-field-envelope-relation-result-v1",
            "core_call_shape": "field_relation(corpus_field, query_field) -> response_field",
            "corpus_hash": "sha256:bogus_unresolvable_hash_not_in_ledger",
            "query_payload_hash": "sha256:also_bogus",
            "corpus_signal_sha256": "bogus",
            "query_signal_sha256": "bogus",
            "result_field_sha256": "bogus",
        },
        "groth16_envelope_proof": {
            "schema_version": "openencoder-groth16-envelope-proof-v1",
            "proof_system": "groth16-bn254-pairing-v1",
            "curve": "bn254",
            "circuit_id": "openencoder-field-envelope-relation-v1",
            "statement": {},
            "statement_sha256": "",
            "public_signals": [1],
            "proof": {"pi_a": [1, 2], "pi_b": [[1, 2], [3, 4]], "pi_c": [1, 2]},
            "verifying_key": {"vk_alpha_1": [1, 2], "vk_beta_2": [[1, 2], [3, 4]], "vk_gamma_2": [[1, 2], [3, 4]], "vk_delta_2": [[1, 2], [3, 4]], "IC": [[1, 2]]},
        },
    }

    emission_path = tmp_path / "emission.json"
    emission_path.write_text(json.dumps(emission), encoding="utf-8")

    decoded_path = tmp_path / "decoded.json"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "decode",
         "--ledger", str(ledger_path),
         "--emission", str(emission_path),
         "--output", str(decoded_path)],
        check=False, capture_output=True, text=True,
    )
    decoded = json.loads(decoded_path.read_text(encoding="utf-8"))

    assert decoded["required_unresolved_reference_count"] > 0
    assert decoded["compatibility"]["passed"] is False
    required_blockers = [b for b in decoded["compatibility"].get("blockers", []) if "required_reference_unresolved" in b]
    assert len(required_blockers) > 0
    assert decoded["local_answer_report"]["all_questions_answered"] is False


def test_repeated_query_same_context_produces_identical_fields(tmp_path: Path) -> None:
    corpus_dir = tmp_path / "corpus"
    query_dir = tmp_path / "query"
    corpus_dir.mkdir()
    query_dir.mkdir()
    (corpus_dir / "a.txt").write_text("Repeated query test corpus.", encoding="utf-8")
    (query_dir / "q.txt").write_text("Repeated query test.", encoding="utf-8")

    request_a = tmp_path / "req_a.json"
    ledger_a = tmp_path / "ledger_a.jsonl"
    _run_encoder(
        "encode", "--corpus-path", str(corpus_dir), "--query-path", str(query_dir),
        "--secret", "repeat-test-secret", "--context", "repeat-context",
        "--width", "16", "--limit", "2", "--ledger", str(ledger_a), "--output", str(request_a),
    )

    request_b = tmp_path / "req_b.json"
    ledger_b = tmp_path / "ledger_b.jsonl"
    _run_encoder(
        "encode", "--corpus-path", str(corpus_dir), "--query-path", str(query_dir),
        "--secret", "repeat-test-secret", "--context", "repeat-context",
        "--width", "16", "--limit", "2", "--ledger", str(ledger_b), "--output", str(request_b),
    )

    ra = json.loads(request_a.read_text(encoding="utf-8"))
    rb = json.loads(request_b.read_text(encoding="utf-8"))
    assert ra["corpus_field"]["field_tensor"] == rb["corpus_field"]["field_tensor"]
    assert ra["corpus_field"]["corpus_hash"] == rb["corpus_field"]["corpus_hash"]
    assert ra["query_field"]["field_tensor"] == rb["query_field"]["field_tensor"]


def test_unicode_non_english_input_encodes_and_decodes(tmp_path: Path) -> None:
    corpus_dir = tmp_path / "corpus"
    query_dir = tmp_path / "query"
    corpus_dir.mkdir()
    query_dir.mkdir()
    (corpus_dir / "cjk.txt").write_text("日本語テスト中文测试한국어테스트", encoding="utf-8")
    (corpus_dir / "emoji.txt").write_text("Security review: encryption is not a goal!", encoding="utf-8")
    (corpus_dir / "cyrillic.txt").write_text("Это тест на русском языке.", encoding="utf-8")
    (query_dir / "q.txt").write_text("What is not a goal?", encoding="utf-8")

    request_path = tmp_path / "req.json"
    ledger_path = tmp_path / "ledger.jsonl"
    _run_encoder(
        "encode", "--corpus-path", str(corpus_dir), "--query-path", str(query_dir),
        "--secret", "unicode-test-secret", "--context", "unicode-test",
        "--width", "32", "--limit", "5", "--ledger", str(ledger_path), "--output", str(request_path),
    )

    request = json.loads(request_path.read_text(encoding="utf-8"))
    assert len(request["corpus_field"]["field_tensor"]) == 32
    assert all(isinstance(v, int) and -32767 <= v <= 32767 for v in request["corpus_field"]["field_tensor"])

    emission_path = tmp_path / "emission.json"
    _run_encoder("emit", "--request", str(request_path), "--output", str(emission_path))

    decoded_path = tmp_path / "decoded.json"
    _run_encoder(
        "decode", "--ledger", str(ledger_path), "--emission", str(emission_path),
        "--include-text", "--output", str(decoded_path),
    )
    decoded = json.loads(decoded_path.read_text(encoding="utf-8"))
    assert decoded["ledger"]["hash_chain_valid"] is True
    assert decoded["envelope_proof"]["passed"] is True


def test_unicode_tokenization_keeps_non_ascii_signals_distinct() -> None:
    from client_field_encoder import _tokens, encode_texts

    assert _tokens("日本語테스트 русский café") == ["日本語테스트", "русский", "café"]
    secret = b"unicode-distinct-secret"
    cjk = encode_texts(["日本語テスト"], secret=secret, width=32, role="a", context="unicode")
    cyrillic = encode_texts(["русский тест"], secret=secret, width=32, role="a", context="unicode")
    accented = encode_texts(["café résumé"], secret=secret, width=32, role="a", context="unicode")
    assert cjk != cyrillic
    assert cjk != accented
    assert cyrillic != accented


def test_different_context_produces_different_field_ids(tmp_path: Path) -> None:
    corpus_dir = tmp_path / "corpus"
    query_dir = tmp_path / "query"
    corpus_dir.mkdir()
    query_dir.mkdir()
    (corpus_dir / "a.txt").write_text("Same text different context.", encoding="utf-8")
    (query_dir / "q.txt").write_text("Context separation test.", encoding="utf-8")

    req_ctx_a = tmp_path / "req_ctx_a.json"
    ledger_a = tmp_path / "ledger_a.jsonl"
    _run_encoder(
        "encode", "--corpus-path", str(corpus_dir), "--query-path", str(query_dir),
        "--secret", "context-sep-secret", "--context", "context-alpha",
        "--width", "16", "--limit", "2", "--ledger", str(ledger_a), "--output", str(req_ctx_a),
    )

    req_ctx_b = tmp_path / "req_ctx_b.json"
    ledger_b = tmp_path / "ledger_b.jsonl"
    _run_encoder(
        "encode", "--corpus-path", str(corpus_dir), "--query-path", str(query_dir),
        "--secret", "context-sep-secret", "--context", "context-beta",
        "--width", "16", "--limit", "2", "--ledger", str(ledger_b), "--output", str(req_ctx_b),
    )

    ra = json.loads(req_ctx_a.read_text(encoding="utf-8"))
    rb = json.loads(req_ctx_b.read_text(encoding="utf-8"))
    assert ra["corpus_field"]["corpus_hash"] != rb["corpus_field"]["corpus_hash"]
    assert ra["corpus_field"]["field_tensor"] != rb["corpus_field"]["field_tensor"]


def test_source_deletion_after_encode_prevents_answer_recovery(tmp_path: Path) -> None:
    corpus_dir = tmp_path / "corpus"
    query_dir = tmp_path / "query"
    corpus_dir.mkdir()
    query_dir.mkdir()
    corpus_file = corpus_dir / "deletable.txt"
    corpus_file.write_text("This file will be deleted after encode.", encoding="utf-8")
    (query_dir / "q.txt").write_text("What happens without source?", encoding="utf-8")

    request_path = tmp_path / "req.json"
    ledger_path = tmp_path / "ledger.jsonl"
    _run_encoder(
        "encode", "--corpus-path", str(corpus_dir), "--query-path", str(query_dir),
        "--secret", "delete-test-secret", "--context", "delete-test",
        "--width", "16", "--limit", "2", "--ledger", str(ledger_path), "--output", str(request_path),
    )

    corpus_file.unlink()

    emission_path = tmp_path / "emission.json"
    _run_encoder("emit", "--request", str(request_path), "--output", str(emission_path))

    decoded_path = tmp_path / "decoded.json"
    _run_encoder(
        "decode", "--ledger", str(ledger_path), "--emission", str(emission_path),
        "--include-text", "--output", str(decoded_path),
    )
    decoded = json.loads(decoded_path.read_text(encoding="utf-8"))
    report = decoded["local_answer_report"]
    answered_rows = [row for row in report["rows"] if row["status"] == "answered" and "will be deleted" in row.get("answer_text", "")]
    assert len(answered_rows) == 0


def test_ledger_truncation_invalidates_hash_chain(tmp_path: Path) -> None:
    corpus_dir = tmp_path / "corpus"
    query_dir = tmp_path / "query"
    corpus_dir.mkdir()
    query_dir.mkdir()
    (corpus_dir / "doc.txt").write_text("Ledger truncation test.", encoding="utf-8")
    (query_dir / "q.txt").write_text("Truncation?", encoding="utf-8")

    ledger_path = tmp_path / "ledger.jsonl"
    request_path = tmp_path / "req.json"
    _run_encoder(
        "encode", "--corpus-path", str(corpus_dir), "--query-path", str(query_dir),
        "--secret", "truncation-secret", "--context", "truncation-test",
        "--width", "16", "--limit", "2", "--ledger", str(ledger_path), "--output", str(request_path),
    )

    lines = ledger_path.read_text(encoding="utf-8").splitlines()
    last_event = json.loads(lines[-1])
    last_event["previous_event_hash"] = "corrupted_hash_value"
    lines[-1] = json.dumps(last_event, sort_keys=True, separators=(",", ":"))
    ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    emission_path = tmp_path / "emission.json"
    _run_encoder("emit", "--request", str(request_path), "--output", str(emission_path))

    decoded_path = tmp_path / "decoded.json"
    _run_encoder(
        "decode", "--ledger", str(ledger_path), "--emission", str(emission_path),
        "--output", str(decoded_path),
    )
    decoded = json.loads(decoded_path.read_text(encoding="utf-8"))
    assert decoded["ledger"]["hash_chain_valid"] is False
    assert decoded["local_answer_report"]["ledger_hash_chain_valid"] is False
