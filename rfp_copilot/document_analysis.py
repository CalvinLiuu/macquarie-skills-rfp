from __future__ import annotations

import json
from pathlib import Path

from .corpus import CorpusStore
from .models import DocumentAnalysisAssignment, DocumentAnalysisPlan, EvidenceRecord
from .taxonomy import (
    analysis_focus_for_document_type,
    detect_document_type,
    document_type_label,
    document_type_purpose,
    specialist_agent_for_document_type,
)


def build_document_analysis_plan(
    corpus: CorpusStore,
    output_dir: str | Path = "data/outputs",
) -> DocumentAnalysisPlan:
    assignments_by_type: dict[str, DocumentAnalysisAssignment] = {}
    records = corpus.list_records()

    for record in records:
        hydrated = _hydrate_record_routing(record)
        assignment = assignments_by_type.setdefault(
            hydrated.document_type,
            DocumentAnalysisAssignment(
                document_type=hydrated.document_type,
                specialist_agent=hydrated.specialist_agent,
                purpose=document_type_purpose(hydrated.document_type),
                analysis_focus=list(hydrated.analysis_focus),
            ),
        )
        assignment.document_refs.append(
            {
                "document_id": hydrated.document_id,
                "title": hydrated.title,
                "source_collection": hydrated.source_collection,
                "approved_for_bids": hydrated.approved_for_bids,
                "source_path": hydrated.source_path,
            }
        )
        if hydrated.source_collection == "update_inbox":
            assignment.staged_count += 1
        else:
            assignment.trusted_count += 1
        if hydrated.approved_for_bids:
            assignment.approved_count += 1

    assignments = sorted(
        assignments_by_type.values(),
        key=lambda item: (item.document_type, item.specialist_agent),
    )
    for assignment in assignments:
        assignment.document_refs.sort(
            key=lambda ref: (
                ref.get("source_collection", ""),
                ref.get("title", "").lower(),
            )
        )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    manifest_path = output_path / "document-analysis-plan.json"
    report_path = output_path / "document-analysis-plan.md"
    manifest_path.write_text(
        json.dumps([assignment.to_dict() for assignment in assignments], indent=2),
        encoding="utf-8",
    )
    report_path.write_text(render_document_analysis_plan_markdown(assignments), encoding="utf-8")
    return DocumentAnalysisPlan(
        assignments=assignments,
        report_path=str(report_path),
        manifest_path=str(manifest_path),
    )


def render_document_analysis_plan_markdown(
    assignments: list[DocumentAnalysisAssignment],
) -> str:
    total_documents = sum(len(item.document_refs) for item in assignments)
    lines = [
        "# Document Analysis Plan",
        "",
        "## Summary",
        f"- Specialist assignments: {len(assignments)}",
        f"- Document count: {total_documents}",
        f"- Trusted documents: {sum(item.trusted_count for item in assignments)}",
        f"- Staged documents: {sum(item.staged_count for item in assignments)}",
        "",
        "## Specialist Routing",
        "",
    ]
    for assignment in assignments:
        lines.extend(
            [
                f"### {document_type_label(assignment.document_type)}",
                f"- Specialist agent: `{assignment.specialist_agent}`",
                f"- Purpose: {assignment.purpose}",
                f"- Document count: {len(assignment.document_refs)}",
                f"- Trusted documents: {assignment.trusted_count}",
                f"- Staged documents: {assignment.staged_count}",
                f"- Approved for bids: {assignment.approved_count}",
                "- Analysis focus:",
            ]
        )
        for focus in assignment.analysis_focus:
            lines.append(f"  - {focus}")
        lines.append("- Documents:")
        for ref in assignment.document_refs:
            approval = "approved" if ref.get("approved_for_bids") else "review required"
            location = ref.get("source_path") or ref.get("source_collection", "")
            lines.append(
                f"  - `{ref['document_id']}` {ref['title']} "
                f"({ref['source_collection']}, {approval}) [{location}]"
            )
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _hydrate_record_routing(record: EvidenceRecord) -> EvidenceRecord:
    if record.document_type and record.specialist_agent and record.analysis_focus:
        return record
    document_type = record.document_type or detect_document_type(
        record.source_path,
        record.title,
        " ".join(record.text_chunks),
    )
    record.document_type = document_type
    record.specialist_agent = record.specialist_agent or specialist_agent_for_document_type(document_type)
    record.analysis_focus = record.analysis_focus or analysis_focus_for_document_type(document_type)
    return record
