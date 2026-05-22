from __future__ import annotations

import re
from pathlib import Path

from .corpus import CorpusStore
from .models import BidRequest, EvidenceRecord, MarkdownBuildResult, Question
from .taxonomy import (
    DOMAIN_ORDER,
    detect_client_segments,
    detect_domains,
    summarize_chunk,
)


def build_document_markdown(record: EvidenceRecord) -> str:
    domains = record.domains or detect_domains(record.title, " ".join(record.text_chunks))
    chunk_map = _group_chunks_by_domain(record)
    lines = [
        "---",
        f"document_id: {record.document_id}",
        f"title: {record.title}",
        f"source_url: {record.source_url}",
        f"source_library: {record.source_library}",
        f"owner: {record.owner}",
        f"effective_date: {record.effective_date}",
        f"review_date: {record.review_date}",
        f"classification: {record.classification}",
        f"approved_for_bids: {'true' if record.approved_for_bids else 'false'}",
        f"version: {record.version}",
        f"domains: [{', '.join(domains)}]",
        f"client_segments: [{', '.join(record.client_segments)}]",
        f"source_collection: {record.source_collection}",
        f"source_path: {record.source_path}",
        "---",
        "",
        f"# {record.title}",
        "",
        "## Document Control",
        f"- Source library: {record.source_library}",
        f"- Source URL: {record.source_url}",
        f"- Owner: {record.owner or 'Unknown'}",
        f"- Effective date: {record.effective_date or 'Unknown'}",
        f"- Review date: {record.review_date or 'Unknown'}",
        f"- Classification: {record.classification or 'Unknown'}",
        f"- Approved for bids: {'Yes' if record.approved_for_bids else 'No'}",
        f"- Client segments: {', '.join(record.client_segments) if record.client_segments else 'general'}",
        f"- Source collection: {record.source_collection}",
        "",
        "## Coverage Domains",
    ]
    if domains:
        for domain in domains:
            lines.append(f"- {domain}")
    else:
        lines.append("- general")
    lines.extend(["", "## Executive Summary"])
    summary = _build_summary(record)
    if summary:
        lines.append(summary)
    else:
        lines.append("No extracted text summary is available.")
    lines.extend(["", "## Structured Evidence"])
    for domain in list(DOMAIN_ORDER) + ["general"]:
        notes = chunk_map.get(domain, [])
        if not notes:
            continue
        lines.append(f"### {domain.title()}")
        for note in notes:
            lines.append(f"- {note}")
        lines.append("")
    lines.append("## Source Chunks")
    for index, chunk in enumerate(record.text_chunks, start=1):
        lines.extend(
            [
                "",
                f"### Chunk {index}",
                chunk,
            ]
        )
    return "\n".join(lines).strip() + "\n"


