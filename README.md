# OpenEncoder: Private-Field Client Kit

**Private text in. Opaque fields out. Local answers back.**

OpenEncoder is a standalone client-side encoder, Groth16-backed reference emitter, and local decoder for opaque-field search workflows. The integer encoder core uses the Python standard library; the proof-backed emit/decode path uses `py-ecc` for BN254 Groth16 pairings.

OpenEncoder is **not encryption**. It does not create ciphertext, it does not decrypt field tensors, and it should not be evaluated as an AES-style encrypted storage or transport system. It is deterministic one-way field encoding plus local ledger bookkeeping: private text stays local, opaque signed `int16` field signals can leave the machine, and only the local ledger/source files can map compatible returned field references back to answerable text.

It reads local corpus and query files, converts them into deterministic keyed field signals, records the private field-to-source map in a local append-only ledger, and later decodes compatible field-service responses back into local, source-backed answer reports.

The remote service receives math-oriented signed `int16` field objects.

The client keeps the text, the ledger, the secret, and the final answer recovery path.

```text
LOCAL FILES              OPENENCODER                 FIELD SERVICE              OPENENCODER
corpus/ + query/   ->    encode + ledger       ->    field math only      ->    local decode
private text             opaque request JSON         no private text            answer report
```

## Status and boundary

OpenEncoder is a **reference client field kit**.

It is not a claim that this repository, by itself, implements every mechanism described in pending patent materials. The current Python reference client emits deterministic, client-keyed, signed `int16` typed-atom field signals and records local source mappings, receipts, compatibility metadata, and Groth16 BN254 topology proof results for reference field emissions. A compatible third-party field service may transform, score, or emit field results with the same proof/receipt boundary. OpenEncoder then resolves compatible returned field references locally through the private ledger and source files.

This distinction matters:

```text
+-----------------------------+--------------------------------------------------------------+
| Claim                       | Current README position                                      |
+-----------------------------+--------------------------------------------------------------+
| Private text is not sent    | Yes, when users send only request JSON + non-secret manifest |
| Local ledger map-back       | Yes, implemented as local append-only JSONL ledger           |
| Deterministic client signal | Yes, signed int16 typed-atom reference path                  |
| Local answer recovery       | Source-backed local report and excerpt selection             |
| Replay proof                | Yes, exact replay + whitespace-change parity artifact        |
| Groth16 topology proof     | Yes, reference emitter creates and decoder verifies BN254 proof |
| Semantic retrieval accuracy | Property of the third-party field service, not OpenEncoder   |
| Encryption/decryption       | Not claimed; fields are opaque signals, not ciphertext       |
| General proof systems       | No Plonk/STARK/FHE; one BN254 Groth16 reference lane only    |
| Full patent embodiment      | Not claimed by this reference client kit                     |
+-----------------------------+--------------------------------------------------------------+
```

Do **not** send `corpus/`, `query/`, `ledger/`, source files, secrets, private config files, or patent filing paperwork to a field service.

Send only the generated request payload and the non-secret submission manifest.

## What it does

```text
+-----------------------------+--------------------------------------------------------------+
| Surface                     | Responsibility                                               |
+-----------------------------+--------------------------------------------------------------+
| client_field_encoder.py     | Encode, emit, decode, requirements, and optional Tk GUI      |
| Local ledger                | Private field-to-source map and hash-chain audit trail       |
| Submission manifest         | Non-secret handoff metadata for a field service              |
| Answer decoder              | Local source-backed answer report and excerpt selection      |
| Requirements command        | Machine/human-readable third-party service requirements      |
| Groth16 proof lane          | BN254 reference topology proof generation and verification   |
| Docs                        | Benchmarks, patent checklist, launcher notes, implementation docs |
+-----------------------------+--------------------------------------------------------------+
```

## What it does not do

