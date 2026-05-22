from __future__ import annotations

import unittest

from rfp_copilot.response_indexer import build_response_index_payload, render_response_index_markdown
from rfp_copilot.rfp_parser import parse_rfp_text


class ResponseIndexerTests(unittest.TestCase):
    def test_build_response_index_marks_human_guidance(self) -> None:
        bid = parse_rfp_text(
            """
            Government department RFP

            1. Describe your sovereign hosting controls.
            2. Provide the required attachments for key personnel and case studies.
            """,
            title="Government RFP",
        )

        payload = build_response_index_payload(bid)

        self.assertEqual(payload["question_count"], 2)
        self.assertEqual(payload["high_touch_count"], 2)
        self.assertIn("government", payload["target_client_segments"])

    def test_render_response_index_markdown_includes_formats(self) -> None:
        bid = parse_rfp_text("1. Provide the required attachments for key personnel.", title="Demo")

        markdown = render_response_index_markdown(bid)

        self.assertIn("Response format: attachment", markdown)
        self.assertIn("Human guidance: Yes", markdown)


if __name__ == "__main__":
    unittest.main()

