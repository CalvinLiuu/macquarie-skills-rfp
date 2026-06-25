---
name: generate-rfp-response
description: Business action for running an end-to-end RFP response generation pass from a bid brief, using only approved true-source evidence plus clearly labeled customer/RFP bid context.
allowed-tools:
  - sharepoint-knowledge/generate_rfp_response
  - sharepoint-knowledge/search_evidence_corpus
  - sharepoint-knowledge/get_evidence_record
  - read
  - edit
---

Use this business action when the user wants a full first-pass RFP response pack from an incoming RFP or bid pack.

This skill is separate from source refresh. It may consume the approved `true source` mirror, and it may optionally sync `truth_source` when the bid brief sets `sync_before_run: true`. It must not sync, read, promote, or consolidate `update_inbox` content. If new source information is needed, stop and use `source-refresh` or `refresh-successful-document-information` as a separate workflow.

Naming:

- Use `generate-rfp-response` for the bid drafting workflow.
- Use `source-refresh` or `refresh-successful-document-information` for evidence consolidation and promotion.
- Use `bid brief` for the user-supplied run input.
- Use `run record` for the audit trail in the generated run folder.

Bid brief contract:

- `company_name` or `customer_name`
- `rfp_input_path`, pointing at one RFP file or a bid pack folder
- `primary_rfp_path` when the bid pack folder does not have exactly one clear primary RFP document
- `truth_source_corpus_dir` or `config_path`
- optional `sync_before_run`, default false
- optional `target_client_segments`
- optional `customer_context`, `bid_context_paths`, `win_themes`, `response_tone`, `answer_profile_path`
- optional `submission_deadline`, `mandatory_attachments`, `human_reviewers`
- optional `requested_package_formats`, such as `json` or `csv`

User-visible process:

1. Tell the user this business action is active.
2. Name the bid brief, incoming RFP or bid pack, target company, and output folder.
3. Explain that customer/RFP context can influence indexing, retrieval filters, tone, win themes, and review prompts, but is not approved capability evidence.
4. Confirm that factual capability claims must come from approved `true source` evidence.
5. Confirm that `update_inbox` will not be touched by this run.
6. Finish by naming the run folder and the generated artifacts.

Sub-skills represented in the run:

1. `rfp-intake`
2. `response-indexing`
3. `evidence-retrieval`
4. `answer-drafting`
5. `gap-and-risk-check`
6. `human-guidance-gate`
7. `compliance-packaging`

Workflow:

1. Read the bid brief and confirm it contains the required inputs.
2. If `rfp_input_path` is a folder, identify the primary RFP from `primary_rfp_path` or one clear primary document. Treat all other bid-pack files as customer-supplied bid context or attachments, not approved evidence.
3. Use `generate_rfp_response` with the bid brief.
4. Preserve the generated run folder under `data/outputs/rfp-response-runs/<date-company-or-opportunity>/`.
5. Verify the run folder includes:
   - `bid-brief.normalized.json`
   - `structured-rfp.md`
   - `response-index.md`
   - `answer-contracts.json`
   - `draft-answers.md`
   - `human-review-actions.md`
   - `run-record.md`
6. Review `human-review-actions.md` before treating the draft as submission-ready.
7. If the run exposes missing or stale evidence, do not patch it inside this workflow. Start the separate source-refresh workflow and rerun generation after approval.
