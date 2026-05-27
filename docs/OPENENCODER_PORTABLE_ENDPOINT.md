# OpenEncoder Portable Endpoint

SPDX-License-Identifier: Apache-2.0 OR Commercial

`bin/OpenEncoder.com` is the canonical single-file OpenEncoder Zig endpoint.
On Linux/WSL, run it directly as `./bin/OpenEncoder.com`.

```text
+---------------------+------------------------------------------------------+
| Surface             | Boundary                                             |
+---------------------+------------------------------------------------------+
| bin/OpenEncoder.com | canonical single-file OpenEncoder Zig endpoint       |
| score-jsonl         | deterministic comparator scoring path                |
| requirements        | machine-readable protocol requirements               |
| self-check          | endpoint smoke check                                 |
| proof receipt       | Legal-MLEB comparator receipt from Gravitas validation vault |
+---------------------+------------------------------------------------------+
```

Linux/WSL smoke commands:

```bash
./bin/OpenEncoder.com --self-check
./bin/OpenEncoder.com requirements
```

Desktop frontend proof:

```text
docs/proofs/openencoder_windows_frontend_e2e_proof.json
```

Release rules:

```text
+-----------------------+------------------------------------------------------+
| Rule                  | Requirement                                          |
+-----------------------+------------------------------------------------------+
| Source text           | User text stays in local RAM during endpoint smoke   |
| Embedded data         | No corpora, answer keys, or private source text      |
| Local paths           | No maintainer workstation paths                      |
| Network               | No network path required for endpoint smoke          |
| Build hygiene         | Endpoint hash is recorded beside comparator receipts |
+-----------------------+------------------------------------------------------+
```
