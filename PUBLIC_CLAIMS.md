# Public Claims

This file is the conservative public-claims boundary for OpenEncoder.

## Safe Public Description

OpenEncoder is a private-field client kit. It deterministically encodes local text into opaque signed `int16` field signals, keeps the source map in a local ledger, and resolves compatible field-service responses back to local source-backed answer reports.

## Supported Claims

```text
+-------------------------------+--------------------------------------------------------------+
| Claim                         | Support                                                      |
+-------------------------------+--------------------------------------------------------------+
| Private text can stay local   | Request/manifest boundary and privacy scan                   |
| Field signals are deterministic | Reference replay and MS MARCO replay proof artifacts       |
| Decode is compatibility-gated | Focused fail-closed tests                                    |
| Local ledger map-back exists  | Reference replay proof and smoke tests                       |
| Groth16 verify path exists    | BN254 fixture and tamper rejection artifact                  |
| OpenEncoder.com is packaged   | Launcher package receipt and E2E proof artifacts             |
+-------------------------------+--------------------------------------------------------------+
```

## Do Not Claim

```text
+-------------------------------+--------------------------------------------------------------+
| Avoid                         | Reason                                                       |
+-------------------------------+--------------------------------------------------------------+
| Encryption/decryption         | OpenEncoder encodes fields; it is not a cipher suite         |
| Semantic retrieval accuracy   | Ranking quality belongs to a field service                   |
| Full patent embodiment        | The repo is a reference client kit                           |
| General-purpose SNARK system  | The repo has one BN254 Groth16 reference lane                |
| Secret-free answer recovery   | Decode needs the local ledger and source material            |
| Unpublished patent details    | Public citation waits for public records or approved wording |
+-------------------------------+--------------------------------------------------------------+
```

## Patent Wording

Use only this public wording unless a later public citation is approved:

```text
Patent pending. Public application details are intentionally omitted until a publication record or maintainer-approved citation is available.
```

Do not publish filing PDFs, filing paths, application numbers, attorney correspondence, claim charts, private prosecution materials, or unpublished claim language.

## Benchmark Wording

Use measured artifact-backed language for release claims. The checked-in MS MARCO proof is a local encode/decode parity proof, not a semantic retrieval benchmark.

Use projection language only when the value is clearly marked as a projection and kept outside the release evidence board.
