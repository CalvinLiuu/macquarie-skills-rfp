from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from rfp_copilot.corpus import CorpusStore, chunk_text
from rfp_copilot.models import EvidenceRecord


class CorpusStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.corpus = CorpusStore(self.temp_dir)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)

    def test_upsert_and_search_prefers_overlap(self) -> None:
        self.corpus.upsert(
            EvidenceRecord(
                document_id="doc-1",
                source_url="https://example.com/doc-1",
                source_library="Library",
                title="Security Controls",
                owner="Alice",
                effective_date="2026-01-01",
                review_date="2026-12-31",
                classification="internal",
                approved_for_bids=True,
                version="1",
                text_chunks=["We maintain ISO 27001 certification and annual control audits."],
            )
        )
        self.corpus.upsert(
            EvidenceRecord(
                document_id="doc-2",
                source_url="https://example.com/doc-2",
                source_library="Library",
                title="Hosting Overview",
                owner="Bob",
                effective_date="2026-01-01",
                review_date="2026-12-31",
                classification="internal",
                approved_for_bids=True,
                version="1",
                text_chunks=["Australian sovereign hosting is available in two Sydney data centres."],
            )
        )

        hits = self.corpus.search("ISO 27001 controls", limit=2)

        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].record.document_id, "doc-1")

    def test_chunk_text_breaks_long_content(self) -> None:
        text = "word " * 700
        chunks = chunk_text(text, max_chars=300)
        self.assertGreater(len(chunks), 1)

    def test_search_can_filter_by_document_type(self) -> None:
        self.corpus.upsert(
            EvidenceRecord(
                document_id="doc-3",
                source_url="https://example.com/doc-3",
                source_library="Library",
                title="Competitor Brochure",
                owner="Strategy",
                effective_date="2026-01-01",
                review_date="2026-12-31",
                classification="internal",
                approved_for_bids=True,
                version="1",
                text_chunks=["Competitor brochure covering sovereign hosting and security controls."],
                document_type="competitor_brochure",
                specialist_agent="competitor-brochure-analyst",
            )
        )

        hits = self.corpus.search(
            "sovereign hosting security",
            limit=5,
            document_types=["competitor_brochure"],
        )

        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].record.document_id, "doc-3")


if __name__ == "__main__":
    unittest.main()
