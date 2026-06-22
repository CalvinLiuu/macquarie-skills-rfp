---
name: source-refresh
description: Ingest the SharePoint update-inbox folder, compare staged documents against the true-source knowledge set, and produce a source decision register that shows conflicts, user questions, approvals, and promotion decisions. Use this when new source material needs to update the trusted corpus.
allowed-tools:
  - sharepoint-knowledge/describe_sharepoint_structure
  - sharepoint-knowledge/sync_sharepoint_library
  - sharepoint-knowledge/prepare_source_refresh
  - sharepoint-knowledge/promote_source_refresh
  - sharepoint-knowledge/build_markdown_knowledge_base
  - read
  - edit
---

Use this skill whenever new source documents arrive.

Naming:

- Use `source decision register` for `data/outputs/source-decision-register.md`.
- Use `client-segment knowledge pack` for consolidated approved content under `data/truth-source/markdown/client-segments/<segment>/`.
- Use `domain knowledge pack` for consolidated approved content under `data/truth-source/markdown/domains/`.
- Do not describe the source decision register as the place where documents are consolidated. It records decisions; the knowledge packs hold reusable content.

User-visible process:

1. Tell the user the `source-refresh` skill is active.
2. Name the source folder or repository path being reviewed.
3. Explain that staged content in `update_inbox` is not trusted until the user approves it.
4. Explain that conflicts and approvals will be recorded in `data/outputs/source-decision-register.md`.
5. Explain that approved content will be rebuilt into trusted knowledge packs under `data/truth-source/markdown/`.
6. Before promotion, ask the user direct questions for conflicts, unclear ownership, or high-risk facts.
7. Finish with a summary of approved changes, unresolved decisions, rebuilt packs, and downstream RFP impact.

Workflow:

1. Confirm the configured SharePoint structure with `describe_sharepoint_structure`.
2. Sync both `true_source` and `update_inbox`.
3. Build staged Markdown views if the new material needs better structure before review.
4. Preserve document typing so staged RFPs, Macquarie documents, and competitor brochures stay in separate lanes.
5. Use `prepare_source_refresh` to compare staged documents with the trusted source set.
6. Write or update `data/outputs/source-decision-register.md` with source inventory, conflicts, user questions, approval decisions, rejected or superseded claims, and downstream impact.
7. Treat the refresh report and source decision register as the decision surface for human owners.
8. After approval, use `promote_source_refresh` to move reviewed candidates into the local true-source corpus.
9. Rebuild trusted Markdown knowledge packs so approved content appears in the correct domain and client-segment packs.
10. Do not assume staged material is ready for drafting just because it exists in SharePoint.
