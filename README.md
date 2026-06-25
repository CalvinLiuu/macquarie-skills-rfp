# GitHub Copilot RFP Skills

This repository now implements a two-layer SharePoint knowledge model for RFP work:

- a `true source` folder for trusted, current-state knowledge
- an `update inbox` folder for newly supplied material that must be curated before it becomes trusted
- structured Markdown normalization for both source content and incoming RFPs
- explicit SharePoint folder roles for segment RFP history, successful RFPs, current successful information, and general documentation
- document-type routing that separates RFPs, Macquarie context, and competitor collateral
- specialist Copilot agents and skills for source curation, document routing, RFP analysis, response indexing, drafting, and human review
- an end-to-end `generate-rfp-response` business action that turns a bid brief into a dated company run folder

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
- `config/`: SharePoint, bid brief, and answer profile examples
- `docs/`: workflow and operating-model notes

## Process Folder Structure

Use this folder structure to keep the skill-guided process aligned. Top-level folders are committed to the repository; deeper `data/` folders are generated or refreshed by the MCP runtime when agents run the skills.

```text
.
|-- .github/
|   |-- copilot-instructions.md
|   |-- ISSUE_TEMPLATE/
|   |   `-- rfp-skill-task.yml
|   |-- workflows/
|   |   `-- rfp-skill-guided-task.yml
|   |-- agents/
|   |   |-- rfp-orchestrator.agent.md
|   |   |-- source-curator.agent.md
|   |   |-- rfp-analyst.agent.md
|   |   |-- response-indexer.agent.md
|   |   |-- human-guidance-review.agent.md
|   |   `-- specialist analysis agents
|   `-- skills/
|       |-- generate-rfp-response/
|       |-- rfp-intake/
|       |-- response-indexing/
|       |-- evidence-retrieval/
|       |-- answer-drafting/
|       |-- source-refresh/
|       |-- documentation-normalization/
|       |-- document-routing/
|       |-- gap-and-risk-check/
|       |-- human-guidance-gate/
|       |-- compliance-packaging/
|       |-- mark-successful-rfp-document-information/
|       `-- refresh-successful-document-information/
|-- config/
|   |-- knowledge-source.example.json
|   |-- bid-brief.example.json
|   `-- answer-profile.example.json
|-- data/
|   |-- truth-source/
|   |   |-- evidence/
|   |   |-- raw/
|   |   `-- markdown/
|   |       |-- documents/
|   |       |-- domains/
|   |       |-- client-segments/
|   |       `-- document-types/
|   |-- update-inbox/
|   |   |-- evidence/
|   |   |-- raw/
|   |   `-- markdown/
|   |-- outputs/
|   |   |-- source-decision-register.md
|   |   |-- refresh-reports/
|   |   |-- past-rfp-package-inventories/
|   |   |-- document-analysis-plans/
|   |   |-- structured-rfps/
|   |   |-- response-indexes/
|   |   |-- rfp-response-runs/
|   |   `-- answer-packages/
|   |-- state/
|   `-- mirror/
|-- docs/
|-- examples/
|-- rfp_copilot/
`-- tests/
```

Folder responsibilities:

- `.github/skills/` defines how agents should work. This is the process layer.
- `.github/agents/` defines who should do each part of the work. This is the role layer.
- `.github/workflows/` starts a manual skill-guided GitHub Actions run. It should stay a thin handoff layer.
- `config/` stores examples for SharePoint and answer preferences. Real secrets should not be committed.
- `data/truth-source/` is the trusted evidence mirror. Agents can draft from this only when evidence is approved.
- `data/update-inbox/` is staged material. Agents can analyze it, but cannot treat it as trusted until a human approves promotion.
- `data/outputs/source-decision-register.md` is the single decision document for freshness, conflicts, user questions, approvals, and promotion history.
- `data/outputs/refresh-reports/` stores source-refresh outputs that feed the decision register.
- `data/outputs/past-rfp-package-inventories/` stores inventories for folders that contain multiple past RFP documents.
- `data/outputs/document-analysis-plans/` stores routing plans for specialist agents.
- `data/truth-source/markdown/client-segments/<segment>/` stores consolidated client-segment knowledge packs, such as Enterprise-specific security or power material.
- `data/truth-source/markdown/domains/` stores consolidated cross-client domain knowledge packs.
- `data/outputs/structured-rfps/`, `response-indexes/`, and `answer-packages/` hold bid-specific working outputs.
- `data/outputs/rfp-response-runs/<date-company-or-opportunity>/` stores end-to-end generation run folders from `generate-rfp-response`.
- `data/state/` stores sync state and checkpoints.
- `data/mirror/` is a local mirror or scratch location. It is not trusted evidence unless promoted into `data/truth-source/`.
- `rfp_copilot/` exposes deterministic MCP tools to the skills. It should not become a script or command-workflow layer.

