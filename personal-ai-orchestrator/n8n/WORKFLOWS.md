# n8n workflows

## Current V1
Import:
`personal-project-agent-flow-v1.json`

Flow:
Manual Trigger → Input → Planner / Router → optional Research → Claude Writer Adapter → ChatGPT Review Packet → Human Gate → Final Integrator.

The Perplexity HTTP node ships disabled until an API key is configured. Claude/ChatGPT/Codex remain adapters until supported programmatic credentials are attached.

## Workspace responsibilities
- Notion: project state / decisions / Change Log.
- Drive: canonical files, _archive, _runs, _handoff.
- GitHub: code projects, branches and PRs.
- Dashboard: status.json-driven visual run state.

## Safety
Never place secrets in workflow JSON or GitHub.
Destructive actions, production deploys, locked research decisions, and budget overruns require Human Gate.
