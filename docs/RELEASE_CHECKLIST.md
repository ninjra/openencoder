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
| 11 | MS MARCO surface docs                | full gamut separated from QA  |
| 12 | Groth16 verifier                     | positive + tampered fixtures  |
| 13 | GitHub Actions CI                    | push, PR, proof, endpoint     |
| 14 | Binary provenance documented         | hash attestation scope        |
| 15 | High-entropy secret scan             | trufflehog/gitleaks clean     |
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
2. benchmark `PENDING` values remain pending unless backed by artifacts,
3. generated local folders such as `ledger/`, `outbox/`, `answers/`, `decoded/`, `.zig-cache/`, and `zig-out/` are absent from the commit,
4. `docs/MSMARCO_REPRODUCTION.md` explains the Hugging Face QA-cache parity proof and does not conflate it with full-gamut MS MARCO,
5. `scripts/release_privacy_scan.py` passes from a fresh checkout,
6. the Groth16 verifier fixture passes with `py-ecc` installed and the tampered fixture fails closed,
7. public CI is configured for push, pull request, focused tests, release privacy scan, Groth16 verification, and OpenEncoder.com endpoint validation,
8. desktop click/open claims are backed by receipts from those operating systems before they appear in public copy,
9. binary provenance is documented as hash attestation of a checked-in artifact (not reproducible source build), and
10. a high-entropy secret scanner (trufflehog, gitleaks, or equivalent) runs clean against the repository.
