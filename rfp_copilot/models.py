from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


def _deep_convert(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return {key: _deep_convert(inner) for key, inner in asdict(value).items()}
    if isinstance(value, dict):
        return {key: _deep_convert(inner) for key, inner in value.items()}
    if isinstance(value, list):
        return [_deep_convert(item) for item in value]
    return value


@dataclass
class Citation:
    document_id: str
    title: str
    source_url: str
    excerpt: str
    source_library: str = ""
    chunk_index: int = 0

    def to_dict(self) -> dict[str, Any]:
        return _deep_convert(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Citation":
        return cls(**payload)


@dataclass
class EvidenceRecord:
    document_id: str
    source_url: str
    source_library: str
    title: str
    owner: str
    effective_date: str
    review_date: str
    classification: str
    approved_for_bids: bool
    version: str
    text_chunks: list[str]
    domains: list[str] = field(default_factory=list)
    client_segments: list[str] = field(default_factory=list)
    source_collection: str = "truth_source"
    source_path: str = ""
    raw_path: str = ""
    markdown_path: str = ""
    document_type: str = ""
    specialist_agent: str = ""
    analysis_focus: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _deep_convert(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "EvidenceRecord":
        return cls(**payload)


@dataclass
class Question:
    question_id: str
    question_text: str
    section: str = ""
    question_type: str = "general"
    related_domains: list[str] = field(default_factory=list)
    related_client_segments: list[str] = field(default_factory=list)
    related_question_ids: list[str] = field(default_factory=list)
    evidence_hints: list[str] = field(default_factory=list)
    response_format: str = "narrative"
    human_guidance_required: bool = False
    human_guidance_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _deep_convert(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Question":
        return cls(**payload)


@dataclass
class RequirementItem:
    item_id: str
    item_type: str
    prompt_text: str
    original_text: str
    section: str = ""
    line_start: int = 0
    line_end: int = 0
    mandatory: bool = False
    response_format: str = "narrative"
    extraction_confidence: str = "medium"

    def to_dict(self) -> dict[str, Any]:
        return _deep_convert(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RequirementItem":
        return cls(**payload)


@dataclass
class BidRequest:
    source_path: str
    questions: list[Question]
    requirement_items: list[RequirementItem] = field(default_factory=list)
    deadlines: list[str] = field(default_factory=list)
    deliverables: list[str] = field(default_factory=list)
    title: str = ""
    target_client_segments: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _deep_convert(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "BidRequest":
        questions = [Question.from_dict(item) for item in payload.get("questions", [])]
        requirement_items = [
            RequirementItem.from_dict(item) for item in payload.get("requirement_items", [])
        ]
        return cls(
            source_path=payload.get("source_path", ""),
            questions=questions,
            requirement_items=requirement_items,
            deadlines=payload.get("deadlines", []),
            deliverables=payload.get("deliverables", []),
            title=payload.get("title", ""),
            target_client_segments=payload.get("target_client_segments", []),
        )


@dataclass
class AnswerContract:
    question_id: str
    question_text: str
    draft_answer: str
    citations: list[Citation]
    confidence: str
    gaps: list[str] = field(default_factory=list)
    followups: list[str] = field(default_factory=list)
    required_attachments: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _deep_convert(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AnswerContract":
        return cls(
            question_id=payload["question_id"],
            question_text=payload["question_text"],
            draft_answer=payload["draft_answer"],
            citations=[Citation.from_dict(item) for item in payload.get("citations", [])],
            confidence=payload["confidence"],
            gaps=payload.get("gaps", []),
            followups=payload.get("followups", []),
            required_attachments=payload.get("required_attachments", []),
        )


@dataclass
class SearchHit:
    record: EvidenceRecord
    score: float
    excerpt: str
    chunk_index: int

    def to_dict(self) -> dict[str, Any]:
        payload = _deep_convert(self)
        payload["score"] = round(self.score, 4)
        return payload


@dataclass
class SyncResult:
    synced: int = 0
    deleted: int = 0
    skipped: int = 0
    markdown_documents: int = 0
    markdown_packs: int = 0
    client_segment_packs: int = 0
    document_type_packs: int = 0
    errors: list[str] = field(default_factory=list)
    delta_link: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _deep_convert(self)


@dataclass
class MarkdownBuildResult:
    documents_written: int = 0
    domain_packs_written: int = 0
    client_segment_packs_written: int = 0
    document_type_packs_written: int = 0
    index_written: bool = False
    output_dir: str = ""
    files: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _deep_convert(self)


@dataclass
class RefreshCandidate:
    candidate_id: str
    title: str
    proposed_action: str
    source_document_id: str
    target_document_id: str = ""
    document_type: str = ""
    specialist_agent: str = ""
    client_segments: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    rationale: str = ""
    human_guidance_required: bool = True
    human_guidance_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _deep_convert(self)


@dataclass
class RefreshPlanResult:
    candidates: list[RefreshCandidate] = field(default_factory=list)
    report_path: str = ""
    manifest_path: str = ""
    promoted: int = 0

    def to_dict(self) -> dict[str, Any]:
        return _deep_convert(self)


@dataclass
class DocumentAnalysisAssignment:
    document_type: str
    specialist_agent: str
    purpose: str
    analysis_focus: list[str] = field(default_factory=list)
    document_refs: list[dict[str, Any]] = field(default_factory=list)
    trusted_count: int = 0
    staged_count: int = 0
    approved_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return _deep_convert(self)


@dataclass
class DocumentAnalysisPlan:
    assignments: list[DocumentAnalysisAssignment] = field(default_factory=list)
    report_path: str = ""
    manifest_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _deep_convert(self)


@dataclass
class SharePointFolderRole:
    role: str
    folder_path: str
    purpose: str
    client_segment: str = ""
    document_type: str = ""
    business_action: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _deep_convert(self)


@dataclass
class SharePointStructurePlan:
    folder_roles: list[SharePointFolderRole] = field(default_factory=list)
    report_path: str = ""
    manifest_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _deep_convert(self)
