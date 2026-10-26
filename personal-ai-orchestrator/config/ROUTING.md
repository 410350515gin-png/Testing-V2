# Routing policy

## Fast path
Use one model only when the request is conversational, explanatory, or does not require project state.

## Project path
For project-specific work:
1. Query Graphify / project state first.
2. Read source files only when the graph does not contain enough evidence.
3. Choose one primary model.
4. Use a second model only for a defined review gate.

## Model roles
### Claude
Use for:
- long-form synthesis
- restructuring reports
- polished document drafts
- merging multiple source passages

### ChatGPT / Codex
Use for:
- methodology and logic review
- cross-file consistency checks
- tool-oriented reasoning
- implementation / code review
- final QA

### Perplexity API
Use only when:
- evidence must be current
- the source is outside the existing corpus
- a citation/DOI/source must be discovered

Do not call Perplexity for questions already answerable from Graphify or Drive.

## Human approval gate
Require user approval before:
- changing research question or hypothesis
- changing experimental design or primary DV
- deleting/overwriting a canonical deliverable when rollback is unavailable
- spending beyond configured external API budget
- publishing externally

Everything else may proceed automatically when reversible.
