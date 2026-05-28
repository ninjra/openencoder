# MS MARCO Parity Reproduction

This guide documents the OpenEncoder MS MARCO encode/decode parity surfaces.
OpenEncoder measures client-side fidelity only. These proofs do not measure
semantic retrieval ranking, field-service quality, answer correctness, or
Groth16 proof verification.

## Dataset Attribution

MS MARCO is published by Microsoft.

```text
+-------------------------+------------------------------------------------------+
| Source                  | Link                                                 |
+-------------------------+------------------------------------------------------+
| Official MS MARCO site  | https://microsoft.github.io/msmarco/                 |
| Hugging Face dataset    | https://huggingface.co/datasets/microsoft/ms_marco   |
| Paper                   | https://arxiv.org/abs/1611.09268                     |
+-------------------------+------------------------------------------------------+
```

## Proof Boundaries

```text
+-----------------------------+----------------------------------------------+
| Surface                     | Boundary                                     |
+-----------------------------+----------------------------------------------+
| microsoft/ms_marco v2.1     | QA-cache encode/decode parity                |
| mteb/msmarco-v2             | retrieval-scale encode/decode parity         |
| Retrieval ranking           | out of scope for these parity receipts       |
| Answer correctness          | out of scope for these parity receipts       |
| Field-service quality       | out of scope for these parity receipts       |
| Groth16 verification        | out of scope for these parity receipts       |
+-----------------------------+----------------------------------------------+
```

## What The Proofs Check

```text
+-------------------------------+-----------------------------------------------+
| Check                         | Meaning                                       |
+-------------------------------+-----------------------------------------------+
| source text hash              | decoded source hash equals original text hash |
| canonical text hash           | tokenizer-normalized text is stable           |
| typed atom hash               | typed atom recipe is stable                   |
| signal replay                 | repeated encode emits the same signal hash    |
| field receipt replay          | repeated encode emits the same receipt hash   |
| field id replay               | repeated encode emits the same field id       |
| mismatch count                | all mismatch counters remain zero             |
+-------------------------------+-----------------------------------------------+
```

## QA-Cache Parity Surface

Install the optional dataset tooling outside the core OpenEncoder dependency path:

```bash
python3 -m pip install datasets pyarrow
```

Download and materialize the Hugging Face QA Arrow cache:

```bash
python3 -c 'from datasets import load_dataset; load_dataset("microsoft/ms_marco", "v2.1", cache_dir="datasets/msmarco_v2")'
```

Run the QA-cache parity proof:

```bash
OPENENCODER_MSMARCO_CACHE=datasets/msmarco_v2 \
python3 scripts/prove_msmarco_full_parity.py \
  --splits train,validation,test \
  --output docs/proofs/msmarco_full_parity_proof.json
```

The command prints a short JSON summary and writes the QA-cache parity receipt
to `docs/proofs/msmarco_full_parity_proof.json`.
The Gravitas submission summary for this local-cache surface is checked in at
`docs/proofs/msmarco_full_parity_gravitas_submission.json`.

Expected QA-cache receipt shape:

```text
+-------------------------------+-----------------------------------------------+
| Field                         | Value                                         |
+-------------------------------+-----------------------------------------------+
| proof_passed                  | true                                          |
| arrow_files                   | 9                                             |
| measured_row_count            | 1,010,916                                     |
| measured_query_count          | 1,010,916                                     |
| measured_passage_count        | 10,087,677                                    |
| encoded_source_count          | 11,098,593                                    |
| decoded_source_count          | 11,098,593                                    |
| encode_decode_parity          | 100.0                                         |
| fidelity_loss_count           | 0                                             |
| mismatch_samples              | []                                            |
+-------------------------------+-----------------------------------------------+
```

## Retrieval-Scale Parity Surface

This repository also keeps a retrieval-scale parity handoff for
`mteb/msmarco-v2`. This receipt covers the first `285,328` query rows and first
`138,364,198` passage rows in deterministic streaming order.

To reproduce the retrieval-scale parity proof locally:

```bash
python3 -m pip install datasets
python3 scripts/prove_msmarco_v2_real_parity.py \
  --query-limit 285328 \
  --passage-limit 138364198 \
  --output docs/proofs/msmarco_v2_real_proof.json
```

