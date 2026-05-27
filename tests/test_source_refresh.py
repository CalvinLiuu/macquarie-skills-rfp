from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from rfp_copilot.models import EvidenceRecord
from rfp_copilot.sharepoint_graph import SyncConfig
from rfp_copilot.source_refresh import SourceRefreshService


class SourceRefreshTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config = SyncConfig(
            tenant_id="tenant",
            client_id="client",
            client_secret="secret",
            site_id="site",
            drive_id="drive",
            source_library="Library",
            state_dir=self.temp_dir / "state",
            truth_source_corpus_dir=self.temp_dir / "truth-source",
            update_inbox_corpus_dir=self.temp_dir / "update-inbox",
            truth_source_folder="Knowledge/True Source",
            update_inbox_folder="Knowledge/Update Inbox",
        )
        self.service = SourceRefreshService(self.config)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)

    def test_build_refresh_plan_detects_add_candidate(self) -> None:
        self.service.update_inbox.corpus.upsert(
            EvidenceRecord(
                document_id="upd-1",
                source_url="https://example.com/upd-1",
                source_library="Library",
                title="Government Security Controls",
                owner="Security",
                effective_date="2026-01-01",
                review_date="2026-12-31",
                classification="internal",
                approved_for_bids=True,
                version="2",
                text_chunks=["Government security controls align to ISO 27001 and IRAP expectations."],
                domains=["security"],
                client_segments=["government"],
                source_collection="update_inbox",
                source_path="Knowledge/Update Inbox/government/security/Government Security Controls.md",
            )
        )

        result = self.service.build_refresh_plan(output_dir=self.temp_dir / "outputs")

        self.assertEqual(len(result.candidates), 1)
        self.assertEqual(result.candidates[0].proposed_action, "add")
        self.assertTrue(Path(result.report_path).exists())
        self.assertTrue(result.candidates[0].human_guidance_required)

    def test_promote_candidates_updates_truth_source_for_low_risk_add(self) -> None:
        self.service.update_inbox.corpus.upsert(
            EvidenceRecord(
                document_id="upd-2",
                source_url="https://example.com/upd-2",
                source_library="Library",
                title="Enterprise Cooling Standards",
                owner="Facilities",
                effective_date="2026-01-01",
                review_date="2026-12-31",
                classification="internal",
                approved_for_bids=True,
                version="1",
                text_chunks=["Cooling redundancy includes N+1 chiller support for enterprise workloads."],
                domains=["cooling"],
                client_segments=["enterprise"],
                source_collection="update_inbox",
                source_path="Knowledge/Update Inbox/enterprise/cooling/Enterprise Cooling Standards.md",
            )
        )

        result = self.service.promote_candidates(
            ["refresh-upd-2"],
            output_dir=self.temp_dir / "outputs",
        )

        self.assertEqual(result.promoted, 1)
        self.assertIsNotNone(self.service.truth_source.corpus.get("truth-upd-2"))


if __name__ == "__main__":
    unittest.main()