def build_markdown_knowledge_base(
    corpus: CorpusStore,
    output_dir: str | Path | None = None,
) -> MarkdownBuildResult:
    base_dir = Path(output_dir) if output_dir else corpus.root / "markdown"
    documents_dir = base_dir / "documents"
    domains_dir = base_dir / "domains"
    segments_dir = base_dir / "client-segments"
    documents_dir.mkdir(parents=True, exist_ok=True)
    domains_dir.mkdir(parents=True, exist_ok=True)
    segments_dir.mkdir(parents=True, exist_ok=True)

    result = MarkdownBuildResult(output_dir=str(base_dir))
    records = corpus.list_records()
    domain_map: dict[str, list[EvidenceRecord]] = {}
    segment_domain_map: dict[str, dict[str, list[EvidenceRecord]]] = {}

    for record in records:
        if not record.domains:
            record.domains = detect_domains(record.title, " ".join(record.text_chunks))
        if not record.client_segments:
            record.client_segments = detect_client_segments(
                record.source_path,
                record.title,
                " ".join(record.text_chunks),
            )
        filename = f"{record.document_id}-{slugify(record.title)}.md"
        document_path = documents_dir / filename
        document_path.write_text(build_document_markdown(record), encoding="utf-8")
        record.markdown_path = str(document_path)
        corpus.upsert(record)
        result.documents_written += 1
        result.files.append(str(document_path))
        for domain in record.domains or ["general"]:
            domain_map.setdefault(domain, []).append(record)
            for segment in record.client_segments or ["general"]:
                segment_domain_map.setdefault(segment, {}).setdefault(domain, []).append(record)

    for domain, records_for_domain in sorted(domain_map.items()):
        pack_path = domains_dir / f"{domain}.md"
        pack_path.write_text(build_domain_pack_markdown(domain, records_for_domain), encoding="utf-8")
        result.domain_packs_written += 1
        result.files.append(str(pack_path))

    for segment, domain_groups in sorted(segment_domain_map.items()):
        segment_dir = segments_dir / segment
        segment_dir.mkdir(parents=True, exist_ok=True)
        index_path = segment_dir / "index.md"
        index_path.write_text(build_client_segment_index(segment, domain_groups), encoding="utf-8")
        result.client_segment_packs_written += 1
        result.files.append(str(index_path))
        for domain, records_for_domain in sorted(domain_groups.items()):
            pack_path = segment_dir / f"{domain}.md"
            pack_path.write_text(
                build_client_segment_domain_pack(segment, domain, records_for_domain),
                encoding="utf-8",
            )
            result.client_segment_packs_written += 1
            result.files.append(str(pack_path))

    index_path = base_dir / "index.md"
    index_path.write_text(build_markdown_index(domain_map, segment_domain_map, records), encoding="utf-8")
    result.index_written = True
    result.files.append(str(index_path))
    return result


def build_domain_pack_markdown(domain: str, records: list[EvidenceRecord]) -> str:
    title = f"{domain.title()} Knowledge Pack"
    lines = [
        f"# {title}",
        "",
        "## Purpose",
        (
            "This pack aggregates normalized markdown evidence for the domain so agents can "
            "retrieve structured facts without scanning every source document."
        ),
        "",
        "## Source Documents",
        "",
    ]
    for record in sorted(records, key=lambda item: item.title.lower()):
        lines.extend(
            [
                f"### {record.title}",
                f"- Document ID: `{record.document_id}`",
                f"- Source URL: {record.source_url}",
                f"- Owner: {record.owner or 'Unknown'}",
                f"- Approved for bids: {'Yes' if record.approved_for_bids else 'No'}",
                f"- Review date: {record.review_date or 'Unknown'}",
                "- Relevant notes:",
            ]
        )
        relevant_chunks = _group_chunks_by_domain(record).get(domain, [])
        for note in relevant_chunks[:5] or [_build_summary(record)]:
            if note:
                lines.append(f"  - {note}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def build_markdown_index(
    domain_map: dict[str, list[EvidenceRecord]],
    segment_domain_map: dict[str, dict[str, list[EvidenceRecord]]],
    records: list[EvidenceRecord],
) -> str:
    lines = [
        "# Knowledge Base Index",
        "",
        "## Domain Packs",
        "",
    ]
    for domain in sorted(domain_map):
        lines.append(f"- [{domain.title()}](domains/{domain}.md)")
    lines.extend(["", "## Client Segment Packs", ""])
    for segment in sorted(segment_domain_map):
        lines.append(f"- [{segment.title()}](client-segments/{segment}/index.md)")
    lines.extend(["", "## Normalized Documents", ""])
    for record in sorted(records, key=lambda item: item.title.lower()):
        filename = f"{record.document_id}-{slugify(record.title)}.md"
        domain_label = ", ".join(record.domains or ["general"])
        segment_label = ", ".join(record.client_segments or ["general"])
        lines.append(f"- [{record.title}](documents/{filename}) - {segment_label} / {domain_label}")
    return "\n".join(lines).strip() + "\n"


