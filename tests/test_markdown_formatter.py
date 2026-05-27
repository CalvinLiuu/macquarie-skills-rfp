from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from rfp_copilot.corpus import CorpusStore
from rfp_copilot.markdown_formatter import build_markdown_knowledge_base, render_rfp_markdown
from rfp_copilot.models import BidRequest, EvidenceRecord, Question
from rfp_copilot.taxonomy import enrich_question_relationships


class MarkdownFormatterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.corpus = CorpusStore(self.temp_dir / "mirror")

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)

    def test_build_markdown_knowledge_base_writes_document_and_domain_pack(self) -> None:
        self.corpus.upsert(
            EvidenceRecord(
                document_id="doc-1",
                source_url="https://example.com/security",
                source_library="Library",
                title="Security and Sovereignty",
                owner="Risk",
                effective_date="2026-01-01",
                review_date="2026-12-31",
                classification="internal",
                approved_for_bids=True,
                version="1",
                text_chunks=[
                    "Our security controls include ISO 27001 certification.",
                    "Australian sovereign hosting keeps workloads onshore in Sydney.",
                ],
            )
        )

        result = build_markdown_knowledge_base(self.corpus)

        self.assertEqual(result.documents_written, 1)
        self.assertEqual(result.domain_packs_written, 2)
        self.assertEqual(result.client_segment_packs_written, 3)
        self.assertEqual(result.document_type_packs_written, 1)
        document_path = self.temp_dir / "mirror" / "markdown" / "documents" / "doc-1-security-and-sovereignty.md"
        security_pack = self.temp_dir / "mirror" / "markdown" / "domains" / "security.md"
        sovereignty_pack = self.temp_dir / "mirror" / "markdown" / "domains" / "sovereignty.md"
        general_segment_pack = self.temp_dir / "mirror" / "markdown" / "client-segments" / "general" / "security.md"
        document_type_pack = self.temp_dir / "mirror" / "markdown" / "document-types" / "general_knowledge.md"
        self.assertTrue(document_path.exists())
        self.assertTrue(security_pack.exists())
        self.assertTrue(sovereignty_pack.exists())
        self.assertTrue(general_segment_pack.exists())
        self.assertTrue(document_type_pack.exists())
        self.assertIn("Structured Evidence", document_path.read_text(encoding="utf-8"))
        self.assertIn("specialist_agent", document_path.read_text(encoding="utf-8"))

    def test_render_rfp_markdown_includes_question_relationships(self) -> None:
        questions = [
            Question(question_id="Q001", question_text="Describe sovereign hosting controls."),
            Question(question_id="Q002", question_text="Explain security controls for sovereign hosting."),
        ]
        enrich_question_relationships(questions)
        bid = BidRequest(
            source_path="demo.md",
            title="Demo RFP",
            questions=questions,
            deadlines=["30 June 2026"],
            deliverables=["Key personnel CVs"],
        )

        markdown = render_rfp_markdown(bid)

        self.assertIn("sovereignty", markdown)
        self.assertIn("Related questions: Q002", markdown)
        self.assertIn("domains/sovereignty.md", markdown)
        self.assertIn("Expected response format: narrative", markdown)


if __name__ == "__main__":
    unittest.main()