```text
+-----------------------------------------+------------------------------------------------------+
| Non-goal                                | Reason                                               |
+-----------------------------------------+------------------------------------------------------+
| Upload private source text              | The field-service boundary is opaque-field only      |
| Decode answers without local source     | Local answer recovery needs ledger + source files    |
| Encrypt or decrypt private text         | OpenEncoder encodes fields; it is not a cipher suite |
| Prove semantic accuracy by itself       | Retrieval/ranking quality belongs to the service     |
| Guarantee collision impossibility       | Hashing reduces risk; it does not abolish it         |
| Provide a general circuit compiler      | OpenEncoder ships one reference BN254 topology lane |
| Replace patent or security review       | Counsel/security review is still required            |
+-----------------------------------------+------------------------------------------------------+
```

## Quick start

OpenEncoder has no PyTorch, model weights, vector database, or heavy ML dependency. Install the package once so the required BN254 Groth16 pairing dependency is present for `emit`, `decode`, and `verify`. The optional Python `gui` command depends on host Tkinter support. The checked-in `bin/OpenEncoder.com` file is the single-file OpenEncoder launcher for GUI and portable smoke checks.

Use **file-backed inputs** for demos that need local answer recovery. Literal `--corpus` and `--query` inputs are useful for encoding smoke tests, but file paths are easier to verify during decode because the ledger can re-read and hash-check the source files.

### 1. Create a tiny local workspace

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

For a demo:

```bash
export CLIENT_SIGNAL_SECRET="example-not-secret"
```

For real use, generate and store a strong secret outside the repository. Do not commit secrets to `config.json`, shell history, CI logs, screenshots, or issue reports.

### 3. Install and encode local files into an opaque field request

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

### 4. Build a reference proven field emission

```bash
python3 client_field_encoder.py emit \
  --request outbox/01_field_request.json \
  --output answers/01_reference_emission.json
```

The `emit` command is the local reference field-service harness: it computes `ZKVOO(field[A], field[B]) -> distaste_topography_field`, attaches a BN254 Groth16 topology proof, and does not read source text or the ledger.

Send only:

```text
outbox/01_field_request.json
outbox/02_submission_manifest.json
```

Keep private:

```text
examples/corpus/
examples/query/
ledger/client_field_ledger.jsonl
CLIENT_SIGNAL_SECRET
config.json if it contains private paths or secrets
```

### 5. Show third-party field-service requirements

```bash
python3 client_field_encoder.py requirements
```

A compatible service must accept field objects, emit field results, preserve the references needed by the local decoder, and avoid synthesizing private prose answers from plaintext it never received.

### 6. Decode service answers locally

After placing service response JSON files in `answers/`:

```bash
python3 client_field_encoder.py decode \
  --ledger ledger/client_field_ledger.jsonl \
  --answers-path answers \
  --include-text \
  --output decoded/decoded_answers.json
```

The decoder writes JSON output and, when possible, a `.txt` report with monospace tables. Current answer text is selected from verified local source excerpts; this reference client does not generate new private prose from opaque fields.

### 7. Launch the optional local Tk GUI

```bash
python3 client_field_encoder.py gui
```

GUI mode requires Python Tkinter on the host system. This is the lightweight cross-platform debugging UI.

### 8. Run the single-file launcher

```bash
sh bin/OpenEncoder.com --self-check
sh bin/OpenEncoder.com --list-apps
sh bin/OpenEncoder.com --synthetic-e2e \
  --app openencoder \
  --documents "OpenEncoder Linux portable proof document. The answer is recovered from the local RAM ledger." \
  --question "Where is the answer recovered from?" \
  --answer-output /tmp/openencoder_linux_ape_answer.txt
```

`bin/OpenEncoder.com` is the public release file to hand to users for the launcher lane. Windows double-click opens the dark OpenEncoder desktop workflow. Linux/WSL runs through `sh`. The checked-in proof artifacts cover package integrity, Linux/WSL synthetic encode/decode, and Windows visible-control frontend automation. macOS payload packaging is present, but ordinary macOS click/open claims still need a host receipt before they appear in public copy.

