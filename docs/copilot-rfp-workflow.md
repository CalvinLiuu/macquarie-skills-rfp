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
   - document-type packs that separate RFPs, Macquarie estate/current-state material, Macquarie implementation material, Macquarie guidelines, and competitor brochures
4. Build a document analysis plan that assigns each document type to a dedicated specialist sub-agent.
5. Compare staged content with true-source content and generate a refresh report.
6. Parse the RFP and render it as structured Markdown.
7. Build a response index that captures format expectations, knowledge-pack hints, and human guidance requirements.
8. Retrieve evidence from the true-source corpus.
9. Draft, check, and package answers.

## Specialist Agents

- `rfp-orchestrator`: coordinates the full workflow
- `source-curator`: manages true-source and update-inbox curation
- `rfp-requirements-analyst`: understands tender structure, answer quality, and requirement intent
- `macquarie-current-state-analyst`: understands existing Macquarie estate and incumbent context
- `macquarie-implementation-analyst`: understands delivery history, new implementations, and lessons learned
- `macquarie-guideline-analyst`: understands Macquarie standards, policies, and guardrails
- `competitor-brochure-analyst`: understands competitor brochures, positioning, and differentiators
- `rfp-analyst`: interprets incoming RFPs
- `response-indexer`: plans the response production workload
- `human-guidance-review`: checks where owner approval is required

## Repository Skills

- `documentation-normalization`
- `document-routing`
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
- `data/truth-source/markdown/document-types/`: specialist packs for RFP, Macquarie, and competitor document lanes
- `data/update-inbox/evidence/`: normalized staged document records
- `data/update-inbox/raw/`: extracted staged raw text
- `data/update-inbox/markdown/`: staged Markdown views used during curation
- `data/outputs/`: document analysis plans, refresh reports, structured RFP markdown, response indexes, and answer packages

## Defaults

- One SharePoint library with two operational folders
- Markdown as the shared machine-readable documentation format
- Document typing is required before specialist analysis so each sub-agent stays inside its own evidence lane
- Human escalation on staged source promotion, conflicts, commercial wording, attachments, and government-sensitive responses
- True-source retrieval preferred over live SharePoint search
