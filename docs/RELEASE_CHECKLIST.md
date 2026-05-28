# Release Checklist

This checklist must pass before release.

## Required Gates

```text
+----+--------------------------------------+-------------------------------+
| #  | Gate                                 | Required state                |
+----+--------------------------------------+-------------------------------+
| 01 | Python compile                       | pass                          |
| 02 | Requirements JSON                    | valid JSON                    |
| 03 | Focused pytest suite                 | pass                          |
| 04 | Request plaintext audit              | no raw corpus/query text      |
| 05 | Ledger tamper fixture                | fail closed / no pass claim   |
| 06 | Source hash mismatch fixture         | fail closed / no pass claim   |
| 07 | Unresolved reference fixture         | unresolved references counted |
| 08 | Release privacy scan                 | no private paths or contacts  |
| 09 | Patent wording                       | patent pending only           |
| 10 | OpenEncoder endpoint docs           | canonical OpenEncoder.com path |
| 11 | MS MARCO surface docs                | stream parity separated from QA/retrieval |
| 12 | Public claims verification proof     | pass / no stale claim wording |
| 13 | Groth16 verifier                     | positive + tampered fixtures  |
| 14 | GitHub Actions CI                    | push, PR, proof, endpoint     |
| 15 | Binary provenance documented         | hash attestation scope        |
| 16 | High-entropy secret scan             | trufflehog/gitleaks clean     |
+----+--------------------------------------+-------------------------------+
```

Launcher gate:

```bash
./bin/OpenEncoder.com --self-check
./bin/OpenEncoder.com requirements
```

The implementation burn-down lives in `docs/PATENT_REFERENCE_EDITION_MATRIX.md`.
Use that matrix to distinguish a public partial reference client from a future
Patent Reference Edition.

## Public Patent Rule

Use only:

```text
Patent pending. Public application details are intentionally omitted until a publication record or approved citation is available.
```

Do not publish application numbers, private filing PDFs, OCR text, attorney correspondence, private contact details, claim charts, or unpublished claim language.

## Visibility Change Rule

Do not make the repository public until:

1. all required gates pass in a fresh checkout,
2. benchmark claims remain tied to checked artifacts and do not turn parity into retrieval quality,
3. generated local folders such as `ledger/`, `outbox/`, `answers/`, `decoded/`, `.zig-cache/`, and `zig-out/` are absent from the commit,
4. `docs/MSMARCO_REPRODUCTION.md` explains both the `mteb/msmarco-v2` stream parity proof and the Hugging Face QA-cache parity proof without conflating either with retrieval quality,
5. `scripts/release_privacy_scan.py` passes from a fresh checkout,
6. `scripts/prove_public_claims.py` passes and writes `docs/proofs/public_claims_verification_proof.json`,
7. the Groth16 verifier fixture passes with `py-ecc` installed and the tampered fixture fails closed,
8. public CI is configured for push, pull request, focused tests, release privacy scan, Groth16 verification, and OpenEncoder.com endpoint validation,
9. desktop click/open claims are backed by receipts from those operating systems before they appear in public copy,
10. binary provenance is documented as hash attestation of a checked-in artifact (not reproducible source build), and
11. a high-entropy secret scanner (trufflehog, gitleaks, or equivalent) runs clean against the repository.
