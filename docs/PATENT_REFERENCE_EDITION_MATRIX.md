# Patent Reference Edition Matrix

This matrix tracks the burn-down for making OpenEncoder a zero-shot,
simple-to-use patent reference edition.

It is grounded against the current OpenEncoder repository and the private filed
patent packet through internal governed review, but it intentionally does not copy private
filing text, application details, claim language, attorney materials, or source
packet paths into this repository.

## Release Posture

```text
+----+--------------------------------------+-------------------------------+-------------------------------+
| #  | Release target                       | Current public position       | Publish decision              |
+----+--------------------------------------+-------------------------------+-------------------------------+
| 01 | Partial reference client             | Implemented and documented    | Candidate after gates pass    |
| 02 | Patent Reference Edition             | Reference path implemented    | Candidate after gates pass    |
| 03 | Full patent embodiment               | Not claimed                   | Do not claim                  |
| 04 | Legacy BN254 pairing fixture       | Implemented                   | Real circuit proof remains gated      |
| 05 | Third-party semantic retrieval system | Out of repo boundary          | Do not claim                  |
| 06 | Encryption/decryption product        | Not implemented               | Do not claim                  |
+----+--------------------------------------+-------------------------------+-------------------------------+
```

## Implementation Matrix

```text
+----+--------------------------------------+-------------------------------+-------------------------------+
| #  | Surface                              | Current state                 | Required end state            |
+----+--------------------------------------+-------------------------------+-------------------------------+
| 01 | Local file-backed encode             | Implemented                   | Keep stable                   |
| 02 | Client-held secret                   | Implemented                   | Keep outside repo             |
| 03 | Opaque request payload               | Implemented                   | Add stronger payload audit    |
| 04 | Local append-only ledger             | Implemented                   | Keep hash-chain verification  |
| 05 | Local source-backed decode           | Implemented                   | Keep fail-closed behavior     |
| 06 | Deterministic replay receipt         | Implemented                   | Keep receipt-backed           |
| 07 | Signed int16 field objects           | Implemented                   | Keep tested                   |
| 08 | Typed atom extraction                | Implemented                   | Keep local/private            |
| 09 | Field receipts                       | Implemented                   | Keep hash-bound               |
| 10 | Compatibility-gated decode           | Implemented                   | Keep fail-closed              |
| 11 | Legacy BN254 verifier               | Implemented                   | Keep valid/tamper fixtures    |
| 12 | Fidelity ladder                      | Not implemented               | Add only when tested          |
| 13 | OpenEncoder portable endpoint     | Multi-OS command shell        | Keep Python as source truth   |
+----+--------------------------------------+-------------------------------+-------------------------------+
```

OpenEncoder fields are not ciphertext and cannot be decrypted. The reference
path is deterministic one-way field encoding plus local ledger map-back. SHA-256
and HMAC-SHA256 are used for content binding and keyed deterministic signal
generation, and Groth16 support is implemented for the reference field-envelope proof
lane used by the local field-service harness.

## Deterministic Burn-Down Gates

```text
+----+--------------------------------------+-------------------------------+-------------------------------+
| #  | Gate                                 | Required evidence             | Blocking rule                 |
+----+--------------------------------------+-------------------------------+-------------------------------+
| 01 | Python compile                       | py_compile exits 0            | Any syntax error blocks       |
| 02 | Requirements JSON                    | json.tool accepts output      | Invalid JSON blocks           |
| 03 | Focused pytest suite                 | smoke tests pass              | Any failed test blocks        |
| 04 | Reference replay proof                | proof_passed true             | Replay mismatch blocks        |
| 05 | Request plaintext audit              | no raw corpus/query text      | Raw text leak blocks          |
| 06 | Ledger tamper fixture                | local answer fails closed     | Passing tamper blocks         |
| 07 | Source mismatch fixture              | local answer fails closed     | Passing mismatch blocks       |
| 08 | Repository privacy scan              | no private paths or contacts  | Private data blocks           |
| 09 | Patent wording audit                 | patent pending only           | Private filing detail blocks  |
| 10 | Governed release review             | no release blockers           | Blocker finding blocks        |
| 11 | Groth16 verifier                     | valid proof passes; tamper fails | Any verifier miss blocks   |
| 12 | Adversarial review                  | clean or explicitly waived    | Blocking finding blocks       |
| 13 | Git state                            | tracked changes synced        | Dirty publish state blocks    |
+----+--------------------------------------+-------------------------------+-------------------------------+
```

## Claim Boundary

```text
+--------------------------------------+--------------------------------------------------------------+
| Claim                                | Public-safe wording                                          |
+--------------------------------------+--------------------------------------------------------------+
| Private text is not sent             | True when users send request JSON and non-secret manifest    |
| Local ledger map-back                | Implemented as local append-only JSONL ledger                |
| Deterministic client signal          | Implemented for signed int16 typed-atom reference path       |
| Signed int16 patent reference path   | Implemented as client reference path with replay proof       |
| Legacy BN254 pairing lane            | Implemented for reference emit/decode compatibility gating   |
| Encryption/decryption                | Not claimed; fields are opaque signals, not ciphertext       |
| Full patent embodiment               | Not claimed by this repository                               |
| Patent status                        | Patent pending                                               |
+--------------------------------------+--------------------------------------------------------------+
```

## Public Release Rule

OpenEncoder can be public as a partial reference client only when every
deterministic burn-down gate passes and the README keeps the implementation
boundary explicit.

OpenEncoder should not be announced as a complete patent embodiment. The OE-ZK1 signed int16 reference path, typed atom recipe,
receipt model, compatibility gates, legacy BN254 verifier and replay receipts are implemented and tested
for the client reference boundary. OpenEncoder ships one pinned real Groth16 reference circuit proof packet and one deterministic legacy BN254 pairing fixture, but does not ship a general circuit compiler, reusable production trusted setup ceremony, or Plonk verification.
