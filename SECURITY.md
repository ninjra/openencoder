# Security Policy

OpenEncoder is designed for local-first opaque-field workflows. Treat generated request payloads as sensitive metadata, and keep all source files, ledgers, secrets, and decoded reports outside public issues and pull requests.

## Supported Scope

Security reports should focus on the current repository surfaces:

- `client_field_encoder.py`
- local ledger integrity and decode behavior
- generated request and submission-manifest hygiene
- optional Python Tk and signed launcher package surfaces
- documentation that could cause private-data exposure or overclaiming

## Report Privately

Do not include private corpora, ledger files, secrets, customer data, or decoded answer reports in a public issue.

Report security issues through GitHub private vulnerability reporting when available, or through the maintainer contact channel listed on the public repository. Add only the minimum reproduction needed, and replace private inputs with synthetic fixtures.

## Boundary

OpenEncoder is deterministic encoding plus local ledger bookkeeping, not encryption and not a security product by itself.

The `emit` command still generates a legacy BN254 pairing fixture with fixed curve points for compatibility verification. The repository also ships a pinned real Groth16 reference circuit proof packet under `docs/proofs/real_groth16/`, gated by `scripts/check_release_gates.py` with R1CS/WASM/proving-key/verifying-key hashes, a known-good proof, tamper rejection, and verifier-key-substitution rejection.

Groth16 is a zkSNARK proof system. OpenEncoder's zkSNARK claim is bounded to
the pinned reference circuit and passing receipt set. It is separate from the
request-egress boundary, which is verified by inspecting generated request
payloads, manifests, and local ledger behavior.

This is a reference circuit and local deterministic setup packet. It is not a general-purpose production proof system, not a multi-party trusted setup, not privacy by itself, and not proof of semantic correctness.

See `docs/THREAT_MODEL.md` for the threat model and known limitations.
