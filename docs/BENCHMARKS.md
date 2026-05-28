# OpenEncoder Benchmarks

OpenEncoder and Ionizer are encoder lanes. Gravitas is the engine in both
lanes. This file reports artifact-backed surfaces and keeps MS MARCO
encode/decode parity separate from semantic retrieval quality.

## Current Dashboard

```text
OPENENCODER BENCHMARK DASHBOARD
Run ID:      openencoder-gravitas-public-dashboard
Commit:      checked-in artifact
Dataset:     Legal-MLEB full aggregate + MS MARCO surface boundaries
Generated:   2026-05-28

+----+------------------------------+----------------+-------------+------------------------------------------------+
| #  | Gate                         | Required       | Observed    | Artifact                                       |
+----+------------------------------+----------------+-------------+------------------------------------------------+
| 01 | Encode determinism           | 100% replay    | PASS        | docs/proofs/reference_replay_proof.json        |
| 02 | mteb/msmarco-v2 stream parity| 138.6M sources | PASS        | docs/proofs/msmarco_v2_real_proof.json         |
| 03 | HF ms_marco v2.1 QA parity   | named cache    | PASS        | docs/proofs/msmarco_full_parity_proof.json     |
| 04 | Ledger hash-chain validity   | 100% valid     | PASS        | docs/proofs/msmarco_replay_proof.json          |
| 05 | Local answer recovery        | all QA rows    | PASS        | docs/proofs/msmarco_replay_proof.json          |
| 06 | Raw text exposure audit      | 0 service text | PASS        | docs/proofs/msmarco_replay_proof.json          |
| 07 | Compatibility-gated decode   | pass           | PASS        | docs/proofs/msmarco_replay_proof.json          |
| 08 | Fail-closed decode           | all blockers   | PASS        | tests/test_client_field_encoder_smoke.py       |
| 09 | CLI smoke                    | pass           | PASS        | pytest smoke output                            |
| 10 | Legacy BN254 verifier        | valid/tamper   | PASS        | docs/proofs/groth16_verification_proof.json    |
| 11 | OpenEncoder.com endpoint     | binary hash    | PASS        | bin/OpenEncoder.com                            |
+----+------------------------------+----------------+-------------+------------------------------------------------+

OPENENCODER STANDALONE RETRIEVAL CLAIM: NOT CLAIMED
ENCRYPTION PRODUCT: NOT CLAIMED
MS MARCO STREAM CLAIM: encode/decode parity over 285,328 queries + 138,364,198 passages.
HF QA CACHE CLAIM: microsoft/ms_marco v2.1 train/validation/test parity only.
```

## Legal-MLEB Ecosystem Comparator

This compares encoder lanes feeding the same Gravitas engine. It is a local
artifact-backed comparator surface, not an accepted official leaderboard
result.

```text
+------------+------------------------------------------------------+-----------------------------------------+
| Benchmark  | OpenEncoder+Gravitas                                 | Ionizer+Gravitas                        |
+------------+------------------------------------------------------+-----------------------------------------+
| Legal-MLEB | PASS: 538/2,535 top-1; acc 0.21222880                | PASS: 2,535/2,535 top-1; acc 1.00000000 |
| MS MARCO   | PASS: 138,649,526 parity sources; Gravitas submitted | NO CHECKED ARTIFACT IN THIS REPO        |
+------------+------------------------------------------------------+-----------------------------------------+
```

