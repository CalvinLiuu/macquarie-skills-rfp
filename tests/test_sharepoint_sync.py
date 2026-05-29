from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from rfp_copilot.sharepoint_graph import SharePointSyncService, SyncConfig


class FakeGraphClient:
    def __init__(self) -> None:
        self.pages = [
            {
                "value": [
                    {
                        "id": "doc-1",
                        "name": "security.md",
                "webUrl": "https://example.com/security",
                "eTag": "v1",
                "createdDateTime": "2026-01-01T00:00:00Z",
                "lastModifiedBy": {"user": {"displayName": "Alice"}},
                "parentReference": {"path": "/drives/drive/root:/RFP Knowledge/Curated Inputs"},
                    }
                ],
                "@odata.deltaLink": "delta-token-1",
            }
        ]

    def get_delta_page(self, site_id: str, drive_id: str, delta_link: str = "") -> dict:
        _ = (site_id, drive_id, delta_link)
        return self.pages[0]

    def download_drive_item(self, drive_id: str, item_id: str) -> bytes:
        _ = (drive_id, item_id)
        return b"# Security\n\nISO 27001 certified controls."

    def get_item_fields(self, drive_id: str, item_id: str) -> dict:
        _ = (drive_id, item_id)
        return {
            "ApprovedForBids": True,
            "DocumentOwner": "Security Team",
            "Classification": "internal",
            "EffectiveDate": "2026-01-01",
            "ReviewDate": "2026-12-31",
            "DocumentType": "Macquarie Guideline",
        }

    def search_drive_items(self, query: str, limit: int = 5, region: str = "") -> list[dict]:
        _ = (query, limit, region)
        return [{"id": "doc-1", "name": "security.md", "webUrl": "https://example.com/security"}]


class SegmentFolderGraphClient(FakeGraphClient):
    def __init__(self) -> None:
        super().__init__()
        self.pages[0]["value"][0]["name"] = "winning-response.md"
        self.pages[0]["value"][0]["parentReference"] = {
            "path": "/drives/drive/root:/RFP Knowledge/Client Segments/Enterprise/Successful RFPs"
        }

    def get_item_fields(self, drive_id: str, item_id: str) -> dict:
        fields = super().get_item_fields(drive_id, item_id)
        fields.pop("DocumentType", None)
        return fields


class SharePointSyncTests(unittest.TestCase):
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
            truth_source_folder="RFP Knowledge/Curated Inputs",
            update_inbox_folder="RFP Knowledge/Incoming Updates",
            allowed_extensions=[".md"],
            metadata_fields={
                "approved_for_bids": "ApprovedForBids",
                "owner": "DocumentOwner",
                "effective_date": "EffectiveDate",
                "review_date": "ReviewDate",
                "classification": "Classification",
                "document_type": "DocumentType",
            },
            approved_default=False,
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)

    def test_sync_writes_record_and_state(self) -> None:
        service = SharePointSyncService(self.config, client=FakeGraphClient())

        result = service.sync()
        record = service.corpus.get("doc-1")

        self.assertEqual(result.synced, 1)
        self.assertEqual(result.markdown_documents, 1)
        self.assertEqual(result.markdown_packs, 1)
        self.assertEqual(result.client_segment_packs, 2)
        self.assertEqual(result.document_type_packs, 1)
        self.assertEqual(result.delta_link, "delta-token-1")
        self.assertIsNotNone(record)
        assert record is not None
        self.assertTrue(record.approved_for_bids)
        self.assertEqual(record.owner, "Security Team")
        self.assertEqual(record.document_type, "macquarie_guideline")
        self.assertEqual(record.specialist_agent, "macquarie-guideline-analyst")
        self.assertTrue(Path(record.markdown_path).exists())

    def test_source_folder_scope_is_respected(self) -> None:
        service = SharePointSyncService(self.config, client=FakeGraphClient())

        result = service.sync()

        self.assertEqual(result.synced, 1)
        self.assertIsNotNone(service.corpus.get("doc-1"))

    def test_live_search_marks_unapproved_results(self) -> None:
        service = SharePointSyncService(self.config, client=FakeGraphClient())

        hits = service.search_live("security")

        self.assertEqual(len(hits), 1)
        self.assertFalse(hits[0]["approved_for_use"])
        self.assertIn("discovery-only", hits[0]["warning"])

    def test_sync_tags_record_from_configured_successful_rfp_folder(self) -> None:
        config = SyncConfig(
            tenant_id="tenant",
            client_id="client",
            client_secret="secret",
            site_id="site",
            drive_id="drive",
            source_library="Library",
            state_dir=self.temp_dir / "state",
            truth_source_corpus_dir=self.temp_dir / "truth-source",
            update_inbox_corpus_dir=self.temp_dir / "update-inbox",
            truth_source_folder="RFP Knowledge/Client Segments",
            update_inbox_folder="RFP Knowledge/Incoming Updates",
            allowed_extensions=[".md"],
            metadata_fields=self.config.metadata_fields,
            sharepoint_structure={
                "client_segment_root": "RFP Knowledge/Client Segments",
                "general_documents_root": "RFP Knowledge/Documents",
            },
            approved_default=False,
        )
        service = SharePointSyncService(config, client=SegmentFolderGraphClient())

        service.sync()
        record = service.corpus.get("doc-1")

        self.assertIsNotNone(record)
        assert record is not None
        self.assertEqual(record.document_type, "rfp")
        self.assertIn("enterprise", record.client_segments)
        self.assertEqual(record.metadata["sharepoint_folder_role"]["role"], "successful_rfps")


if __name__ == "__main__":
    unittest.main()
