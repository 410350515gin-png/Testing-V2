# Credential setup — V1

Goal: keep secrets out of GitHub and activate only the providers that are actually needed.

## Required now
### Claude
V1 can continue to run from the Claude Project OS without an API key. The n8n adapter remains a placeholder until you choose a supported Anthropic API/connector path.

### Notion / Drive / GitHub
Use OAuth or native connectors in the host platform. Never paste tokens into workflow JSON.

## Optional provider adapters
### Perplexity
Environment variable:
`PERPLEXITY_API_KEY`

The included workflow already contains a disabled HTTP Request node. Enable it only after the key exists in the n8n runtime.

### ChatGPT
Keep V1 as review-packet handoff until an official supported programmatic credential is available for the chosen runtime. Do not scrape or proxy consumer-session cookies.

### Codex
Software-project branch only. Prefer official OpenAI/Codex authentication supported by the chosen runtime; otherwise leave disabled.

## Secret policy
- Never commit .env, tokens, cookies, OAuth refresh tokens, or API keys.
- Use the workflow host's credential store or environment variables.
- Any secret/production credential change is behind Human Gate.

## Today’s operational target
1. Import `n8n/personal-project-agent-flow-v1.json`.
2. Leave Perplexity disabled if no API key yet.
3. Confirm Manual Trigger → Planner → Writer Adapter → Review Packet → Human Gate → Integrator works.
4. Keep real document execution in Claude Project OS until provider adapters are activated.
