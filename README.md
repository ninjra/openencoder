Copyright 2026 Shri Narayan Justin Ram / Mushku Nobleworks. All Rights Reserved.

# OpenEncoder

OpenEncoder is a publishable reference encoder kit for the Gravitas field
envelope. It turns local text into deterministic signed `int16` field signals,
keeps the source ledger local, and lets a compatible field service operate on
opaque numeric payloads instead of raw source text.

OpenEncoder is not a required preprocessing stack. Customers may encrypt at
rest, redact, tokenize, shard, normalize, or apply their own local controls
before field generation. Ionizer and compatible customer encoders can run
entirely inside the customer network over the customer's chosen local
representation. Mushku does not require raw source text to cross the service
boundary; the service contract only requires the emitted field envelope.

## Reference Boundary

```text
+-------------------------+-----------------------------------------------+
| Surface                 | OpenEncoder Claim                             |
+-------------------------+-----------------------------------------------+
| Local source text       | not emitted in tested request/manifest files  |
| Field envelope          | deterministic signed int16 reference lane     |
| Decode                  | local ledger/source-backed excerpt recovery   |
| Security posture        | reference kit, not encryption                 |
| Binary provenance       | hash-attested artifact, not reproducible build|
| Groth16 zkSNARK         | pinned circuit proof packet passes release gate|
+-------------------------+-----------------------------------------------+
```

## External Comparator Snapshot

Retrieval quality and proof-surface claims are intentionally separated. The
OpenEncoder comparator number is an answer-quality metric. The receipt/replay
and no-raw-source-text checks are proof-surface metrics.

```text
+--------------------------+-----------------------+---------------------------+
| Retrieval Quality        | OpenEncoder+Gravitas  | Ionizer+Gravitas          |
+--------------------------+-----------------------+---------------------------+
| Legal-MLEB local run     | 538 / 2,535 top-1     | 2,535 / 2,535 top-1       |
| Legal-MLEB accuracy      | 0.21222880            | 1.00000000                |
| Official leaderboard     | not claimed           | not claimed               |
+--------------------------+-----------------------+---------------------------+
```

```text
+--------------------------+-----------------------+---------------------------+
| Proof Surface            | OpenEncoder+Gravitas  | Ionizer+Gravitas          |
+--------------------------+-----------------------+---------------------------+
| Encoder                  | OpenEncoder           | Ionizer                   |
| Engine                   | Gravitas              | Gravitas                  |
| Hotpath                  | Zig                   | Zig                       |
| Python hotpath           | false                 | false                     |
| Deterministic replay     | true                  | true                      |
| Raw source text egress   | 0 bytes               | 0 bytes                   |
| GPU VRAM required        | 0 GB                  | 0 GB                      |
+--------------------------+-----------------------+---------------------------+
```

OpenEncoder and Ionizer are encoder lanes. Gravitas is the engine in both
lanes. Ionizer+Gravitas is the commercial receipt-backed path.

The service contract is protocol compatibility, not encoder lock-in.
OpenEncoder is the public reference encoder, Ionizer is the commercial
high-performance encoder lane, and customers may implement their own compatible
encoder. A compatible field service receives field tensors plus necessary
auth/submission metadata; source text, local ledgers, client secrets, and
decoded answer reports remain local.

```text
+-----------------------------+----------------------------------------------+
| Surface                     | Boundary                                     |
+-----------------------------+----------------------------------------------+
| MS MARCO v2.1 full gamut    | 285,328 queries x 138,364,198 records        |
| Ionizer+Gravitas            | receipt-backed baseline exists              |
| OpenEncoder+Gravitas        | NOT CLAIMED until exact full-gamut run       |
| HF ms_marco v2.1 QA cache   | encode/decode parity only, separate surface  |
+-----------------------------+----------------------------------------------+
```

