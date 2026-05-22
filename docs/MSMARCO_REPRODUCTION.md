# MS MARCO Full Parity Reproduction

This guide reproduces the checked OpenEncoder encode/decode parity proof for the Hugging Face `microsoft/ms_marco` `v2.1` Question Answering cache.

OpenEncoder measures client fidelity only. This proof does not measure retrieval ranking, field-service quality, answer correctness, or Groth16 proof verification.

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

The checked proof targets `ms_marco` configuration `v2.1` and splits `train`, `validation`, and `test`.

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

## Reproduce Locally

Install the optional dataset tooling outside the core OpenEncoder dependency path:

```bash
python3 -m pip install datasets pyarrow
```

Download and materialize the Hugging Face Arrow cache:

```bash
python3 -c 'from datasets import load_dataset; load_dataset("microsoft/ms_marco", "v2.1", cache_dir="datasets/msmarco_v2")'
```

Run the full parity proof:

```bash
OPENENCODER_MSMARCO_CACHE=datasets/msmarco_v2 \
python3 scripts/prove_msmarco_full_parity.py \
  --splits train,validation,test \
  --output docs/proofs/msmarco_full_parity_proof.json
```

The command prints a short JSON summary and writes the full artifact to `docs/proofs/msmarco_full_parity_proof.json`.

## Expected Public Artifact Shape

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
| encode_decode_accuracy        | 100.0                                         |
| fidelity_loss_count           | 0                                             |
| mismatch_samples              | []                                            |
+-------------------------------+-----------------------------------------------+
```

The artifact intentionally avoids raw MS MARCO text and local absolute paths.

## Verify The Artifact

```bash
python3 -m json.tool docs/proofs/msmarco_full_parity_proof.json >/dev/null
python3 -m pytest tests/test_client_field_encoder_smoke.py -q --tb=short
```

If the Hugging Face dataset packaging changes, regenerate the artifact and keep the README counts tied to the new checked artifact.
