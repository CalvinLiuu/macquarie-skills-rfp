from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from rfp_copilot.answering import draft_answers_for_bid, package_answers
from rfp_copilot.corpus import CorpusStore
from rfp_copilot.models import BidRequest, EvidenceRecord, Question


class AnsweringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.corpus = CorpusStore(self.temp_dir)
        self.corpus.upsert(
            EvidenceRecord(
                document_id="doc-1",
                source_url="https://example.com/hosting",
                source_library="Library",
                title="Hosting Capability",
                owner="Operations",
                effective_date="2026-01-01",
                review_date="2026-12-31",
                classification="internal",
                approved_for_bids=True,
                version="1",
                text_chunks=[
                    "Australian sovereign hosting is available with dual Sydney availability zones."
                ],
            )
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)

    def test_draft_answers_returns_contract(self) -> None:
        bid = BidRequest(
            source_path="demo.md",
            title="Demo",
            questions=[Question(question_id="Q001", question_text="Describe your sovereign hosting.")],
        )

        answers = draft_answers_for_bid(bid, self.corpus)

        self.assertEqual(len(answers), 1)
        self.assertEqual(answers[0].question_id, "Q001")
        self.assertEqual(answers[0].confidence, "medium")
        self.assertEqual(len(answers[0].citations), 1)

    def test_package_answers_renders_markdown(self) -> None:
        bid = BidRequest(
            source_path="demo.md",
            title="Demo",
            questions=[Question(question_id="Q001", question_text="Describe your sovereign hosting.")],
        )

        answers = draft_answers_for_bid(bid, self.corpus)
        markdown = package_answers(answers, output_format="markdown")

        self.assertIn("# RFP Draft Answers", markdown)
        self.assertIn("Q001", markdown)


if __name__ == "__main__":
    unittest.main()
