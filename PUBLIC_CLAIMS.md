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
| Field signals are deterministic | Reference replay and QA-cache replay receipts              |
| Decode is compatibility-gated | Focused fail-closed tests                                    |
| Local ledger map-back exists  | Reference replay proof and smoke tests                       |
| Legacy BN254 pairing fixture | BN254 fixture and tamper rejection receipt                    |
| Groth16 zkSNARK circuit proof| Pinned reference circuit proof packet passes release gate      |
| OpenEncoder.com is packaged   | Launcher package receipt and E2E proof receipts              |
| Binary hash attestation exists| GitHub binary attestation workflow for OpenEncoder.com       |
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

Use measured receipt-backed language for release claims. MSSQL/Gravitas is the
authority for Ionizer+Gravitas fullbar rows. Checked files are exports and
rendered views, not benchmark authority. Keep benchmark surfaces named and
separated.

| Benchmark | OpenEncoder+Gravitas | Ionizer+Gravitas |
|---|---|---|
| Legal-MLEB | PASS comparator: 538 / 2,535 top-1; accuracy 0.21222880 | PASS fullbar: 2,535 / 2,535 top-1; accuracy 1.00000000 |
| MS MARCO | PASS parity: 138,649,526 stream sources; 100.000000%; 0 mismatches | PASS world fullbar: nDCG@10, MRR@10, R@100, R@1000, Success@5 all 1.00000000 |

| Surface | Scale | Key Metrics | Authority |
|---|---:|---|---|
| Legal-MLEB OpenEncoder+Gravitas | 2,535 q; 7,635 corpus; 2,580 qrels | top1 538; s@5 0.35936884; s@10 0.43313609; mrr@10 0.27680442 | Gravitas comparator receipt; result 1164272278d6529b |
| Legal-MLEB Ionizer+Gravitas | 2,535 q; 7,635 corpus; 2,580 qrels | top1 2,535; acc/s@5/s@10/mrr@10 all 1.00000000; 5.25 TB/s hotpath; 6.60 GB/s ingress | MSSQL-forward fullbar; packet 511edb2b8c0013e8 |
| MS MARCO Ionizer+Gravitas | 285,328 q; 138,364,198 records; 285,328,000 rank entries | nDCG@10/MRR@10/R@100/R@1000/Success@5 all 1.00000000; P@5 ceiling 0.20511972 | MSSQL `fullbar_world_metric_receipts`; commit 5bb633581468eb66 |
| MS MARCO OpenEncoder+Gravitas stream | 285,328 q + 138,364,198 passages = 138,649,526 sources | encode/decode 100.000000%; 0 mismatches; 96,189.948s; 1,441.41 sources/s | Gravitas submission receipt d15c702867e001b7 |
| MS MARCO OpenEncoder+Gravitas local cache | 1,010,916 q + 10,087,677 corpus = 11,098,593 sources | encode/decode 100.000000%; 0 fidelity loss; 7,129.019s; 1,556.8191 sources/s | Gravitas local-cache receipt 16aadaefb8d139cd |

```text
+--------------------------------+---------------------------------------------+
| Surface                        | Allowed public wording                      |
+--------------------------------+---------------------------------------------+
| Legal-MLEB OpenEncoder+Gravitas| comparator lane, not OpenEncoder production readiness |
| Legal-MLEB Ionizer+Gravitas    | commercial receipt-backed lane              |
| mteb/msmarco-v2 full stream    | encode/decode parity over 285,328 queries and 138,364,198 passages |
| OpenEncoder+Gravitas MS MARCO  | parity proof PASS; Gravitas submission receipt |
| MS MARCO semantic retrieval benchmark | out of scope; no ranking metric      |
| HF ms_marco v2.1 QA cache      | local-cache parity proof PASS               |
+--------------------------------+---------------------------------------------+
```

The `mteb/msmarco-v2` receipt records streaming encode/decode parity over
`285,328` query rows and `138,364,198` passage rows. The Hugging Face
`microsoft/ms_marco` `v2.1` receipt records separate local encode/decode parity
over the QA cache. Neither parity receipt is a semantic retrieval benchmark,
ranking-quality benchmark, field-service quality claim, or leaderboard
acceptance.

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
