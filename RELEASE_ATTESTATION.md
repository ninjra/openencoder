# OpenEncoder v1.0.0 Release Attestation

This file records the public release gate for OpenEncoder v1.0.0.

## Release Identity

```text
+----------------------+--------------------------------------------------------------+
| Field                | Value                                                        |
+----------------------+--------------------------------------------------------------+
| Release              | v1.0.0                                                       |
| Repository           | ninjra/openencoder                                           |
| Package              | bin/OpenEncoder.com                                          |
| Package SHA-256      | 97802ae390bac1fc493b6b5ee2c2799f95b04f5354a8c09fc3ac93aa04a3e8a2 |
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
| MS MARCO full parity proof     | PASS     | docs/proofs/msmarco_full_parity_proof.json |
| MS MARCO replay proof          | PASS     | docs/proofs/msmarco_replay_proof.json      |
| Groth16 verification fixture   | PASS     | docs/proofs/groth16_verification_proof.json |
| OpenEncoder.com package proof  | PASS     | docs/proofs/openencoder_origamold_masterfield_ape_package_receipt.json |
| OpenEncoder.com provenance     | PASS     | .github/workflows/release-attestation.yml |
| Linux launcher synthetic E2E   | PASS     | docs/proofs/openencoder_linux_ape_e2e_proof.json |
| Windows frontend E2E           | PASS     | docs/proofs/openencoder_windows_frontend_e2e_proof.json |
+--------------------------------+----------+--------------------------------------------+
```

## Public Claim Boundary

OpenEncoder v1.0.0 claims:

1. deterministic signed `int16` field encoding,
2. local append-only ledger map-back,
3. compatibility-gated local decode,
4. source-backed local answer recovery,
5. BN254 Groth16 verification for the reference topology proof lane,
6. checked-in replay and parity proof artifacts, and
7. a single-file OpenEncoder launcher artifact for release smoke checks.

OpenEncoder v1.0.0 does not claim:

1. encryption or decryption,
2. semantic retrieval quality,
3. Plonk, STARK, FHE, or a general circuit compiler,
4. a complete statement of patent claim scope,
5. secret-free answer recovery, or
6. public disclosure of unpublished patent filing materials.

## Binary Provenance

The public repository includes `.github/workflows/release-attestation.yml`, which verifies the `bin/OpenEncoder.com` SHA-256 and emits a GitHub artifact attestation for the release binary. This is supply-chain provenance for the checked-in release artifact. It is not a substitute for Microsoft Authenticode, Apple notarization, or any private certificate-backed OS vendor signature. Those require maintainer-controlled signing credentials and must be added only when those credentials exist.

## Reproducibility Rule

Public claims must stay tied to checked-in proof artifacts or commands documented in `README.md`, `docs/BENCHMARKS.md`, `docs/MSMARCO_REPRODUCTION.md`, and `docs/RELEASE_CHECKLIST.md`.

Do not replace measured values with projections. Projections belong outside the release evidence board unless they are explicitly labeled as projections.
