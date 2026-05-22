# Copilot RFP Workflow

## Architecture

This repository treats SharePoint as the upstream system of record and GitHub Copilot as the orchestration and drafting surface.

The flow is:

1. Sync `true source` from SharePoint into `data/truth-source/`.
2. Sync `update inbox` from SharePoint into `data/update-inbox/`.
3. Normalize source content into:
   - per-document Markdown
   - domain packs like `security`, `compliance`, `sovereignty`, `power`, and `cooling`
   - client-segment packs like `government/security` or `enterprise/sovereignty`
4. Compare staged content with true-source content and generate a refresh report.
5. Parse the RFP and render it as structured Markdown.
6. Build a response index that captures format expectations, knowledge-pack hints, and human guidance requirements.
7. Retrieve evidence from the true-source corpus.
8. Draft, check, and package answers.

## Specialist Agents

- `rfp-orchestrator`: coordinates the full workflow
- `source-curator`: manages true-source and update-inbox curation
- `rfp-analyst`: interprets incoming RFPs
- `response-indexer`: plans the response production workload
- `human-guidance-review`: checks where owner approval is required

## Repository Skills

- `documentation-normalization`
- `source-refresh`
- `rfp-intake`
- `response-indexing`
- `evidence-retrieval`
- `answer-drafting`
- `human-guidance-gate`
- `gap-and-risk-check`
- `compliance-packaging`

## Runtime Data

- `data/truth-source/evidence/`: normalized trusted document records
- `data/truth-source/raw/`: extracted trusted raw text
- `data/truth-source/markdown/documents/`: structured Markdown per trusted source document
- `data/truth-source/markdown/domains/`: cross-segment domain packs
- `data/truth-source/markdown/client-segments/`: client-specific domain packs
- `data/update-inbox/evidence/`: normalized staged document records
- `data/update-inbox/raw/`: extracted staged raw text
- `data/update-inbox/markdown/`: staged Markdown views used during curation
- `data/outputs/`: refresh reports, structured RFP markdown, response indexes, and answer packages

## Defaults

- One SharePoint library with two operational folders
- Markdown as the shared machine-readable documentation format
- Human escalation on staged source promotion, conflicts, commercial wording, attachments, and government-sensitive responses
- True-source retrieval preferred over live SharePoint search

