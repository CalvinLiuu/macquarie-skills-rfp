from __future__ import annotations

import shutil
import tempfile
import unittest
import json
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

    def test_describe_sharepoint_structure_tool(self) -> None:
        config_path = self.temp_dir / "knowledge-source.json"
        config_path.write_text(
            json.dumps(
                {
                    "tenant_id": "tenant",
                    "client_id": "client",
                    "client_secret": "secret",
                    "site_id": "site",
                    "drive_id": "drive",
                    "source_library": "Library",
                    "sharepoint_structure": {
                        "client_segment_root": "RFP Knowledge/Client Segments",
                        "general_documents_root": "RFP Knowledge/Documents",
                    },
                }
            ),
            encoding="utf-8",
        )

        result = _call_tool(
            "describe_sharepoint_structure",
            {
                "config_path": str(config_path),
                "output_dir": str(self.temp_dir / "outputs"),
            },
        )

        self.assertEqual(len(result["folder_roles"]), 15)
        self.assertTrue(Path(result["report_path"]).exists())

    def test_generate_rfp_response_tool(self) -> None:
        corpus = CorpusStore(self.temp_dir / "truth-source")
        corpus.upsert(
            EvidenceRecord(
                document_id="doc-1",
                source_url="https://example.com/security",
                source_library="Library",
                title="Security Controls",
                owner="Security",
                effective_date="2026-01-01",
                review_date="2026-12-31",
                classification="internal",
                approved_for_bids=True,
                version="1",
                text_chunks=["Security controls include monitored Australian hosting services."],
                domains=["security"],
                client_segments=["enterprise"],
            )
        )
        rfp_path = self.temp_dir / "rfp.md"
        rfp_path.write_text("1. Outline your security controls.", encoding="utf-8")

        result = _call_tool(
            "generate_rfp_response",
            {
                "bid_brief": {
                    "company_name": "Acme Bank",
                    "run_date": "2026-06-24",
                    "rfp_input_path": str(rfp_path),
                    "truth_source_corpus_dir": str(self.temp_dir / "truth-source"),
                    "output_root": str(self.temp_dir / "outputs"),
                    "target_client_segments": ["enterprise"],
                }
            },
        )

        self.assertEqual(result["run_id"], "2026-06-24-acme-bank")
        self.assertTrue(Path(result["artifacts"]["run-record.md"]).exists())


if __name__ == "__main__":
    unittest.main()
