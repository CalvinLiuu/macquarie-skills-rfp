---
name: refresh-successful-document-information
description: Business action for refreshing successful up-to-date RFP information from new general documentation such as infrastructure, equipment, power, cooling, or centre changes.
allowed-tools:
  - sharepoint-knowledge/describe_sharepoint_structure
  - sharepoint-knowledge/sync_sharepoint_library
  - sharepoint-knowledge/prepare_source_refresh
  - sharepoint-knowledge/promote_source_refresh
  - sharepoint-knowledge/build_markdown_knowledge_base
  - sharepoint-knowledge/plan_document_analysis
  - read
  - edit
---

Use this business action when new general documentation should refresh the approved successful information used for future RFPs.

Sub-skills to run:

1. `source-refresh`
2. `documentation-normalization`
3. `document-routing`
4. `gap-and-risk-check`
5. `human-guidance-gate`

Workflow:

1. Run `describe_sharepoint_structure` to confirm the general document folders and segment `Successful Up To Date Information` folders are mapped.
2. Sync `truth_source` and `update_inbox`.
3. Use `prepare_source_refresh` to compare new infrastructure, equipment, and important-information documents against trusted successful information.
4. Treat the refresh report as the human decision surface.
5. After approval, use `promote_source_refresh` for approved candidates.
6. Rebuild the Markdown knowledge base and run `plan_document_analysis` so refreshed facts appear in the right segment and document-type packs.
