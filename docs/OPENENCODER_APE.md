# OpenEncoder APE

SPDX-License-Identifier: Apache-2.0 OR Commercial

`bin/OpenEncoder.com` is the canonical single-file OpenEncoder launcher artifact.
It embeds Windows, Linux, and macOS payloads. On Windows, double-click launches
the dark OpenEncoder desktop workflow. On Linux/WSL, run it with `sh`.

```text
+---------------------+------------------------------------------------------+
| Surface             | Boundary                                             |
+---------------------+------------------------------------------------------+
| bin/OpenEncoder.com | canonical single-file OpenEncoder launcher           |
| Windows payload     | dark GUI package/decode workflow                     |
| Linux payload       | portable CLI/TUI package/decode smoke workflow       |
| macOS payload       | embedded payload packaged; host receipt still needed |
| proof receipt       | docs/proofs/openencoder_origamold_masterfield_ape_package_receipt.json |
+---------------------+------------------------------------------------------+
```

Linux/WSL smoke commands:

```bash
sh bin/OpenEncoder.com --self-check
sh bin/OpenEncoder.com --list-apps
sh bin/OpenEncoder.com --synthetic-e2e \
  --app openencoder \
  --documents "OpenEncoder Linux portable proof document. The answer is recovered from the local RAM ledger." \
  --question "Where is the answer recovered from?" \
  --answer-output /tmp/openencoder_linux_ape_answer.txt
```

Windows frontend proof:

```text
docs/proofs/openencoder_windows_frontend_e2e_proof.json
```

Release rules:

```text
+-----------------------+------------------------------------------------------+
| Rule                  | Requirement                                          |
+-----------------------+------------------------------------------------------+
| Source text           | User text stays in local RAM during launcher smoke   |
| Embedded data         | No corpora, answer keys, or private source text      |
| Local paths           | No maintainer workstation paths                      |
| Network               | No network path required for launcher smoke          |
| Build hygiene         | Package receipt records embedded payload hashes      |
+-----------------------+------------------------------------------------------+
```
