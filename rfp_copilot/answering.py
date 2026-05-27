from __future__ import annotations

import json
from pathlib import Path

from .corpus import CorpusStore
from .models import AnswerContract, BidRequest, Citation, Question, SearchHit


def build_answer_contract(question: Question, hits: list[SearchHit]) -> AnswerContract:
    citations = [
        Citation(
            document_id=hit.record.document_id,
            title=hit.record.title,
            source_url=hit.record.source_url,
            excerpt=hit.excerpt[:400],
            source_library=hit.record.source_library,
            chunk_index=hit.chunk_index,
        )
        for hit in hits[:3]
    ]
    confidence = _derive_confidence(hits)
    gaps: list[str] = []
    followups: list[str] = ["Human reviewer should confirm wording before submission."]
    required_attachments = _infer_required_attachments(question.question_text)
    if question.human_guidance_required:
        followups.extend(question.human_guidance_reasons)
    if not hits:
        draft_answer = (
            "No approved evidence was found in the mirrored corpus for this question. "
            "Escalate for human research before drafting a final response."
        )
        gaps.append("No approved evidence found.")
        followups.append("Search SharePoint live or request a new approved source.")
    else:
        lead = hits[0].excerpt.strip().rstrip(".")
        draft_answer = (
            f"Based on approved source material, {lead}. "
            "Use the cited documents to convert this into final customer-ready prose."
        )
        if confidence != "high":
            gaps.append("Evidence exists but needs human strengthening or reconciliation.")
        if len(hits) == 1:
            followups.append("Locate a second corroborating source if the response is high risk.")
    return AnswerContract(
        question_id=question.question_id,
        question_text=question.question_text,
        draft_answer=draft_answer,
        citations=citations,
        confidence=confidence,
        gaps=gaps,
        followups=followups,
        required_attachments=required_attachments,
    )


def draft_answers_for_bid(
    bid_request: BidRequest,
    corpus: CorpusStore,
    evidence_limit: int = 3,
) -> list[AnswerContract]:
    answers: list[AnswerContract] = []
    for question in bid_request.questions:
        hits = corpus.search(
            question.question_text,
            limit=evidence_limit,
            approved_only=True,
            client_segments=question.related_client_segments,
            domains=question.related_domains,
        )
        answers.append(build_answer_contract(question, hits))
    return answers


def package_answers(
    answers: list[AnswerContract],
    output_format: str = "markdown",
) -> str:
    normalized = output_format.lower()
    if normalized == "json":
        return json.dumps([answer.to_dict() for answer in answers], indent=2)
    if normalized == "markdown":
        return _render_markdown(answers)
    if normalized == "csv":
        rows = [
            "question_id,question_text,confidence,draft_answer,citation_count",
        ]
        for answer in answers:
            escaped_question = answer.question_text.replace('"', '""')
            escaped_draft = answer.draft_answer.replace('"', '""')
            rows.append(
                f'{answer.question_id},"{escaped_question}",{answer.confidence},"{escaped_draft}",{len(answer.citations)}'
            )
        return "\n".join(rows)
    raise ValueError(f"Unsupported output format: {output_format}")


def save_packaged_answers(
    answers: list[AnswerContract],
    path: str | Path,
    output_format: str = "markdown",
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(package_answers(answers, output_format=output_format), encoding="utf-8")
    return target


def _derive_confidence(hits: list[SearchHit]) -> str:
    if not hits:
        return "low"
    top_score = hits[0].score
    if len(hits) >= 2 and top_score >= 0.9:
        return "high"
    if top_score >= 0.55:
        return "medium"
    return "low"


def _infer_required_attachments(text: str) -> list[str]:
    lower = text.lower()
    attachments: list[str] = []
    if "cv" in lower or "personnel" in lower or "staff" in lower:
        attachments.append("key-personnel-cvs")
    if "case stud" in lower:
        attachments.append("relevant-case-studies")
    if "certificate" in lower or "certification" in lower:
        attachments.append("security-certifications")
    return attachments


def _render_markdown(answers: list[AnswerContract]) -> str:
    lines = ["# RFP Draft Answers", ""]
    for answer in answers:
        lines.append(f"## {answer.question_id}: {answer.question_text}")
        lines.append("")
        lines.append(f"**Confidence:** {answer.confidence}")
        lines.append("")
        lines.append(answer.draft_answer)
        lines.append("")
        if answer.citations:
            lines.append("**Citations**")
            for citation in answer.citations:
                lines.append(
                    f"- `{citation.title}` ({citation.source_library}) - {citation.source_url}"
                )
            lines.append("")
        if answer.gaps:
            lines.append("**Gaps**")
            for gap in answer.gaps:
                lines.append(f"- {gap}")
            lines.append("")
        if answer.followups:
            lines.append("**Follow-ups**")
            for followup in answer.followups:
                lines.append(f"- {followup}")
            lines.append("")
        if answer.required_attachments:
            lines.append("**Required Attachments**")
            for attachment in answer.required_attachments:
                lines.append(f"- {attachment}")
            lines.append("")
    return "\n".join(lines).strip() + "\n"