Naming rules:

- Use **client-segment knowledge pack** for consolidated reusable content by segment, such as `enterprise/security.md`.
- Use **domain knowledge pack** for consolidated reusable content by topic across segments, such as `security.md`.
- Use **source decision register** for the review log that records conflicts, user questions, approvals, rejections, and promotion decisions.
- Use **past RFP package** for a folder of related historical RFP material, such as the original tender, submitted response, addenda, clarifications, attachments, pricing, internal notes, and outcome notes.
- Do not use the decision register as the consolidated document store. It explains what changed and what was approved; the knowledge packs hold the reusable content.

Example: if SharePoint contains several Enterprise documents, the approved reusable content should be consolidated into client-segment knowledge packs such as `data/truth-source/markdown/client-segments/enterprise/security.md` or `data/truth-source/markdown/client-segments/enterprise/power.md`. The source decision register should only record which Enterprise sources were reviewed, what conflicted, what the user approved, and which packs were rebuilt.

Example: if more files appear under an Enterprise `Previous RFP` folder, treat that folder as a past RFP package first. Build an inventory of all documents in the folder, classify each document, ask whether the RFP was won or approved for reuse, and only then promote approved facts into Enterprise knowledge packs.

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

- `generate-rfp-response`: creates an end-to-end RFP response run from a bid brief using approved true-source evidence and bid-specific customer context.
- `mark-successful-rfp-document-information`: confirms successful RFP documents in the right segment folder and turns them into reusable evidence.
- `refresh-successful-document-information`: updates successful up-to-date information from new general documents such as infrastructure, power, cooling, and equipment changes.

These business actions rely on sub-skills such as `documentation-normalization`, `document-routing`, `source-refresh`, `evidence-retrieval`, and `human-guidance-gate`.

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

## V1 Workflow Split

Use `generate-rfp-response` for the main end-to-end drafting workflow. The user supplies a bid brief, incoming RFP file or bid pack folder, approved true-source corpus/config, customer context, optional win themes, review owners, and output preferences. The run writes `bid-brief.normalized.json`, `structured-rfp.md`, `response-index.md`, `answer-contracts.json`, `draft-answers.md`, `human-review-actions.md`, and `run-record.md` under `data/outputs/rfp-response-runs/<date-company-or-opportunity>/`.

Customer/RFP context can influence indexing, retrieval filters, tone, win themes, and review prompts, but it is labeled as bid-context input rather than approved capability evidence. Factual capability claims must still cite approved `true source` evidence.

Use `source-refresh` or `refresh-successful-document-information` separately when new or changed material needs to update trusted knowledge. Generation must not sync, read, promote, or consolidate `update_inbox`.

## Full Process

Use this process whenever work enters the repository through an issue, a Copilot chat, or the manual GitHub Actions workflow.

### 1. Capture The Task

- Start from a clear natural-language request.
- Use `.github/ISSUE_TEMPLATE/rfp-skill-task.yml` for repeatable handoff.
- Select the primary skill or business action before doing any work.
- Include the relevant RFP path, source folder, SharePoint location, desired output path, and any known review owner.

Expected output: a task with enough context for an AI agent to choose the right skill and produce a reviewable artifact.

### 2. Apply Repository Instructions

