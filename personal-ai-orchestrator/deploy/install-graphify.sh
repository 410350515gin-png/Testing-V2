#!/usr/bin/env bash
set -euo pipefail

if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

uv tool install graphifyy || uv tool upgrade graphifyy

# Register Graphify with OpenClaw.
graphify claw install

echo
echo "Graphify installed and registered with OpenClaw."
echo "From a project directory, build/query the graph with Graphify."