## Protocol flow

```text
+------+-------------------------+-------------------------+----------------------------+
| Step | Actor                   | Output                  | Privacy boundary           |
+------+-------------------------+-------------------------+----------------------------+
| 1    | OpenEncoder client      | field request JSON      | Text stays local           |
| 2    | OpenEncoder client      | local ledger event(s)   | Ledger stays local         |
| 3    | User/client             | submission manifest     | Non-secret metadata only   |
| 4    | Field service           | proven field emission   | Service sees fields only   |
| 5    | OpenEncoder decoder     | answer report           | Uses local ledger/source   |
+------+-------------------------+-------------------------+----------------------------+
```

The service response must contain enough returned field identifiers, hashes, or compatible references for the local decoder to resolve the response through the ledger. If the response cannot be resolved, the decoder should fail closed rather than inventing an answer.

## Encoding boundary

OpenEncoder uses SHA-256 and HMAC-SHA256 as deterministic hash/keyed-signal primitives, and it can verify supplied BN254 Groth16 proof payloads. Those facts do not make the encode/decode path an encryption system.

```text
+-------------------------------+--------------------------------------------------+
| Question                      | OpenEncoder answer                               |
+-------------------------------+--------------------------------------------------+
| Is private text encrypted?    | No                                               |
| Are field tensors ciphertext? | No                                               |
| Can fields be decrypted?      | No                                               |
| What leaves the client?       | Opaque signed int16 field objects + metadata     |
| What stays local?             | Source text, ledger, client secret, answer path  |
| What recovers answer text?    | Local ledger/source map-back, not decryption     |
| What does Groth16 do here?    | Proves/verifies reference field topology, not encryption |
+-------------------------------+--------------------------------------------------+
```

## Current implementation notes

The reference Python client currently uses:

```text
+-------------------------+----------------------------------------------------------+
| Component               | Current behavior                                         |
+-------------------------+----------------------------------------------------------+
| Signal generation       | HMAC-SHA256 typed atoms, axes, and signed weights           |
| Signal representation   | Fixed-width signed int16 tensor in [-32767, 32767]         |
| Default width           | 64                                                        |
| Source identity         | text_sha256, canonical_text_sha256, signal_sha256          |
| Receipts                | field_receipt, request_receipt, receipt SHA-256 bindings   |
| Proof lane              | Required Groth16 BN254 reference topology proof via `py-ecc` |
| Request identity        | request_sha256, client_request_id, request_receipt_sha256  |
| Ledger                  | JSONL append-only events with previous/event hash chain    |
| Decode                  | Resolve response refs and gate recipe/dtype compatibility  |
| Answer text             | Selected from current local source files when hashes match |
| Hardware footprint      | Standard-library int16 core; no ML runtime dependency      |
+-------------------------+----------------------------------------------------------+
```

The core encoder is integer-oriented and dependency-free on the default path. That makes it suitable for small edge builds and cross-platform native packaging, including native binary distribution experiments, as long as the target supplies normal file I/O and SHA-256/HMAC primitives.

The signed `int16` typed-atom reference path is covered by deterministic replay/parity receipts. The only proof lane is the BN254 Groth16 reference topology path used by `emit` and verified during `decode`, with the standalone verifier fixture covered by `docs/proofs/groth16_verification_proof.json`. OpenEncoder still does not claim third-party semantic retrieval quality, a general circuit compiler, reusable trusted setup ceremony, Plonk verification, or a full patent embodiment.

## Design boundary

```text
+---------------------------+---------------------------+----------------------------------+
| OpenEncoder owns          | Field service owns        | OpenEncoder does not claim       |
+---------------------------+---------------------------+----------------------------------+
| Local file reading        | Field scoring             | Universal source reconstruction  |
| Deterministic signals     | Field result emission     | Secret-free answer decoding      |
| Private ledger binding    | Ranking/retrieval quality | Collision impossibility          |
| Request manifest creation | Response JSON format      | Service-side private text use    |
| Local answer reporting    | Service benchmarks        | General-purpose proof systems |
| Fail-closed decode checks | Latency/throughput        | Patent claim coverage by README  |
+---------------------------+---------------------------+----------------------------------+
```