- Read `.github/copilot-instructions.md`.
- Confirm the no-scripts rule for the task.
- Use `docs/script-exceptions.md` only when an executable bridge is unavoidable.
- Keep business logic in `.github/skills/*/SKILL.md` and `.github/agents/*.agent.md`.

Expected output: a skill-guided plan, not a command sequence.

### 3. Choose The Skill Path

- For end-to-end RFP response generation, start with `generate-rfp-response`.
- For new RFPs, start with `rfp-intake`.
- For reusable winning material, start with `mark-successful-rfp-document-information`.
- For new or changed general documentation, start with `refresh-successful-document-information` or `source-refresh`.
- For answer production, move through `response-indexing`, `evidence-retrieval`, `answer-drafting`, `gap-and-risk-check`, `human-guidance-gate`, and `compliance-packaging`.

Expected output: the selected skill, any supporting sub-skills, and the specialist agent that should handle deeper analysis.

### 4. Curate Source Material

- Treat SharePoint `true source` as trusted evidence.
- Treat SharePoint `update inbox` as staged material.
- Use `documentation-normalization` to create structured Markdown, domain packs, client-segment packs, and document-type packs.
- Use `document-routing` to separate RFPs, Macquarie current-state material, implementation material, guidelines, competitor brochures, and general knowledge.

Expected output: normalized knowledge packs and a document analysis plan that keeps specialists inside their evidence lanes.

### 5. Refresh Trusted Evidence

- Use `source-refresh` when staged documents need to update trusted knowledge.
- Compare staged content against `true source`.
- Produce a refresh report that shows proposed additions, updates, conflicts, stale sources, and owner review needs.
- Promote only approved candidates.
- If the staged content is a past RFP package, inventory the whole folder before promotion and keep package relationships visible.

Expected output: a human-review refresh surface before any staged material becomes trusted evidence.

### 6. Intake The RFP

- Use `rfp-intake` to parse the RFP or bid pack.
- Preserve question IDs through the whole workflow.
- Capture deadlines, deliverables, target client segments, domains, expected answer shape, and attachment needs.
- Render the RFP into structured Markdown when it helps later agents reason safely.

Expected output: structured RFP questions that later skills can trust.

### 7. Build The Response Index

- Use `response-indexing` before drafting.
- Map each question to response format, related domains, related client segments, suggested evidence packs, and human-guidance flags.
- Route specialist analysis to the right agent when interpretation is needed.

Expected output: a production index that explains how each answer should be built.

### 8. Retrieve Evidence

- Use `evidence-retrieval` against the approved true-source corpus first.
- Prefer evidence with strong overlap to the question, domain, client segment, and document type.
- Label live SharePoint findings as unconfirmed unless they are already mirrored and approved.
- Treat missing, stale, or conflicting evidence as a gap.

Expected output: citations and evidence records that can support each answer claim.

### 9. Draft Answers

- Use `answer-drafting` only after response indexing and evidence retrieval.
- Keep every answer inside the contract: `question_id`, `question_text`, `draft_answer`, `citations[]`, `confidence`, `gaps[]`, `followups[]`, and `required_attachments[]`.
- Avoid unsupported commitments, especially for commercial, legal, privacy, attachment-heavy, and government-sensitive questions.

Expected output: evidence-backed answer contracts that are useful but still reviewable.

### 10. Review Risk And Human Guidance

- Use `gap-and-risk-check` before packaging.
- Use `human-guidance-gate` wherever owner approval, clarification, attachments, or high-risk wording are required.
- Lower confidence rather than hiding uncertainty.
- Keep the human action visible and specific.

Expected output: explicit gaps, follow-ups, confidence changes, and owner review points.

### 11. Package The Deliverable

- Use `compliance-packaging` after review.
- Preserve citations, confidence, gaps, follow-ups, attachment requirements, and human-review flags.
- Write outputs under `data/outputs/` unless the task specifies another repository path.

Expected output: a Markdown, JSON, or CSV deliverable that can be reviewed and carried into the bid process.

### 12. Run Through GitHub Actions When Needed

