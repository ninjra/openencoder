# OpenEncoder Benchmarks

This file is the artifact-backed benchmark reporting surface for OpenEncoder. It is intentionally table-first so benchmark numbers can be pasted into a stable monospace dashboard.

## Current Dashboard

```text
OPENENCODER BENCHMARK DASHBOARD
Run ID:      msmarco-full-local-cache-parity
Commit:      checked-in artifact
Dataset:     ms_marco v2.1 train+validation+test local Arrow cache
Generated:   2026-05-21

+----+----------------------------+----------------+----------------+------------------------------+
| #  | Gate                       | Required       | Observed       | Artifact                     |
+----+----------------------------+----------------+----------------+------------------------------+
| 01 | Encode determinism         | 100% replay    | PASS           | docs/proofs/reference_replay_proof.json |
| 02 | MS MARCO full parity       | 100% parity    | PASS           | docs/proofs/msmarco_full_parity_proof.json |
| 03 | MS MARCO exact replay      | exact hashes   | PASS           | docs/proofs/msmarco_replay_proof.json  |
| 04 | Ledger hash-chain validity | 100% valid     | PASS           | docs/proofs/msmarco_replay_proof.json  |
| 05 | Local answer recovery      | all queries    | PASS           | docs/proofs/msmarco_replay_proof.json  |
| 06 | Raw text exposure audit    | 0 service text | PASS           | docs/proofs/msmarco_replay_proof.json  |
| 07 | Compatibility-gated decode | pass           | PASS           | docs/proofs/msmarco_replay_proof.json  |
| 08 | Fail-closed decode         | all blockers   | PASS           | tests/test_client_field_encoder_smoke.py |
| 09 | CLI smoke                  | pass           | PASS           | pytest smoke output          |
| 10 | Groth16 BN254 verifier      | valid/tamper   | PASS           | docs/proofs/groth16_verification_proof.json |
| 11 | OpenEncoder.com package    | payload hash   | PASS           | docs/proofs/openencoder_origamold_masterfield_ape_package_receipt.json |
| 12 | Windows frontend E2E       | UI encode/decode | PASS         | docs/proofs/openencoder_windows_frontend_e2e_proof.json |
+----+----------------------------+----------------+----------------+------------------------------+

FULLBAR PROOF: NOT CLAIMED
ENCRYPTION PRODUCT: NOT CLAIMED
Reason: OpenEncoder measures local client replay and verifies supplied BN254 Groth16 payloads; it does not claim encrypted text transport, decryptable ciphertext, external retrieval quality, proof generation, or circuit compilation.
```

## Reference Hardware & Performance

These workstation numbers are local reference points for scale and reproducibility. They are not guaranteed performance floors across machines. The checked-in proof artifacts remain the authoritative benchmark evidence. Private host names, local paths, service ports, PIDs, and unrelated LLM serving-stack details are intentionally omitted.

```text
REFERENCE WORKSTATION ENVIRONMENT
Captured: 2026-05-21 14:56:06 -06:00
Scope: private verification workspace, sanitized for public release

+-------------------------------+-----------------------------------------------+
| Field                         | Value                                         |
+-------------------------------+-----------------------------------------------+
| host class                    | AI workstation, host name omitted             |
| operating_system              | Ubuntu 24.04.4 LTS                            |
| kernel                        | Linux 6.17.0-20-generic x86_64                |
| cpu                           | AMD RYZEN AI MAX+ 395, Radeon 8060S           |
| cpu_topology                  | 16 cores / 32 threads                         |
| l3_cache                      | 64 MiB, 2 instances                           |
| system_memory                 | 124 GiB DDR5                                  |
| rocm                          | ROCm 7.13                                     |
| graphics                      | AMD Radeon 8060S integrated, gfx1151          |
| unified_memory_gtt            | 116.0 GiB total allocation space              |
| gtt_used_free                 | 58.81 GiB used (50.70%); 57.19 GiB free       |
| gpu_admission                 | open; normal_generation + large_generation    |
| python_encoder_dependencies   | Python standard library                       |
| groth16_verifier_dependency   | py-ecc 8.x required proof dependency                     |
+-------------------------------+-----------------------------------------------+
```

