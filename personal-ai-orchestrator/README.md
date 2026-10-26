# Personal AI Orchestrator v1

Goal: one conversational entry point that can advance a project, consult shared project knowledge, delegate reasoning/writing, execute deterministic automations, and report only decisions that need the user.

## Roles
- OpenClaw: conversational manager / router.
- Graphify: shared project knowledge graph.
- ChatGPT/Codex: reasoning, methodology review, QA.
- Claude: long-form synthesis and document drafting.
- Perplexity API: external research only when current/outside evidence is needed.
- n8n: deterministic execution (Drive, Notion, file/version operations, notifications).
- Google Drive: canonical deliverables.
- Notion: project state, tasks, decisions, change log.

## First project
Psychology Experimental Methods proposal.

### One-command target
"Advance the psychology experiment project as far as safely possible."

The system should:
1. Read current project state.
2. Locate canonical files.
3. Query project knowledge before re-reading everything.
4. Identify incomplete work.
5. Delegate drafting/review to the appropriate model.
6. Execute low-risk file/task operations.
7. Stop only for high-impact design decisions.
8. Update Drive/Notion.
9. Return a compact completion report.

## Safety rule
Never store provider credentials in GitHub. Use runtime environment variables / secret stores only.
