---
name: mark-successful-rfp-document-information
description: Business action for identifying successful RFP material in SharePoint, marking the relevant documents as successful evidence, and routing them into the right segment knowledge lane.
allowed-tools:
  - sharepoint-knowledge/describe_sharepoint_structure
  - sharepoint-knowledge/sync_sharepoint_library
  - sharepoint-knowledge/build_markdown_knowledge_base
  - sharepoint-knowledge/plan_document_analysis
  - read
  - edit
---

Use this business action when a previous RFP or response has been confirmed as successful and should become reusable evidence.

Sub-skills to run:

1. `documentation-normalization`
2. `document-routing`
3. `evidence-retrieval`
4. `human-guidance-gate`

Workflow:

1. Run `describe_sharepoint_structure` to confirm the segment folders exist for `enterprise`, `hyperscaler`, `small_business`, and `government`.
2. Sync the `truth_source` folder so the latest SharePoint state is mirrored locally.
3. Confirm the document is in the correct segment folder under `Previous RFP` or `Successful RFPs`.
4. Build the Markdown knowledge base so the document appears in document-type, domain, and segment packs.
5. Run `plan_document_analysis` to route the document to `rfp-requirements-analyst`.
6. Keep the source path, approval status, owner, and segment visible for human review.