- Use `.github/workflows/rfp-skill-guided-task.yml` for a manual skill-guided run.
- Provide `skill`, `task_context`, `target_paths`, and `output_file`.
- Keep the workflow as a thin Copilot handoff. Do not add task-specific shell logic.
- Review the workflow artifact before treating it as final.

Expected output: a generated artifact from the selected skill plus a visible script exception notice for the GitHub Actions bridge.

## Past RFP Package Discovery

Use this process when more documentation is found inside a folder for past RFP documentation, such as a segment `Previous RFP` or `Successful RFPs` folder.

Do not treat every file in a past RFP folder as reusable evidence. A folder may contain mixed material:

- original client RFP or tender documents
- submitted responses
- successful response versions
- addenda, clarifications, and client questions
- attachments such as case studies, CVs, certificates, diagrams, or policies
- pricing, legal, commercial, privacy, or security material
- internal review notes, win/loss notes, debriefs, and draft working files
- Macquarie current-state, implementation, guideline, or competitor documents stored with the RFP package

### Package Flow

1. `source-curator` tells the user it found a past RFP package and names the SharePoint folder or repository path.
2. The agent explains that the folder will be inventoried first and that nothing will be promoted into trusted evidence until the user approves it.
3. `documentation-normalization` converts readable documents into structured Markdown.
4. `document-routing` classifies each file by document type and specialist lane.
5. The agent writes a package inventory under `data/outputs/past-rfp-package-inventories/`.
6. `rfp-requirements-analyst` reviews RFP/tender documents, previous answer structure, scoring signals, mandatory requirements, and answer patterns.
7. Other specialist agents review only their relevant lanes when the package includes current-state, implementation, guideline, competitor, or general knowledge material.
8. `human-guidance-gate` asks the user direct questions before reuse:
   - Was this RFP won, lost, withdrawn, or unknown?
   - Which submitted response version is the approved version?
   - Which attachments are approved for reuse?
   - Are pricing, legal, security, privacy, or commercial claims still current?
   - Which sources are superseded or should never be reused?
9. Approved decisions are recorded in `data/outputs/source-decision-register.md`.
10. Only approved facts and documents are promoted into `data/truth-source/`.
11. Trusted client-segment, domain, and document-type knowledge packs are rebuilt.
12. The agent summarizes the package, approval decisions, rebuilt packs, unresolved questions, and downstream RFP impact.

### Package Inventory

Use this outline for each inventory file under `data/outputs/past-rfp-package-inventories/`:

```markdown
# Past RFP Package Inventory

## Package Context
- Segment:
- Source folder:
- RFP or client name:
- Outcome status:
- Review owner:
- Selected skill:

## Documents Found
| Document | Source path | Document role | Specialist lane | Reuse status | User question |
| --- | --- | --- | --- | --- | --- |

## Package Relationships
| Relationship | Documents | Notes |
| --- | --- | --- |

## Reuse Decisions Needed
| Question | Why it matters | Blocking? |
| --- | --- | --- |

## Recommended Next Step
- 
```

Expected output: a package inventory, source decision register updates, direct user questions for unclear reuse decisions, and rebuilt knowledge packs only for approved reusable material.

## Data Refresh And Source Decisions

Use this process separately from bid drafting whenever new material arrives, source material changes, or agents find conflicting information. The goal is to keep all reusable evidence aligned before it influences answers.

### Source Decision Register

Maintain one decision document at `data/outputs/source-decision-register.md`. Every data-refresh run should update or produce this document so all agents can reason from the same review surface.

The source decision register should contain:

- run context: date, requester, trigger, source folders, and selected skill
- source inventory: new, changed, unchanged, stale, and missing documents
- canonical facts: approved facts that can be reused in future answers
- conflicts: competing claims, source paths, owners, dates, and confidence
- user questions: specific decisions required from the human owner
- promotion decisions: approved, rejected, deferred, and superseded material
- agent handoffs: which specialist agent reviewed each document lane
- downstream impact: affected domains, client segments, RFP responses, and answer packs
- next actions: owner, due date, and follow-up needed before drafting

