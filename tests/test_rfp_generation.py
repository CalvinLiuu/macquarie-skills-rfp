from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from rfp_copilot.corpus import CorpusStore
from rfp_copilot.models import EvidenceRecord
from rfp_copilot.rfp_generation import generate_rfp_response_run


class RfpGenerationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.corpus_dir = self.temp_dir / "truth-source"
        self.corpus = CorpusStore(self.corpus_dir)
        self.corpus.upsert(
            EvidenceRecord(
                document_id="hosting-1",
                source_url="https://example.com/hosting",
                source_library="Bid Knowledge Library",
                title="Enterprise Sovereign Hosting",
                owner="Platform",
                effective_date="2026-01-01",
                review_date="2026-12-31",
                classification="internal",
                approved_for_bids=True,
                version="1",
                text_chunks=[
                    "Australian sovereign hosting is available for enterprise customers with "
                    "data residency controls and security monitoring."
                ],
                domains=["sovereignty", "security"],
                client_segments=["enterprise"],
            )
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)

    def test_generate_rfp_response_writes_run_folder_artifacts(self) -> None:
        bid_pack = self.temp_dir / "bid-pack"
        bid_pack.mkdir()
        primary_rfp = bid_pack / "acme-rfp.md"
        primary_rfp.write_text(
            """
            # Acme Bank Data Centre RFP

            Submission deadline: 30 June 2026

            1. Describe your sovereign hosting and data residency controls.
            2. Provide the required attachments for key personnel and case studies.
            """,
            encoding="utf-8",
        )
        customer_context = bid_pack / "company-info.md"
        customer_context.write_text(
            "Acme Bank is an enterprise financial services customer focused on Australian data residency.",
            encoding="utf-8",
        )
        brief_path = self.temp_dir / "bid-brief.json"
        brief_path.write_text(
            json.dumps(
                {
                    "company_name": "Acme Bank",
                    "run_date": "2026-06-24",
                    "rfp_input_path": str(bid_pack),
                    "primary_rfp_path": "acme-rfp.md",
                    "truth_source_corpus_dir": str(self.corpus_dir),
                    "output_root": str(self.temp_dir / "outputs" / "rfp-response-runs"),
                    "target_client_segments": ["enterprise"],
                    "customer_context": {"sector": "financial services"},
                    "win_themes": ["Australian data residency"],
                    "mandatory_attachments": ["pricing schedule"],
                    "human_reviewers": ["Bid Manager"],
                    "requested_package_formats": ["json", "csv"],
                }
            ),
            encoding="utf-8",
        )

        result = generate_rfp_response_run(brief_path)

        self.assertEqual(result.run_id, "2026-06-24-acme-bank")
        run_dir = Path(result.run_dir)
        expected_files = {
            "bid-brief.normalized.json",
            "structured-rfp.md",
            "response-index.md",
            "answer-contracts.json",
            "draft-answers.md",
            "draft-answers.json",
            "draft-answers.csv",
            "human-review-actions.md",
            "run-record.md",
        }
        self.assertTrue(expected_files.issubset({path.name for path in run_dir.iterdir()}))

        normalized = json.loads((run_dir / "bid-brief.normalized.json").read_text(encoding="utf-8"))
        self.assertEqual(
            normalized["customer_context_status"],
            "bid-context-input-not-approved-evidence",
        )
        self.assertIn(str(customer_context), normalized["bid_pack_context_files"])

        run_record = (run_dir / "run-record.md").read_text(encoding="utf-8")
        self.assertIn("- Update inbox touched: No", run_record)
        self.assertIn("- Source consolidation or promotion performed: No", run_record)
        self.assertIn("hosting-1", run_record)

        draft_answers = (run_dir / "draft-answers.md").read_text(encoding="utf-8")
        self.assertIn("pricing schedule", draft_answers)
        self.assertIn("Customer-specific bid context influenced retrieval", draft_answers)

    def test_folder_input_requires_primary_when_ambiguous(self) -> None:
        bid_pack = self.temp_dir / "ambiguous-bid-pack"
        bid_pack.mkdir()
        (bid_pack / "one-rfp.md").write_text("1. Describe hosting.", encoding="utf-8")
        (bid_pack / "two-rfp.md").write_text("1. Describe security.", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "primary_rfp_path"):
            generate_rfp_response_run(
                bid_brief={
                    "company_name": "Acme Bank",
                    "run_date": "2026-06-24",
                    "rfp_input_path": str(bid_pack),
                    "truth_source_corpus_dir": str(self.corpus_dir),
                    "output_root": str(self.temp_dir / "outputs"),
                }
            )


if __name__ == "__main__":
    unittest.main()