This comparator belongs to the wider OpenEncoder/Ionizer/Gravitas ecosystem.
It is a local comparator run, not an accepted official leaderboard result, and
not an OpenEncoder standalone production-readiness claim. Full evidence:
`docs/BENCHMARKS.md`.

## How It Works

```text
+------+------------------------+-----------------------------------------+
| Step | Surface                | Boundary                                |
+------+------------------------+-----------------------------------------+
| 01   | Local files            | source text stays local                 |
| 02   | OpenEncoder            | emits deterministic signed int16 fields |
| 03   | Field service / engine | receives opaque field math only         |
| 04   | Local decoder          | maps results back through local ledger  |
+------+------------------------+-----------------------------------------+
```

## What It Is / What It Is Not

```text
+--------------------------------------+--------------------------------------+
| OpenEncoder IS                       | OpenEncoder IS NOT                   |
+--------------------------------------+--------------------------------------+
| Deterministic field encoder          | Encryption or decryption             |
| Local ledger map-back                | A cipher suite                       |
| Opaque numeric payload generator     | Secret-free answer recovery          |
| Encode/decode parity proof surface   | Standalone retrieval production engine |
| Zig endpoint smoke/check artifact    | Reproducible source-built binary     |
| Legacy BN254 pairing fixture         | Blanket privacy proof                |
| Pinned Groth16 circuit proof         | General-purpose SNARK system         |
| Reference kit                        | Security product                     |
+--------------------------------------+--------------------------------------+
```

## Groth16 zkSNARK Boundary

OpenEncoder includes a bounded Groth16 zkSNARK proof surface for its pinned
reference circuit. That claim is tied to the passing release gate, circuit
manifest, proof packet, verification key, and tamper/substitution rejection
artifacts.

This is separate from the request-egress boundary. The no-raw-source-text claim
is inspected from the outbound envelope and local ledger behavior; the Groth16
claim applies only to the proved circuit relation.

## Quick Start

### 1. Create a workspace

```bash
mkdir -p examples/corpus examples/query ledger outbox answers decoded

cat > examples/corpus/renewal.txt <<'EOF'
Contract renewal requires finance approval before Friday. Legal signoff is also required.
EOF

cat > examples/query/approval.txt <<'EOF'
What approval is needed for renewal?
EOF
```

### 2. Set a client-held secret

```bash
export CLIENT_SIGNAL_SECRET="$(openssl rand -hex 32)"
```

Generated request JSON is sensitive metadata. Keep the secret, source files,
ledger, and decoded reports local.

### 3. Install and encode

```bash
python3 -m pip install .

python3 client_field_encoder.py encode \
  --corpus-path examples/corpus \
  --query-path examples/query \
  --context demo \
  --ledger ledger/client_field_ledger.jsonl \
  --output outbox/01_field_request.json \
  --submission-manifest-output outbox/02_submission_manifest.json
```

Send only `outbox/01_field_request.json` and `outbox/02_submission_manifest.json` to the field service. Keep `examples/`, `ledger/`, and `CLIENT_SIGNAL_SECRET` local.

### 4. Decode service answers locally

Place the service response JSON in `answers/`, then:

```bash
python3 client_field_encoder.py decode \
  --ledger ledger/client_field_ledger.jsonl \
  --answers-path answers \
  --include-text \
  --output decoded/decoded_answers.json
```

The decoder resolves answers through the local ledger and source files. If references cannot be resolved, it fails closed.

## Commands

```text
+--------------+------------------------------------------------------+
| Command      | Purpose                                              |
+--------------+------------------------------------------------------+
| encode       | Build field request JSON and local ledger events     |
| emit         | Build reference field emission plus field-envelope fixture |
| decode       | Verify fixture and resolve through local ledger      |
| verify       | Verify BN254 Groth16 proof payloads                  |
| requirements | Print field-service protocol constraints as JSON     |
| gui          | Launch local Tk debug UI                             |
+--------------+------------------------------------------------------+
```

## Privacy

