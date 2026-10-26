# Tool contract: Advance_Project

## Input
Natural-language project instruction, e.g.
- "把心理實驗法推進到目前能完成的最高程度"
- "檢查現在缺什麼並把能做的都做掉"

## Workflow
1. Resolve project by name.
2. Load locked project contract.
3. Read project state from Notion.
4. Locate canonical Drive folder and newest files.
5. Query Graphify for relevant relationships and prior decisions.
6. Build a dependency graph of unfinished work.
7. Classify each task:
   - deterministic/reversible -> execute via n8n
   - writing/synthesis -> Claude
   - methodology/logic/QA -> ChatGPT/Codex
   - external current research -> Perplexity API
   - high-impact decision -> ask user
8. Execute independent safe tasks.
9. Run consistency review.
10. Save outputs to Drive with version-safe naming.
11. Update Notion task state + change log.
12. Return:
   - completed
   - changed files
   - remaining blockers
   - decisions required from user

## Performance rule
Do not run every tool on every request.
Use the shortest path that can safely finish the task.
