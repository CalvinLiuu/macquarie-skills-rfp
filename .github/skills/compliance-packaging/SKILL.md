---
name: compliance-packaging
description: Package structured RFP answers into markdown, JSON, or CSV while preserving citations, confidence, gaps, and required attachments. Use this when the answer set is ready to be assembled into an output deliverable.
allowed-tools:
  - sharepoint-knowledge/package_answers
  - read
  - edit
---

Use this skill at the end of the workflow.

Workflow:

1. Confirm every answer still follows the repository contract.
2. Package the answer set into the requested format with `package_answers`.
3. Keep gaps, follow-ups, attachment requirements, and human-review flags visible in the output.
4. If the user asks for a submission-ready pack, state clearly which parts still need human review or non-model inputs.

Do not drop low-confidence warnings just to make the output look complete.