## Security and privacy rules

1. Use `--corpus-path` and `--query-path` for answerable workflows.
2. Keep the ledger local.
3. Keep the client secret local.
4. Do not upload source files to a field service.
5. Do not upload the ledger to a field service.
6. Do not commit real secrets, private corpora, decoded answer reports, or signed patent paperwork.
7. Treat request payloads as sensitive metadata even though they should not contain raw source text.
8. For image, audio, or video workflows, store local answerable text such as captions, OCR, transcripts, or operator-approved descriptions. Raw binary bytes alone are not enough for a useful human answer report.
9. Do not describe OpenEncoder fields as encrypted text or decryptable ciphertext.
10. Replace `PENDING` benchmark claims only with measured, artifact-backed results.

## Evidence Board

OpenEncoder's published evidence focuses on what this client owns: deterministic encoding, local map-back, payload hygiene, fail-closed decode behavior, and encode/decode fidelity. Semantic retrieval metrics such as NDCG, Recall, MRR, and precision are service-specific and should be reported by the field service, not by this client alone.

```text
OPENENCODER EVIDENCE BOARD
Generated: 2026-05-21

+-------------------------------+-------------+----------+--------------------------------------------+
| Track                         | Target      | Current  | Evidence                                   |
+-------------------------------+-------------+----------+--------------------------------------------+
| Encode determinism            | 100% replay | PASS     | docs/proofs/reference_replay_proof.json    |
| MS MARCO full local parity    | 100% parity | PASS     | docs/proofs/msmarco_full_parity_proof.json |
| MS MARCO replay proof         | exact hashes| PASS     | docs/proofs/msmarco_replay_proof.json      |
| Signed int16 reference path   | int16 dtype | PASS     | docs/proofs/reference_replay_proof.json    |
| Easy-change field parity      | no loss     | PASS     | docs/proofs/reference_replay_proof.json    |
| File-backed local recovery    | report all  | PASS     | docs/proofs/reference_replay_proof.json    |
| Ledger hash-chain validity    | 100% pass   | PASS     | docs/proofs/reference_replay_proof.json    |
| Compatibility-gated decode    | fail closed | PASS     | tests/test_client_field_encoder_smoke.py   |
| Request plaintext exposure    | 0 raw text  | PASS     | tests/test_client_field_encoder_smoke.py   |
| Requirements command          | valid JSON  | PASS     | docs/proofs/requirements_validation.json   |
| Groth16 topology proof        | emit/decode | PASS     | docs/proofs/reference_replay_proof.json    |
| Groth16 BN254 verify          | valid/tamper| PASS     | docs/proofs/groth16_verification_proof.json |
| OpenEncoder.com package        | payload hash| PASS     | docs/proofs/openencoder_origamold_masterfield_ape_package_receipt.json |
| Windows frontend E2E           | UI encode/decode | PASS  | docs/proofs/openencoder_windows_frontend_e2e_proof.json |
+-------------------------------+-------------+----------+--------------------------------------------+

Measured full-cache result:

+-------------------------------+-----------------------------------------------+
| Field                         | Value                                         |
+-------------------------------+-----------------------------------------------+
| dataset                       | MS MARCO v2.1 local Arrow cache               |
| splits                        | train, validation, test                       |
| arrow_files                   | 9                                             |
| rows                          | 1,010,916                                     |
| queries                       | 1,010,916                                     |
| passage_entries               | 10,087,677                                    |
| encoded_sources               | 11,098,593                                    |
| decoded_sources               | 11,098,593                                    |
| encode_decode_accuracy        | 100.0%                                        |
| fidelity_loss_count           | 0                                             |
+-------------------------------+-----------------------------------------------+

source_chain_sha256:   c493488583133dbaf89a56dd119cb5d237a74e36d1a8721e430f8713fde48bd2
decode_chain_sha256:   a64c858d59b4b8239f6a45da5d695b3b2850261dc6d78922dc1a93d0267266cc
signal_chain_sha256:   1368394b5b4e8fc66f891d4c8add014e792d55a8fc5517a713c72177fcd7010c
receipt_chain_sha256:  613c945e05138473ca4d6ad8eca15033792e1055a9360edf9f9bf2bd19e9e46c
artifact_sha256:       16aadaefb8d139cd32a2855c2c810c596f30afb1634aa2cc00b5e35dbc17a6aa
```