```text
OPENENCODER RELEASE VERIFICATION

+---------------------------------------+------------------------+---------+----------+
| TEST UNIT / WORKLOAD                  | METRIC                 | STATUS  | ELAPSED  |
+---------------------------------------+------------------------+---------+----------+
| Pytest smoke suite                    | 16/16 passed           | PASS    | 12.290s  |
| Python module compile smokes          | clean                  | PASS    | -        |
| text_round_trip_correctness           | 100.00%                | PASS    | -        |
| requirements_json_contract            | valid schema           | PASS    | -        |
| private_paths_leak_check              | 0 found                | PASS    | -        |
| tamper_fail_closed_checks             | 4/4 verified           | PASS    | -        |
| Reference replay proof                | 100.0% parity          | PASS    | 0.090s   |
| ledger hash chain                     | valid                  | PASS    | -        |
| exact replay parity                   | exact                  | PASS    | -        |
| Groth16 BN254 verification            | pairings valid         | PASS    | 11.720s  |
| Groth16 positive fixture              | 1/1 passed             | PASS    | -        |
| Groth16 negative tamper fixture       | pairing_product_not_one| PASS    | -        |
| MS MARCO v2.1 full parity             | 9/9 files, 100.0%      | PASS    | 7129.02s |
+---------------------------------------+------------------------+---------+----------+
```

Reference replay normalized answer: `Contract renewal requires legal approval before Friday.`

Groth16 tamper blocker signature:
`d2b01ed9819d4158aec16b80515cddfbbfc09298b218868b71a7a8bdadfa78ab`

```text
MS MARCO V2.1 PARITY COMPARISON
Status: COMPLETE AND VERIFIED
Cache target: Hugging Face MS MARCO v2.1 Arrow dataset, about 4.1 GiB on disk
Total rows: 1,010,916; queries: 1,010,916; passages: 10,087,677

+-------------------------------+---------------------------+---------------------------+
| Metric                        | Host baseline run         | Pristine sandbox run      |
+-------------------------------+---------------------------+---------------------------+
| Arrow files covered           | 9 / 9, 100.0%             | 9 / 9, 100.0%             |
| Total rows checked            | 1,010,916 / 1,010,916     | 1,010,916 / 1,010,916     |
| Total passages checked        | 10,087,677                | 10,087,677                |
| Decoded sources verified      | 11,098,593                | 11,098,593                |
| Fidelity/exception failures   | 0, 0.00%                  | 0, 0.00%                  |
| Hash/atom mismatches          | 0, 0.00%                  | 0, 0.00%                  |
| Signal replay mismatches      | 0, 0.00%                  | 0, 0.00%                  |
| Accuracy percent              | 100.0%                    | 100.0%                    |
| Elapsed time                  | 7,129.02 sec, 2.1 hours   | 7,113.83 sec, 1.98 hours  |
| Estimated time remaining      | N/A, completed            | N/A, completed            |
| Status                        | COMPLETE, PASSED          | COMPLETE, PASSED          |
+-------------------------------+---------------------------+---------------------------+
```

```text
MS MARCO SPLIT BREAKDOWN

+------------+---------------------+-------------------------+
| Split      | Rows verified       | Status                  |
+------------+---------------------+-------------------------+
| test       | 101,092 / 101,092   | 100.0% complete, passed |
| train      | 808,731 / 808,731   | 100.0% complete, passed |
| validation | 101,093 / 101,093   | 100.0% complete, passed |
+------------+---------------------+-------------------------+
```

The completed host baseline is the release artifact in `docs/proofs/msmarco_full_parity_proof.json`.

Proof hashes:

```text
+--------------------------------------+------------------------------------------------------------------+
| Hash                                 | Value                                                            |
+--------------------------------------+------------------------------------------------------------------+
| checked_in_full_parity_artifact_sha  | 16aadaefb8d139cd32a2855c2c810c596f30afb1634aa2cc00b5e35dbc17a6aa |
| final_sandbox_reported_proof_hash    | 782fa53229be93698c7d916f8028515e8ea8e2d507ed86d55d33863490decf40 |
+--------------------------------------+------------------------------------------------------------------+
```

