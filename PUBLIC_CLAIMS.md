# Public Claims

This file defines the claims boundary for OpenEncoder.

## Safe Public Description

OpenEncoder is a client-side field encoding tool. It converts local text into opaque signed `int16` field signals, records the source mapping in a local ledger, and decodes compatible field-service responses back into source-backed answer reports.

The public architecture claim is field-envelope compatibility, not mandatory
use of OpenEncoder. OpenEncoder is the reference lane. Ionizer is the commercial
high-performance lane. Customers may implement their own compatible local
encoder as long as the outbound field envelope and local recovery contract are
preserved.

Customers control their preprocessing boundary. They may encrypt at rest,
redact, tokenize, shard, normalize, or apply other local controls before field
generation. Ionizer or any compatible encoder can run entirely inside the
customer network over the customer's chosen local representation. The public
claim is not that arbitrary ciphertext remains semantically searchable; it is
that Mushku does not require raw source text, local ledgers, client secrets, or
decoded answers to cross the service boundary.

## Supported Claims

```text
+-------------------------------+--------------------------------------------------------------+
| Claim                         | Support                                                      |
+-------------------------------+--------------------------------------------------------------+
| Private text can stay local   | Request/manifest boundary and privacy scan                   |
| Field signals are deterministic | Reference replay and QA-cache replay proof artifacts       |
| Decode is compatibility-gated | Focused fail-closed tests                                    |
| Local ledger map-back exists  | Reference replay proof and smoke tests                       |
| Legacy BN254 pairing fixture | BN254 fixture and tamper rejection artifact                   |
| Groth16 zkSNARK circuit proof| Pinned reference circuit proof packet passes release gate      |
| OpenEncoder.com is packaged   | Launcher package receipt and E2E proof artifacts             |
| Binary hash attestation exists| GitHub artifact attestation workflow for OpenEncoder.com     |
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
| Blanket ZK privacy proof      | Groth16 claim is tied to the pinned circuit receipt only      |
| General-purpose SNARK system  | No claim; repo has one bounded Groth16 reference circuit plus legacy fixture |
| Secret-free answer recovery   | Decode needs the local ledger and source material            |
| Unpublished patent details    | Public citation waits for public records or approved wording |
| OS vendor code-signing        | Requires private Authenticode/notary credentials             |
+-------------------------------+--------------------------------------------------------------+
```

## Patent Wording

Use only this wording unless a later public citation is approved:

```text
Patent pending. Public application details are intentionally omitted until a publication record or approved citation is available.
```

Do not publish filing PDFs, filing paths, application numbers, attorney correspondence, claim charts, private prosecution materials, or unpublished claim language.

## Benchmark Wording

Use measured artifact-backed language for release claims. Keep benchmark
surfaces named and separated.

```text
+--------------------------------+---------------------------------------------+
| Surface                        | Allowed public wording                      |
+--------------------------------+---------------------------------------------+
| Legal-MLEB OpenEncoder+Gravitas| comparator lane, not OpenEncoder production readiness |
| Legal-MLEB Ionizer+Gravitas    | commercial receipt-backed lane              |
| MS MARCO v2.1 full gamut       | 285,328 queries x 138,364,198 records only  |
| OpenEncoder MS MARCO full gamut| NOT CLAIMED until exact artifact exists     |
| HF ms_marco v2.1 QA cache      | encode/decode parity only                   |
+--------------------------------+---------------------------------------------+
```

The checked-in Hugging Face `microsoft/ms_marco` `v2.1` proof is a local
encode/decode parity proof over the QA cache. It is not a semantic retrieval
benchmark and not the full-gamut MS MARCO v2.1 run.

Use projection language only when the value is clearly marked as a projection and kept outside the release evidence board.

## Groth16 zkSNARK Wording

Allowed wording:

```text
OpenEncoder includes a bounded Groth16 zkSNARK proof surface for its pinned
reference circuit. The claim is tied to the release-gated circuit manifest,
proof packet, verification key, and tamper/substitution rejection receipts.
```

Do not use Groth16 or zkSNARK language as a blanket privacy claim for the whole
product unless the exact privacy relation is proven by that circuit.
