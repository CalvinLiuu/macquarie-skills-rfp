---
name: gap-and-risk-check
description: Check RFP answers for missing evidence, stale sources, conflicting material, unsupported claims, and required follow-up actions. Use this before packaging or submission review.
allowed-tools:
  - sharepoint-knowledge/search_evidence_corpus
  - sharepoint-knowledge/get_evidence_record
  - sharepoint-knowledge/build_response_index
  - read
---

Use this skill after drafting and before packaging.

Check for:

1. Questions with no citations or only one weak citation.
2. Sources that appear unapproved, stale, or ownerless.
3. Claims in the draft answer that are stronger than the evidence.
4. Conflicting evidence across versions or documents.
5. Missing attachments, next actions, or decision points that a human needs to resolve.
6. Questions already flagged for human guidance in the response index.

When you find a risk:

- Put the problem into `gaps[]` when it blocks a trustworthy answer.
- Put the next action into `followups[]`.
- Lower confidence rather than hiding uncertainty.

