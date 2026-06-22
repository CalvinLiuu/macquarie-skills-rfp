# GitHub Copilot RFP Skills

This repository now implements a two-layer SharePoint knowledge model for RFP work:

- a `true source` folder for trusted, current-state knowledge
- an `update inbox` folder for newly supplied material that must be curated before it becomes trusted
- structured Markdown normalization for both source content and incoming RFPs
- explicit SharePoint folder roles for segment RFP history, successful RFPs, current successful information, and general documentation
- document-type routing that separates RFPs, Macquarie context, and competitor collateral
- specialist Copilot agents and skills for source curation, document routing, RFP analysis, response indexing, drafting, and human review

## Repository Layout

- `.github/agents/`: orchestrator plus specialist agents
- `.github/skills/`: repository skills for curation, intake, indexing, drafting, and review
- `.github/copilot-instructions.md`: repository-wide instructions for skill-first work
- `.github/ISSUE_TEMPLATE/`: issue handoff template for skill-guided Copilot tasks
- `.github/workflows/`: manual GitHub Actions entry point for selected repository skills
- `rfp_copilot/`: MCP runtime for the `sharepoint-knowledge/*` tools used by agents and skills
- `data/truth-source/`: mirrored trusted content and generated Markdown packs
- `data/update-inbox/`: mirrored staged source updates
- `data/outputs/`: refresh reports, structured RFP markdown, response indexes, and answer outputs
- `config/`: SharePoint and answer profile examples
- `docs/`: workflow and operating-model notes

## Operating Model

The intended workflow is:

1. Confirm the SharePoint structure that maps:
   - `enterprise`, `hyperscaler`, `small_business`, and `government`
   - `Previous RFP`
   - `Successful RFPs`
   - `Successful Up To Date Information`
   - general `Documents` such as important information, new infrastructure, and equipment changes
2. Sync the `true source` SharePoint folder.
3. Sync the `update inbox` SharePoint folder.
4. Normalize trusted content into:
   - one Markdown file per source document
   - domain packs like `security`, `compliance`, `sovereignty`, `power`, and `cooling`
   - client-segment packs like `government/security` or `enterprise/power`
   - document-type packs for `rfp`, `macquarie_current_state`, `macquarie_implementation`, `macquarie_guideline`, and `competitor_brochure`
5. Build a document analysis plan that routes each document type to a dedicated specialist sub-agent.
6. Build a source refresh report that compares staged updates against trusted content.
7. Parse the incoming RFP.
8. Build a response index that shows:
   - question relationships
   - target client segments
   - expected response formats
   - suggested evidence packs
   - human-guidance requirements
9. Draft evidence-backed answers only after the response index is ready.

## Business Actions

The project separates business actions from the lower-level skills that make them happen:

- `mark-successful-rfp-document-information`: confirms successful RFP documents in the right segment folder and turns them into reusable evidence.
- `refresh-successful-document-information`: updates successful up-to-date information from new general documents such as infrastructure, power, cooling, and equipment changes.

Both business actions rely on sub-skills such as `documentation-normalization`, `document-routing`, `source-refresh`, `evidence-retrieval`, and `human-guidance-gate`.

## Assumptions Used In This V1

- SharePoint remains the upstream system of record.
- The first rollout uses one library with separate `true source` and `update inbox` folders.
- Human review remains mandatory for commercial, legal, compliance, attachment-heavy, and government-sensitive content.
- PDF extraction is best effort and requires `pdftotext`; text, markdown, CSV, JSON, TSV, and DOCX work without extra Python dependencies.

## Skill-First Operation

This folder should guide AI agents rather than collect task scripts.

1. Start from `.github/copilot-instructions.md`.
2. Pick the closest repository skill from `.github/skills/`.
3. Use the matching custom agent from `.github/agents/` when specialist analysis is needed.
4. Keep the task context, target paths, evidence status, and expected output visible.
5. Produce reviewable outputs in `data/outputs/` with citations, gaps, confidence, follow-ups, and required attachments.

There is no `scripts/` directory and no installable console entry point. The retained Python package is the MCP runtime for `sharepoint-knowledge/*` tools because the skills need deterministic access to SharePoint sync, parsing, normalization, response indexing, and answer-contract helpers.

## GitHub Actions Usage

Use the manual `RFP skill-guided task` workflow when a GitHub Actions run should hand work to a selected skill.

Workflow inputs:

- `skill`: the repository skill or business action to start from
- `task_context`: the natural-language task request
- `target_paths`: optional repository paths, output paths, or SharePoint locations
- `output_file`: where Copilot should write the run artifact under `data/outputs/`

The workflow requires a `COPILOT_CLI_PAT` repository secret for Copilot CLI authentication. Its runner commands are limited to installing Copilot CLI, building one natural-language prompt, invoking the selected skill, and attaching the output artifact.

## Script Policy

- Do not add standalone scripts, task-specific shell automation, or a `scripts/` directory.
- Keep process guidance in `.github/skills/*/SKILL.md` and `.github/agents/*.agent.md`.
- If an executable bridge is unavoidable, include a visible script exception notice with the reason, dependent skill or agent, remaining business logic, and validation path.
- Current exceptions are documented in `docs/script-exceptions.md`.

## Copilot Usage

The repository is designed to support:

- `rfp-orchestrator`: end-to-end coordination
- `source-curator`: update-inbox curation and refresh reporting
- `mark-successful-rfp-document-information`: business action for marking winning RFP material as reusable evidence
- `refresh-successful-document-information`: business action for updating approved successful information from general documentation
- `rfp-requirements-analyst`: tender-specific requirement analysis
- `macquarie-current-state-analyst`: current-state estate and incumbent context
- `macquarie-implementation-analyst`: implementation history and lessons learned
- `macquarie-guideline-analyst`: standards, guardrails, and policy interpretation
- `competitor-brochure-analyst`: competitor collateral and positioning analysis
- `rfp-analyst`: RFP parsing and relationship mapping
- `response-indexer`: response production planning
- `human-guidance-review`: explicit review gates before submission

## Remaining External Setup

- Register the Microsoft Graph app and grant the required SharePoint permissions.
- Populate `config/knowledge-source.json` with the real `site_id`, `drive_id`, `truth_source_folder`, and `update_inbox_folder`.
- Decide who approves promotion from `update inbox` into `true source`.
- Confirm the real client-segment taxonomy and any extra domains beyond the defaults.
- Add the required GitHub Copilot repository or organization settings for custom agents.
