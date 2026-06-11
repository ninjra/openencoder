<!-- SPDX-License-Identifier: Apache-2.0 OR Commercial -->

# OpenEncoder Blackbox Disclosure Packet

This packet is the validator-facing public disclosure surface. It is intentionally narrower than the README.

forward_relation_recommendations: present
approval_choice_plan: present
implicit_execution_allowed: false

## Boundary

No benchmark-specific execution path is allowed.
No hard-coded cap is allowed.
No qrel-dependent execution is allowed.
No identity receipt may be presented as an answer.
Metric contracts must be generic conveyor-emitted required keys.

## Field Path

The public blackbox path carries integer field objects, receipts, ledger references, and local map-back status only.
Private corpus and query bodies stay outside the service boundary.
The service-facing object is an opaque field request plus public handoff metadata.
The local decoder accepts only compatible field references with valid receipts.

## Release Gate

Measurement output is post-gate evidence only.
Measurement output cannot satisfy release authority by itself.
Release promotion requires current-source tests, privacy scan, replay receipt, proof receipt, and this validator packet to pass in the same release lane.

## Frozen Surfaces: Ionizer Fractal Datatype

OpenEncoder shares the same ionizer bytechunk hotpath. The fractal datatype geometry is frozen:

- **Sint16Field with carry chains** — `fractal_field_dim = 65536 × (carry_depth + 1)`. No hard dimension cap.
- **No Python in the hotpath** — zig endpoint only.
- **No u64 axis hashing** — destroys fractal structure.
- **No fixed per-packet dimension space** — branching factor 65536.

Authoritative documents: `../gravitas/docs/GLOBAL_IONIZER_CLAMP_MATRIX.md`, `../gravitas/gravitas/frozen_surfaces.py`