Observed completed-run throughput: about 142 MS MARCO query rows/second on the host baseline and about 142 MS MARCO query rows/second on the final pristine sandbox run, pure Python local parity verification over the full local Arrow cache.

## Additional Local System Reference Point

The table below was captured on the local WSL2 host used for this documentation update. It is a second reference point, separate from the workstation validation snapshot above, and is not a guaranteed performance floor across machines.

```text
CURRENT LOCAL WSL2 CHECK
Captured: 2026-05-21 during release documentation update
Scope: local verification host

+------------------------------+------------------------------------------------+
| Field                        | Value                                          |
+------------------------------+------------------------------------------------+
| operating_system             | Ubuntu 24.04.4 LTS                             |
| kernel                       | 6.6.87.2-microsoft-standard-WSL2               |
| virtualization               | Microsoft WSL2                                 |
| cpu                          | AMD Ryzen 9 9950X3D 16-Core Processor          |
| visible_cpus                 | 32                                             |
| cpu_topology                 | 16 cores / 32 threads                          |
| l3_cache                     | 96 MiB, 1 instance                             |
| memory                       | 62 GiB total                                   |
| swap                         | 32 GiB total                                   |
+------------------------------+------------------------------------------------+
```

```text
CURRENT LOCAL WSL2 VALIDATION

+------------------------------+----------------------+---------+---------+
| TEST UNIT / WORKLOAD         | METRIC               | STATUS  | ELAPSED |
+------------------------------+----------------------+---------+---------+
| Pytest smoke suite           | 15 passed, 1 skipped | PASS    | 0.81s   |
| Groth16 BN254 verification   | pairings valid       | PASS    | 6.29s   |
| Reference replay proof       | deterministic        | PASS    | 0.27s   |
+------------------------------+----------------------+---------+---------+
```

## Result Template

```text
OPENENCODER RUN SUMMARY

+----------------------+------------------------------------------------------+
| Field                | Value                                                |
+----------------------+------------------------------------------------------+
| run_id               |                                                      |
| commit               |                                                      |
| corpus_items         |                                                      |
| query_items          |                                                      |
| field_width          |                                                      |
| service_text_leaks   |                                                      |
| ledger_events        |                                                      |
| hash_chain_valid     |                                                      |
| decoded_queries      |                                                      |
| unanswered_queries   |                                                      |
| elapsed_ms_encode    |                                                      |
| elapsed_ms_decode    |                                                      |
+----------------------+------------------------------------------------------+
```

## Artifact Contract

Each benchmark update should include checked-in machine-readable artifacts under `docs/proofs/` or another declared evidence directory:

```text
+----------------------------+------------------------------------------------------+
| Artifact                   | Required Contents                                    |
+----------------------------+------------------------------------------------------+
| reference_replay_proof.json| encode/change/decode deterministic replay receipt  |
| msmarco_replay_proof.json  | cached MS MARCO encode/decode replay receipt       |
| msmarco_full_parity_proof.json | full local cache encode/decode parity proof      |
| requirements_validation.json | requirements command JSON validation output       |
| groth16_verification_proof.json | BN254 Groth16 positive/tampered verification proof |
| openencoder_origamold_masterfield_ape_package_receipt.json | OpenEncoder.com embedded payload package receipt |
| openencoder_windows_frontend_e2e_proof.json | Windows visible-control frontend encode/decode proof |
| openencoder_linux_ape_e2e_proof.json | Linux/WSL portable launcher encode/decode proof |
| tests/test_client_field_encoder_smoke.py | fail-closed, privacy, CLI smoke checks |
+----------------------------+------------------------------------------------------+
```

Do not add a metric unless the artifact or named test exists and can be reproduced by the documented command.

## MS MARCO Deterministic Replay Proof

OpenEncoder includes `scripts/prove_msmarco_replay.py` for a deterministic encode/decode replay proof over a local MS MARCO HuggingFace Arrow cache.

```bash
OPENENCODER_MSMARCO_CACHE=/path/to/msmarco_v2 \
python3 scripts/prove_msmarco_replay.py \
  --config v2.1 \
  --split validation \
  --sample-size 3
```

