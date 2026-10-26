#!/usr/bin/env bash
set -euo pipefail

# Official OpenClaw installation path for Linux/VPS.
# Run this on the private host, not in GitHub Actions.

curl -fsSL https://openclaw.ai/install.sh | bash -s -- --no-onboard

echo
echo "OpenClaw installed."
echo "Next: run 'openclaw onboard --install-daemon' interactively on the host."
echo "Then run 'openclaw doctor' and 'openclaw gateway status'."
