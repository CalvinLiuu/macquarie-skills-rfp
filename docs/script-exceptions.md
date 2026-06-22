# Script Exceptions

This repository is intended to stay skill-first. Do not add a `scripts/` directory, standalone shell files, or one-off command wrappers for RFP business work.

## Current Exceptions

### `rfp_copilot/`

Reason: the package is the local MCP runtime behind the `sharepoint-knowledge/*` tools referenced by the repository skills and agents.

What it enables:

- SharePoint sync and live search
- RFP question extraction
- Markdown normalization
- response indexing
- evidence retrieval contracts
- source refresh planning

Business logic should still be described in `.github/skills/*/SKILL.md`; the runtime only exposes deterministic tools the AI can call.

### `.github/workflows/rfp-skill-guided-task.yml`

Reason: GitHub Actions cannot invoke Copilot CLI without runner commands.

Allowed shell use:

- install Copilot CLI
- create one prompt from workflow inputs
- invoke Copilot with the selected repository skill
- attach the generated output as a workflow artifact

Not allowed:

- task-specific shell logic
- hidden source curation scripts
- automated promotion of unreviewed SharePoint material
- generated answer content without citations, gaps, confidence, and follow-ups

## Future Exception Standard

Any future executable step must include a visible script exception notice with:

1. the reason the executable step is unavoidable
2. the skill or agent that depends on it
3. the business logic that remains in skill guidance instead of code
4. the validation expected from a human reviewer
