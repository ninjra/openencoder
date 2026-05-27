# OpenEncoder Threat Model

## What OpenEncoder Is

Deterministic field encoding plus local ledger bookkeeping. Not encryption.

OpenEncoder converts local text into opaque signed `int16` field signals using HMAC-SHA256 keyed primitives. The field service receives field math only. Answer recovery happens locally through the private ledger and source files.

## Assets and Exposure

| Asset | Location | Exposure to field service |
|-------|----------|---------------------------|
| Source text | Local filesystem only | Never sent |
| Client secret | Local env/config only | Never sent |
| Local ledger | Local JSONL file only | Never sent |
| Field tensors | Sent to field service | Opaque int16 arrays visible |
| Typed atom counts | In request JSON | Visible to service |
| Tensor shapes and width | In request JSON | Visible to service |
| Field IDs (HMAC-derived hashes) | In request JSON | Visible to service |
| Context labels | In request JSON | Visible to service |
| Request structure | In request JSON | Query/corpus ratio visible |

## Attacker Capabilities and Inferences

| Attacker position | Can observe | Can infer |
|-------------------|-------------|-----------|
| Network observer (TLS termination) | Field tensors, metadata | Tensor shape, width, value distribution |
| Compromised field service | All request fields | Typed atom counts, repeated query patterns, corpus/query ratio, request frequency, context labels |
| Local file access (ledger) | Full source map | All source text paths, hashes, encoding parameters |
| Repeated requests, same context and secret | Stable field IDs and tensors | Same-document indicator, query deduplication, request correlation |

## Known Limitations

1. **Deterministic fields leak equality**: Same text + same secret + same context = same field tensor. Repeated queries are linkable by the field service.

2. **Typed atom counts reveal structure**: Token frequency counts are in the request. A motivated attacker can infer document length and vocabulary overlap patterns.

3. **Weak client secrets**: A guessable secret makes the field tensors reproducible by the attacker. Use high-entropy secrets. The encoder does not enforce minimum secret entropy.

4. **Ledger tampering**: A local attacker who rewrites the entire ledger can create a new valid hash chain. The ledger detects sequential edits within the current chain, but it does not provide immutable audit logging. Stronger guarantees require external anchoring, signatures, or append-only storage.

5. **No forward secrecy**: A compromised client secret allows retrospective field reconstruction for any stored request encoded with that secret.

6. **Metadata correlation**: Request count, timing, tensor norms, and context labels are visible to the field service and can be correlated across sessions.

7. **Field tensor side channels**: The value distribution of int16 tensors may leak statistical properties of the underlying text vocabulary. A motivated adversary with known-plaintext samples and the same secret could attempt targeted reconstruction.

8. **Binary provenance**: `bin/OpenEncoder.com` is hash-attested by the GitHub workflow, but is not reproducibly built from auditable source. See `RELEASE_ATTESTATION.md` for the hash attestation boundary.

## Not in Scope

- Transport-layer encryption (use TLS between client and field service)
- Side-channel resistance (timing, power analysis)
- Post-compromise recovery or key rotation
- Quantum-resistant cryptography
- Protection against a fully compromised local machine

## Mitigations

| Risk | Current mitigation | Recommended strengthening |
|------|--------------------|--------------------------|
| Query linkage | Context labels separate engagement domains | Rotate secrets per engagement; never reuse context across unrelated corpora |
| Weak secrets | Documentation warns against weak secrets | Add minimum-entropy validation to the encode command |
| Ledger tamper | Hash chain + tamper detection tests | External anchoring (signed checkpoints, append-only storage) for stronger guarantees |
| Service metadata exposure | Non-secret manifest only; no source text in request | Field service trust agreement; audit service compliance |
| Request correlation | Different context produces different field IDs | Use per-session contexts; avoid long-lived static contexts |
| Statistical leakage | HMAC-SHA256 keyed derivation adds secret-dependent noise | Increase width; add noise dimensions (future work) |

## Groth16 Proof Boundary

Groth16 is a zkSNARK proof system. The current legacy Groth16 path in
OpenEncoder builds a deterministic BN254 pairing fixture with fixed curve
points (`alpha = 5*G1`, `beta = G2`, `gamma = G2`, `delta = G2`). This proves
the pairing equation holds for the reference field-envelope statement. It does
**not**:

- Compile an arithmetic circuit
- Perform a trusted setup ceremony
- Prove knowledge of a private witness
- Provide a blanket zero-knowledge privacy guarantee for the whole product

The legacy fixture is a receipt that the reference field emission was constructed using the declared field-envelope parameters, verifiable by any party with the verifying key. The repository also includes a pinned real Groth16 zkSNARK reference circuit proof packet whose manifest and artifacts are checked by `scripts/check_release_gates.py`. This is still not a production multi-party setup, blanket privacy proof, encryption claim, or semantic correctness claim.