`mteb/msmarco-v2` provides:

- queries stream: `285,328` rows.
- corpus stream: `138,364,198` rows.

`--query-limit` and `--passage-limit` control each stream independently.
`--limit` remains a compatibility fallback when a single cap is intended for
both streams.

The resulting receipt export is `docs/proofs/msmarco_v2_real_proof.json`. A public
handoff manifest is available at
`docs/proofs/msmarco_v2_real_public_handoff.json`.

Expected retrieval-scale receipt shape:

```text
+--------------------------------+-----------------------------------------------+
| Field                          | Value                                         |
+--------------------------------+-----------------------------------------------+
| proof_passed                   | true                                          |
| dataset_id                     | mteb/msmarco-v2                               |
| query_count                    | 285,328                                       |
| passage_count                  | 138,364,198                                   |
| encoded_decoded_source_count   | 138,649,526                                   |
| encode_decode_accuracy_percent | 100.0                                         |
| throughput_sources_per_second  | 1,441.41                                      |
| elapsed_seconds                | 96,189.948                                    |
| text_hash_mismatches           | 0                                             |
| canonical_hash_mismatches      | 0                                             |
| typed_atom_hash_mismatches     | 0                                             |
| signal_replay_mismatches       | 0                                             |
| field_receipt_replay_mismatches| 0                                             |
| field_id_replay_mismatches     | 0                                             |
| exceptions                     | 0                                             |
+--------------------------------+-----------------------------------------------+
```

The receipt intentionally avoids raw MS MARCO text and local absolute paths.

Checked rebuild and handoff metadata:

```text
+--------------------------------+-----------------------------------------------+
| Field                          | Value                                         |
+--------------------------------+-----------------------------------------------+
| finished_at                    | 2026-05-27T15:38:46-0600                     |
| ended_at_iso                   | 2026-05-27T21:34:42Z                         |
| rebuild_pid                    | 3368955                                      |
| runtime_seconds                | 95,970.298                                   |
| proof_payload_sha256           | d15c702867e001b7020e65e55b5d23b3844c03638203f45bc3237154b3ddd202 |
| proof_file_sha256              | 38782428a27e12e2ef3da5ccd137f90d8e270546e68bec1a87a520633dc24932 |
| completion_file_sha256         | a8e12eddb382467e460eeb1fd0055849b4c4ca7f01eba36cc7e215fe5939b4d8 |
| runtime_log_sha256             | 656107eaa6180824b0018c2fdfa8623d07013e770a10e748bdddbb4cfb34ff45 |
+--------------------------------+-----------------------------------------------+
```

The runtime log hash is transport evidence from the rebuild host. The large log
is intentionally not checked into this repository.

## Compare Retrieval-Scale Receipts

When comparing against another repository, use either positional arguments:

```bash
python3 scripts/compare_msmarco_v2_real.py \
  docs/proofs/msmarco_v2_real_proof.json \
  <other_repo>/docs/proofs/msmarco_v2_real_proof.json
```

or named arguments:

```bash
python3 scripts/compare_msmarco_v2_real.py \
  --left docs/proofs/msmarco_v2_real_proof.json \
  --right <other_repo>/docs/proofs/msmarco_v2_real_proof.json
```

## Verify Receipt Exports

```bash
python3 -m json.tool docs/proofs/msmarco_full_parity_proof.json >/dev/null
python3 -m json.tool docs/proofs/msmarco_full_parity_gravitas_submission.json >/dev/null
python3 -m json.tool docs/proofs/msmarco_v2_real_proof.json >/dev/null
python3 -m json.tool docs/proofs/msmarco_v2_real_public_handoff.json >/dev/null
python3 -m json.tool docs/proofs/msmarco_v2_real_parity_rebuild_completion.json >/dev/null
python3 -m json.tool docs/proofs/msmarco_v2_real_proof_rebuild_done.json >/dev/null
python3 scripts/compare_msmarco_v2_real.py \
  docs/proofs/msmarco_v2_real_proof.json \
  docs/proofs/msmarco_v2_real_proof.json
python3 -m pytest tests/test_client_field_encoder_smoke.py -q --tb=short
```

If Hugging Face dataset packaging changes, regenerate the affected receipt and
keep the README counts tied to the receipt.
