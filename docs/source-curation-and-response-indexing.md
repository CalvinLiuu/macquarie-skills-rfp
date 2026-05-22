# Source Curation And Response Indexing

## Operating Model

The repository assumes two SharePoint folders:

1. `true source`
   The trusted knowledge base used for retrieval and drafting.
2. `update inbox`
   New material that must be normalized, compared, and reviewed before it joins the trusted set.

## Source Curation

The curation flow is:

1. Sync `update inbox`.
2. Normalize staged documents into Markdown.
3. Compare staged documents to `true source`.
4. Produce a refresh report with explicit human-review requirements.

This is intentionally conservative. Staged content should not become trusted drafting material without review.

## Response Indexing

The response index is built before drafting and should answer:

- Which client segment does this RFP most closely target?
- Which knowledge domains are relevant for each question?
- What response format is expected for each question?
- Which knowledge packs should the answer use?
- Where does a human owner need to approve, clarify, or supply artifacts?

## Human Guidance Triggers

Human guidance should be explicit when:

- the source document is not marked approved for bids
- the staged source overlaps ambiguously with trusted content
- the question requires pricing, legal, or contractual commitments
- the question is government-sensitive
- the question needs named attachments such as CVs or case studies
