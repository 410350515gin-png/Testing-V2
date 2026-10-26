# Routing policy

## Entry
Claude is the user-facing orchestrator in V1. It should interpret natural language, load Project State, choose specialist branches, and integrate results.

## Cost-aware order
1. Existing project state and canonical files
2. Claude reasoning / connected Drive / Notion
3. Claude web research
4. Perplexity API only for missing/current external evidence
5. ChatGPT second-model review when the decision merits independent review
6. Codex for software implementation, debugging, tests, and code review

Gemini is not part of V1.

## Specialist roles
### Claude
Use for planning, routing, long-form writing, document synthesis, first-pass review, workspace actions, and final integration.

### Perplexity
Use only when evidence must be current/outside the existing corpus, or when citation/source discovery is required.

### ChatGPT
Use for independent second-model review, methodology/statistics/logic checks, contradiction finding, and high-value QA.

### Codex
Use only for software projects: repo reading, implementation, debugging, tests, and PR-oriented code work.

### Graphify
V2 optional shared knowledge layer. Do not block V1 on Graphify.

## Human approval gate
Require approval before:
- changing research question, hypothesis, experimental design, primary DV, or statistical method;
- accepting conflicting reviewer advice that changes locked decisions;
- destructive file deletion or unrecoverable overwrite;
- DB schema/migration, production deploy, secrets changes, repository/branch deletion;
- external submission/publication/sharing;
- spend above configured API budget.

Everything else may continue automatically when reversible.

## Run status contract
Each role reports:
- status: queued | running | completed | failed | waiting_human
- actor/model
- short current action
- started_at / finished_at
- output_ref
- error_summary (if any)

The visual layer should display these fields without exposing secrets or raw chain-of-thought.
