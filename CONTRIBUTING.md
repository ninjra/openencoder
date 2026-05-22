# Contributing

Keep contributions aligned with the reference-client boundary.

Good changes:

- deterministic encoder and decoder tests
- ledger integrity fixtures
- request payload privacy audits
- fail-closed decode fixtures
- clearer service integration contracts
- documentation that avoids unmeasured benchmark or proof claims

Avoid:

- committing secrets, private corpora, ledgers, decoded reports, or patent filing packets
- claiming full cryptographic zero-knowledge verification without verifier code and tests
- replacing `PENDING` benchmark fields without checked-in artifacts
- adding GUI or service behavior that uploads private source text by default

## Local Checks

Run the focused checks before opening a pull request:

```bash
python3 -m py_compile client_field_encoder.py
python3 client_field_encoder.py requirements > /tmp/openencoder_requirements.json
python3 -m json.tool /tmp/openencoder_requirements.json >/dev/null
python3 -m pytest tests/test_client_field_encoder_smoke.py -q --tb=short
```

Launcher smoke:

```bash
sh bin/OpenEncoder.com --self-check
sh bin/OpenEncoder.com --list-apps
```
