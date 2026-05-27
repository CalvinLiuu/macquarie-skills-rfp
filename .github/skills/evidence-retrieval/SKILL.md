---
name: evidence-retrieval
description: Retrieve approved bid evidence from the true-source SharePoint corpus and optionally search SharePoint live for fresh material. Use this when an RFP question needs supporting source material and citations.
allowed-tools:
  - sharepoint-knowledge/search_evidence_corpus
  - sharepoint-knowledge/get_evidence_record
  - sharepoint-knowledge/search_sharepoint_live
  - sharepoint-knowledge/sync_sharepoint_library
---

Use this skill after RFP intake and response indexing.

Workflow:

1. Search the true-source mirrored corpus first with `search_evidence_corpus`.
2. Prefer approved evidence with strong overlap to the question language, client segment, and domain.
3. Open the returned evidence records when you need metadata, ownership, dates, or exact excerpts.
4. Prefer client-segment packs when the RFP clearly targets `hyperscaler`, `startup`, `enterprise`, or `government`.
5. If mirrored evidence is missing or obviously stale, use `search_sharepoint_live`.
6. Label live SharePoint findings as unconfirmed unless they are already mirrored and approved.
7. If multiple sources disagree, stop and mark the issue for `gap-and-risk-check`.

Never invent a citation. If a claim cannot be tied back to an evidence record, treat it as a gap.