```text
+------------------------------+----------------------------------------------+
| Surface                      | Boundary                                     |
+------------------------------+----------------------------------------------+
| Leaves machine               | field request JSON + non-secret manifest     |
| Stays local                  | source files, ledger, secret, decoded output |
| Field service receives       | opaque signed int16 fields                   |
| Field service never receives | raw source text or local ledger              |
+------------------------------+----------------------------------------------+
```

## Validation

Validation installs the required Groth16 dependency and runs the proof-backed path:

```bash
python3 -m pip install . pytest
python3 -m py_compile client_field_encoder.py openencoder_groth16.py scripts/prove_reference_replay.py scripts/prove_msmarco_replay.py scripts/prove_msmarco_full_parity.py scripts/package_portable_launcher_ape.py scripts/release_privacy_scan.py
python3 client_field_encoder.py requirements > /tmp/openencoder_requirements.json
python3 -m json.tool /tmp/openencoder_requirements.json >/dev/null
python3 scripts/release_privacy_scan.py
python3 -m pytest tests/test_client_field_encoder_smoke.py -q --tb=short
python3 scripts/prove_reference_replay.py
```

Groth16 fixture validation:

```bash
python3 client_field_encoder.py verify --proof docs/proofs/groth16_verification_proof.json
```

OpenEncoder.com endpoint validation:

```bash
./bin/OpenEncoder.com --self-check
./bin/OpenEncoder.com requirements
```

## Evidence Board

```text
+------------------------------+-------------+-------------+-----------------------------------------------+
| Track                        | Target      | Status      | Evidence                                      |
+------------------------------+-------------+-------------+-----------------------------------------------+
| Encode determinism           | 100% replay | PASS        | docs/proofs/reference_replay_proof.json       |
| MS MARCO v2.1 full gamut     | 285k x 138M | NOT CLAIMED | pending exact full-gamut artifact             |
| HF ms_marco v2.1 QA parity   | 11.1M items | PASS        | docs/proofs/msmarco_full_parity_proof.json    |
| Signed int16 reference path  | int16 dtype | PASS        | docs/proofs/reference_replay_proof.json       |
| File-backed local recovery   | report all  | PASS        | docs/proofs/reference_replay_proof.json       |
| Ledger hash-chain validity   | 100% pass   | PASS        | docs/proofs/reference_replay_proof.json       |
| Compatibility-gated decode   | fail closed | PASS        | tests/test_client_field_encoder_smoke.py      |
| Request plaintext exposure   | 0 raw text  | PASS        | tests/test_client_field_encoder_smoke.py      |
| Requirements command         | valid JSON  | PASS        | docs/proofs/requirements_validation.json      |
| Legacy BN254 verify          | valid/tamper| PASS        | docs/proofs/groth16_verification_proof.json   |
| OpenEncoder.com endpoint     | binary hash | PASS        | bin/OpenEncoder.com                           |
+------------------------------+-------------+-------------+-----------------------------------------------+
```

```text
+--------------------------+----------------------------------------------+
| MS MARCO surface         | Value                                        |
+--------------------------+----------------------------------------------+
| canonical_query_count    | 285,328                                      |
| canonical_record_count   | 138,364,198                                  |
| openencoder_full_scale   | NOT CLAIMED                                  |
| hf_qa_cache_scope        | microsoft/ms_marco v2.1 train/validation/test|
| hf_qa_cache_role         | encode/decode parity, not full-gamut search  |
+--------------------------+----------------------------------------------+
```

## Repository Map

