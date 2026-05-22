from __future__ import annotations

import unittest

from rfp_copilot.rfp_parser import extract_deadlines, extract_deliverables, parse_rfp_text


class RfpParserTests(unittest.TestCase):
    def test_parse_rfp_text_extracts_questions(self) -> None:
        payload = """
        Submission deadline: 30 June 2026

        1. Describe your sovereign hosting controls.
        2. Outline your information security certification status.

        Attachments required:
        - Key personnel CVs
        - Case studies
        """

        bid = parse_rfp_text(payload, title="Demo RFP")

        self.assertEqual(bid.title, "Demo RFP")
        self.assertEqual(len(bid.questions), 2)
        self.assertEqual(bid.questions[0].question_id, "Q001")
        self.assertEqual(bid.questions[1].question_type, "security")
        self.assertIn("sovereignty", bid.questions[0].related_domains)
        self.assertIn("security", bid.questions[1].related_domains)
        self.assertIn("domains/security.md", bid.questions[1].evidence_hints)
        self.assertEqual(bid.questions[0].response_format, "narrative")
        self.assertTrue(bid.questions[0].human_guidance_required)
        self.assertIn("30 June 2026", bid.deadlines[0])
        self.assertIn("Key personnel CVs", bid.deliverables)

    def test_deadlines_and_deliverables_work_with_simple_lines(self) -> None:
        text = "Submit by: 01 July 2026\n- Attachment A\n- Attachment B"
        self.assertEqual(extract_deadlines(text), ["01 July 2026"])
        self.assertEqual(extract_deliverables(text), [])


if __name__ == "__main__":
    unittest.main()
