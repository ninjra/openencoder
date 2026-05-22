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
    assert decoded["topology_proof"]["passed"] is True
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
    assert all(isinstance(value, int) and -32767 <= value <= 32767 for value in corpus_tensor)
    assert all(isinstance(value, int) and -32767 <= value <= 32767 for value in query_tensor)
    assert all(event.get("recipe_id") == "openencoder-oezk1-signed-int16-typed-atom-v1" for event in ledger_events)
    assert all(event.get("dtype") == "int16" for event in ledger_events)
    assert all("field_receipt_sha256" in event for event in ledger_events if event["event_type"] == "field_map")


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
    assert "scripts/package_origamold_masterfield_ape.py" in workflow
    assert "python3 -m pip install . pytest" in workflow
    assert "docs/proofs/groth16_verification_proof.json" in workflow
    assert "sh bin/OpenEncoder.com --synthetic-e2e" in workflow


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
    assert artifact["encode_decode_accuracy_percent"] == 100.0
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
    assert "_topology_proof_report" in source
    assert "verify-groth16" not in source
    assert "verify-groth16" not in readme
    assert "docs/proofs/groth16_verification_proof.json" in readme
