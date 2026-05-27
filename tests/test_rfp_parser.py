from __future__ import annotations

import unittest

from rfp_copilot.rfp_parser import (
    extract_deadlines,
    extract_deliverables,
    extract_requirement_items,
    parse_rfp_text,
)


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
        self.assertEqual(len(bid.requirement_items), 5)
        self.assertEqual(bid.requirement_items[0].item_type, "deadline")
        self.assertEqual(bid.requirement_items[3].item_type, "deliverable")

    def test_deadlines_and_deliverables_work_with_simple_lines(self) -> None:
        text = "Submit by: 01 July 2026\n- Attachment A\n- Attachment B"
        self.assertEqual(extract_deadlines(text), ["01 July 2026"])
        self.assertEqual(extract_deliverables(text), [])

    def test_extract_requirement_items_captures_instructions_and_statements(self) -> None:
        text = """
        Response Requirements:
        1. Provide a transition plan covering cutover and rollback.
        - Explain your governance model for service delivery.
        The bidder must include ISO 27001 certification details.

        Deliverables:
        - Three customer case studies
        """

        items = extract_requirement_items(text)
        bid = parse_rfp_text(text, title="Structured Intake")

        self.assertEqual([item.item_type for item in items], ["instruction", "instruction", "statement", "deliverable"])
        self.assertEqual(items[0].prompt_text, "Provide a transition plan covering cutover and rollback.")
        self.assertEqual(items[1].prompt_text, "Explain your governance model for service delivery.")
        self.assertTrue(items[2].mandatory)
        self.assertEqual(items[3].response_format, "attachment")
        self.assertEqual(len(bid.questions), 3)
        self.assertEqual(bid.questions[0].question_id, "Q001")
        self.assertEqual(bid.questions[1].question_type, "technical")


if __name__ == "__main__":
    unittest.main()
