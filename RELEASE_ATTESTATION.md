# OpenEncoder v1.0.0 Release Attestation

This file records the public release gate for OpenEncoder v1.0.0. Current state:
local release gates pass for the checked-in reference artifact and real Groth16 circuit proof packet. Reproducible source-build provenance remains out of scope.

## Release Identity

```text
+----------------------+--------------------------------------------------------------+
| Field                | Value                                                        |
+----------------------+--------------------------------------------------------------+
| Release              | v1.0.0                                                       |
| Repository           | ninjra/openencoder                                           |
| Package              | bin/OpenEncoder.com                                          |
| Package SHA-256      | 523ca8b008c45ef89c3a387efdb557e0ea6f3a8cfa39962f935075575c3183e2 |
| License              | Apache-2.0 OR Commercial                                     |
| Patent status        | Patent pending                                               |
+----------------------+--------------------------------------------------------------+
```

## Required Release Gates

These gates define the public v1.0.0 release boundary.

```text
+--------------------------------+----------+--------------------------------------------+
| Gate                           | State    | Evidence                                   |
+--------------------------------+----------+--------------------------------------------+
| Python compile                 | PASS     | validation command                         |
| Requirements JSON              | PASS     | docs/proofs/requirements_validation.json   |
| Focused smoke suite            | PASS     | tests/test_client_field_encoder_smoke.py   |
| Release privacy scan           | PASS     | scripts/release_privacy_scan.py            |
| Reference replay proof         | PASS     | docs/proofs/reference_replay_proof.json    |
| HF ms_marco QA parity proof    | PASS     | docs/proofs/msmarco_full_parity_proof.json |
| HF ms_marco QA replay proof    | PASS     | docs/proofs/msmarco_replay_proof.json      |
| mteb/msmarco-v2 stream parity  | PASS     | docs/proofs/msmarco_v2_real_proof.json     |
| MS MARCO retrieval quality     | NO CLAIM | parity artifact only; no ranking metric    |
| Legacy BN254 pairing fixture   | PASS     | groth16_verification_proof.json            |
| Real Groth16 circuit proof     | PASS     | docs/proofs/openencoder_real_groth16_circuit_manifest.json |
| Release gate script            | PASS     | scripts/check_release_gates.py             |
| OpenEncoder.com endpoint proof | PASS     | bin/OpenEncoder.com --self-check           |
| OpenEncoder.com requirements   | PASS     | bin/OpenEncoder.com requirements           |
+--------------------------------+----------+--------------------------------------------+
```

Full package SHA-256:
`523ca8b008c45ef89c3a387efdb557e0ea6f3a8cfa39962f935075575c3183e2`

## Public Claim Boundary

OpenEncoder v1.0.0 claims:

1. deterministic signed `int16` field encoding,
2. local append-only ledger map-back,
3. compatibility-gated local decode,
4. source-backed local answer recovery,
5. legacy BN254 pairing fixture verification,
6. a pinned real Groth16 reference circuit proof packet,
7. checked-in replay, QA-cache parity, and `mteb/msmarco-v2` stream parity proof artifacts, and
8. a single-file OpenEncoder Zig endpoint artifact for release smoke checks.

OpenEncoder v1.0.0 does not claim:

1. encryption or decryption,
2. semantic retrieval quality,
3. production multi-party trusted setup,
4. a complete statement of patent claim scope,
5. secret-free answer recovery, or
6. reproducible source build provenance for `bin/OpenEncoder.com`.

## Binary Provenance

The public repository includes `.github/workflows/release-attestation.yml`, which verifies the `bin/OpenEncoder.com` SHA-256 and emits a GitHub artifact attestation for the release binary. This is hash attestation of a checked-in artifact: it confirms the binary you download matches the binary the maintainer committed. It is not reproducible source build provenance, meaning the binary cannot currently be rebuilt byte-for-byte from the repository source alone. Reproducible builds from auditable source are a future goal, not a current claim. This is also not a substitute for Microsoft Authenticode, Apple notarization, or any private certificate-backed OS vendor signature. Those require maintainer-controlled signing credentials and must be added only when those credentials exist.

## Reproducibility Rule

Public claims must stay tied to checked-in proof artifacts or commands documented in `README.md`, `docs/BENCHMARKS.md`, `docs/MSMARCO_REPRODUCTION.md`, and `docs/RELEASE_CHECKLIST.md`.

Do not replace measured values with projections. Projections belong outside the release evidence board unless they are explicitly labeled as projections.

## MS MARCO Rule

```text
+------------------------------+---------------------------------------------+
| Surface                      | Release Claim                               |
+------------------------------+---------------------------------------------+
| mteb/msmarco-v2 stream parity| PASS for OpenEncoder+Gravitas parity only   |
| Stream scale                 | 285,328 queries + 138,364,198 passages      |
| MS MARCO retrieval quality   | NOT CLAIMED                                 |
| HF microsoft/ms_marco v2.1   | QA-cache encode/decode parity only          |
| QA-cache splits              | train, validation, test                     |
+------------------------------+---------------------------------------------+
```