def render_rfp_markdown(bid_request: BidRequest) -> str:
    lines = [
        "---",
        f"title: {bid_request.title}",
        f"source_path: {bid_request.source_path}",
        f"question_count: {len(bid_request.questions)}",
        f"deadlines: [{', '.join(bid_request.deadlines)}]",
        f"deliverables: [{', '.join(bid_request.deliverables)}]",
        f"target_client_segments: [{', '.join(bid_request.target_client_segments)}]",
        "---",
        "",
        f"# {bid_request.title or 'RFP Intake'}",
        "",
        "## Submission Context",
    ]
    if bid_request.deadlines:
        for deadline in bid_request.deadlines:
            lines.append(f"- Deadline: {deadline}")
    else:
        lines.append("- Deadline: not detected")
    if bid_request.deliverables:
        lines.append("- Deliverables:")
        for deliverable in bid_request.deliverables:
            lines.append(f"  - {deliverable}")
    else:
        lines.append("- Deliverables: not detected")
    lines.append(
        f"- Target client segments: {', '.join(bid_request.target_client_segments) if bid_request.target_client_segments else 'not inferred'}"
    )
    lines.extend(["", "## Question Map", ""])
    for question in bid_request.questions:
        lines.extend(_render_question_markdown(question))
    return "\n".join(lines).strip() + "\n"


def build_client_segment_index(
    segment: str,
    domain_groups: dict[str, list[EvidenceRecord]],
) -> str:
    lines = [
        f"# {segment.title()} Client Pack",
        "",
        "## Domain Packs",
        "",
    ]
    for domain in sorted(domain_groups):
        lines.append(f"- [{domain.title()}]({domain}.md)")
    return "\n".join(lines).strip() + "\n"


def build_client_segment_domain_pack(
    segment: str,
    domain: str,
    records: list[EvidenceRecord],
) -> str:
    lines = [
        f"# {segment.title()} / {domain.title()}",
        "",
        "## Purpose",
        "This pack contains segment-specific normalized evidence for retrieval and drafting.",
        "",
    ]
    for record in sorted(records, key=lambda item: item.title.lower()):
        lines.extend(
            [
                f"## {record.title}",
                f"- Source URL: {record.source_url}",
                f"- Owner: {record.owner or 'Unknown'}",
                f"- Approved for bids: {'Yes' if record.approved_for_bids else 'No'}",
                "- Relevant notes:",
            ]
        )
        notes = _group_chunks_by_domain(record).get(domain, [])
        for note in notes[:5] or [_build_summary(record)]:
            if note:
                lines.append(f"  - {note}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def save_rfp_markdown(
    bid_request: BidRequest,
    output_path: str | Path,
) -> Path:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_rfp_markdown(bid_request), encoding="utf-8")
    return target


def _build_summary(record: EvidenceRecord) -> str:
    summaries = [summarize_chunk(chunk) for chunk in record.text_chunks[:2] if summarize_chunk(chunk)]
    return " ".join(summaries).strip()


def _group_chunks_by_domain(record: EvidenceRecord) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for chunk in record.text_chunks:
        summary = summarize_chunk(chunk)
        if not summary:
            continue
        domains = detect_domains(record.title, chunk) or ["general"]
        for domain in domains:
            grouped.setdefault(domain, []).append(summary)
    return grouped


def _render_question_markdown(question: Question) -> list[str]:
    lines = [
        f"### {question.question_id}",
        question.question_text,
        "",
        f"- Question type: {question.question_type}",
        (
            f"- Related client segments: {', '.join(question.related_client_segments)}"
            if question.related_client_segments
            else "- Related client segments: not inferred"
        ),
        f"- Related domains: {', '.join(question.related_domains) if question.related_domains else 'general'}",
        f"- Expected response format: {question.response_format}",
        (
            f"- Related questions: {', '.join(question.related_question_ids)}"
            if question.related_question_ids
            else "- Related questions: none detected"
        ),
        (
            f"- Suggested evidence packs: {', '.join(question.evidence_hints)}"
            if question.evidence_hints
            else "- Suggested evidence packs: none inferred"
        ),
        (
            f"- Human guidance required: {'Yes - ' + '; '.join(question.human_guidance_reasons)}"
            if question.human_guidance_required
            else "- Human guidance required: No"
        ),
        "",
    ]
    return lines


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "document"
