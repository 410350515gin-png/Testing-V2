# VPS deployment order

This file intentionally contains no secrets.

## 0. Requirements
Recommended for the first version:
- Linux VPS
- Docker Engine + Docker Compose v2
- Node supported by current OpenClaw installer
- Python 3.10+
- HTTPS reverse proxy / private access
- enough RAM for OpenClaw + n8n + database

OpenClaw's official Docker documentation recommends using an official image/setup path and warns that public-host exposure should be hardened. The normal installer is simpler for a single private assistant, so V1 runs OpenClaw on the host and n8n in Docker.

## 1. Install OpenClaw
Run:

```bash
bash deploy/install-openclaw.sh
openclaw onboard --install-daemon
openclaw doctor
openclaw gateway status
```

Do the model sign-ins on the host. Never paste OAuth tokens into GitHub.

## 2. Install Graphify
Run:

```bash
bash deploy/install-graphify.sh
```

Graphify's official PyPI package is `graphifyy` (double y); the installed CLI is `graphify`.
It requires Python 3.10+.
The OpenClaw integration command is `graphify claw install`.

## 3. Start n8n
Create a private runtime `.env` from the repository's `.env.example`.
At minimum set:
- POSTGRES_PASSWORD
- N8N_ENCRYPTION_KEY
- N8N_HOST
- WEBHOOK_URL

Then:

```bash
docker compose -f deploy/docker-compose.n8n.yml up -d
```

Do not expose port 5678 directly to the public internet without HTTPS/authentication.

## 4. Connect Notion + Google Drive inside n8n
Create credentials in n8n's credential store, not in workflow JSON or GitHub.

First workflows:
1. project_state_read
2. drive_canonical_files
3. save_project_artifact
4. update_project_state

## 5. External research
Perplexity API is optional and should be used only for missing/current outside evidence.
Set a hard monthly budget and a per-run query cap.

## 6. First end-to-end test
Command:
"把心理實驗法專案推進到目前能安全完成的最高程度。"

Expected behavior:
- read project state
- locate canonical Drive files
- query project graph
- detect missing Methods/Materials
- review any new files against locked design
- update Notion
- save only version-safe artifacts
- ask the user only for high-impact design decisions
