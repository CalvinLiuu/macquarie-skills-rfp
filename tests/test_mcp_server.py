from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from rfp_copilot.corpus import CorpusStore
from rfp_copilot.mcp_server import _call_tool
from rfp_copilot.models import EvidenceRecord


class McpServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)

    def test_extract_rfp_questions_tool(self) -> None:
        result = _call_tool(
            "extract_rfp_questions",
            {
                "text": "1. Describe your hosting approach.\n2. Outline your security controls.",
                "title": "Inline RFP",
            },
        )

        self.assertEqual(result["title"], "Inline RFP")
        self.assertEqual(len(result["questions"]), 2)
        self.assertEqual(result["questions"][0]["question_id"], "Q001")

    def test_plan_document_analysis_tool(self) -> None:
        corpus = CorpusStore(self.temp_dir / "corpus")
        corpus.upsert(
            EvidenceRecord(
                document_id="doc-1",
                source_url="https://example.com/rfp",
                source_library="Library",
                title="Request for Proposal",
                owner="Bid Team",
                effective_date="2026-01-01",
                review_date="2026-12-31",
                classification="internal",
                approved_for_bids=False,
                version="1",
                text_chunks=["This request for proposal requires a transition plan."],
                source_collection="update_inbox",
                source_path="incoming/rfp/request-for-proposal.docx",
            )
        )

        result = _call_tool(
            "plan_document_analysis",
            {
                "corpus_dir": str(self.temp_dir / "corpus"),
                "output_dir": str(self.temp_dir / "outputs"),
            },
        )

        self.assertEqual(len(result["assignments"]), 1)
        self.assertEqual(result["assignments"][0]["document_type"], "rfp")


if __name__ == "__main__":
    unittest.main()
