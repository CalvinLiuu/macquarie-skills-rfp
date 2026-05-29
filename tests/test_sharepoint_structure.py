from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from rfp_copilot.sharepoint_structure import (
    build_sharepoint_folder_roles,
    build_sharepoint_structure_plan,
    match_sharepoint_folder_role,
)


class SharePointStructureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.structure = {
            "client_segment_root": "RFP Knowledge/Client Segments",
            "general_documents_root": "RFP Knowledge/Documents",
        }

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)

    def test_build_sharepoint_folder_roles_includes_segment_and_general_folders(self) -> None:
        roles = build_sharepoint_folder_roles(self.structure)

        self.assertEqual(len(roles), 15)
        role_names = {role.role for role in roles}
        segments = {role.client_segment for role in roles if role.client_segment}
        self.assertIn("previous_rfps", role_names)
        self.assertIn("successful_rfps", role_names)
        self.assertIn("successful_current_info", role_names)
        self.assertIn("infrastructure_changes", role_names)
        self.assertIn("enterprise", segments)
        self.assertIn("small_business", segments)

    def test_match_sharepoint_folder_role_prefers_successful_rfp_segment_folder(self) -> None:
        role = match_sharepoint_folder_role(
            self.structure,
            "RFP Knowledge/Client Segments/Enterprise/Successful RFPs/winning-response.md",
        )

        self.assertIsNotNone(role)
        assert role is not None
        self.assertEqual(role.role, "successful_rfps")
        self.assertEqual(role.client_segment, "enterprise")
        self.assertEqual(role.document_type, "rfp")
        self.assertEqual(role.business_action, "mark_successful_rfp_document_information")

    def test_build_sharepoint_structure_plan_writes_report_and_manifest(self) -> None:
        result = build_sharepoint_structure_plan(
            self.structure,
            output_dir=self.temp_dir / "outputs",
        )

        self.assertEqual(len(result.folder_roles), 15)
        self.assertTrue(Path(result.report_path).exists())
        self.assertTrue(Path(result.manifest_path).exists())


if __name__ == "__main__":
    unittest.main()
