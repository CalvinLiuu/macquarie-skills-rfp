---
name: documentation-normalization
description: Convert SharePoint source files and RFP inputs into structured Markdown, grouped into domain and client-segment knowledge packs such as government/security or enterprise/power. Use this when raw source material needs to be normalized before retrieval or drafting.
allowed-tools:
  - sharepoint-knowledge/sync_sharepoint_library
  - sharepoint-knowledge/build_markdown_knowledge_base
  - sharepoint-knowledge/render_rfp_markdown
  - read
  - edit
---

Use this skill before evidence retrieval whenever the source material is still in mixed formats such as PDF, DOCX, spreadsheets, or loose markdown.

Workflow:

1. Sync the `true_source` folder first.
2. Convert the mirrored documents into structured Markdown with `build_markdown_knowledge_base`.
3. Ensure the output creates:
   - one normalized Markdown file per source document
   - one domain pack per topic such as `security`, `compliance`, `sovereignty`, `power`, and `cooling`
   - one client-segment pack per segment/domain combination such as `government/security`
   - a Markdown index that makes those packs easy to navigate
4. Convert the RFP itself into Markdown with `render_rfp_markdown`.
5. Preserve question relationships by keeping related domains, related client segments, related questions, and suggested evidence packs visible.

The goal is not just format conversion. The Markdown should be structured so later agents can extract facts quickly and safely.

