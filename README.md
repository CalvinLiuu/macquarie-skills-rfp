# GitHub Copilot RFP Skills

This repository now implements a two-layer SharePoint knowledge model for RFP work:

- a `true source` folder for trusted, current-state knowledge
- an `update inbox` folder for newly supplied material that must be curated before it becomes trusted
- structured Markdown normalization for both source content and incoming RFPs
- document-type routing that separates RFPs, Macquarie context, and competitor collateral
- specialist Copilot agents and skills for source curation, document routing, RFP analysis, response indexing, drafting, and human review

## Repository Layout

- `.github/agents/`: orchestrator plus specialist agents
- `.github/skills/`: repository skills for curation, intake, indexing, drafting, and review
- `rfp_copilot/`: Python package for SharePoint sync, normalization, response indexing, curation, and MCP transport
- `data/truth-source/`: mirrored trusted content and generated Markdown packs
- `data/update-inbox/`: mirrored staged source updates
- `data/outputs/`: refresh reports, structured RFP markdown, response indexes, and answer outputs
- `config/`: SharePoint and answer profile examples
- `docs/`: workflow and operating-model notes

## Operating Model

The intended workflow is:

1. Sync the `true source` SharePoint folder.
2. Sync the `update inbox` SharePoint folder.
3. Normalize trusted content into:
   - one Markdown file per source document
   - domain packs like `security`, `compliance`, `sovereignty`, `power`, and `cooling`
   - client-segment packs like `government/security` or `enterprise/power`
   - document-type packs for `rfp`, `macquarie_current_state`, `macquarie_implementation`, `macquarie_guideline`, and `competitor_brochure`
4. Build a document analysis plan that routes each document type to a dedicated specialist sub-agent.
5. Build a source refresh report that compares staged updates against trusted content.
6. Parse the incoming RFP.
7. Build a response index that shows:
   - question relationships
   - target client segments
   - expected response formats
   - suggested evidence packs
   - human-guidance requirements
8. Draft evidence-backed answers only after the response index is ready.

## Assumptions Used In This V1

- SharePoint remains the upstream system of record.
- The first rollout uses one library with separate `true source` and `update inbox` folders.
- Human review remains mandatory for commercial, legal, compliance, attachment-heavy, and government-sensitive content.
- PDF extraction is best effort and requires `pdftotext`; text, markdown, CSV, JSON, TSV, and DOCX work without extra Python dependencies.

## Quick Start

1. Copy the example configuration:

```bash
cp config/knowledge-source.example.json config/knowledge-source.json
cp config/answer-profile.example.json config/answer-profile.json
```

2. Set the SharePoint secret:

```bash
export SHAREPOINT_CLIENT_SECRET="..."
```

3. Run the tests:

```bash
python3 -m unittest discover -s tests -v
```

4. Parse the sample RFP:

```bash
python3 -m rfp_copilot.cli parse-rfp \
  --input examples/sample-rfp.md
```

5. Sync the true-source folder:

```bash
python3 -m rfp_copilot.cli sync \
  --config config/knowledge-source.json \
  --folder-key truth_source
```

6. Sync the update inbox:

```bash
python3 -m rfp_copilot.cli sync \
  --config config/knowledge-source.json \
  --folder-key update_inbox
```

7. Build the true-source Markdown knowledge base:

```bash
python3 -m rfp_copilot.cli build-knowledge-markdown \
  --config config/knowledge-source.json \
  --folder-key truth_source
```

8. Build the document analysis plan:

```bash
python3 -m rfp_copilot.cli plan-document-analysis \
  --corpus-dir data/truth-source \
  --output-dir data/outputs
```

9. Build the source refresh report:

```bash
python3 -m rfp_copilot.cli prepare-source-refresh \
  --config config/knowledge-source.json
```

10. Promote an approved refresh candidate into the local true-source corpus:

```bash
python3 -m rfp_copilot.cli promote-source-refresh \
  --config config/knowledge-source.json \
  --candidate-id refresh-example
```

11. Render the RFP into structured Markdown:

```bash
python3 -m rfp_copilot.cli render-rfp-markdown \
  --input examples/sample-rfp.md \
  --output data/outputs/sample-rfp-structured.md
```

12. Build the response index:

```bash
python3 -m rfp_copilot.cli render-response-index \
  --input examples/sample-rfp.md \
  --output data/outputs/sample-rfp-response-index.md
```

## Copilot Usage

The repository is designed to support:

- `rfp-orchestrator`: end-to-end coordination
- `source-curator`: update-inbox curation and refresh reporting
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
