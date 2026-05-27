from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from rfp_copilot.corpus import CorpusStore
from rfp_copilot.document_analysis import build_document_analysis_plan
from rfp_copilot.models import EvidenceRecord


class DocumentAnalysisTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.corpus = CorpusStore(self.temp_dir / "mirror")

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)

    def test_build_document_analysis_plan_groups_records_by_specialist_lane(self) -> None:
        self.corpus.upsert(
            EvidenceRecord(
                document_id="doc-rfp",
                source_url="https://example.com/rfp",
                source_library="Library",
                title="Macquarie RFP Questionnaire",
                owner="Bid Team",
                effective_date="2026-01-01",
                review_date="2026-12-31",
                classification="internal",
                approved_for_bids=False,
                version="1",
                text_chunks=["This request for proposal asks suppliers to explain service transition and controls."],
                source_collection="update_inbox",
                source_path="incoming/rfp/macquarie-rfp-questionnaire.docx",
            )
        )
        self.corpus.upsert(
            EvidenceRecord(
                document_id="doc-competitor",
                source_url="https://example.com/competitor",
                source_library="Library",
                title="Acme Competitor Brochure",
                owner="Strategy",
                effective_date="2026-01-01",
                review_date="2026-12-31",
                classification="internal",
                approved_for_bids=True,
                version="1",
                text_chunks=["Competitor brochure with service overview and capability statements."],
                source_collection="truth_source",
                source_path="market/competitor/acme-competitor-brochure.pdf",
            )
        )

        result = build_document_analysis_plan(self.corpus, output_dir=self.temp_dir / "outputs")

        self.assertEqual(len(result.assignments), 2)
        assignments_by_type = {item.document_type: item for item in result.assignments}
        self.assertIn("rfp", assignments_by_type)
        self.assertIn("competitor_brochure", assignments_by_type)
        self.assertEqual(
            assignments_by_type["rfp"].specialist_agent,
            "rfp-requirements-analyst",
        )
        self.assertEqual(
            assignments_by_type["competitor_brochure"].specialist_agent,
            "competitor-brochure-analyst",
        )
        self.assertTrue(Path(result.report_path).exists())
        self.assertTrue(Path(result.manifest_path).exists())


if __name__ == "__main__":
    unittest.main()
