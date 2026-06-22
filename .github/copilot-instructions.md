# Repository Instructions

This repository is a skill-first RFP workflow. Start every task by choosing the relevant repository skill from `.github/skills/`, then follow the matching specialist agent in `.github/agents/` when the task needs deeper analysis.

## Working Rules

- Use repository skills as the source of process. Do not invent one-off shell scripts, helper scripts, or ad hoc automation for RFP work.
- Keep business logic inside `SKILL.md` guidance, custom agents, and the `sharepoint-knowledge/*` tools exposed through the local MCP runtime.
- Prefer natural-language handoff through skills over command sequences. A human reviewer should be able to understand the workflow from the skill file alone.
- If an executable bridge is unavoidable, add a script exception notice that explains:
  - why the executable step is required
  - which skill or agent depends on it
  - what business logic remains outside the executable step
  - how a reviewer can validate the result
- Never promote staged SharePoint material into trusted evidence without an explicit human review surface.
- Keep citations, gaps, follow-ups, confidence, and required attachments visible in every answer contract.

## GitHub Actions

Use `.github/workflows/rfp-skill-guided-task.yml` for manual GitHub Actions runs. The workflow only bootstraps Copilot CLI and passes a natural-language task to the selected repository skill. It must not grow task-specific shell logic.