The MS MARCO proof covers the Hugging Face `microsoft/ms_marco` `v2.1` Question Answering cache. MS MARCO is published by Microsoft; the dataset card points to the official MS MARCO homepage and the paper "MS MARCO: A Human Generated MAchine Reading COmprehension Dataset" (`arXiv:1611.09268`).

Dataset and citation links:

- Official MS MARCO site: https://microsoft.github.io/msmarco/
- Hugging Face dataset: https://huggingface.co/datasets/microsoft/ms_marco
- Paper: https://arxiv.org/abs/1611.09268

See `docs/BENCHMARKS.md` for the benchmark dashboard, local reference-hardware performance notes, and proof artifact map; `docs/MSMARCO_REPRODUCTION.md` for the replication workflow; and `docs/RELEASE_CHECKLIST.md` for the public-release gate.
See `RELEASE_ATTESTATION.md` and `PUBLIC_CLAIMS.md` for the v1.0.0 release boundary and public claim discipline.

## Repository map

```text
openencoder/
  client_field_encoder.py          # standalone Python encoder / emitter / decoder / Tk GUI
  openencoder_groth16.py            # BN254 Groth16 proof helpers
  README.md                        # repo front door
  RELEASE_ATTESTATION.md           # v1.0.0 release gate and artifact boundary
  PUBLIC_CLAIMS.md                 # conservative public-claims boundary
  pyproject.toml                   # minimal Python project metadata
  examples/                        # tiny runnable sample corpus + query
  tests/                           # focused smoke and integrity tests
  bin/
    OpenEncoder.com                 # canonical single-file OpenEncoder APE launcher
  scripts/
    prove_reference_replay.py       # deterministic reference replay proof
    prove_msmarco_replay.py         # MS MARCO replay proof harness
    prove_msmarco_full_parity.py    # full MS MARCO parity proof harness
    package_origamold_masterfield_ape.py # OpenEncoder.com package receipt helper
    release_privacy_scan.py         # public-release private-data scanner
  docs/
    BENCHMARKS.md                  # benchmark dashboard scaffold
    MSMARCO_REPRODUCTION.md        # full local-cache proof replication guide
    proofs/                        # deterministic replay and Groth16 verification artifacts
    PATENT_REFERENCE.md            # public-safe patent citation checklist
    README_DESIGN_NOTES.md         # README structure sources and design rationale
    RELEASE_CHECKLIST.md           # public-release readiness gate
    OPENENCODER_APE.md            # OpenEncoder.com launcher notes
  .github/workflows/ci.yml         # Python, privacy, Groth16, and OpenEncoder.com CI
  SECURITY.md                      # security and private-data reporting policy
  CONTRIBUTING.md                  # contribution boundary and test expectations
  CHANGELOG.md                     # release history
  openencoder_logo.png              # project logo asset
```

## CLI surface

```text
+---------------+-------------------------------------------------------------+
| Command       | Purpose                                                     |
+---------------+-------------------------------------------------------------+
| encode        | Build field request JSON and append local ledger events     |
| emit          | Build reference field emission plus Groth16 topology proof  |
| decode        | Verify Groth16 topology proof and resolve through ledger    |
| verify        | Verify BN254 Groth16 proof payloads with `py-ecc`           |
| requirements  | Print field-service protocol and API constraints as JSON    |
| gui           | Launch a lightweight Tkinter UI for local debugging         |
+---------------+-------------------------------------------------------------+
```

