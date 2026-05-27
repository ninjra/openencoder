// Copyright 2026 Shri Narayan Justin Ram / Mushku Nobleworks. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0 OR Commercial
template OpenEncoderFieldEnvelope(width) {
    signal input recipe_sha256;
    signal input request_sha256;
    signal input request_receipt_sha256;
    signal input field_envelope_root;
    signal input ledger_checkpoint_hash;
    signal input encoder_version_hash;
    signal input circuit_id_hash;
    signal input verifying_key_hash;

    signal private input expected_recipe_sha256;
    signal private input expected_request_sha256;
    signal private input expected_request_receipt_sha256;
    signal private input expected_field_envelope_root;
    signal private input expected_ledger_checkpoint_hash;
    signal private input expected_encoder_version_hash;
    signal private input expected_circuit_id_hash;
    signal private input expected_verifying_key_hash;
    signal private input field_tensor[width];
    signal private input expected_field_tensor[width];

    recipe_sha256 === expected_recipe_sha256;
    request_sha256 === expected_request_sha256;
    request_receipt_sha256 === expected_request_receipt_sha256;
    field_envelope_root === expected_field_envelope_root;
    ledger_checkpoint_hash === expected_ledger_checkpoint_hash;
    encoder_version_hash === expected_encoder_version_hash;
    circuit_id_hash === expected_circuit_id_hash;
    verifying_key_hash === expected_verifying_key_hash;

    for (var i = 0; i < width; i++) {
        field_tensor[i] === expected_field_tensor[i];
    }
}

component main = OpenEncoderFieldEnvelope(64);
