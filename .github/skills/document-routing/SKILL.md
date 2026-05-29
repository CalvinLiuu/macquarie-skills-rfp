---
name: document-routing
description: Classify mirrored SharePoint documents into specialist analysis lanes and produce a document analysis plan that keeps RFPs, Macquarie context, and competitor collateral separated. Use this after normalization and before deeper document analysis or drafting.
allowed-tools:
  - sharepoint-knowledge/build_markdown_knowledge_base
  - sharepoint-knowledge/plan_document_analysis
  - read
---

Use this skill after SharePoint sync and Markdown normalization.

Workflow:

1. Confirm the configured SharePoint structure with `describe_sharepoint_structure`.
2. Confirm the mirrored documents have been normalized into structured Markdown.
3. Build the document analysis plan with `plan_document_analysis`.
4. Route each lane to its dedicated specialist:
   - `rfp` -> `rfp-requirements-analyst`
   - `macquarie_current_state` -> `macquarie-current-state-analyst`
   - `macquarie_implementation` -> `macquarie-implementation-analyst`
   - `macquarie_guideline` -> `macquarie-guideline-analyst`
   - `competitor_brochure` -> `competitor-brochure-analyst`
5. Keep the lane boundaries intact. Do not ask one specialist to reason over unrelated document types unless a human explicitly wants synthesis.
6. Use the resulting document-type packs when a specialist needs a condensed view of its assigned evidence.
