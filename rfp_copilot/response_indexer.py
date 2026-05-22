from __future__ import annotations

import json
from pathlib import Path

from .models import BidRequest, Question


def build_response_index_payload(bid_request: BidRequest) -> dict:
    high_touch = [question for question in bid_request.questions if question.human_guidance_required]
    by_format: dict[str, int] = {}
    by_domain: dict[str, int] = {}
    for question in bid_request.questions:
        by_format[question.response_format] = by_format.get(question.response_format, 0) + 1
        for domain in question.related_domains or ["general"]:
            by_domain[domain] = by_domain.get(domain, 0) + 1
    return {
        "title": bid_request.title,
        "source_path": bid_request.source_path,
        "target_client_segments": bid_request.target_client_segments,
        "question_count": len(bid_request.questions),
        "high_touch_count": len(high_touch),
        "by_format": by_format,
        "by_domain": by_domain,
        "questions": [question.to_dict() for question in bid_request.questions],
    }


def render_response_index_markdown(bid_request: BidRequest) -> str:
    payload = build_response_index_payload(bid_request)
    lines = [
        f"# {bid_request.title or 'RFP Response Index'}",
        "",
        "## Summary",
        f"- Question count: {payload['question_count']}",
        f"- High-touch questions: {payload['high_touch_count']}",
        (
            f"- Target client segments: {', '.join(bid_request.target_client_segments)}"
            if bid_request.target_client_segments
            else "- Target client segments: not inferred"
        ),
        "",
        "## Response Format Mix",
    ]
    for key, value in sorted(payload["by_format"].items()):
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Domain Coverage"])
    for key, value in sorted(payload["by_domain"].items()):
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Indexed Questions", ""])
    for question in bid_request.questions:
        lines.extend(_render_indexed_question(question))
    return "\n".join(lines).strip() + "\n"


def render_response_index_json(bid_request: BidRequest) -> str:
    return json.dumps(build_response_index_payload(bid_request), indent=2)


def save_response_index(
    bid_request: BidRequest,
    output_path: str | Path,
    *,
    output_format: str = "markdown",
) -> Path:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    normalized = output_format.lower()
    if normalized == "json":
        content = render_response_index_json(bid_request)
    else:
        content = render_response_index_markdown(bid_request)
    target.write_text(content, encoding="utf-8")
    return target


def _render_indexed_question(question: Question) -> list[str]:
    lines = [
        f"### {question.question_id}",
        question.question_text,
        "",
        f"- Response format: {question.response_format}",
        f"- Question type: {question.question_type}",
        (
            f"- Client segments: {', '.join(question.related_client_segments)}"
            if question.related_client_segments
            else "- Client segments: not inferred"
        ),
        f"- Domains: {', '.join(question.related_domains) if question.related_domains else 'general'}",
        (
            f"- Evidence packs: {', '.join(question.evidence_hints)}"
            if question.evidence_hints
            else "- Evidence packs: none inferred"
        ),
        (
            f"- Human guidance: {'Yes - ' + '; '.join(question.human_guidance_reasons)}"
            if question.human_guidance_required
            else "- Human guidance: No"
        ),
        "",
    ]
    return lines
