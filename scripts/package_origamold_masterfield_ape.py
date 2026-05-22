#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR Commercial
"""Package an Origamold APE from an existing envelope prefix and fresh payloads."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile


APE_MAGIC = b"MZqFpD='"
ZIP_MAGIC = b"PK\x03\x04"
PAYLOADS = (
    ("Origamold.exe", 0o644),
    ("OrigamoldTui-linux-x86_64", 0o755),
    ("OrigamoldTui-macos-x86_64", 0o755),
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return f"external:{resolved.name}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--envelope", required=True, type=Path)
    parser.add_argument("--windows", required=True, type=Path)
    parser.add_argument("--linux", required=True, type=Path)
    parser.add_argument("--macos", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()

    payload_paths = {
        "Origamold.exe": args.windows,
        "OrigamoldTui-linux-x86_64": args.linux,
        "OrigamoldTui-macos-x86_64": args.macos,
    }
    missing = [str(path) for path in [args.envelope, *payload_paths.values()] if not path.is_file()]
    if missing:
        raise SystemExit(f"missing required input files: {missing}")

    envelope_bytes = args.envelope.read_bytes()
    zip_offset = envelope_bytes.find(ZIP_MAGIC)
    if not envelope_bytes.startswith(APE_MAGIC):
        raise SystemExit("envelope does not start with APE magic")
    if zip_offset <= 0:
        raise SystemExit("envelope has no zip payload boundary")
    prefix = envelope_bytes[:zip_offset]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(prefix)
    with zipfile.ZipFile(args.output, "a") as archive:
        for name, mode in PAYLOADS:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = mode << 16
            archive.writestr(info, payload_paths[name].read_bytes())
    args.output.chmod(args.output.stat().st_mode | 0o755)

    with zipfile.ZipFile(args.output, "r") as archive:
        zip_names = archive.namelist()
        zip_hashes = {name: sha256_bytes(archive.read(name)) for name in zip_names}

    checks = {
        "ape_magic_matches": args.output.read_bytes()[: len(APE_MAGIC)] == APE_MAGIC,
        "zip_names_exact": zip_names == [name for name, _mode in PAYLOADS],
        "windows_payload_matches": zip_hashes.get("Origamold.exe") == sha256_file(args.windows),
        "linux_payload_matches": zip_hashes.get("OrigamoldTui-linux-x86_64") == sha256_file(args.linux),
        "macos_payload_matches": zip_hashes.get("OrigamoldTui-macos-x86_64") == sha256_file(args.macos),
    }
    receipt = {
        "schema_version": "openencoder-origamold-masterfield-ape-package-v1",
        "envelope": display_path(args.envelope),
        "envelope_sha256": sha256_file(args.envelope),
        "output": display_path(args.output),
        "output_sha256": sha256_file(args.output),
        "prefix_byte_count": len(prefix),
        "zip_offset": zip_offset,
        "zip_names": zip_names,
        "zip_hashes": zip_hashes,
        "payloads": {name: {"path": display_path(path), "sha256": sha256_file(path)} for name, path in payload_paths.items()},
        "checks": checks,
        "proof_passed": all(checks.values()),
        "claim_boundary": "Reuses an existing Origamold APE envelope prefix and replaces only deterministic embedded payload ZIP entries.",
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["proof_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
