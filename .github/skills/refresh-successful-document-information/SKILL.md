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

Naming:

- Record conflicts, user questions, approvals, and rejected or superseded claims in the source decision register at `data/outputs/source-decision-register.md`.
- Rebuild approved reusable content into trusted knowledge packs under `data/truth-source/markdown/`.
- Keep client-specific consolidated content in client-segment knowledge packs such as `data/truth-source/markdown/client-segments/enterprise/security.md`.

User-visible process:

1. Tell the user this business action is active.
2. Name the general documentation folder, segment folder, or SharePoint location being refreshed.
3. Explain which agents will review the material and why.
4. Explain that conflicting information will be converted into direct user questions before promotion.
5. Confirm that only approved decisions are promoted into trusted evidence.
6. Finish by naming the updated decision register and rebuilt knowledge packs.

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
4. Treat the refresh report and `data/outputs/source-decision-register.md` as the human decision surface.
5. After approval, use `promote_source_refresh` for approved candidates.
6. Rebuild the Markdown knowledge base and run `plan_document_analysis` so refreshed facts appear in the right segment and document-type packs.