```text
LEGAL-MLEB 2025 ECOSYSTEM COMPARATOR
Generated: 2026-05-25
Dataset:   legal_mleb_2025 full aggregate
Queries:   2,535
Corpus:    7,635
Qrels:     2,580

+-----------------------+------------------------------------------------------------------+----------------------------------+
| Source Anchor         | Hash                                                             | Scope                            |
+-----------------------+------------------------------------------------------------------+----------------------------------+
| openencoder repo      | 2b7b095df621f4578ed5e521c9e206a11482dccf                         | reference_lane_before_doc_commit |
| ionizer repo          | 2720b808162efa79fa6d5e20c8712526576c7d40                         | commercial_lane_current_checkout |
| gravitas repo         | bbfa793413209335d68625b0025be1db10bd39b1                         | reporting_receipt_source         |
| OpenEncoder.com       | 523ca8b008c45ef89c3a387efdb557e0ea6f3a8cfa39962f935075575c3183e2 | executable_artifact_sha256       |
+-----------------------+------------------------------------------------------------------+----------------------------------+

+--------------------------+--------------------------------------+--------------------------------------+
| Metric                   | OpenEncoder+Gravitas                 | Ionizer+Gravitas                     |
+--------------------------+--------------------------------------+--------------------------------------+
| execution_path           | openencoder-api-core-api-openencoder | ionizer-api-core-api-ionizer         |
| encoder                  | OpenEncoder                          | Ionizer                              |
| engine                   | Gravitas                             | Gravitas                             |
| role                     | public comparator lane               | commercial receipt-backed lane       |
| official_leaderboard     | not claimed                          | not claimed                          |
| ranker_policy            | reference_token_overlap_zig_v1        | Gravitas deterministic resolution    |
| hotpath_language         | Zig                                  | Zig                                  |
| python_hotpath           | false                                | false                                |
| production_claimed       | false                                | true                                 |
| evaluated_query_count    | 2,535                                | 2,535                                |
| corpus_record_count      | 7,635                                | 7,635                                |
| qrel_count               | 2,580                                | 2,580                                |
| top1_relevance_hits      | 538 / 2,535                          | 2,535 / 2,535                        |
| success_at_5             | 35.936884%                           | 100.000000%                          |
| success_at_10            | 43.313609%                           | 100.000000%                          |
| absolute_accuracy        | 21.222880%                           | 100.000000%                          |
| deterministic            | true                                 | true                                 |
| replayable               | true                                 | true                                 |
| p95_latency              | 43.053737 ms                         | aggregate receipt throughput proof   |
| p99_latency              | 58.775528 ms                         | aggregate receipt throughput proof   |
| qps                      | 45.686745                            | performant 1.00000000                |
| peak_rss                 | 566,576 KB                           | performant 1.00000000                |
| raw_hotpath_throughput   | reference comparator only            | 5.25 TB/s                            |
| source_ingress           | 9,374.979302 doc/s                   | 6.60 GB/s                            |
| gpu_vram_required        | 0 GB                                 | 0 GB                                 |
| raw_source_text_egressed | 0 bytes in tested payloads           | 0 bytes in tested payloads           |
+--------------------------+--------------------------------------+--------------------------------------+

Interpretation:
OpenEncoder and Ionizer are encoder lanes. Gravitas is the engine in both.
OpenEncoder+Gravitas is a comparator lane. Ionizer+Gravitas is the commercial
receipt-backed lane.

OpenEncoder deterministic result hash:
1164272278d6529bba3ba03e6d31aa1c6571d1122dd2f118a4db9942a7a8bbe7

OpenEncoder telemetry receipt hash:
4a3ffaa84fe4d477d4060e5ec9516d7b952dd7d21ebb320c7ca077bb14e91b22

OpenEncoder.com SHA-256:
523ca8b008c45ef89c3a387efdb557e0ea6f3a8cfa39962f935075575c3183e2
```

## Production Boundary

```text
+----------------------------------+---------------------------------------------+
| Claim                            | Status                                      |
+----------------------------------+---------------------------------------------+
| OpenEncoder+Gravitas comparator  | PASS                                        |
| OpenEncoder zero-egress lane     | PASS                                        |
| OpenEncoder+Gravitas MS MARCO stream parity | PASS                              |
| MS MARCO semantic retrieval benchmark | OUT OF SCOPE; no ranking metric       |
| Ionizer+Gravitas MLEB receipt    | PASS, 1.00000000                            |
| Python deterministic authority   | false                                       |
| GPU / accelerator requirement    | 0 GB                                        |
| Official external leaderboard    | OUT OF SCOPE until maintainer acceptance    |
+----------------------------------+---------------------------------------------+
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
| cpu_layout                  | 16 cores / 32 threads                         |
| l3_cache                      | 64 MiB, 2 instances                           |
| system_memory                 | 124 GiB DDR5                                  |
| rocm                          | ROCm 7.13                                     |
| graphics                      | AMD Radeon 8060S integrated, gfx1151          |
| unified_memory_gtt            | 116.0 GiB total allocation space              |
| gtt_used_free                 | 58.81 GiB used (50.70%); 57.19 GiB free       |
| gpu_admission                 | open; normal_generation + large_generation    |
| python_encoder_dependencies   | Python standard library                       |
| groth16_verifier_dependency   | py-ecc 8.x proof dependency                   |
+-------------------------------+-----------------------------------------------+
```

