# Hugging Face MS MARCO QA-Cache Parity

This guide reproduces the checked OpenEncoder encode/decode parity proof for
the Hugging Face `microsoft/ms_marco` `v2.1` Question Answering cache.

This is not the full-gamut MS MARCO v2.1 run. The full-gamut boundary is
`285,328` queries by `138,364,198` records and remains not claimed for
OpenEncoder+Gravitas until an exact full-gamut artifact exists.

OpenEncoder measures client fidelity only. This proof does not measure
retrieval ranking, field-service quality, answer correctness, full-gamut MS
MARCO throughput, or Groth16 proof verification.

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

The checked proof targets Hugging Face dataset `microsoft/ms_marco`,
configuration `v2.1`, splits `train`, `validation`, and `test`.

## Surface Boundary

```text
+-----------------------------+----------------------------------------------+
| Field                       | Value                                        |
+-----------------------------+----------------------------------------------+
| public_name                 | HF ms_marco v2.1 QA-cache parity             |
| dataset                     | microsoft/ms_marco                           |
| configuration               | v2.1                                         |
| splits                      | train, validation, test                      |
| measured_row_count          | 1,010,916                                    |
| measured_query_count        | 1,010,916                                    |
| measured_passage_count      | 10,087,677                                   |
| encoded_source_count        | 11,098,593                                   |
| decoded_source_count        | 11,098,593                                   |
| role                        | encode/decode parity only                    |
| full_gamut_ms_marco_claim   | false                                        |
| retrieval_accuracy_claim    | false                                        |
+-----------------------------+----------------------------------------------+
```

```text
+-----------------------------+----------------------------------------------+
| Full-Gamut MS MARCO Field   | Required Value                               |
+-----------------------------+----------------------------------------------+
| canonical_query_count       | 285,328                                      |
| canonical_record_count      | 138,364,198                                  |
| openencoder_gravitas_claim  | NOT CLAIMED                                  |
| ionizer_gravitas_baseline   | receipt-backed baseline exists              |
+-----------------------------+----------------------------------------------+
```

## What The Proof Checks

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

## Reproduce The QA-Cache Parity Surface

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

The command prints a short JSON summary and writes the QA-cache parity artifact
to `docs/proofs/msmarco_full_parity_proof.json`.

## Expected QA-Cache Artifact Shape

The checked artifact currently reports:

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

The artifact intentionally avoids raw MS MARCO text and local absolute paths.
It must not be described as the full-gamut `285,328 x 138,364,198` run.

## Verify The Artifact

```bash
python3 -m json.tool docs/proofs/msmarco_full_parity_proof.json >/dev/null
python3 -m pytest tests/test_client_field_encoder_smoke.py -q --tb=short
```

If the Hugging Face dataset packaging changes, regenerate the artifact and keep
the README counts tied to the new checked QA-cache artifact.
