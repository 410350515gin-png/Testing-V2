# Free-template assembly plan

V1 uses the working Claude Project OS as the control layer and borrows proven patterns from free n8n templates instead of rebuilding the logic from scratch.

## Base patterns to reuse
1. n8n template #16662 — Researcher → Writer → Reviewer loop with circuit breaker and Notion publishing.
   - Keep: specialist separation, reviewer rejection loop, max-revision circuit breaker, audit metadata.
   - Replace: GPT-4o nodes with our model adapters; Tavily with Perplexity when enabled; publishing target with Project State / Change Log.
2. n8n Human-in-the-loop / Send-and-Wait pattern.
   - Keep: pause execution, wait for approval/input, resume same run.
3. n8n Google Drive + Notion native nodes.
   - Keep: deterministic file/state operations.
4. GitHub/Render branch for software projects.
   - Keep: branch/PR/test/deploy status; production merge/deploy remains behind Human Gate.

## V1 logical graph
Input
→ Load Project State
→ Planner/Router
→ conditional specialist branches
   → Research (Claude web; Perplexity adapter later)
   → Writer (Claude)
   → Reviewer #1 (Claude isolated context)
   → Reviewer #2 (ChatGPT adapter; manual bridge until automated)
   → Coding (Codex adapter for software)
→ Review decision
   → revise loop OR Human Gate OR continue
→ Integrator
→ deterministic workspace writes
→ final status

## What is free today
- Claude-native role separation using the existing Project OS
- Notion and Drive project state
- GitHub branch/project files
- this workflow specification and dashboard
- n8n community templates themselves

## What remains adapter-dependent
- automatic ChatGPT model invocation
- automatic Perplexity invocation
- automatic Codex invocation
- always-on n8n runtime

These must stay modular so V1 can run before every adapter is connected.