The script reads cached `.arrow` files directly with `pyarrow`, writes a small file-backed fixture, runs `client_field_encoder.py encode`, builds a deterministic field-service-style emission, runs `client_field_encoder.py decode`, writes deterministic replay receipts, repeats the same path at the same run path, and compares exact output hashes.

The checked-in `docs/proofs/msmarco_replay_proof.json` sample records:

```text
+------------------------------+-----------------------------------------------+
| Field                        | Value                                         |
+------------------------------+-----------------------------------------------+
| dataset                      | ms_marco v2.1 validation                      |
| sample_size                  | 3                                             |
| corpus_file_count            | 9                                             |
| query_file_count             | 3                                             |
| exact_replay_passed          | true                                          |
| ledger_hash_chain_passed     | true                                          |
| compatibility_gate_passed    | true                                          |
| unresolved_reference_count   | 0                                             |
| local_excerpt_recovery_percent | 100.0                                    |
| request_plaintext_audit      | pass                                          |
+------------------------------+-----------------------------------------------+
```

This is a client replay proof. Local excerpt recovery means ledger/source map-back produced a source-backed excerpt; it does not claim MS MARCO answer correctness, semantic ranking quality, or remote service quality. Groth16 verification is the only proof-verification lane and is covered by `docs/proofs/groth16_verification_proof.json`.


## MS MARCO Full Local-Cache Parity Proof

`docs/proofs/msmarco_full_parity_proof.json` was generated by `scripts/prove_msmarco_full_parity.py` over the local Hugging Face `microsoft/ms_marco` `v2.1` Arrow cache. It measures OpenEncoder encode/decode fidelity only: source text hash, canonical text hash, typed-atom hash, signal replay, field receipt replay, and field id replay. It does not measure semantic ranking accuracy.

Dataset links:

- Official MS MARCO site: https://microsoft.github.io/msmarco/
- Hugging Face dataset: https://huggingface.co/datasets/microsoft/ms_marco
- Paper: https://arxiv.org/abs/1611.09268

```text
+-------------------------------+-----------------------------------------------+
| Field                         | Value                                         |
+-------------------------------+-----------------------------------------------+
| splits                        | train, validation, test                       |
| arrow_files                   | 9                                             |
| measured_row_count            | 1,010,916                                     |
| measured_query_count          | 1,010,916                                     |
| measured_passage_count        | 10,087,677                                    |
| encoded_source_count          | 11,098,593                                    |
| decoded_source_count          | 11,098,593                                    |
| encode_decode_accuracy        | 100.0                                         |
| fidelity_loss_count           | 0                                             |
| source_chain_sha256           | c493488583133dbaf89a56dd119cb5d237a74e36d1a8721e430f8713fde48bd2 |
| decode_chain_sha256           | a64c858d59b4b8239f6a45da5d695b3b2850261dc6d78922dc1a93d0267266cc |
| signal_chain_sha256           | 1368394b5b4e8fc66f891d4c8add014e792d55a8fc5517a713c72177fcd7010c |
| receipt_chain_sha256          | 613c945e05138473ca4d6ad8eca15033792e1055a9360edf9f9bf2bd19e9e46c |
| mismatch_samples              | []                                            |
| separate_138m_collection      | not found in local cache                      |
+-------------------------------+-----------------------------------------------+
```

## OpenEncoder APE Proof

`bin/OpenEncoder.com` is validated by direct launcher smoke checks and checked-in proof receipts.

```bash
sh bin/OpenEncoder.com --self-check
sh bin/OpenEncoder.com --list-apps
sh bin/OpenEncoder.com --synthetic-e2e \
  --app openencoder \
  --documents "OpenEncoder Linux portable proof document. The answer is recovered from the local RAM ledger." \
  --question "Where is the answer recovered from?" \
  --answer-output /tmp/openencoder_linux_ape_answer.txt
```

The package receipt is `docs/proofs/openencoder_origamold_masterfield_ape_package_receipt.json`.
The Windows frontend proof is `docs/proofs/openencoder_windows_frontend_e2e_proof.json`.
The Linux/WSL portable proof is `docs/proofs/openencoder_linux_ape_e2e_proof.json`.
macOS payload packaging is present, but ordinary macOS click/open claims still need a host receipt before they appear in public copy.