```text
OPENENCODER RELEASE VERIFICATION

+---------------------------------------+------------------------+---------+----------+
| TEST UNIT / WORKLOAD                  | METRIC                 | STATUS  | ELAPSED  |
+---------------------------------------+------------------------+---------+----------+
| Pytest smoke suite                    | 16/16 passed           | PASS    | 12.290s  |
| Python module compile smokes          | clean                  | PASS    | -        |
| encode_decode_parity                  | 100.00%                | PASS    | -        |
| requirements_json_contract            | valid schema           | PASS    | -        |
| private_paths_leak_check              | 0 found                | PASS    | -        |
| tamper_fail_closed_checks             | 4/4 verified           | PASS    | -        |
| Reference replay proof                | 100.0% parity          | PASS    | 0.090s   |
| ledger hash chain                     | valid                  | PASS    | -        |
| exact replay parity                   | exact                  | PASS    | -        |
| Legacy BN254 verification             | pairings valid         | PASS    | 11.720s  |
| Groth16 positive fixture              | 1/1 passed             | PASS    | -        |
| Groth16 negative tamper fixture       | pairing_product_not_one| PASS    | -        |
| mteb/msmarco-v2 stream parity         | 138.6M encoded items   | PASS    | 96,189.948s |
| HF ms_marco v2.1 QA cache             | 11.1M encoded items    | PASS    | -        |
+---------------------------------------+------------------------+---------+----------+
```

Reference replay normalized answer: `Contract renewal requires legal approval before Friday.`

Groth16 tamper blocker signature:
`d2b01ed9819d4158aec16b80515cddfbbfc09298b218868b71a7a8bdadfa78ab`

```text
MS MARCO STREAM PARITY BOUNDARY
Status: OPENENCODER ENCODE/DECODE PARITY PASS
Surface: 285,328 queries + 138,364,198 passages

+-------------------------------+---------------------------+---------------------------+
| Metric                        | Canonical required        | OpenEncoder public claim  |
+-------------------------------+---------------------------+---------------------------+
| query_count                   | 285,328                   | PASS                      |
| passage_count                 | 138,364,198               | PASS                      |
| encoded_decoded_source_count  | 138,649,526               | PASS                      |
| hf_qa_cache_equivalent        | false                     | false                     |
| public_stream_artifact        | required                  | docs/proofs/msmarco_v2_real_proof.json |
| semantic_retrieval_claim      | false                     | false                     |
| Status                        | REQUIRED                  | PASS, parity only         |
+-------------------------------+---------------------------+---------------------------+
```

```text
MS MARCO SURFACE BREAKDOWN

+----------------------------+---------------------+-----------------------------+
| Surface                    | Rows                | Status                      |
+----------------------------+---------------------+-----------------------------+
| mteb/msmarco-v2 passages   | 138,364,198 records | parity passed               |
| mteb/msmarco-v2 queries    | 285,328 queries     | parity passed               |
| mteb/msmarco-v2 sources    | 138,649,526 items   | parity passed               |
| HF QA cache rows           | 1,010,916 rows      | parity only                 |
| HF QA cache passages       | 10,087,677 passages | parity only                 |
| HF QA cache encoded items  | 11,098,593 items    | parity only                 |
+----------------------------+---------------------+-----------------------------+
```

The Hugging Face QA cache is a named encode/decode parity surface. It is not
the `mteb/msmarco-v2` stream proof and neither surface is semantic retrieval
quality evidence.

Proof hashes:

```text
+--------------------------------------+------------------------------------------------------------------+
| Hash                                 | Value                                                            |
+--------------------------------------+------------------------------------------------------------------+
| msmarco_v2_real_payload_sha256       | d15c702867e001b7020e65e55b5d23b3844c03638203f45bc3237154b3ddd202 |
| msmarco_v2_real_file_sha256          | 38782428a27e12e2ef3da5ccd137f90d8e270546e68bec1a87a520633dc24932 |
| msmarco_v2_public_handoff_sha256     | a640232df9ae6400a54371be3aa41e9364c1365a2843a8f7c06722ea27cf9125 |
| msmarco_full_parity_file_sha256      | fd4d778b065f62ae5b7f60e40bd0e705813b47684c0471a902940181bda73e1c |
| gravitas_submission_file_sha256      | 92e8a052b5bb0c7fc1246c26c947af52796731c9d65d4344c7e7a0f37cf951b7 |
| gravitas_reported_artifact_sha256    | 16aadaefb8d139cd32a2855c2c810c596f30afb1634aa2cc00b5e35dbc17a6aa |
+--------------------------------------+------------------------------------------------------------------+
```

OpenEncoder MS MARCO retrieval throughput, ranking quality, and leaderboard
standing remain unclaimed. The checked stream proof is encode/decode parity
only.

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
| cpu_layout                 | 16 cores / 32 threads                          |
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
| Legacy BN254 verification    | pairings valid       | PASS    | 6.29s   |
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
+------------------------------------------+--------------------------------------------------------------+
| Artifact                                 | Required Contents                                            |
+------------------------------------------+--------------------------------------------------------------+
| reference_replay_proof.json              | encode/change/decode deterministic replay receipt            |
| msmarco_replay_proof.json                | HF QA cache replay; not retrieval-quality authority          |
| msmarco_full_parity_proof.json           | HF QA cache parity; not retrieval-quality authority          |
| msmarco_full_parity_gravitas_submission.json | Gravitas submission summary for local-cache parity       |
| msmarco_v2_real_proof.json               | mteb/msmarco-v2 stream parity proof                         |
| msmarco_v2_real_public_handoff.json      | reproducibility and transport hashes for stream proof       |
| public_claims_verification_proof.json    | stale-claim rejection proof for public wording              |
| requirements_validation.json             | requirements command JSON validation output                  |
| groth16_verification_proof.json          | BN254 Groth16 positive/tampered verification proof           |
| bin/OpenEncoder.com                      | self-contained Zig endpoint                                  |
| tests/test_client_field_encoder_smoke.py | fail-closed, privacy, CLI smoke checks                       |
+------------------------------------------+--------------------------------------------------------------+
```

Do not add a metric unless the artifact or named test exists and can be reproduced by the documented command.

## MS MARCO v2 Surface Boundary

Only checked artifacts are reportable. The `mteb/msmarco-v2` stream artifact
is reportable as encode/decode parity over the declared stream counts. The
Hugging Face QA cache remains reportable only as a named local-cache
encode/decode parity surface.

```text
+----------------------------+----------------------------------------------+
| Field                      | Value                                        |
+----------------------------+----------------------------------------------+
| benchmark_stream           | mteb/msmarco-v2                              |
| stream_query_count         | 285,328                                      |
| stream_passage_count       | 138,364,198                                  |
| stream_encoded_sources     | 138,649,526                                  |
| openencoder_gravitas_claim | PASS, encode/decode parity only              |
| semantic_retrieval_claim   | NOT CLAIMED                                  |
| ionizer_gravitas_baseline  | receipt-backed baseline exists              |
| hf_qa_cache_role           | parity only, separate named surface          |
+----------------------------+----------------------------------------------+
```

## OpenEncoder Portable Endpoint Proof

`bin/OpenEncoder.com` is validated by direct endpoint smoke checks and checked-in proof receipts.

```bash
./bin/OpenEncoder.com --self-check
./bin/OpenEncoder.com requirements
```

The current endpoint receipt is the checked-in `bin/OpenEncoder.com` artifact and the Legal-MLEB comparator receipt above.
