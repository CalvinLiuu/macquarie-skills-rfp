---
name: answer-drafting
description: Draft question-by-question RFP responses using only approved evidence and explicit citations. Use this when enough source material has been gathered and the task is to produce the first response draft.
allowed-tools:
  - sharepoint-knowledge/create_answer_contract
  - sharepoint-knowledge/search_evidence_corpus
  - read
  - edit
---

Use this skill only after response indexing and evidence retrieval.

Workflow:

1. Start from `create_answer_contract` so every answer uses the repository contract.
2. Follow the expected response format from the response index before rewriting into customer-facing prose.
3. Keep claims scoped to what the cited material supports.
4. Maintain explicit citations and a confidence level.
5. If the question has a human-guidance flag, preserve that review requirement in the answer output.
6. If the question is commercial, legal, or privacy-sensitive, prefer a partial answer plus a follow-up rather than overcommitting.
7. If the question requests attachments, populate `required_attachments[]`.

The answer should be useful, but still obviously reviewable by a human bid manager.
