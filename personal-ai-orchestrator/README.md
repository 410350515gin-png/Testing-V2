# Personal Project Agent Flow v1

Goal: one natural-language entry point that can advance a project, route work to specialist AI roles, preserve project state, pause for human decisions, and show visible execution status.

## V1 architecture

User
→ Claude Project / Orchestrator
→ Project State (Notion + canonical Drive/GitHub links)
→ Specialist branches
   - Claude: planner, writer, integrator, first-pass reviewer
   - Perplexity: external/current research when needed
   - ChatGPT: second-model review / methodology / logic
   - Codex: coding/debug/test branch for software projects
→ Human Gate
→ Drive / Notion / GitHub
→ Visual run status

Gemini is intentionally excluded from V1. Graphify is reserved for V2 as an optional shared knowledge layer.

## Fixed entry intents
- Start_Project: create/register a project and its state.
- Advance_Project: continue all safe work.
- Review_Project: run read-only/low-risk review.
- Finalize_Project: final QA and prepare for submission/deploy.

## First validated project
Psychology Experimental Methods proposal.

The Claude-native V1 has already demonstrated:
- parallel Researcher + Reviewer roles,
- Writer tracked-change output,
- Integrator decisions,
- Notion state updates,
- Drive _archive / _runs / _handoff,
- Human Gate blocking destructive actions.

## Safety
Never store provider credentials in GitHub.
Canonical files are never destructively overwritten without a rollback path.
High-impact research/design/deploy/delete actions require Human Gate approval.