Use this outline for `source-decision-register.md`:

```markdown
# Source Decision Register

## Run Context
- Date:
- Requester:
- Trigger:
- Source folders:
- Selected skill:

## Source Inventory
| Status | Source path | Owner | Date | Document type | Notes |
| --- | --- | --- | --- | --- | --- |

## Canonical Facts
| Fact ID | Approved fact | Source path | Owner | Applies to | Confidence |
| --- | --- | --- | --- | --- | --- |

## Conflict Register
| Conflict ID | Topic | Source A | Source B | Impact | User question | Status |
| --- | --- | --- | --- | --- | --- | --- |

## User Decisions
| Decision ID | Question | User decision | Approved source | Superseded source | Follow-up |
| --- | --- | --- | --- | --- | --- |

## Agent Handoffs
| Agent | Lane | Inputs reviewed | Findings | Next owner |
| --- | --- | --- | --- | --- |

## Promotion Log
| Candidate | Decision | Destination | Approved by | Notes |
| --- | --- | --- | --- | --- |

## Downstream Impact
| Area | Impacted files or answers | Required action |
| --- | --- | --- |

## Next Actions
| Owner | Action | Due date | Blocking? |
| --- | --- | --- | --- |
```

### Refresh Flow

1. `source-curator` starts with `source-refresh` when new or changed material appears in `data/update-inbox/`.
2. The agent tells the user which folder is being reviewed, which skill is active, and that staged content will not become trusted without approval.
3. `documentation-normalization` converts staged material into structured Markdown.
4. `document-routing` assigns each document to the right specialist lane.
5. Specialist agents review only their lane:
   - `rfp-requirements-analyst` for RFP and tender material
   - `macquarie-current-state-analyst` for current-state and incumbent context
   - `macquarie-implementation-analyst` for implementation history and lessons learned
   - `macquarie-guideline-analyst` for standards, policies, and guardrails
   - `competitor-brochure-analyst` for competitor collateral
   - `general-knowledge-analyst` for broad reusable capability evidence
6. `gap-and-risk-check` compares staged findings with `data/truth-source/`.
7. `human-guidance-gate` turns unresolved conflicts into direct user questions.
8. The user confirms which information is correct, outdated, superseded, or needs more evidence.
9. Approved decisions are recorded in `source-decision-register.md`.
10. Only approved candidates are promoted into `data/truth-source/`.
11. `documentation-normalization` rebuilds the trusted Markdown packs so future RFP answers use aligned information.
12. The agent summarizes what changed, which packs were rebuilt, which decisions are still open, and where the user can review the output.

### Agent Communication During Skill Execution

When an agent executes `source-refresh` or `refresh-successful-document-information`, it should give the user a clear running explanation:

1. **Skill active:** name the skill or business action being used.
2. **Inputs:** name the SharePoint folder or repository path being reviewed.
3. **Purpose:** state whether the agent is refreshing trusted evidence, checking staged updates, or resolving conflicts.
4. **Where content goes:** explain that approved consolidated content is rebuilt into knowledge packs under `data/truth-source/markdown/`.
5. **Where decisions go:** explain that conflicts and approvals are recorded in `data/outputs/source-decision-register.md`.
6. **Human decisions:** list any direct user questions before promoting or trusting new information.
7. **Result:** summarize approved changes, unresolved gaps, rebuilt packs, and downstream RFP impacts.

### Conflict Rules

- Do not silently choose between conflicting sources.
- Prefer newer material only when it is approved and does not conflict with a controlled policy, contract, or owner-approved source.
- Ask the user when two approved sources disagree, when ownership is unclear, or when a source changes commercial, legal, compliance, security, privacy, or government-sensitive claims.
- Mark unresolved facts as gaps instead of drafting from them.
- Keep rejected or superseded claims visible in the source decision register so agents do not reintroduce them later.

Expected output: a current `source-decision-register.md`, updated trusted packs, and clear user decisions for every conflict that blocks reliable drafting.

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
- `generate-rfp-response`: business action for end-to-end bid drafting from a bid brief
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
