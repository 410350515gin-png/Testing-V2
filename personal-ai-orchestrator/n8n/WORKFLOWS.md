# n8n workflows to implement

## 1. project_state_read
Inputs: project_name
Outputs: current stage, open tasks, locked decisions, canonical folder id

## 2. drive_canonical_files
Inputs: project_name
Outputs: canonical files + metadata + latest version markers

## 3. save_project_artifact
Inputs: project_name, artifact, artifact_type, overwrite_policy
Behavior:
- default: version-safe write
- never destructive overwrite without rollback

## 4. update_project_state
Inputs: project_name, completed_tasks, new_tasks, decision_log_entries
Outputs: updated Notion state

## 5. external_research
Inputs: research_question, max_queries, budget_guard
Behavior:
- first check existing evidence
- call Perplexity only if missing/current evidence is required
- hard-stop at configured budget

## 6. advance_project
Orchestrates 1-5 but delegates high-level reasoning to the manager agent.

The first implementation milestone is workflows 1, 2, 3, and 4.