```text
openencoder/
  client_field_encoder.py          # encoder / emitter / decoder / Tk GUI
  openencoder_groth16.py           # BN254 Groth16 proof helpers
  pyproject.toml                   # project metadata
  examples/                        # sample corpus + query
  tests/                           # smoke and integrity tests
  bin/
    OpenEncoder.com                # single-file Zig endpoint (see docs/OPENENCODER_PORTABLE_ENDPOINT.md)
  scripts/
    prove_reference_replay.py      # deterministic replay proof
    prove_msmarco_replay.py        # HF QA cache replay; not full-gamut authority
    prove_msmarco_full_parity.py   # HF QA cache parity; not full-gamut authority
    package_portable_launcher_ape.py
    release_privacy_scan.py
  docs/
    BENCHMARKS.md
    MSMARCO_REPRODUCTION.md
    THREAT_MODEL.md
    PATENT_REFERENCE.md            # patent citation checklist
    OPENENCODER_PORTABLE_ENDPOINT.md # endpoint documentation
    RELEASE_CHECKLIST.md
    proofs/                        # replay and Groth16 verification artifacts
```

## Field-Service Integration Checklist

A compatible third-party field service should:

```text
+----+---------------------------------------------------------------------+
| #  | Requirement                                                         |
+----+---------------------------------------------------------------------+
| 1  | Accept field objects, not private source text                       |
| 2  | Preserve corpus/query field identifiers in response JSON            |
| 3  | Emit deterministic field results for replayable inputs              |
| 4  | Report emission quality separately from local answer recovery       |
| 5  | Never claim access to private text unless the user sent it          |
| 6  | Change calc_hash when tokenization/weighting/width/recipe changes   |
| 7  | Return enough references for local ledger resolution                |
| 8  | Allow the client decoder to fail closed on unresolved references    |
+----+---------------------------------------------------------------------+
```

Machine-readable version:

```bash
python3 client_field_encoder.py requirements
```

## HF QA Cache Parity Hashes

```text
+--------------------------+------------------------------------------------------------------+
| Artifact                 | SHA-256                                                          |
+--------------------------+------------------------------------------------------------------+
| msmarco_full_parity      | fd4d778b065f62ae5b7f60e40bd0e705813b47684c0471a902940181bda73e1c |
| source_chain_sha256      | c493488583133dbaf89a56dd119cb5d237a74e36d1a8721e430f8713fde48bd2 |
| decode_chain_sha256      | a64c858d59b4b8239f6a45da5d695b3b2850261dc6d78922dc1a93d0267266cc |
| signal_chain_sha256      | 1368394b5b4e8fc66f891d4c8add014e792d55a8fc5517a713c72177fcd7010c |
| receipt_chain_sha256     | 613c945e05138473ca4d6ad8eca15033792e1055a9360edf9f9bf2bd19e9e46c |
+--------------------------+------------------------------------------------------------------+
```

## FAQ

### What should I send to the field service?

Only the generated request JSON and non-secret submission manifest. Never send source files, the ledger, secrets, or private config.

### Can I use literal `--corpus` and `--query` arguments?

Yes, for smoke tests. For workflows that need local answer recovery, prefer `--corpus-path` and `--query-path` so the ledger can verify source paths and hashes.

### Does OpenEncoder measure retrieval accuracy?

No. OpenEncoder measures client-side determinism, ledger integrity, payload hygiene, and decode behavior. Semantic metrics (NDCG, Recall, MRR, precision) depend on the field service.

### Can the remote service produce answer text?

The intended flow: the service emits field results, and the local decoder produces source-backed answer reports. Current reports quote local source excerpts — they do not synthesize text remotely.

### How does answer recovery work?

The local ledger records the mapping between encoded field signals and original source text. When the service returns field results, the decoder uses the ledger to look up the corresponding source excerpts. Without the ledger and source files, answers cannot be recovered.

### What is `bin/OpenEncoder.com`?

The single-file OpenEncoder Zig endpoint. On Linux/WSL, run it directly as `./bin/OpenEncoder.com`. See `docs/OPENENCODER_PORTABLE_ENDPOINT.md` for details.

## Patent

Patent pending.

## License

Apache-2.0. Commercial licensing for private deployments, Ionizer, Gravitas,
signed customer packages, and customer-specific evidence bundles is handled
separately in `COMMERCIAL_LICENSE.md`.
