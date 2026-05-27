---
name: source-refresh
description: Ingest the SharePoint update-inbox folder, compare staged documents against the true-source knowledge set, and produce a refresh plan that shows where human approval is required. Use this when new source material needs to update the trusted corpus.
allowed-tools:
  - sharepoint-knowledge/sync_sharepoint_library
  - sharepoint-knowledge/prepare_source_refresh
  - sharepoint-knowledge/promote_source_refresh
  - sharepoint-knowledge/build_markdown_knowledge_base
  - read
---

Use this skill whenever new source documents arrive.

Workflow:

1. Sync both `true_source` and `update_inbox`.
2. Build staged Markdown views if the new material needs better structure before review.
3. Preserve document typing so staged RFPs, Macquarie documents, and competitor brochures stay in separate lanes.
4. Use `prepare_source_refresh` to compare staged documents with the trusted source set.
5. Treat the refresh report as the decision surface for human owners.
6. After approval, use `promote_source_refresh` to move reviewed candidates into the local true-source corpus.
7. Do not assume staged material is ready for drafting just because it exists in SharePoint.
