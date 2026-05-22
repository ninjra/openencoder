# OpenEncoder Example

This directory contains a tiny corpus/query pair for a first local run.

```bash
python3 ../client_field_encoder.py encode \
  --corpus-path corpus \
  --query-path query \
  --secret sample-client-secret \
  --context demo \
  --ledger ../ledger/client_field_ledger.jsonl \
  --output ../outbox/01_field_request.json \
  --submission-manifest-output ../outbox/02_submission_manifest.json
```
