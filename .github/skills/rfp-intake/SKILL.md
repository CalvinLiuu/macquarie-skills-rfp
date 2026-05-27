---
name: rfp-intake
description: Parse an RFP or bid pack into discrete questions, deadlines, deliverables, client segments, and likely question types. Use this when the user provides a tender, questionnaire, or bid request that needs to be structured before drafting.
allowed-tools:
  - sharepoint-knowledge/extract_rfp_questions
  - sharepoint-knowledge/render_rfp_markdown
  - sharepoint-knowledge/build_response_index
  - read
---

When the task starts with a raw RFP, do the intake step first.

Workflow:

1. Use `extract_rfp_questions` with the RFP file path or raw text.
2. Confirm the parsed question count, deadlines, deliverables, target client segments, and related domains.
3. Preserve the returned `question_id` values through the whole workflow.
4. If the parser misses questionnaire rows or attachment requests, supplement them manually and say that you did so.
5. Produce the structured Markdown and response index before drafting begins.

Do not draft final customer prose in this skill. The goal is a clean intake structure that later skills can trust.

