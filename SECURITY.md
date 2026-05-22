# Security Policy

OpenEncoder is designed for local-first opaque-field workflows. Treat generated request payloads as sensitive metadata, and keep all source files, ledgers, secrets, decoded reports, and private patent materials outside public issues and pull requests.

## Supported Scope

Security reports should focus on the current repository surfaces:

- `client_field_encoder.py`
- local ledger integrity and decode behavior
- generated request and submission-manifest hygiene
- optional Python Tk and Origamold APE surfaces
- documentation that could cause private-data exposure or overclaiming

## Report Privately

Do not publish private corpora, ledger files, secrets, customer data, decoded answer reports, signed filing packets, attorney correspondence, or unpublished claim text in an issue.

Report security issues through GitHub private vulnerability reporting when available, or through the maintainer contact channel listed on the public repository. Add only the minimum reproduction needed, and replace private inputs with synthetic fixtures.

## Boundary

OpenEncoder is deterministic encoding plus local ledger bookkeeping, not encryption. It verifies supplied BN254 Groth16 payloads when the optional `snark` extra is installed, but it does not generate proofs, compile circuits, or claim a full proof system by itself.
