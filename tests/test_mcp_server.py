from __future__ import annotations

import unittest

from rfp_copilot.mcp_server import _call_tool


class McpServerTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