## Validation

Validation installs the required Groth16 dependency and runs the proof-backed path:

```bash
python3 -m pip install . pytest
python3 -m py_compile client_field_encoder.py openencoder_groth16.py scripts/prove_reference_replay.py scripts/prove_msmarco_replay.py scripts/prove_msmarco_full_parity.py scripts/package_origamold_masterfield_ape.py scripts/release_privacy_scan.py
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

Deterministic MS MARCO replay proof, using an existing local HuggingFace Arrow cache:

```bash
OPENENCODER_MSMARCO_CACHE=/path/to/msmarco_v2 \
python3 scripts/prove_msmarco_replay.py \
  --config v2.1 \
  --split validation \
  --sample-size 3
```

The checked-in sample artifact is `docs/proofs/msmarco_replay_proof.json`. It records `ms_marco` `v2.1` `validation`, `sample_size=3`, `corpus_file_count=9`, exact encode/decode replay, ledger hash-chain validity, compatibility-gated decode, zero unresolved references, 100% local excerpt recovery, and request plaintext audit pass. Local excerpt recovery means the decoder recovered a source-backed excerpt from the private ledger/source files; it is not MS MARCO answer correctness or retrieval quality.

Full local-cache parity proof, using every text item in the local HuggingFace Arrow cache:

```bash
OPENENCODER_MSMARCO_CACHE=/path/to/msmarco_v2 \
python3 scripts/prove_msmarco_full_parity.py \
  --splits train,validation,test
```

The checked-in full-local artifact is `docs/proofs/msmarco_full_parity_proof.json`. It covers all 9 local v2.1 Arrow files: 1,010,916 rows, 1,010,916 queries, 10,087,677 passage entries, and 11,098,593 encoded/decoded text sources. It reports 100.0% encode/decode parity and `fidelity_loss_count=0`. The local cache did not include a separate 138M-passage collection; the artifact says that explicitly.

To reproduce the dataset cache and full parity proof on another machine, follow `docs/MSMARCO_REPRODUCTION.md`.

The checked-in Groth16 artifact verifies a positive BN254 pairing-equation fixture and a tampered negative fixture. The reference replay artifact proves the current encode -> emit -> decode topology path, including Groth16 proof verification during decode.


OpenEncoder.com launcher validation:

```bash
sh bin/OpenEncoder.com --self-check
sh bin/OpenEncoder.com --list-apps
sh bin/OpenEncoder.com --synthetic-e2e \
  --app openencoder \
  --documents "OpenEncoder Linux portable proof document. The answer is recovered from the local RAM ledger." \
  --question "Where is the answer recovered from?" \
  --answer-output /tmp/openencoder_linux_ape_answer.txt
```

For the release burn-down and Patent Reference Edition boundary, see
`docs/PATENT_REFERENCE_EDITION_MATRIX.md`.

## OpenEncoder APE

`bin/OpenEncoder.com` is the canonical single-file OpenEncoder launcher artifact. On Windows it opens the dark desktop workflow. On Linux/WSL it exposes portable self-check, app inventory, package, and synthetic encode/decode commands.

```text
+-------------------+---------------------------------------------------+
| Surface           | Status                                            |
+-------------------+---------------------------------------------------+
| Native entry      | bin/OpenEncoder.com                                  |
| Payload source    | external release payloads; hashes bound in receipt |
| Runtime bridge    | embedded platform payloads; no Python dispatch in launcher smoke |
| Proof artifact    | docs/proofs/openencoder_origamold_masterfield_ape_package_receipt.json |
| Leakage rule      | OpenEncoder vocabulary only                       |
+-------------------+---------------------------------------------------+
```

Details: `docs/OPENENCODER_APE.md`.

## Field-service integration checklist

A compatible third-party field service should:

```text
+----+--------------------------------------------------------------------+
| #  | Requirement                                                        |
+----+--------------------------------------------------------------------+
| 1  | Accept field objects, not private source text                       |
| 2  | Preserve corpus/query field identifiers in response JSON            |
| 3  | Emit deterministic field results for replayable inputs              |
| 4  | Report emission quality separately from local answer recovery       |
| 5  | Never claim access to private text unless the user sent it          |
| 6  | Change calc_hash when tokenization/weighting/width/recipe changes   |
| 7  | Return enough references for local ledger resolution                |
| 8  | Allow the client decoder to fail closed on unresolved references    |
+----+--------------------------------------------------------------------+
```

Run this for the machine-readable version:

```bash
python3 client_field_encoder.py requirements
```

This command prints OpenEncoder protocol and integration requirements: field tensor shape, signed `int16` typed-atom expectations, metadata preservation rules, local-ledger map-back requirements, and fail-closed decoder constraints. It is not a pip dependency list and it is not a service-specific envelope.

## Patent status

SPDX-License-Identifier: `Apache-2.0 OR Commercial`

Patent pending.

The deterministic local payload transformation and map-back architecture associated with this project is the subject of pending patent filings. This repository is a public reference client kit and should not be treated as a complete statement of claim scope.

Public patent details are intentionally omitted until an official publication record or maintainer-approved citation is available.

Do not commit signed filing forms, unpublished claim charts, private prosecution materials, or private patent correspondence to this repository.

See `docs/PATENT_REFERENCE.md` for the public-safe citation checklist.

## License

This repository is offered under:

```text
Apache-2.0 OR Commercial
```

Review the license terms and contributor policy before accepting outside contributions, especially if patent rights, commercial licensing, or dual licensing are part of the project strategy.

## Contributing

Please keep contributions aligned with the project boundary:

```text
+-----------------------------+-----------------------------------------------+
| Good contribution           | Avoid                                         |
+-----------------------------+-----------------------------------------------+
| Deterministic tests         | Unmeasured benchmark claims                   |
| Ledger integrity fixtures   | Secrets in config or examples                 |
| Payload audit tools         | Private corpora or customer data              |
| Decode failure fixtures     | Claims of full ZK without verifier code       |
| Clear service interfaces    | Patent scope without public citation       |
+-----------------------------+-----------------------------------------------+
```

Before opening an issue or pull request, remove private text, secrets, ledger files, decoded answer reports, and patent paperwork.

## FAQ

### Is OpenEncoder encryption?

No. OpenEncoder is deterministic encoding and local bookkeeping. It does not encrypt text, emit ciphertext, or decrypt field tensors. Local answer recovery works because the client kept the private ledger and source files.

### Is OpenEncoder "zero knowledge"?

OpenEncoder supports a zero-knowledge-style service boundary: the service can receive opaque field objects instead of private source text. That boundary is not the same thing as encrypted transport or a full SNARK/zero-knowledge proof system. The current reference client generates and verifies one deterministic BN254 Groth16 topology proof for its reference field emission path. It does not provide a general circuit compiler, reusable trusted setup ceremony, Plonk verifier, or encryption scheme.

### Can the remote service produce answer text?

The intended split is: the service emits field results, and the local decoder produces source-backed answer reports using the private ledger and local source files. Current reports quote or select local source excerpts; they do not synthesize private text remotely.

### Can I use literal `--corpus` and `--query` arguments?

Yes, for smoke tests. For workflows that need local answer recovery, prefer `--corpus-path` and `--query-path` so the ledger can later verify source paths and hashes.

### Does OpenEncoder measure retrieval accuracy?

Not by itself. OpenEncoder can measure client-side determinism, ledger integrity, payload hygiene, and local decode behavior. Semantic metrics such as NDCG, Recall, MRR, and precision depend on the field service.

### What should I send to a field service?

Send only the generated request JSON and non-secret submission manifest.

Do not send source files, the local ledger, secrets, or private config.
